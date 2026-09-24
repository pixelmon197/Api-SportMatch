from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import (
    Reporte,
    TicketSoporte,
    TicketMensaje,
    AuditoriaLog,
    ESTADOS_REPORTE,
    ESTADOS_TICKET,
    PRIORIDADES_TICKET,
)
from utils.auth import admin_required, get_usuario_actual
from utils.auditoria import registrar_auditoria

soporte_bp = Blueprint("soporte", __name__, url_prefix="/api")


# ============ REPORTES (moderación de contenido / usuarios) ============

@soporte_bp.route("/reportes", methods=["POST"])
@jwt_required()
def crear_reporte():
    """Cualquier usuario reporta contenido o a otro usuario.
    tipo_entidad/entidad_id son genéricos: apuntan a la tabla que sea
    (ej. tipo_entidad="usuario", entidad_id=42; o "evento", "ruta", etc.)."""
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}

    faltantes = [
        c for c in ("tipo_entidad", "entidad_id", "motivo") if not data.get(c)
    ]
    if faltantes:
        return jsonify({"error": f"Campos requeridos faltantes: {', '.join(faltantes)}"}), 400

    reporte = Reporte(
        reportante_id=usuario.id,
        tipo_entidad=data["tipo_entidad"],
        entidad_id=data["entidad_id"],
        motivo=data["motivo"],
        descripcion=data.get("descripcion"),
    )
    db.session.add(reporte)
    db.session.commit()
    return jsonify(reporte.to_dict()), 201


@soporte_bp.route("/reportes/me", methods=["GET"])
@jwt_required()
def mis_reportes():
    usuario = get_usuario_actual()
    reportes = Reporte.query.filter_by(reportante_id=usuario.id).order_by(Reporte.creado_en.desc()).all()
    return jsonify([r.to_dict() for r in reportes]), 200


@soporte_bp.route("/reportes", methods=["GET"])
@admin_required
def listar_reportes():
    """Bandeja de moderación. Filtros: estado (default 'pendiente'), tipo_entidad."""
    query = Reporte.query
    estado = request.args.get("estado", "pendiente")
    if estado != "todos":
        query = query.filter_by(estado=estado)
    if tipo_entidad := request.args.get("tipo_entidad"):
        query = query.filter_by(tipo_entidad=tipo_entidad)
    reportes = query.order_by(Reporte.creado_en).all()
    return jsonify([r.to_dict() for r in reportes]), 200


@soporte_bp.route("/reportes/<int:reporte_id>", methods=["GET"])
@jwt_required()
def obtener_reporte(reporte_id):
    usuario = get_usuario_actual()
    reporte = Reporte.query.get_or_404(reporte_id)
    if usuario.rol != "admin" and reporte.reportante_id != usuario.id:
        return jsonify({"error": "No tienes acceso a este reporte"}), 403
    return jsonify(reporte.to_dict()), 200


@soporte_bp.route("/reportes/<int:reporte_id>", methods=["PUT"])
@admin_required
def moderar_reporte(reporte_id):
    """El admin asigna, resuelve o desestima un reporte; queda en la auditoría."""
    reporte = Reporte.query.get_or_404(reporte_id)
    data = request.get_json(force=True, silent=True) or {}
    admin = get_usuario_actual()
    estado_anterior = reporte.estado

    if "estado" in data:
        if data["estado"] not in ESTADOS_REPORTE:
            return jsonify({"error": f"estado debe ser uno de: {', '.join(ESTADOS_REPORTE)}"}), 400
        reporte.estado = data["estado"]
        if data["estado"] in ("resuelto", "desestimado"):
            reporte.resuelto_en = datetime.now(timezone.utc)

    for campo in ("asignado_a", "accion_tomada", "notas_moderador"):
        if campo in data:
            setattr(reporte, campo, data[campo])

    db.session.commit()

    if "estado" in data and data["estado"] != estado_anterior:
        registrar_auditoria(
            usuario_id=admin.id,
            accion="reporte.cambiar_estado",
            tipo_entidad="reporte",
            entidad_id=reporte.id,
            antes={"estado": estado_anterior},
            despues={"estado": reporte.estado, "accion_tomada": reporte.accion_tomada},
        )

    return jsonify(reporte.to_dict()), 200


# ============ TICKETS DE SOPORTE ============

@soporte_bp.route("/tickets", methods=["POST"])
@jwt_required()
def crear_ticket():
    """El usuario abre un ticket con su primer mensaje."""
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}

    if not data.get("asunto") or not data.get("mensaje"):
        return jsonify({"error": "asunto y mensaje son obligatorios"}), 400
    if data.get("prioridad") and data["prioridad"] not in PRIORIDADES_TICKET:
        return jsonify({"error": f"prioridad debe ser una de: {', '.join(PRIORIDADES_TICKET)}"}), 400

    ticket = TicketSoporte(
        usuario_id=usuario.id,
        categoria=data.get("categoria"),
        prioridad=data.get("prioridad", "media"),
        asunto=data["asunto"],
    )
    db.session.add(ticket)
    db.session.flush()
    db.session.add(TicketMensaje(ticket_id=ticket.id, autor_id=usuario.id, mensaje=data["mensaje"]))
    db.session.commit()
    return jsonify(ticket.to_dict(con_mensajes=True)), 201


@soporte_bp.route("/tickets/me", methods=["GET"])
@jwt_required()
def mis_tickets():
    usuario = get_usuario_actual()
    tickets = TicketSoporte.query.filter_by(usuario_id=usuario.id).order_by(TicketSoporte.creado_en.desc()).all()
    return jsonify([t.to_dict() for t in tickets]), 200


@soporte_bp.route("/tickets", methods=["GET"])
@admin_required
def listar_tickets():
    """Bandeja de soporte. Filtros: estado, prioridad, asignado_a."""
    query = TicketSoporte.query
    if estado := request.args.get("estado"):
        query = query.filter_by(estado=estado)
    if prioridad := request.args.get("prioridad"):
        query = query.filter_by(prioridad=prioridad)
    if asignado_a := request.args.get("asignado_a", type=int):
        query = query.filter_by(asignado_a=asignado_a)
    tickets = query.order_by(TicketSoporte.creado_en).all()
    return jsonify([t.to_dict() for t in tickets]), 200


@soporte_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@jwt_required()
def obtener_ticket(ticket_id):
    usuario = get_usuario_actual()
    ticket = TicketSoporte.query.get_or_404(ticket_id)
    if usuario.rol != "admin" and ticket.usuario_id != usuario.id:
        return jsonify({"error": "No tienes acceso a este ticket"}), 403
    return jsonify(ticket.to_dict(con_mensajes=True, incluir_internos=(usuario.rol == "admin"))), 200


@soporte_bp.route("/tickets/<int:ticket_id>/mensajes", methods=["POST"])
@jwt_required()
def agregar_mensaje(ticket_id):
    usuario = get_usuario_actual()
    ticket = TicketSoporte.query.get_or_404(ticket_id)
    if usuario.rol != "admin" and ticket.usuario_id != usuario.id:
        return jsonify({"error": "No tienes acceso a este ticket"}), 403
    if ticket.estado == "cerrado":
        return jsonify({"error": "Este ticket ya está cerrado"}), 400

    data = request.get_json(force=True, silent=True) or {}
    if not data.get("mensaje"):
        return jsonify({"error": "mensaje es obligatorio"}), 400

    es_interno = bool(data.get("es_interno", False)) and usuario.rol == "admin"
    mensaje = TicketMensaje(ticket_id=ticket_id, autor_id=usuario.id, mensaje=data["mensaje"], es_interno=es_interno)
    db.session.add(mensaje)

    # Si responde el usuario, el ticket vuelve a "abierto"; si responde soporte, pasa a "en_progreso".
    if not es_interno:
        ticket.estado = "en_progreso" if usuario.rol == "admin" else "abierto"

    db.session.commit()
    return jsonify(mensaje.to_dict()), 201


@soporte_bp.route("/tickets/<int:ticket_id>", methods=["PUT"])
@admin_required
def actualizar_ticket(ticket_id):
    """El admin asigna, cambia prioridad/estado o cierra el ticket."""
    ticket = TicketSoporte.query.get_or_404(ticket_id)
    data = request.get_json(force=True, silent=True) or {}

    if "estado" in data:
        if data["estado"] not in ESTADOS_TICKET:
            return jsonify({"error": f"estado debe ser uno de: {', '.join(ESTADOS_TICKET)}"}), 400
        ticket.estado = data["estado"]
        if data["estado"] == "cerrado":
            ticket.cerrado_en = datetime.now(timezone.utc)

    if "prioridad" in data:
        if data["prioridad"] not in PRIORIDADES_TICKET:
            return jsonify({"error": f"prioridad debe ser una de: {', '.join(PRIORIDADES_TICKET)}"}), 400
        ticket.prioridad = data["prioridad"]

    for campo in ("asignado_a", "categoria"):
        if campo in data:
            setattr(ticket, campo, data[campo])

    db.session.commit()
    return jsonify(ticket.to_dict()), 200


# ============ AUDITORÍA (solo lectura, solo admin) ============

@soporte_bp.route("/admin/auditoria", methods=["GET"])
@admin_required
def listar_auditoria():
    """Filtros: tipo_entidad, entidad_id, usuario_id. Paginado."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)

    query = AuditoriaLog.query
    if tipo_entidad := request.args.get("tipo_entidad"):
        query = query.filter_by(tipo_entidad=tipo_entidad)
    if entidad_id := request.args.get("entidad_id", type=int):
        query = query.filter_by(entidad_id=entidad_id)
    if usuario_id := request.args.get("usuario_id", type=int):
        query = query.filter_by(usuario_id=usuario_id)

    paginado = query.order_by(AuditoriaLog.registrada_en.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify(
        {
            "registros": [r.to_dict() for r in paginado.items],
            "total": paginado.total,
            "page": page,
            "per_page": per_page,
            "paginas": paginado.pages,
        }
    ), 200

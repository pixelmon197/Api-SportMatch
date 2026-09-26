from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import (
    Organizador,
    OrganizadorMiembro,
    SolicitudValidacion,
    DocumentoValidacion,
    CuentaCobro,
    ROLES_MIEMBRO_ORG,
    TIPOS_DOCUMENTO_VALIDACION,
)
from utils.auth import admin_required, get_usuario_actual, puede_gestionar_organizador
from utils.auditoria import registrar_auditoria

organizadores_bp = Blueprint("organizadores", __name__, url_prefix="/api/organizadores")


def _requiere_gestion_organizador(organizador_id):
    usuario = get_usuario_actual()
    if not puede_gestionar_organizador(usuario, organizador_id):
        return jsonify({"error": "No perteneces a ese organizador"}), 403
    return None


# ============ CONSULTA ============

@organizadores_bp.route("", methods=["GET"])
def listar_organizadores():
    """Público: solo organizadores aprobados. ?estado_validacion= para admin."""
    query = Organizador.query.filter(Organizador.eliminado_en.is_(None))
    estado = request.args.get("estado_validacion")
    query = query.filter_by(estado_validacion=estado) if estado else query.filter_by(estado_validacion="aprobada")
    return jsonify([o.to_dict() for o in query.order_by(Organizador.id).all()]), 200


@organizadores_bp.route("/<int:organizador_id>", methods=["GET"])
def obtener_organizador(organizador_id):
    organizador = Organizador.query.filter_by(id=organizador_id).filter(
        Organizador.eliminado_en.is_(None)
    ).first_or_404()
    return jsonify(organizador.to_dict(detalle=True)), 200


# ============ REGISTRARSE COMO ORGANIZADOR ============

@organizadores_bp.route("", methods=["POST"])
@jwt_required()
def crear_organizador():
    """Cualquier usuario autenticado puede crear su perfil de organizador
    (queda en 'sin_solicitud' hasta que envíe una solicitud de validación y
    un admin la apruebe). Un usuario solo puede tener un organizador propio."""
    usuario = get_usuario_actual()
    if Organizador.query.filter_by(usuario_id=usuario.id).first():
        return jsonify({"error": "Ya tienes un perfil de organizador"}), 409

    data = request.get_json(force=True, silent=True) or {}
    if not data.get("nombre_comercial"):
        return jsonify({"error": "nombre_comercial es obligatorio"}), 400

    organizador = Organizador(
        usuario_id=usuario.id,
        nombre_comercial=data["nombre_comercial"],
        descripcion=data.get("descripcion"),
        correo_contacto=data.get("correo_contacto"),
        telefono_contacto=data.get("telefono_contacto"),
        ciudad_id=data.get("ciudad_id"),
        estado_validacion="sin_solicitud",
    )
    db.session.add(organizador)
    db.session.flush()

    db.session.add(OrganizadorMiembro(organizador_id=organizador.id, usuario_id=usuario.id, rol="propietario"))
    db.session.commit()
    return jsonify(organizador.to_dict(detalle=True)), 201


@organizadores_bp.route("/<int:organizador_id>", methods=["PUT"])
@jwt_required()
def actualizar_organizador(organizador_id):
    if error := _requiere_gestion_organizador(organizador_id):
        return error
    organizador = Organizador.query.get_or_404(organizador_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("nombre_comercial", "descripcion", "correo_contacto", "telefono_contacto", "ciudad_id"):
        if campo in data:
            setattr(organizador, campo, data[campo])
    db.session.commit()
    return jsonify(organizador.to_dict(detalle=True)), 200


@organizadores_bp.route("/<int:organizador_id>", methods=["DELETE"])
@jwt_required()
def eliminar_organizador(organizador_id):
    if error := _requiere_gestion_organizador(organizador_id):
        return error
    organizador = Organizador.query.get_or_404(organizador_id)
    organizador.eliminado_en = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(organizador.to_dict()), 200


# ============ MIEMBROS DEL EQUIPO ============

@organizadores_bp.route("/<int:organizador_id>/miembros", methods=["POST"])
@jwt_required()
def agregar_miembro(organizador_id):
    if error := _requiere_gestion_organizador(organizador_id):
        return error
    Organizador.query.get_or_404(organizador_id)
    data = request.get_json(force=True, silent=True) or {}
    usuario_id = data.get("usuario_id")
    rol = data.get("rol", "colaborador")

    if not usuario_id:
        return jsonify({"error": "usuario_id es obligatorio"}), 400
    if rol not in ROLES_MIEMBRO_ORG:
        return jsonify({"error": f"rol debe ser uno de: {', '.join(ROLES_MIEMBRO_ORG)}"}), 400
    if OrganizadorMiembro.query.get((organizador_id, usuario_id)):
        return jsonify({"error": "Ese usuario ya es miembro de este organizador"}), 409

    miembro = OrganizadorMiembro(organizador_id=organizador_id, usuario_id=usuario_id, rol=rol)
    db.session.add(miembro)
    db.session.commit()
    return jsonify(miembro.to_dict()), 201


@organizadores_bp.route("/<int:organizador_id>/miembros/<int:usuario_id>", methods=["DELETE"])
@jwt_required()
def quitar_miembro(organizador_id, usuario_id):
    if error := _requiere_gestion_organizador(organizador_id):
        return error
    miembro = OrganizadorMiembro.query.get_or_404((organizador_id, usuario_id))
    if miembro.rol == "propietario":
        return jsonify({"error": "No puedes quitar al propietario del organizador"}), 400
    db.session.delete(miembro)
    db.session.commit()
    return "", 204


# ============ CUENTAS DE COBRO ============

@organizadores_bp.route("/<int:organizador_id>/cuentas-cobro", methods=["GET"])
@jwt_required()
def listar_cuentas_cobro(organizador_id):
    if error := _requiere_gestion_organizador(organizador_id):
        return error
    cuentas = CuentaCobro.query.filter_by(organizador_id=organizador_id).filter(
        CuentaCobro.eliminado_en.is_(None)
    ).all()
    return jsonify([c.to_dict() for c in cuentas]), 200


@organizadores_bp.route("/<int:organizador_id>/cuentas-cobro", methods=["POST"])
@jwt_required()
def agregar_cuenta_cobro(organizador_id):
    if error := _requiere_gestion_organizador(organizador_id):
        return error
    Organizador.query.get_or_404(organizador_id)
    data = request.get_json(force=True, silent=True) or {}
    faltantes = [c for c in ("banco", "titular", "clabe") if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Campos requeridos faltantes: {', '.join(faltantes)}"}), 400

    if data.get("es_principal"):
        CuentaCobro.query.filter_by(organizador_id=organizador_id, es_principal=True).update(
            {"es_principal": False}
        )

    cuenta = CuentaCobro(
        organizador_id=organizador_id,
        banco=data["banco"],
        titular=data["titular"],
        clabe=data["clabe"],
        es_principal=data.get("es_principal", False),
    )
    db.session.add(cuenta)
    db.session.commit()
    return jsonify(cuenta.to_dict()), 201


@organizadores_bp.route("/cuentas-cobro/<int:cuenta_id>/verificar", methods=["PUT"])
@admin_required
def verificar_cuenta_cobro(cuenta_id):
    """Solo un admin verifica que la cuenta bancaria es legítima."""
    cuenta = CuentaCobro.query.get_or_404(cuenta_id)
    cuenta.verificada = True
    db.session.commit()
    return jsonify(cuenta.to_dict()), 200


@organizadores_bp.route("/cuentas-cobro/<int:cuenta_id>", methods=["DELETE"])
@jwt_required()
def eliminar_cuenta_cobro(cuenta_id):
    cuenta = CuentaCobro.query.get_or_404(cuenta_id)
    if error := _requiere_gestion_organizador(cuenta.organizador_id):
        return error
    cuenta.eliminado_en = datetime.now(timezone.utc)
    db.session.commit()
    return "", 204


# ============ SOLICITUDES DE VALIDACIÓN ============

@organizadores_bp.route("/<int:organizador_id>/solicitudes", methods=["POST"])
@jwt_required()
def enviar_solicitud(organizador_id):
    """El propietario/administrador manda a revisión su organizador,
    opcionalmente adjuntando documentos de una vez."""
    if error := _requiere_gestion_organizador(organizador_id):
        return error
    organizador = Organizador.query.get_or_404(organizador_id)

    if SolicitudValidacion.query.filter_by(organizador_id=organizador_id, estado="pendiente").first():
        return jsonify({"error": "Ya tienes una solicitud pendiente de revisión"}), 409

    data = request.get_json(force=True, silent=True) or {}
    solicitud = SolicitudValidacion(organizador_id=organizador_id, estado="pendiente")
    db.session.add(solicitud)
    db.session.flush()

    for doc in data.get("documentos", []):
        tipo_documento = doc.get("tipo_documento")
        archivo_id = doc.get("archivo_id")
        if not tipo_documento or not archivo_id:
            continue
        if tipo_documento not in TIPOS_DOCUMENTO_VALIDACION:
            db.session.rollback()
            return jsonify(
                {"error": f"tipo_documento debe ser uno de: {', '.join(TIPOS_DOCUMENTO_VALIDACION)}"}
            ), 400
        db.session.add(
            DocumentoValidacion(
                solicitud_id=solicitud.id,
                tipo_documento=tipo_documento,
                archivo_id=archivo_id,
                numero_documento=doc.get("numero_documento"),
            )
        )

    organizador.estado_validacion = "en_revision"
    db.session.commit()
    return jsonify(solicitud.to_dict(con_documentos=True)), 201


@organizadores_bp.route("/solicitudes/<int:solicitud_id>/documentos", methods=["POST"])
@jwt_required()
def agregar_documento(solicitud_id):
    solicitud = SolicitudValidacion.query.get_or_404(solicitud_id)
    if error := _requiere_gestion_organizador(solicitud.organizador_id):
        return error

    data = request.get_json(force=True, silent=True) or {}
    tipo_documento = data.get("tipo_documento")
    archivo_id = data.get("archivo_id")
    if not tipo_documento:
        return jsonify({"error": "tipo_documento es obligatorio"}), 400
    if tipo_documento not in TIPOS_DOCUMENTO_VALIDACION:
        return jsonify(
            {"error": f"tipo_documento debe ser uno de: {', '.join(TIPOS_DOCUMENTO_VALIDACION)}"}
        ), 400
    if not archivo_id:
        return jsonify({"error": "archivo_id es obligatorio"}), 400

    documento = DocumentoValidacion(
        solicitud_id=solicitud_id,
        tipo_documento=tipo_documento,
        archivo_id=archivo_id,
        numero_documento=data.get("numero_documento"),
    )
    db.session.add(documento)
    db.session.commit()
    return jsonify(documento.to_dict()), 201


@organizadores_bp.route("/solicitudes", methods=["GET"])
@admin_required
def listar_solicitudes():
    """Bandeja del admin. Filtro opcional ?estado=pendiente (default: pendientes)."""
    estado = request.args.get("estado", "pendiente")
    query = SolicitudValidacion.query
    if estado != "todas":
        query = query.filter_by(estado=estado)
    solicitudes = query.order_by(SolicitudValidacion.enviada_en).all()
    return jsonify([s.to_dict(con_documentos=True) for s in solicitudes]), 200


@organizadores_bp.route("/solicitudes/<int:solicitud_id>/revisar", methods=["PUT"])
@admin_required
def revisar_solicitud(solicitud_id):
    """El admin aprueba o rechaza; se refleja en `organizadores.estado_validacion`
    y queda registrado en la bitácora de auditoría."""
    solicitud = SolicitudValidacion.query.get_or_404(solicitud_id)
    organizador = Organizador.query.get_or_404(solicitud.organizador_id)
    data = request.get_json(force=True, silent=True) or {}
    decision = data.get("decision")  # "aprobar" | "rechazar"

    if decision not in ("aprobar", "rechazar"):
        return jsonify({"error": "decision debe ser 'aprobar' o 'rechazar'"}), 400

    admin = get_usuario_actual()
    estado_anterior = organizador.estado_validacion
    solicitud.revisor_id = admin.id
    solicitud.comentarios = data.get("comentarios")
    solicitud.resuelta_en = datetime.now(timezone.utc)

    if decision == "aprobar":
        solicitud.estado = "aprobada"
        organizador.estado_validacion = "aprobada"
        organizador.validado_en = datetime.now(timezone.utc)
    else:
        solicitud.estado = "rechazada"
        solicitud.motivo_rechazo = data.get("motivo_rechazo")
        organizador.estado_validacion = "rechazada"

    db.session.commit()

    registrar_auditoria(
        usuario_id=admin.id,
        accion=f"organizador.solicitud_{solicitud.estado}",
        tipo_entidad="organizador",
        entidad_id=organizador.id,
        antes={"estado_validacion": estado_anterior},
        despues={"estado_validacion": organizador.estado_validacion},
    )

    return jsonify({"organizador": organizador.to_dict(), "solicitud": solicitud.to_dict()}), 200

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import (
    Evento,
    EventoCategoria,
    EventoBoleto,
    EventoFecha,
    PaqueteRecuperacion,
    Inscripcion,
    ValoracionEvento,
    CalendarioUsuario,
    ESTADOS_INSCRIPCION,
)
from utils.auth import get_usuario_actual, puede_gestionar_evento

inscripciones_bp = Blueprint("inscripciones", __name__, url_prefix="/api")


def _requiere_gestion_evento(evento):
    """Admin, o miembro del organizador dueño del evento. Regresa una
    respuesta de error (jsonify, status) si no tiene permiso, o None si sí."""
    usuario = get_usuario_actual()
    if not puede_gestionar_evento(usuario, evento):
        return jsonify({"error": "No tienes permisos para gestionar este evento"}), 403
    return None


# ============ PAQUETES DE RECUPERACIÓN (catálogo por evento) ============

@inscripciones_bp.route("/eventos/<int:evento_id>/paquetes", methods=["GET"])
def listar_paquetes(evento_id):
    Evento.query.get_or_404(evento_id)
    query = PaqueteRecuperacion.query.filter_by(evento_id=evento_id)
    if request.args.get("incluir_inactivos") != "1":
        query = query.filter_by(activo=True)
    return jsonify([p.to_dict() for p in query.all()]), 200


@inscripciones_bp.route("/eventos/<int:evento_id>/paquetes", methods=["POST"])
@jwt_required()
def crear_paquete(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    if error := _requiere_gestion_evento(evento):
        return error
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("nombre"):
        return jsonify({"error": "nombre es obligatorio"}), 400

    paquete = PaqueteRecuperacion(
        evento_id=evento_id,
        nivel=data.get("nivel"),
        nombre=data["nombre"],
        descripcion=data.get("descripcion"),
        precio=data.get("precio", 0),
        moneda=data.get("moneda", "MXN"),
        activo=data.get("activo", True),
    )
    db.session.add(paquete)
    db.session.commit()
    return jsonify(paquete.to_dict()), 201


@inscripciones_bp.route("/paquetes/<int:paquete_id>", methods=["PUT"])
@jwt_required()
def actualizar_paquete(paquete_id):
    paquete = PaqueteRecuperacion.query.get_or_404(paquete_id)
    if error := _requiere_gestion_evento(Evento.query.get(paquete.evento_id)):
        return error
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("nivel", "nombre", "descripcion", "precio", "moneda", "activo"):
        if campo in data:
            setattr(paquete, campo, data[campo])
    db.session.commit()
    return jsonify(paquete.to_dict()), 200


@inscripciones_bp.route("/paquetes/<int:paquete_id>", methods=["DELETE"])
@jwt_required()
def desactivar_paquete(paquete_id):
    paquete = PaqueteRecuperacion.query.get_or_404(paquete_id)
    if error := _requiere_gestion_evento(Evento.query.get(paquete.evento_id)):
        return error
    paquete.activo = False
    db.session.commit()
    return jsonify(paquete.to_dict()), 200


# ============ INSCRIPCIONES ============

def _validar_referencias_cruzadas(evento_id, fecha_id, categoria_id, boleto_id, paquete_id):
    """Verifica que fecha/categoría/boleto/paquete realmente pertenezcan
    al evento (y la categoría al boleto), antes de crear la inscripción."""
    fecha = EventoFecha.query.get(fecha_id)
    if not fecha or fecha.evento_id != evento_id:
        return "fecha_id no pertenece a este evento"

    categoria = EventoCategoria.query.get(categoria_id)
    if not categoria or categoria.evento_id != evento_id:
        return "categoria_id no pertenece a este evento"

    boleto = EventoBoleto.query.get(boleto_id)
    if not boleto or boleto.categoria_id != categoria_id:
        return "boleto_id no pertenece a esa categoría"
    if not boleto.activo:
        return "Ese boleto ya no está disponible"

    ahora = datetime.now(timezone.utc)
    if boleto.disponible_desde and ahora < boleto.disponible_desde.replace(tzinfo=timezone.utc):
        return "Ese boleto todavía no está a la venta"
    if boleto.disponible_hasta and ahora > boleto.disponible_hasta.replace(tzinfo=timezone.utc):
        return "Ese boleto ya cerró su venta"

    if paquete_id is not None:
        paquete = PaqueteRecuperacion.query.get(paquete_id)
        if not paquete or paquete.evento_id != evento_id or not paquete.activo:
            return "paquete_id inválido para este evento"

    return None


@inscripciones_bp.route("/inscripciones", methods=["POST"])
@jwt_required()
def crear_inscripcion():
    """Body: {evento_id, fecha_id, categoria_id, boleto_id, paquete_id?}
    El estado queda en "pendiente" (a falta del módulo de pagos); si la
    categoría ya llegó a su cupo, cae en "lista_espera" cuando la
    categoría lo permite, o se rechaza si no.
    """
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}

    evento_id = data.get("evento_id")
    fecha_id = data.get("fecha_id")
    categoria_id = data.get("categoria_id")
    boleto_id = data.get("boleto_id")
    paquete_id = data.get("paquete_id")

    faltantes = [
        campo
        for campo, valor in {
            "evento_id": evento_id, "fecha_id": fecha_id,
            "categoria_id": categoria_id, "boleto_id": boleto_id,
        }.items()
        if not valor
    ]
    if faltantes:
        return jsonify({"error": f"Campos requeridos faltantes: {', '.join(faltantes)}"}), 400

    evento = Evento.query.filter_by(id=evento_id).filter(Evento.eliminado_en.is_(None)).first()
    if not evento or evento.estado != "publicado":
        return jsonify({"error": "El evento no existe o no está publicado"}), 404

    error = _validar_referencias_cruzadas(evento_id, fecha_id, categoria_id, boleto_id, paquete_id)
    if error:
        return jsonify({"error": error}), 400

    ya_inscrita = Inscripcion.query.filter(
        Inscripcion.usuario_id == usuario.id,
        Inscripcion.categoria_id == categoria_id,
        Inscripcion.estado != "cancelada",
    ).first()
    if ya_inscrita:
        return jsonify({"error": "Ya tienes una inscripción activa en esta categoría"}), 409

    categoria = EventoCategoria.query.get(categoria_id)
    estado = "pendiente"
    if categoria.cupo_total is not None:
        activas = Inscripcion.query.filter(
            Inscripcion.categoria_id == categoria_id,
            Inscripcion.estado.in_(("pendiente", "confirmada", "completada")),
        ).count()
        if activas >= categoria.cupo_total:
            if not categoria.permite_lista_espera:
                return jsonify({"error": "Ya no hay cupo en esta categoría"}), 409
            estado = "lista_espera"

    inscripcion = Inscripcion(
        usuario_id=usuario.id,
        evento_id=evento_id,
        fecha_id=fecha_id,
        categoria_id=categoria_id,
        boleto_id=boleto_id,
        paquete_id=paquete_id,
        estado=estado,
    )
    db.session.add(inscripcion)
    db.session.commit()
    return jsonify(inscripcion.to_dict(detalle=True)), 201


@inscripciones_bp.route("/inscripciones/me", methods=["GET"])
@jwt_required()
def mis_inscripciones():
    usuario = get_usuario_actual()
    query = Inscripcion.query.filter_by(usuario_id=usuario.id)
    if estado := request.args.get("estado"):
        query = query.filter_by(estado=estado)
    inscripciones = query.order_by(Inscripcion.inscrita_en.desc()).all()
    return jsonify([i.to_dict(detalle=True) for i in inscripciones]), 200


@inscripciones_bp.route("/inscripciones/<int:inscripcion_id>", methods=["GET"])
@jwt_required()
def obtener_inscripcion(inscripcion_id):
    usuario = get_usuario_actual()
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    if usuario.rol != "admin" and inscripcion.usuario_id != usuario.id:
        return jsonify({"error": "No tienes acceso a esta inscripción"}), 403
    return jsonify(inscripcion.to_dict(detalle=True)), 200


@inscripciones_bp.route("/inscripciones/<int:inscripcion_id>/cancelar", methods=["PUT"])
@jwt_required()
def cancelar_inscripcion(inscripcion_id):
    usuario = get_usuario_actual()
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    if usuario.rol != "admin" and inscripcion.usuario_id != usuario.id:
        return jsonify({"error": "No tienes acceso a esta inscripción"}), 403
    if inscripcion.estado == "cancelada":
        return jsonify({"error": "Esa inscripción ya estaba cancelada"}), 400

    inscripcion.estado = "cancelada"
    inscripcion.cancelada_en = datetime.now(timezone.utc)
    db.session.commit()

    # Si había alguien en lista de espera para la misma categoría, sube al primero.
    siguiente = (
        Inscripcion.query.filter_by(categoria_id=inscripcion.categoria_id, estado="lista_espera")
        .order_by(Inscripcion.inscrita_en)
        .first()
    )
    if siguiente:
        siguiente.estado = "pendiente"
        db.session.commit()

    return jsonify(inscripcion.to_dict()), 200


@inscripciones_bp.route("/inscripciones/<int:inscripcion_id>/estado", methods=["PUT"])
@jwt_required()
def cambiar_estado_inscripcion(inscripcion_id):
    """Admin, o el organizador del evento, confirma/rechaza manualmente
    mientras no exista el módulo de pagos."""
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    if error := _requiere_gestion_evento(Evento.query.get(inscripcion.evento_id)):
        return error
    data = request.get_json(force=True, silent=True) or {}
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ESTADOS_INSCRIPCION:
        return jsonify({"error": f"estado debe ser uno de: {', '.join(ESTADOS_INSCRIPCION)}"}), 400

    inscripcion.estado = nuevo_estado
    if nuevo_estado == "cancelada":
        inscripcion.cancelada_en = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(inscripcion.to_dict()), 200


@inscripciones_bp.route("/inscripciones/<int:inscripcion_id>/resultado", methods=["PUT"])
@jwt_required()
def registrar_resultado(inscripcion_id):
    """El día del evento: marca asistencia y captura tiempo/posiciones (admin u organizador)."""
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    if error := _requiere_gestion_evento(Evento.query.get(inscripcion.evento_id)):
        return error
    data = request.get_json(force=True, silent=True) or {}

    if data.get("asistio", False):
        inscripcion.asistio_en = datetime.now(timezone.utc)
        inscripcion.asistencia_latitud = data.get("asistencia_latitud")
        inscripcion.asistencia_longitud = data.get("asistencia_longitud")

    for campo in ("tiempo_oficial", "posicion_general", "posicion_categoria", "numero_participante"):
        if campo in data:
            setattr(inscripcion, campo, data[campo])

    if data.get("completada", False):
        inscripcion.estado = "completada"

    db.session.commit()
    return jsonify(inscripcion.to_dict()), 200


@inscripciones_bp.route("/eventos/<int:evento_id>/inscripciones", methods=["GET"])
@jwt_required()
def listar_inscripciones_de_evento(evento_id):
    """Vista del organizador/admin: quién se inscribió a un evento."""
    evento = Evento.query.get_or_404(evento_id)
    if error := _requiere_gestion_evento(evento):
        return error
    query = Inscripcion.query.filter_by(evento_id=evento_id)
    if categoria_id := request.args.get("categoria_id", type=int):
        query = query.filter_by(categoria_id=categoria_id)
    if estado := request.args.get("estado"):
        query = query.filter_by(estado=estado)
    inscripciones = query.order_by(Inscripcion.inscrita_en).all()
    return jsonify([i.to_dict() for i in inscripciones]), 200


# ============ VALORACIONES ============

@inscripciones_bp.route("/inscripciones/<int:inscripcion_id>/valoracion", methods=["POST"])
@jwt_required()
def valorar_evento(inscripcion_id):
    """El usuario deja su reseña una vez que la inscripción quedó "completada".
    Si ya había valorado, se actualiza la reseña existente."""
    usuario = get_usuario_actual()
    inscripcion = Inscripcion.query.get_or_404(inscripcion_id)
    if inscripcion.usuario_id != usuario.id:
        return jsonify({"error": "No puedes valorar una inscripción que no es tuya"}), 403
    if inscripcion.estado != "completada":
        return jsonify({"error": "Solo puedes valorar un evento al que ya asististe"}), 400

    data = request.get_json(force=True, silent=True) or {}
    calificacion = data.get("calificacion_evento")
    if not calificacion or not (1 <= int(calificacion) <= 5):
        return jsonify({"error": "calificacion_evento es obligatoria y debe ser de 1 a 5"}), 400

    calif_organizador = data.get("calificacion_organizador")
    if calif_organizador is not None and not (1 <= int(calif_organizador) <= 5):
        return jsonify({"error": "calificacion_organizador debe ser de 1 a 5"}), 400

    valoracion = ValoracionEvento.query.filter_by(inscripciones_id=inscripcion_id).first()
    if not valoracion:
        valoracion = ValoracionEvento(inscripciones_id=inscripcion_id)
        db.session.add(valoracion)

    valoracion.calificacion_evento = calificacion
    valoracion.calificacion_organizador = calif_organizador
    valoracion.comentario = data.get("comentario")

    db.session.commit()
    return jsonify(valoracion.to_dict()), 201


@inscripciones_bp.route("/eventos/<int:evento_id>/valoraciones", methods=["GET"])
def valoraciones_de_evento(evento_id):
    Evento.query.get_or_404(evento_id)
    valoraciones = (
        ValoracionEvento.query.join(Inscripcion)
        .filter(Inscripcion.evento_id == evento_id)
        .order_by(ValoracionEvento.creado_en.desc())
        .all()
    )
    return jsonify([v.to_dict() for v in valoraciones]), 200


@inscripciones_bp.route("/valoraciones/<int:valoracion_id>/responder", methods=["PUT"])
@jwt_required()
def responder_valoracion(valoracion_id):
    """El organizador del evento (o un admin) responde públicamente a la reseña."""
    valoracion = ValoracionEvento.query.get_or_404(valoracion_id)
    if error := _requiere_gestion_evento(Evento.query.get(valoracion.inscripcion.evento_id)):
        return error
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("respuesta_organizador"):
        return jsonify({"error": "respuesta_organizador es obligatoria"}), 400

    valoracion.respuesta_organizador = data["respuesta_organizador"]
    valoracion.respondida_en = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(valoracion.to_dict()), 200


# ============ CALENDARIO PERSONAL ============

@inscripciones_bp.route("/usuarios/me/calendario", methods=["GET"])
@jwt_required()
def mi_calendario():
    usuario = get_usuario_actual()
    entradas = CalendarioUsuario.query.filter_by(usuario_id=usuario.id).all()
    return jsonify([e.to_dict() for e in entradas]), 200


@inscripciones_bp.route("/usuarios/me/calendario", methods=["POST"])
@jwt_required()
def agregar_a_calendario():
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    fecha_id = data.get("fecha_id")
    if not fecha_id or not EventoFecha.query.get(fecha_id):
        return jsonify({"error": "fecha_id inválido"}), 400

    if CalendarioUsuario.query.get((usuario.id, fecha_id)):
        return jsonify({"error": "Esa fecha ya está en tu calendario"}), 409

    entrada = CalendarioUsuario(usuario_id=usuario.id, fecha_id=fecha_id)
    db.session.add(entrada)
    db.session.commit()
    return jsonify(entrada.to_dict()), 201


@inscripciones_bp.route("/usuarios/me/calendario/<int:fecha_id>", methods=["DELETE"])
@jwt_required()
def quitar_de_calendario(fecha_id):
    usuario = get_usuario_actual()
    entrada = CalendarioUsuario.query.get_or_404((usuario.id, fecha_id))
    db.session.delete(entrada)
    db.session.commit()
    return "", 204

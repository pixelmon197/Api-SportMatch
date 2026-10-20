from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import Amistad, Usuario
from utils.auth import get_usuario_actual
from utils.social import cuenta_disponible, hay_bloqueo, paginar, yo_bloquee

amistades_bp = Blueprint("amistades", __name__, url_prefix="/api/amistades")


def _entre(a_id, b_id):
    """Todas las filas de amistad entre dos usuarios, en ambos sentidos."""
    return Amistad.query.filter(
        db.or_(
            db.and_(Amistad.usuario_id == a_id, Amistad.amigo_id == b_id),
            db.and_(Amistad.usuario_id == b_id, Amistad.amigo_id == a_id),
        )
    ).all()


def _solo_disponibles(query):
    return query.filter(Usuario.estado_cuenta == "activa", Usuario.eliminado_en.is_(None))


# ============ Enviar solicitud ============

@amistades_bp.route("/solicitudes", methods=["POST"])
@jwt_required()
def enviar_solicitud():
    """Envía una solicitud de amistad. Body: {"usuario_id": 2}."""
    yo = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    objetivo_id = data.get("usuario_id")
    if not isinstance(objetivo_id, int) or isinstance(objetivo_id, bool):
        return jsonify({"error": "usuario_id es obligatorio y debe ser un número entero"}), 400

    objetivo = Usuario.query.get(objetivo_id)
    if not cuenta_disponible(objetivo):
        return jsonify({"error": "Usuario no encontrado"}), 404
    if objetivo.id == yo.id:
        return jsonify({"error": "No puedes enviarte una solicitud a ti mismo"}), 400
    if yo_bloquee(yo.id, objetivo.id):
        return jsonify({"error": "Tienes bloqueado a este usuario; desbloquéalo primero"}), 409
    if hay_bloqueo(yo.id, objetivo.id):  # él me bloqueó: no se revela
        return jsonify({"error": "Usuario no encontrado"}), 404

    mia_rechazada = None
    for fila in _entre(yo.id, objetivo.id):
        if fila.estado == "aceptada":
            return jsonify({"error": "Ya son amigos"}), 409
        if fila.estado == "pendiente" and fila.usuario_id == yo.id:
            return jsonify({"error": "Ya le enviaste una solicitud a este usuario"}), 409
        if fila.estado == "pendiente" and fila.usuario_id == objetivo.id:
            return jsonify(
                {"error": "Ese usuario ya te envió una solicitud; acéptala", "solicitud_id": fila.id}
            ), 409
        if fila.estado == "rechazada" and fila.usuario_id == yo.id:
            mia_rechazada = fila

    if mia_rechazada:
        # Neon solo permite una fila por sentido (UNIQUE), así que una
        # solicitud mía que fue rechazada se reutiliza.
        mia_rechazada.estado = "pendiente"
        mia_rechazada.creado_en = datetime.now(timezone.utc)
        mia_rechazada.respondida_en = None
        fila = mia_rechazada
    else:
        fila = Amistad(usuario_id=yo.id, amigo_id=objetivo.id, estado="pendiente")
        db.session.add(fila)
    db.session.commit()
    return jsonify(fila.to_dict()), 201


# ============ Bandejas ============

@amistades_bp.route("/solicitudes/recibidas", methods=["GET"])
@jwt_required()
def solicitudes_recibidas():
    """Solicitudes pendientes que me enviaron. Query params: page, per_page."""
    yo = get_usuario_actual()
    query = _solo_disponibles(
        db.session.query(Usuario, Amistad.id, Amistad.creado_en)
        .join(Amistad, Amistad.usuario_id == Usuario.id)
        .filter(Amistad.amigo_id == yo.id, Amistad.estado == "pendiente")
    ).order_by(Amistad.creado_en.desc(), Amistad.id)
    return jsonify(paginar(
        query, "solicitudes",
        lambda ficha, fila: {"solicitud_id": fila[1], "usuario": ficha, "creado_en": fila[2].isoformat()},
    )), 200


@amistades_bp.route("/solicitudes/enviadas", methods=["GET"])
@jwt_required()
def solicitudes_enviadas():
    """Solicitudes pendientes que yo envié. Query params: page, per_page."""
    yo = get_usuario_actual()
    query = _solo_disponibles(
        db.session.query(Usuario, Amistad.id, Amistad.creado_en)
        .join(Amistad, Amistad.amigo_id == Usuario.id)
        .filter(Amistad.usuario_id == yo.id, Amistad.estado == "pendiente")
    ).order_by(Amistad.creado_en.desc(), Amistad.id)
    return jsonify(paginar(
        query, "solicitudes",
        lambda ficha, fila: {"solicitud_id": fila[1], "usuario": ficha, "creado_en": fila[2].isoformat()},
    )), 200


# ============ Responder / cancelar ============

def _responder(solicitud_id, nuevo_estado):
    yo = get_usuario_actual()
    solicitud = Amistad.query.get_or_404(solicitud_id)
    if solicitud.amigo_id != yo.id:
        return jsonify({"error": "Esa solicitud no es para ti"}), 403
    if solicitud.estado != "pendiente":
        return jsonify({"error": f"Esa solicitud ya estaba {solicitud.estado}"}), 409
    solicitud.estado = nuevo_estado
    solicitud.respondida_en = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(solicitud.to_dict()), 200


@amistades_bp.route("/solicitudes/<int:solicitud_id>/aceptar", methods=["PUT"])
@jwt_required()
def aceptar_solicitud(solicitud_id):
    """Acepto una solicitud que me enviaron (solo quien la recibió)."""
    return _responder(solicitud_id, "aceptada")


@amistades_bp.route("/solicitudes/<int:solicitud_id>/rechazar", methods=["PUT"])
@jwt_required()
def rechazar_solicitud(solicitud_id):
    """Rechazo una solicitud que me enviaron (solo quien la recibió)."""
    return _responder(solicitud_id, "rechazada")


@amistades_bp.route("/solicitudes/<int:solicitud_id>", methods=["DELETE"])
@jwt_required()
def cancelar_solicitud(solicitud_id):
    """Cancelo una solicitud que yo envié y sigue pendiente."""
    yo = get_usuario_actual()
    solicitud = Amistad.query.get_or_404(solicitud_id)
    if solicitud.usuario_id != yo.id:
        return jsonify({"error": "Esa solicitud no la enviaste tú"}), 403
    if solicitud.estado != "pendiente":
        return jsonify({"error": f"Esa solicitud ya estaba {solicitud.estado}"}), 409
    db.session.delete(solicitud)
    db.session.commit()
    return "", 204


# ============ Mis amigos ============

@amistades_bp.route("", methods=["GET"])
@jwt_required()
def mis_amigos():
    """Mis amigos (amistades aceptadas). Query params: page, per_page."""
    yo = get_usuario_actual()
    query = _solo_disponibles(
        db.session.query(Usuario, Amistad.id, Amistad.respondida_en)
        .join(
            Amistad,
            db.or_(
                db.and_(Amistad.usuario_id == yo.id, Amistad.amigo_id == Usuario.id),
                db.and_(Amistad.amigo_id == yo.id, Amistad.usuario_id == Usuario.id),
            ),
        )
        .filter(Amistad.estado == "aceptada")
    ).order_by(Usuario.nombre_completo, Usuario.id)
    return jsonify(paginar(
        query, "amigos",
        lambda ficha, fila: {
            **ficha,
            "amistad_id": fila[1],
            "desde": fila[2].isoformat() if fila[2] else None,
        },
    )), 200


@amistades_bp.route("/amigos/<int:usuario_id>", methods=["DELETE"])
@jwt_required()
def eliminar_amigo(usuario_id):
    """Elimino a alguien de mis amigos (se borra la amistad para ambos)."""
    yo = get_usuario_actual()
    filas = [f for f in _entre(yo.id, usuario_id) if f.estado == "aceptada"]
    if not filas:
        return jsonify({"error": "No son amigos"}), 404
    for fila in filas:
        db.session.delete(fila)
    db.session.commit()
    return "", 204

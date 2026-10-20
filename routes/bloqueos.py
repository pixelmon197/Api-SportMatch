from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from database import db
from models import Amistad, Bloqueo, Seguidor, Usuario
from utils.auth import get_usuario_actual
from utils.social import paginar

bloqueos_bp = Blueprint("bloqueos", __name__, url_prefix="/api/bloqueos")


@bloqueos_bp.route("/<int:usuario_id>", methods=["POST"])
@jwt_required()
def bloquear(usuario_id):
    """Bloquea a un usuario. Efectos: deja de poder ver mi perfil (le sale
    404), de seguirme, de enviarme solicitudes; y se borran los
    seguimientos (en ambos sentidos) y la amistad o solicitudes pendientes
    que hubiera entre los dos. Desbloquear después NO los restaura."""
    yo = get_usuario_actual()
    if usuario_id == yo.id:
        return jsonify({"error": "No puedes bloquearte a ti mismo"}), 400
    if not Usuario.query.get(usuario_id):
        return jsonify({"error": "Usuario no encontrado"}), 404
    if Bloqueo.query.get((yo.id, usuario_id)):
        return jsonify({"error": "Ya tienes bloqueado a este usuario"}), 409

    bloqueo = Bloqueo(bloqueador_id=yo.id, bloqueado_id=usuario_id)
    db.session.add(bloqueo)

    Seguidor.query.filter(
        db.or_(
            db.and_(Seguidor.seguidor_id == yo.id, Seguidor.seguido_id == usuario_id),
            db.and_(Seguidor.seguidor_id == usuario_id, Seguidor.seguido_id == yo.id),
        )
    ).delete(synchronize_session=False)
    Amistad.query.filter(
        db.or_(
            db.and_(Amistad.usuario_id == yo.id, Amistad.amigo_id == usuario_id),
            db.and_(Amistad.usuario_id == usuario_id, Amistad.amigo_id == yo.id),
        )
    ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify(
        {"bloqueador_id": yo.id, "bloqueado_id": usuario_id, "creado_en": bloqueo.creado_en.isoformat()}
    ), 201


@bloqueos_bp.route("/<int:usuario_id>", methods=["DELETE"])
@jwt_required()
def desbloquear(usuario_id):
    yo = get_usuario_actual()
    bloqueo = Bloqueo.query.get((yo.id, usuario_id))
    if not bloqueo:
        return jsonify({"error": "No tienes bloqueado a este usuario"}), 404
    db.session.delete(bloqueo)
    db.session.commit()
    return "", 204


@bloqueos_bp.route("", methods=["GET"])
@jwt_required()
def mis_bloqueados():
    """Usuarios que he bloqueado. Query params: page, per_page."""
    yo = get_usuario_actual()
    query = (
        db.session.query(Usuario, Bloqueo.creado_en)
        .join(Bloqueo, Bloqueo.bloqueado_id == Usuario.id)
        .filter(Bloqueo.bloqueador_id == yo.id)
        .order_by(Bloqueo.creado_en.desc(), Usuario.id)
    )
    return jsonify(paginar(
        query, "bloqueados",
        lambda ficha, fila: {**ficha, "bloqueado_en": fila[1].isoformat()},
    )), 200

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from database import db
from models import Seguidor, Usuario
from utils.auth import get_usuario_actual
from utils.social import (
    cuenta_disponible,
    error_de_acceso_al_perfil,
    hay_bloqueo,
    ids_con_bloqueo_respecto_a,
    paginar,
    perfil_o_valores_por_defecto,
    usuario_que_consulta,
    yo_bloquee,
)

seguidores_bp = Blueprint("seguidores", __name__, url_prefix="/api/seguidores")


@seguidores_bp.route("/<int:usuario_id>", methods=["POST"])
@jwt_required()
def seguir(usuario_id):
    """Empieza a seguir a un usuario. Seguir no necesita aprobación (a
    diferencia de la amistad)."""
    yo = get_usuario_actual()
    objetivo = Usuario.query.get(usuario_id)
    if not cuenta_disponible(objetivo):
        return jsonify({"error": "Usuario no encontrado"}), 404
    if objetivo.id == yo.id:
        return jsonify({"error": "No puedes seguirte a ti mismo"}), 400
    if yo_bloquee(yo.id, objetivo.id):
        return jsonify({"error": "Tienes bloqueado a este usuario; desbloquéalo primero"}), 409
    if hay_bloqueo(yo.id, objetivo.id):  # él me bloqueó: no se revela
        return jsonify({"error": "Usuario no encontrado"}), 404
    if Seguidor.query.get((yo.id, objetivo.id)):
        return jsonify({"error": "Ya sigues a este usuario"}), 409

    fila = Seguidor(seguidor_id=yo.id, seguido_id=objetivo.id)
    db.session.add(fila)
    db.session.commit()
    return jsonify(
        {"seguidor_id": fila.seguidor_id, "seguido_id": fila.seguido_id, "creado_en": fila.creado_en.isoformat()}
    ), 201


@seguidores_bp.route("/<int:usuario_id>", methods=["DELETE"])
@jwt_required()
def dejar_de_seguir(usuario_id):
    yo = get_usuario_actual()
    fila = Seguidor.query.get((yo.id, usuario_id))
    if not fila:
        return jsonify({"error": "No sigues a este usuario"}), 404
    db.session.delete(fila)
    db.session.commit()
    return "", 204


def _lista_de_seguidores(usuario_id, consulta):
    """Quienes siguen a `usuario_id`."""
    query = (
        db.session.query(Usuario, Seguidor.creado_en)
        .join(Seguidor, Seguidor.seguidor_id == Usuario.id)
        .filter(Seguidor.seguido_id == usuario_id)
    )
    return _filtrar_y_paginar(query, consulta, "seguidores")


def _lista_de_seguidos(usuario_id, consulta):
    """A quienes sigue `usuario_id`."""
    query = (
        db.session.query(Usuario, Seguidor.creado_en)
        .join(Seguidor, Seguidor.seguido_id == Usuario.id)
        .filter(Seguidor.seguidor_id == usuario_id)
    )
    return _filtrar_y_paginar(query, consulta, "siguiendo")


def _filtrar_y_paginar(query, consulta, nombre):
    # Cuentas no disponibles fuera, y quien consulta no ve a quienes bloqueó
    # ni a quienes lo bloquearon.
    query = query.filter(Usuario.estado_cuenta == "activa", Usuario.eliminado_en.is_(None))
    if consulta is not None:
        query = query.filter(Usuario.id.notin_(ids_con_bloqueo_respecto_a(consulta.id)))
    query = query.order_by(db.desc("creado_en"), Usuario.id)
    return paginar(query, nombre, lambda ficha, fila: {**ficha, "desde": fila[1].isoformat()})


@seguidores_bp.route("/me/seguidores", methods=["GET"])
@jwt_required()
def mis_seguidores():
    """Quienes me siguen. Query params: page, per_page."""
    return jsonify(_lista_de_seguidores(get_usuario_actual().id, get_usuario_actual())), 200


@seguidores_bp.route("/me/siguiendo", methods=["GET"])
@jwt_required()
def a_quienes_sigo():
    """A quienes sigo. Query params: page, per_page."""
    return jsonify(_lista_de_seguidos(get_usuario_actual().id, get_usuario_actual())), 200


def _con_acceso(usuario_id, funcion):
    """Los seguidores de otra persona solo se ven si su perfil se puede ver."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"error": "Perfil no encontrado"}), 404
    consulta = usuario_que_consulta()
    error = error_de_acceso_al_perfil(consulta, usuario, perfil_o_valores_por_defecto(usuario))
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(funcion(usuario.id, consulta)), 200


@seguidores_bp.route("/<int:usuario_id>/seguidores", methods=["GET"])
def seguidores_de(usuario_id):
    """Seguidores de otro usuario (respeta la visibilidad de su perfil)."""
    return _con_acceso(usuario_id, _lista_de_seguidores)


@seguidores_bp.route("/<int:usuario_id>/siguiendo", methods=["GET"])
def siguiendo_de(usuario_id):
    """A quienes sigue otro usuario (respeta la visibilidad de su perfil)."""
    return _con_acceso(usuario_id, _lista_de_seguidos)

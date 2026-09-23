from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import Deporte, UsuarioDeporte, NIVELES_DEPORTE
from utils.auth import admin_required, get_usuario_actual

deportes_bp = Blueprint("deportes", __name__, url_prefix="/api/deportes")


# ============ CATÁLOGO DE DEPORTES ============

@deportes_bp.route("", methods=["GET"])
def listar_deportes():
    """Público. Por defecto solo deportes activos; ?incluir_inactivos=1 para admin."""
    query = Deporte.query
    if request.args.get("incluir_inactivos") != "1":
        query = query.filter_by(activo=True)
    deportes = query.order_by(Deporte.nombre).all()
    return jsonify([d.to_dict() for d in deportes]), 200


@deportes_bp.route("/<int:deporte_id>", methods=["GET"])
def obtener_deporte(deporte_id):
    deporte = Deporte.query.get_or_404(deporte_id)
    return jsonify(deporte.to_dict()), 200


@deportes_bp.route("", methods=["POST"])
@admin_required
def crear_deporte():
    data = request.get_json(force=True, silent=True) or {}
    nombre = data.get("nombre")
    if not nombre:
        return jsonify({"error": "nombre es obligatorio"}), 400
    if Deporte.query.filter_by(nombre=nombre).first():
        return jsonify({"error": "Ya existe un deporte con ese nombre"}), 409

    deporte = Deporte(nombre=nombre, categoria=data.get("categoria"), activo=data.get("activo", True))
    db.session.add(deporte)
    db.session.commit()
    return jsonify(deporte.to_dict()), 201


@deportes_bp.route("/<int:deporte_id>", methods=["PUT"])
@admin_required
def actualizar_deporte(deporte_id):
    deporte = Deporte.query.get_or_404(deporte_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("nombre", "categoria", "activo"):
        if campo in data:
            setattr(deporte, campo, data[campo])
    db.session.commit()
    return jsonify(deporte.to_dict()), 200


@deportes_bp.route("/<int:deporte_id>", methods=["DELETE"])
@admin_required
def desactivar_deporte(deporte_id):
    """Borrado suave: hay muchas tablas que dependen de un deporte
    (rutas, eventos, opciones del cuestionario), así que nunca se borra
    físicamente, solo se desactiva."""
    deporte = Deporte.query.get_or_404(deporte_id)
    deporte.activo = False
    db.session.commit()
    return jsonify(deporte.to_dict()), 200


# ============ DEPORTES QUE PRACTICA EL USUARIO AUTENTICADO ============

@deportes_bp.route("/me", methods=["GET"])
@jwt_required()
def mis_deportes():
    usuario = get_usuario_actual()
    return jsonify([ud.to_dict() for ud in usuario.deportes]), 200


@deportes_bp.route("/me", methods=["POST"])
@jwt_required()
def agregar_mi_deporte():
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    deporte_id = data.get("deporte_id")
    nivel = data.get("nivel", "principiante")
    es_principal = bool(data.get("es_principal", False))

    if not deporte_id:
        return jsonify({"error": "deporte_id es obligatorio"}), 400
    if nivel not in NIVELES_DEPORTE:
        return jsonify({"error": f"nivel debe ser uno de: {', '.join(NIVELES_DEPORTE)}"}), 400

    deporte = Deporte.query.get(deporte_id)
    if not deporte or not deporte.activo:
        return jsonify({"error": "Ese deporte no existe o no está activo"}), 404

    existente = UsuarioDeporte.query.get((usuario.id, deporte_id))
    if existente:
        return jsonify({"error": "Ya tienes registrado ese deporte"}), 409

    if es_principal:
        UsuarioDeporte.query.filter_by(usuario_id=usuario.id, es_principal=True).update(
            {"es_principal": False}
        )

    ud = UsuarioDeporte(
        usuario_id=usuario.id, deporte_id=deporte_id, nivel=nivel, es_principal=es_principal
    )
    db.session.add(ud)
    db.session.commit()
    return jsonify(ud.to_dict()), 201


@deportes_bp.route("/me/<int:deporte_id>", methods=["PUT"])
@jwt_required()
def actualizar_mi_deporte(deporte_id):
    usuario = get_usuario_actual()
    ud = UsuarioDeporte.query.get_or_404((usuario.id, deporte_id))
    data = request.get_json(force=True, silent=True) or {}

    if "nivel" in data:
        if data["nivel"] not in NIVELES_DEPORTE:
            return jsonify({"error": f"nivel debe ser uno de: {', '.join(NIVELES_DEPORTE)}"}), 400
        ud.nivel = data["nivel"]

    if data.get("es_principal") is True:
        UsuarioDeporte.query.filter_by(usuario_id=usuario.id, es_principal=True).update(
            {"es_principal": False}
        )
        ud.es_principal = True
    elif "es_principal" in data:
        ud.es_principal = bool(data["es_principal"])

    db.session.commit()
    return jsonify(ud.to_dict()), 200


@deportes_bp.route("/me/<int:deporte_id>", methods=["DELETE"])
@jwt_required()
def quitar_mi_deporte(deporte_id):
    usuario = get_usuario_actual()
    ud = UsuarioDeporte.query.get_or_404((usuario.id, deporte_id))
    db.session.delete(ud)
    db.session.commit()
    return "", 204

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import Ruta, RutaPunto, EventoRuta, EventoCategoria, Deporte, TIPOS_PUNTO_RUTA
from utils.auth import get_usuario_actual

rutas_bp = Blueprint("rutas", __name__, url_prefix="/api/rutas")


def _es_dueno_o_admin(ruta, usuario):
    return usuario.rol == "admin" or ruta.creador_id == usuario.id


# ============ CONSULTA ============

@rutas_bp.route("", methods=["GET"])
def listar_rutas():
    """Público: solo rutas públicas y no eliminadas. Filtros: deporte_id, creador_id."""
    query = Ruta.query.filter_by(es_publica=True).filter(Ruta.eliminado_en.is_(None))
    if deporte_id := request.args.get("deporte_id", type=int):
        query = query.filter_by(deporte_id=deporte_id)
    if creador_id := request.args.get("creador_id", type=int):
        query = query.filter_by(creador_id=creador_id)
    rutas = query.order_by(Ruta.id.desc()).all()
    return jsonify([r.to_dict() for r in rutas]), 200


@rutas_bp.route("/<int:ruta_id>", methods=["GET"])
def obtener_ruta(ruta_id):
    ruta = Ruta.query.filter_by(id=ruta_id).filter(Ruta.eliminado_en.is_(None)).first_or_404()
    return jsonify(ruta.to_dict(con_puntos=True)), 200


# ============ CREAR / EDITAR (cualquier usuario autenticado crea sus propias rutas) ============

@rutas_bp.route("", methods=["POST"])
@jwt_required()
def crear_ruta():
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}

    nombre = data.get("nombre")
    deporte_id = data.get("deporte_id")
    if not nombre or not deporte_id:
        return jsonify({"error": "nombre y deporte_id son obligatorios"}), 400
    if not Deporte.query.get(deporte_id):
        return jsonify({"error": "deporte_id inválido"}), 400

    ruta = Ruta(
        creador_id=usuario.id,
        deporte_id=deporte_id,
        dificultad=data.get("dificultad"),
        nombre=nombre,
        descripcion=data.get("descripcion"),
        distancia_m=data.get("distancia_m"),
        desnivel_positivo_m=data.get("desnivel_positivo_m"),
        es_publica=data.get("es_publica", True),
    )
    db.session.add(ruta)
    db.session.flush()

    for punto in data.get("puntos", []):
        if punto.get("tipo") and punto["tipo"] not in TIPOS_PUNTO_RUTA:
            db.session.rollback()
            return jsonify({"error": f"tipo de punto debe ser uno de: {', '.join(TIPOS_PUNTO_RUTA)}"}), 400
        db.session.add(
            RutaPunto(
                ruta_id=ruta.id,
                tipo=punto.get("tipo", "paso"),
                orden=punto.get("orden", 0),
                nombre=punto.get("nombre"),
                latitud=punto["latitud"],
                longitud=punto["longitud"],
                altitud_m=punto.get("altitud_m"),
            )
        )

    db.session.commit()
    return jsonify(ruta.to_dict(con_puntos=True)), 201


@rutas_bp.route("/<int:ruta_id>", methods=["PUT"])
@jwt_required()
def actualizar_ruta(ruta_id):
    ruta = Ruta.query.get_or_404(ruta_id)
    usuario = get_usuario_actual()
    if not _es_dueno_o_admin(ruta, usuario):
        return jsonify({"error": "No tienes permisos para editar esta ruta"}), 403

    data = request.get_json(force=True, silent=True) or {}
    for campo in (
        "nombre", "descripcion", "dificultad", "distancia_m", "desnivel_positivo_m", "es_publica",
    ):
        if campo in data:
            setattr(ruta, campo, data[campo])
    db.session.commit()
    return jsonify(ruta.to_dict(con_puntos=True)), 200


@rutas_bp.route("/<int:ruta_id>", methods=["DELETE"])
@jwt_required()
def eliminar_ruta(ruta_id):
    from datetime import datetime, timezone

    ruta = Ruta.query.get_or_404(ruta_id)
    usuario = get_usuario_actual()
    if not _es_dueno_o_admin(ruta, usuario):
        return jsonify({"error": "No tienes permisos para eliminar esta ruta"}), 403

    ruta.eliminado_en = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(ruta.to_dict()), 200


@rutas_bp.route("/<int:ruta_id>/puntos", methods=["POST"])
@jwt_required()
def agregar_punto(ruta_id):
    ruta = Ruta.query.get_or_404(ruta_id)
    usuario = get_usuario_actual()
    if not _es_dueno_o_admin(ruta, usuario):
        return jsonify({"error": "No tienes permisos para editar esta ruta"}), 403

    data = request.get_json(force=True, silent=True) or {}
    if data.get("latitud") is None or data.get("longitud") is None:
        return jsonify({"error": "latitud y longitud son obligatorias"}), 400
    if data.get("tipo") and data["tipo"] not in TIPOS_PUNTO_RUTA:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_PUNTO_RUTA)}"}), 400

    punto = RutaPunto(
        ruta_id=ruta_id,
        tipo=data.get("tipo", "paso"),
        orden=data.get("orden", 0),
        nombre=data.get("nombre"),
        latitud=data["latitud"],
        longitud=data["longitud"],
        altitud_m=data.get("altitud_m"),
    )
    db.session.add(punto)
    db.session.commit()
    return jsonify(punto.to_dict()), 201


@rutas_bp.route("/puntos/<int:punto_id>", methods=["DELETE"])
@jwt_required()
def eliminar_punto(punto_id):
    punto = RutaPunto.query.get_or_404(punto_id)
    ruta = Ruta.query.get_or_404(punto.ruta_id)
    usuario = get_usuario_actual()
    if not _es_dueno_o_admin(ruta, usuario):
        return jsonify({"error": "No tienes permisos para editar esta ruta"}), 403

    db.session.delete(punto)
    db.session.commit()
    return "", 204


# ============ LIGAR UNA RUTA A UNA CATEGORÍA DE EVENTO (solo admin) ============

@rutas_bp.route("/categorias/<int:categoria_id>/rutas", methods=["POST"])
@jwt_required()
def ligar_ruta_a_categoria(categoria_id):
    usuario = get_usuario_actual()
    if usuario.rol != "admin":
        return jsonify({"error": "Solo un administrador puede ligar rutas a un evento"}), 403

    EventoCategoria.query.get_or_404(categoria_id)
    data = request.get_json(force=True, silent=True) or {}
    ruta_id = data.get("ruta_id")
    if not ruta_id or not Ruta.query.get(ruta_id):
        return jsonify({"error": "ruta_id inválido"}), 400

    evento_ruta = EventoRuta(ruta_id=ruta_id, categoria_id=categoria_id)
    db.session.add(evento_ruta)
    db.session.commit()
    return jsonify(evento_ruta.to_dict()), 201


@rutas_bp.route("/categorias/<int:categoria_id>/rutas", methods=["GET"])
def rutas_de_categoria(categoria_id):
    EventoCategoria.query.get_or_404(categoria_id)
    ligas = EventoRuta.query.filter_by(categoria_id=categoria_id).all()
    return jsonify([lr.to_dict() for lr in ligas]), 200


@rutas_bp.route("/eventos-rutas/<int:evento_ruta_id>", methods=["DELETE"])
@jwt_required()
def desligar_ruta(evento_ruta_id):
    usuario = get_usuario_actual()
    if usuario.rol != "admin":
        return jsonify({"error": "Solo un administrador puede desligar rutas de un evento"}), 403

    evento_ruta = EventoRuta.query.get_or_404(evento_ruta_id)
    db.session.delete(evento_ruta)
    db.session.commit()
    return "", 204

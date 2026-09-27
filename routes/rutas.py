from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import Ruta, RutaPunto, EventoRuta, EventoCategoria, Evento, Deporte, TIPOS_PUNTO_RUTA, DIFICULTADES_RUTA
from utils.auth import get_usuario_actual, puede_gestionar_evento

rutas_bp = Blueprint("rutas", __name__, url_prefix="/api/rutas")


def _es_dueno_o_admin(ruta, usuario):
    return usuario.rol == "administrador" or ruta.creador_id == usuario.id


def _validar_ruta(datos):
    """Valida los CHECK reales de `rutas`. Regresa un mensaje de error
    (str) o None si todo está bien."""
    if datos.get("dificultad") and datos["dificultad"] not in DIFICULTADES_RUTA:
        return f"dificultad debe ser una de: {', '.join(DIFICULTADES_RUTA)}"
    distancia_m = datos.get("distancia_m")
    if distancia_m is not None:
        if not float(distancia_m).is_integer():
            return "distancia_m debe ser un número entero de metros"
        if distancia_m <= 0:
            return "distancia_m debe ser mayor a 0"
    desnivel = datos.get("desnivel_positivo_m")
    if desnivel is not None:
        if not float(desnivel).is_integer():
            return "desnivel_positivo_m debe ser un número entero de metros"
        if desnivel < 0:
            return "desnivel_positivo_m no puede ser negativo"
    return None


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
    error = _validar_ruta(data)
    if error:
        return jsonify({"error": error}), 400

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

    ordenes_usados = set()
    for punto in data.get("puntos", []):
        if punto.get("tipo") and punto["tipo"] not in TIPOS_PUNTO_RUTA:
            db.session.rollback()
            return jsonify({"error": f"tipo de punto debe ser uno de: {', '.join(TIPOS_PUNTO_RUTA)}"}), 400
        orden = punto.get("orden", 0)
        if orden in ordenes_usados:
            db.session.rollback()
            return jsonify({"error": f"orden={orden} está repetido entre los puntos"}), 400
        ordenes_usados.add(orden)
        db.session.add(
            RutaPunto(
                ruta_id=ruta.id,
                tipo=punto.get("tipo", "punto_interes"),
                orden=orden,
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
    datos_completos = {
        "dificultad": data.get("dificultad", ruta.dificultad),
        "distancia_m": data.get("distancia_m", ruta.distancia_m),
        "desnivel_positivo_m": data.get("desnivel_positivo_m", ruta.desnivel_positivo_m),
    }
    error = _validar_ruta(datos_completos)
    if error:
        return jsonify({"error": error}), 400
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
    orden = data.get("orden", 0)
    if RutaPunto.query.filter_by(ruta_id=ruta_id, orden=orden).first():
        return jsonify({"error": f"Ya existe un punto con orden={orden} en esta ruta"}), 409

    punto = RutaPunto(
        ruta_id=ruta_id,
        tipo=data.get("tipo", "punto_interes"),
        orden=orden,
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


# ============ LIGAR UNA RUTA A UNA CATEGORÍA DE EVENTO (admin u organizador del evento) ============

@rutas_bp.route("/categorias/<int:categoria_id>/rutas", methods=["POST"])
@jwt_required()
def ligar_ruta_a_categoria(categoria_id):
    usuario = get_usuario_actual()
    categoria = EventoCategoria.query.get_or_404(categoria_id)
    evento = Evento.query.get(categoria.evento_id)
    if not puede_gestionar_evento(usuario, evento):
        return jsonify({"error": "No tienes permisos para gestionar este evento"}), 403

    data = request.get_json(force=True, silent=True) or {}
    ruta_id = data.get("ruta_id")
    if not ruta_id or not Ruta.query.get(ruta_id):
        return jsonify({"error": "ruta_id inválido"}), 400
    if EventoRuta.query.get((evento.id, ruta_id)):
        return jsonify({"error": "Esa ruta ya está ligada a este evento"}), 409

    evento_ruta = EventoRuta(evento_id=evento.id, ruta_id=ruta_id, categoria_id=categoria_id)
    db.session.add(evento_ruta)
    db.session.commit()
    return jsonify(evento_ruta.to_dict()), 201


@rutas_bp.route("/categorias/<int:categoria_id>/rutas", methods=["GET"])
def rutas_de_categoria(categoria_id):
    EventoCategoria.query.get_or_404(categoria_id)
    ligas = EventoRuta.query.filter_by(categoria_id=categoria_id).all()
    return jsonify([lr.to_dict() for lr in ligas]), 200


@rutas_bp.route("/eventos-rutas/<int:evento_id>/<int:ruta_id>", methods=["DELETE"])
@jwt_required()
def desligar_ruta(evento_id, ruta_id):
    usuario = get_usuario_actual()
    evento_ruta = EventoRuta.query.get_or_404((evento_id, ruta_id))
    evento = Evento.query.get(evento_id)
    if not puede_gestionar_evento(usuario, evento):
        return jsonify({"error": "No tienes permisos para gestionar este evento"}), 403

    db.session.delete(evento_ruta)
    db.session.commit()
    return "", 204

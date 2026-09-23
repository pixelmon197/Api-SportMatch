from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import Cuestionario, Pregunta, OpcionRespuesta, RespuestaUsuario, TIPOS_PREGUNTA
from utils.auth import admin_required, get_usuario_actual

cuestionarios_bp = Blueprint("cuestionarios", __name__, url_prefix="/api/cuestionarios")


# ============ CONSULTA (público: el front necesita esto para armar el registro) ============

@cuestionarios_bp.route("", methods=["GET"])
def listar_cuestionarios():
    activos = request.args.get("incluir_inactivos") != "1"
    query = Cuestionario.query
    if activos:
        query = query.filter_by(activo=True)
    return jsonify([c.to_dict() for c in query.order_by(Cuestionario.id).all()]), 200


@cuestionarios_bp.route("/<string:codigo>", methods=["GET"])
def obtener_cuestionario(codigo):
    """Regresa el cuestionario completo (preguntas + opciones) para renderizar el formulario."""
    cuestionario = Cuestionario.query.filter_by(codigo=codigo).first()
    if not cuestionario:
        return jsonify({"error": "Cuestionario no encontrado"}), 404
    return jsonify(cuestionario.to_dict(con_preguntas=True)), 200


# ============ ADMINISTRACIÓN (solo admin) ============

@cuestionarios_bp.route("", methods=["POST"])
@admin_required
def crear_cuestionario():
    data = request.get_json(force=True, silent=True) or {}
    codigo = data.get("codigo")
    titulo = data.get("titulo")
    if not codigo or not titulo:
        return jsonify({"error": "codigo y titulo son obligatorios"}), 400
    if Cuestionario.query.filter_by(codigo=codigo).first():
        return jsonify({"error": "Ya existe un cuestionario con ese código"}), 409

    cuestionario = Cuestionario(
        codigo=codigo,
        titulo=titulo,
        descripcion=data.get("descripcion"),
        activo=data.get("activo", True),
    )
    db.session.add(cuestionario)
    db.session.commit()
    return jsonify(cuestionario.to_dict()), 201


@cuestionarios_bp.route("/<int:cuestionario_id>", methods=["PUT"])
@admin_required
def actualizar_cuestionario(cuestionario_id):
    cuestionario = Cuestionario.query.get_or_404(cuestionario_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("titulo", "descripcion", "activo"):
        if campo in data:
            setattr(cuestionario, campo, data[campo])
    db.session.commit()
    return jsonify(cuestionario.to_dict()), 200


@cuestionarios_bp.route("/<int:cuestionario_id>/preguntas", methods=["POST"])
@admin_required
def crear_pregunta(cuestionario_id):
    Cuestionario.query.get_or_404(cuestionario_id)
    data = request.get_json(force=True, silent=True) or {}
    codigo = data.get("codigo")
    texto = data.get("texto")
    tipo = data.get("tipo", "opcion_unica")

    if not codigo or not texto:
        return jsonify({"error": "codigo y texto son obligatorios"}), 400
    if tipo not in TIPOS_PREGUNTA:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_PREGUNTA)}"}), 400

    pregunta = Pregunta(
        cuestionario_id=cuestionario_id,
        codigo=codigo,
        texto=texto,
        tipo=tipo,
        obligatoria=data.get("obligatoria", True),
        orden=data.get("orden", 0),
        activa=data.get("activa", True),
    )
    db.session.add(pregunta)
    db.session.commit()

    # Atajo: permite mandar las opciones junto con la pregunta.
    for op in data.get("opciones", []):
        db.session.add(
            OpcionRespuesta(
                pregunta_id=pregunta.id,
                deporte_id=op.get("deporte_id"),
                codigo_id=op.get("codigo_id"),
                texto=op["texto"],
                orden=op.get("orden", 0),
            )
        )
    db.session.commit()

    return jsonify(pregunta.to_dict(con_opciones=True)), 201


@cuestionarios_bp.route("/preguntas/<int:pregunta_id>", methods=["PUT"])
@admin_required
def actualizar_pregunta(pregunta_id):
    pregunta = Pregunta.query.get_or_404(pregunta_id)
    data = request.get_json(force=True, silent=True) or {}

    if "tipo" in data and data["tipo"] not in TIPOS_PREGUNTA:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_PREGUNTA)}"}), 400

    for campo in ("codigo", "texto", "tipo", "obligatoria", "orden", "activa"):
        if campo in data:
            setattr(pregunta, campo, data[campo])
    db.session.commit()
    return jsonify(pregunta.to_dict(con_opciones=True)), 200


@cuestionarios_bp.route("/preguntas/<int:pregunta_id>", methods=["DELETE"])
@admin_required
def eliminar_pregunta(pregunta_id):
    pregunta = Pregunta.query.get_or_404(pregunta_id)
    db.session.delete(pregunta)
    db.session.commit()
    return "", 204


@cuestionarios_bp.route("/preguntas/<int:pregunta_id>/opciones", methods=["POST"])
@admin_required
def agregar_opcion(pregunta_id):
    Pregunta.query.get_or_404(pregunta_id)
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("texto"):
        return jsonify({"error": "texto es obligatorio"}), 400

    opcion = OpcionRespuesta(
        pregunta_id=pregunta_id,
        deporte_id=data.get("deporte_id"),
        codigo_id=data.get("codigo_id"),
        texto=data["texto"],
        orden=data.get("orden", 0),
    )
    db.session.add(opcion)
    db.session.commit()
    return jsonify(opcion.to_dict()), 201


@cuestionarios_bp.route("/opciones/<int:opcion_id>", methods=["DELETE"])
@admin_required
def eliminar_opcion(opcion_id):
    opcion = OpcionRespuesta.query.get_or_404(opcion_id)
    db.session.delete(opcion)
    db.session.commit()
    return "", 204


# ============ RESPONDER (usuario autenticado) ============

@cuestionarios_bp.route("/<string:codigo>/responder", methods=["POST"])
@jwt_required()
def responder_cuestionario(codigo):
    """Body: {"respuestas": [{"pregunta_id": 1, "opcion_id": 3}, {"pregunta_id": 2, "respuesta_texto": "..."}]}
    Si el usuario ya había respondido una pregunta, se sobreescribe (permite editar el registro).
    """
    cuestionario = Cuestionario.query.filter_by(codigo=codigo, activo=True).first()
    if not cuestionario:
        return jsonify({"error": "Cuestionario no encontrado o inactivo"}), 404

    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    respuestas = data.get("respuestas", [])
    if not isinstance(respuestas, list) or not respuestas:
        return jsonify({"error": "respuestas debe ser una lista con al menos un elemento"}), 400

    ids_preguntas_validas = {p.id for p in cuestionario.preguntas}
    guardadas = []

    for r in respuestas:
        pregunta_id = r.get("pregunta_id")
        if pregunta_id not in ids_preguntas_validas:
            return jsonify({"error": f"pregunta_id {pregunta_id} no pertenece a este cuestionario"}), 400

        existente = RespuestaUsuario.query.filter_by(
            usuario_id=usuario.id, pregunta_id=pregunta_id
        ).first()
        if existente:
            existente.opcion_id = r.get("opcion_id")
            existente.respuesta_texto = r.get("respuesta_texto")
            guardadas.append(existente)
        else:
            nueva = RespuestaUsuario(
                usuario_id=usuario.id,
                pregunta_id=pregunta_id,
                opcion_id=r.get("opcion_id"),
                respuesta_texto=r.get("respuesta_texto"),
            )
            db.session.add(nueva)
            guardadas.append(nueva)

    db.session.commit()
    return jsonify([g.to_dict() for g in guardadas]), 201


@cuestionarios_bp.route("/me/respuestas", methods=["GET"])
@jwt_required()
def mis_respuestas():
    usuario = get_usuario_actual()
    respuestas = RespuestaUsuario.query.filter_by(usuario_id=usuario.id).all()
    return jsonify([r.to_dict() for r in respuestas]), 200

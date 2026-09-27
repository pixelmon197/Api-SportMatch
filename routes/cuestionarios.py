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
    if Pregunta.query.filter_by(cuestionario_id=cuestionario_id, codigo=codigo).first():
        return jsonify({"error": "Ya existe una pregunta con ese código en este cuestionario"}), 409

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
    db.session.flush()

    # Atajo: permite mandar las opciones junto con la pregunta.
    codigos_usados = set()
    for op in data.get("opciones", []):
        codigo_opcion = op.get("codigo")
        if not codigo_opcion or not op.get("texto"):
            db.session.rollback()
            return jsonify({"error": "cada opción necesita codigo y texto"}), 400
        if codigo_opcion in codigos_usados:
            db.session.rollback()
            return jsonify({"error": f"codigo '{codigo_opcion}' repetido entre las opciones"}), 400
        codigos_usados.add(codigo_opcion)
        db.session.add(
            OpcionRespuesta(
                pregunta_id=pregunta.id,
                deporte_id=op.get("deporte_id"),
                codigo=codigo_opcion,
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
    if "codigo" in data and data["codigo"] != pregunta.codigo:
        if Pregunta.query.filter_by(cuestionario_id=pregunta.cuestionario_id, codigo=data["codigo"]).first():
            return jsonify({"error": "Ya existe una pregunta con ese código en este cuestionario"}), 409

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
    codigo = data.get("codigo")
    if not data.get("texto") or not codigo:
        return jsonify({"error": "codigo y texto son obligatorios"}), 400
    if OpcionRespuesta.query.filter_by(pregunta_id=pregunta_id, codigo=codigo).first():
        return jsonify({"error": "Ya existe una opción con ese código en esta pregunta"}), 409

    opcion = OpcionRespuesta(
        pregunta_id=pregunta_id,
        deporte_id=data.get("deporte_id"),
        codigo=codigo,
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
    Para una pregunta de tipo "opcion_multiple" se pueden mandar varias
    entradas con el mismo pregunta_id (una por cada opción elegida).
    Cada llamada reemplaza por completo las respuestas previas del usuario
    para las preguntas incluidas en el body (permite editar el registro).
    """
    cuestionario = Cuestionario.query.filter_by(codigo=codigo, activo=True).first()
    if not cuestionario:
        return jsonify({"error": "Cuestionario no encontrado o inactivo"}), 404

    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    respuestas = data.get("respuestas", [])
    if not isinstance(respuestas, list) or not respuestas:
        return jsonify({"error": "respuestas debe ser una lista con al menos un elemento"}), 400

    preguntas_por_id = {p.id: p for p in cuestionario.preguntas}

    # Agrupa por pregunta_id: una pregunta de opción múltiple puede traer
    # varias entradas (una por opción elegida).
    por_pregunta = {}
    for r in respuestas:
        pregunta_id = r.get("pregunta_id")
        if pregunta_id not in preguntas_por_id:
            return jsonify({"error": f"pregunta_id {pregunta_id} no pertenece a este cuestionario"}), 400
        por_pregunta.setdefault(pregunta_id, []).append(r)

    # Valida todo antes de tocar la base (para no dejar cambios a medias).
    filas_por_pregunta = {}
    for pregunta_id, items in por_pregunta.items():
        pregunta = preguntas_por_id[pregunta_id]
        if len(items) > 1 and pregunta.tipo != "opcion_multiple":
            return jsonify({"error": f"pregunta_id {pregunta_id} no acepta múltiples respuestas"}), 400
        filas = []
        for r in items:
            opcion_id = r.get("opcion_id")
            respuesta_texto = r.get("respuesta_texto")
            # CHECK real de `respuestas_usuario`: opcion_id o respuesta_texto.
            if opcion_id is None and not respuesta_texto:
                return jsonify(
                    {"error": f"pregunta_id {pregunta_id}: se requiere opcion_id o respuesta_texto"}
                ), 400
            # FK compuesta real: la opción debe pertenecer a esa pregunta.
            if opcion_id is not None and not OpcionRespuesta.query.filter_by(
                id=opcion_id, pregunta_id=pregunta_id
            ).first():
                return jsonify(
                    {"error": f"opcion_id {opcion_id} no pertenece a la pregunta {pregunta_id}"}
                ), 400
            filas.append((opcion_id, respuesta_texto))
        filas_por_pregunta[pregunta_id] = filas

    guardadas = []
    for pregunta_id, filas in filas_por_pregunta.items():
        # Reemplaza cualquier respuesta previa de esta pregunta (permite
        # editar, y evita duplicados si antes había otra selección).
        RespuestaUsuario.query.filter_by(usuario_id=usuario.id, pregunta_id=pregunta_id).delete()
        for opcion_id, respuesta_texto in filas:
            fila = RespuestaUsuario(
                usuario_id=usuario.id,
                pregunta_id=pregunta_id,
                opcion_id=opcion_id,
                respuesta_texto=respuesta_texto,
            )
            db.session.add(fila)
            guardadas.append(fila)

    db.session.commit()
    return jsonify([g.to_dict() for g in guardadas]), 201


@cuestionarios_bp.route("/me/respuestas", methods=["GET"])
@jwt_required()
def mis_respuestas():
    usuario = get_usuario_actual()
    respuestas = RespuestaUsuario.query.filter_by(usuario_id=usuario.id).all()
    return jsonify([r.to_dict() for r in respuestas]), 200

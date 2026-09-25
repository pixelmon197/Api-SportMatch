from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from database import db
from models import Usuario, ROLES_VALIDOS, SEXOS_VALIDOS, TokenVerificacion
from utils.auth import get_usuario_actual
from utils.fechas import parse_date

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """Autoregistro público. Siempre crea el usuario con rol 'usuario';
    para dar de alta administradores se usa POST /api/usuarios/admins (solo admin).
    """
    data = request.get_json(force=True, silent=True) or {}

    nombre_completo = data.get("nombre_completo")
    nombre_usuario = (data.get("nombre_usuario") or "").strip().lower() or None
    correo = data.get("correo")
    password = data.get("password")
    fecha_nacimiento_raw = data.get("fecha_nacimiento")
    sexo = data.get("sexo")

    # La tabla `usuarios` en Neon exige (CHECK usuarios_check) que si
    # `registro_completo_en` no es nulo -> correo, fecha_nacimiento y sexo
    # tampoco lo sean. Como este registro marca `registro_completo_en` de
    # una vez, estos tres campos pasan a ser obligatorios aquí también.
    faltantes = [
        campo
        for campo, valor in {
            "nombre_completo": nombre_completo,
            "nombre_usuario": nombre_usuario,
            "correo": correo,
            "password": password,
            "fecha_nacimiento": fecha_nacimiento_raw,
            "sexo": sexo,
        }.items()
        if not valor
    ]
    if faltantes:
        return jsonify(
            {"error": f"Campos requeridos faltantes: {', '.join(faltantes)}"}
        ), 400

    if len(nombre_usuario) > 30:
        return jsonify({"error": "nombre_usuario no puede tener más de 30 caracteres"}), 400

    if sexo not in SEXOS_VALIDOS:
        return jsonify(
            {"error": f"sexo debe ser uno de: {', '.join(SEXOS_VALIDOS)}"}
        ), 400

    try:
        fecha_nacimiento = parse_date(fecha_nacimiento_raw)
    except ValueError:
        return jsonify({"error": "fecha_nacimiento debe tener formato YYYY-MM-DD"}), 400

    correo = correo.lower().strip()

    if Usuario.query.filter_by(correo=correo).first():
        return jsonify({"error": "Ese correo ya está registrado"}), 409
    if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
        return jsonify({"error": "Ese nombre de usuario ya existe"}), 409

    usuario = Usuario(
        nombre_completo=nombre_completo,
        nombre_usuario=nombre_usuario,
        correo=correo,
        rol="usuario",
        telefono=data.get("telefono"),
        sexo=sexo,
        fecha_de_nacimiento=fecha_nacimiento,
        ciudad_id=data.get("ciudad_id"),
        registro_completo_en=datetime.now(timezone.utc),
    )
    usuario.set_password(password)

    db.session.add(usuario)
    db.session.commit()

    access_token = create_access_token(
        identity=str(usuario.id),
        additional_claims={"rol": usuario.rol},
    )
    return jsonify({"access_token": access_token, "usuario": usuario.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    correo = data.get("correo")
    password = data.get("password")

    if not correo or not password:
        return jsonify({"error": "correo y password son obligatorios"}), 400

    usuario = Usuario.query.filter_by(correo=correo.lower().strip()).first()
    if not usuario or not usuario.check_password(password):
        return jsonify({"error": "Credenciales inválidas"}), 401
    if usuario.estado_cuenta != "activa":
        return jsonify({"error": f"La cuenta está en estado '{usuario.estado_cuenta}'"}), 403

    usuario.ultimo_acceso = datetime.now(timezone.utc)
    db.session.commit()

    access_token = create_access_token(
        identity=str(usuario.id),
        additional_claims={"rol": usuario.rol},
    )
    return jsonify({"access_token": access_token, "usuario": usuario.to_dict()}), 200


@auth_bp.route("/olvide-contrasena", methods=["POST"])
def olvide_contrasena():
    """Inicia el flujo de recuperación de contraseña.

    Siempre responde 200 con un mensaje genérico (no confirma si el correo
    existe, para no filtrar qué correos están registrados). Mientras no
    haya un servicio de envío de correo integrado, el token de un solo uso
    se regresa en `token_reseteo` únicamente para pruebas locales; en
    producción ese token se debe enviar por correo y nunca en la respuesta.
    """
    data = request.get_json(force=True, silent=True) or {}
    correo = (data.get("correo") or "").lower().strip()

    if not correo:
        return jsonify({"error": "correo es obligatorio"}), 400

    respuesta = {
        "mensaje": "Si el correo está registrado, se enviarán instrucciones para restablecer la contraseña."
    }

    usuario = Usuario.query.filter_by(correo=correo).first()
    if usuario:
        _, token_plano = TokenVerificacion.generar(
            usuario.id, "restablecer_contrasena", minutos_validez=30
        )
        # TODO: enviar `token_plano` por correo cuando exista un servicio de
        # email; por ahora se expone en la respuesta solo para pruebas.
        respuesta["token_reseteo"] = token_plano

    return jsonify(respuesta), 200


@auth_bp.route("/restablecer-contrasena", methods=["POST"])
def restablecer_contrasena():
    """Completa el flujo de recuperación: intercambia el token de un solo
    uso (obtenido en /olvide-contrasena) por una contraseña nueva."""
    data = request.get_json(force=True, silent=True) or {}
    token_plano = data.get("token")
    nueva_password = data.get("nueva_password")

    if not token_plano or not nueva_password:
        return jsonify({"error": "token y nueva_password son obligatorios"}), 400
    if len(nueva_password) < 8:
        return jsonify({"error": "nueva_password debe tener al menos 8 caracteres"}), 400

    token = TokenVerificacion.buscar_valido("restablecer_contrasena", token_plano)
    if token is None:
        return jsonify({"error": "Token inválido, expirado o ya utilizado"}), 400

    usuario = Usuario.query.get(token.usuario_id)
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    usuario.set_password(nueva_password)
    token.marcar_usado()  # hace commit de la sesión completa (usuario + token)

    return jsonify({"mensaje": "Contraseña actualizada correctamente"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    usuario = get_usuario_actual()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(usuario.to_dict()), 200

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from database import db
from models import Usuario, ROLES_VALIDOS
from utils.auth import get_usuario_actual

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """Autoregistro público. Siempre crea el usuario con rol 'usuario';
    para dar de alta administradores se usa POST /api/usuarios/admins (solo admin).
    """
    data = request.get_json(force=True, silent=True) or {}

    nombre_completo = data.get("nombre_completo")
    nombre_usuario = data.get("nombre_usuario")
    correo = data.get("correo")
    password = data.get("password")

    faltantes = [
        campo
        for campo, valor in {
            "nombre_completo": nombre_completo,
            "nombre_usuario": nombre_usuario,
            "correo": correo,
            "password": password,
        }.items()
        if not valor
    ]
    if faltantes:
        return jsonify(
            {"error": f"Campos requeridos faltantes: {', '.join(faltantes)}"}
        ), 400

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
        sexo=data.get("sexo"),
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


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    usuario = get_usuario_actual()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(usuario.to_dict()), 200

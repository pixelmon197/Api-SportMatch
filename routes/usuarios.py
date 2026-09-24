from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from database import db
from models import Usuario, ROLES_VALIDOS, ESTADOS_CUENTA
from utils.auth import admin_required, get_usuario_actual
from utils.auditoria import registrar_auditoria

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/api/usuarios")


# ============ PERFIL PROPIO (cualquier usuario autenticado) ============

@usuarios_bp.route("/me", methods=["PUT"])
@jwt_required()
def actualizar_perfil_propio():
    """El usuario autenticado edita sus propios datos (no su rol ni estado)."""
    usuario = get_usuario_actual()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    data = request.get_json(force=True, silent=True) or {}
    for campo in ("nombre_completo", "telefono", "sexo", "idioma", "zona_horaria", "ciudad_id"):
        if campo in data:
            setattr(usuario, campo, data[campo])

    db.session.commit()
    return jsonify(usuario.to_dict()), 200


@usuarios_bp.route("/me/password", methods=["PUT"])
@jwt_required()
def cambiar_password_propio():
    usuario = get_usuario_actual()
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    data = request.get_json(force=True, silent=True) or {}
    actual = data.get("password_actual")
    nueva = data.get("password_nueva")

    if not actual or not nueva:
        return jsonify({"error": "password_actual y password_nueva son obligatorios"}), 400
    if not usuario.check_password(actual):
        return jsonify({"error": "La contraseña actual no es correcta"}), 401

    usuario.set_password(nueva)
    db.session.commit()
    return jsonify({"mensaje": "Contraseña actualizada"}), 200


# ============ ADMINISTRACIÓN DE USUARIOS (solo admin) ============

@usuarios_bp.route("", methods=["GET"])
@admin_required
def listar_usuarios():
    """Lista usuarios con filtros y paginación simples.
    Query params: page, per_page, rol, estado_cuenta, q (busca en nombre/correo).
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Usuario.query
    if rol := request.args.get("rol"):
        query = query.filter_by(rol=rol)
    if estado := request.args.get("estado_cuenta"):
        query = query.filter_by(estado_cuenta=estado)
    if q := request.args.get("q"):
        like = f"%{q}%"
        query = query.filter(
            (Usuario.nombre_completo.ilike(like)) | (Usuario.correo.ilike(like))
        )

    paginado = query.order_by(Usuario.id).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "usuarios": [u.to_dict() for u in paginado.items],
            "total": paginado.total,
            "page": page,
            "per_page": per_page,
            "paginas": paginado.pages,
        }
    ), 200


@usuarios_bp.route("/<int:usuario_id>", methods=["GET"])
@admin_required
def obtener_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    return jsonify(usuario.to_dict()), 200


@usuarios_bp.route("/<int:usuario_id>/rol", methods=["PUT"])
@admin_required
def cambiar_rol(usuario_id):
    """Sube/baja privilegios de un usuario (lo hace admin, como en arsh_cssi)."""
    usuario = Usuario.query.get_or_404(usuario_id)
    data = request.get_json(force=True, silent=True) or {}
    nuevo_rol = data.get("rol")

    if nuevo_rol not in ROLES_VALIDOS:
        return jsonify({"error": f"rol debe ser uno de: {', '.join(ROLES_VALIDOS)}"}), 400

    rol_anterior = usuario.rol
    usuario.rol = nuevo_rol
    db.session.commit()

    if rol_anterior != nuevo_rol:
        registrar_auditoria(
            usuario_id=get_jwt_identity(),
            accion="usuario.cambiar_rol",
            tipo_entidad="usuario",
            entidad_id=usuario.id,
            antes={"rol": rol_anterior},
            despues={"rol": nuevo_rol},
        )
    return jsonify(usuario.to_dict()), 200


@usuarios_bp.route("/<int:usuario_id>/estado", methods=["PUT"])
@admin_required
def cambiar_estado(usuario_id):
    """Activa, suspende o marca como eliminada (borrado suave) una cuenta."""
    usuario = Usuario.query.get_or_404(usuario_id)
    data = request.get_json(force=True, silent=True) or {}
    nuevo_estado = data.get("estado_cuenta")

    if nuevo_estado not in ESTADOS_CUENTA:
        return jsonify({"error": f"estado_cuenta debe ser uno de: {', '.join(ESTADOS_CUENTA)}"}), 400

    estado_anterior = usuario.estado_cuenta
    usuario.estado_cuenta = nuevo_estado
    if nuevo_estado == "eliminada":
        usuario.eliminado_en = datetime.now(timezone.utc)
    db.session.commit()

    if estado_anterior != nuevo_estado:
        registrar_auditoria(
            usuario_id=get_jwt_identity(),
            accion="usuario.cambiar_estado",
            tipo_entidad="usuario",
            entidad_id=usuario.id,
            antes={"estado_cuenta": estado_anterior},
            despues={"estado_cuenta": nuevo_estado},
        )
    return jsonify(usuario.to_dict()), 200


@usuarios_bp.route("/admins", methods=["POST"])
@admin_required
def crear_admin():
    """Un admin da de alta a otro administrador (equivalente a /auth/register,
    pero forzando rol='admin'; solo accesible por un admin ya autenticado).
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
        return jsonify({"error": f"Campos requeridos faltantes: {', '.join(faltantes)}"}), 400

    correo = correo.lower().strip()
    if Usuario.query.filter_by(correo=correo).first():
        return jsonify({"error": "Ese correo ya está registrado"}), 409
    if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
        return jsonify({"error": "Ese nombre de usuario ya existe"}), 409

    admin = Usuario(
        nombre_completo=nombre_completo,
        nombre_usuario=nombre_usuario,
        correo=correo,
        rol="admin",
        registro_completo_en=datetime.now(timezone.utc),
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    return jsonify(admin.to_dict()), 201

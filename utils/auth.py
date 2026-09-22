from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity

from models import Usuario


def roles_required(*roles):
    """
    Exige un JWT válido y que el rol del usuario esté en `roles`.
    Uso: @roles_required("admin") o @roles_required("admin", "usuario")
    """

    def decorador(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("rol") not in roles:
                return jsonify(
                    {"error": "No tienes permisos para realizar esta acción"}
                ), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorador


def admin_required(fn):
    """Exige un JWT válido con rol 'admin'."""
    return roles_required("admin")(fn)


def usuario_autenticado_required(fn):
    """Exige un JWT válido, sin importar el rol."""
    return roles_required("usuario", "admin")(fn)


def get_usuario_actual():
    """Regresa el objeto Usuario autenticado a partir del JWT (o None)."""
    verify_jwt_in_request()
    return Usuario.query.get(int(get_jwt_identity()))

from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

# Nombres de rol tal como estarán en la tabla `roles`.
ROL_ADMIN = "admin"


def roles_required(*roles):
    """
    Exige un JWT válido y que el rol del usuario esté en `roles`.
    Uso: @roles_required(ROL_ADMIN) o @roles_required(ROL_ADMIN, "otro_rol")
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
    return roles_required(ROL_ADMIN)(fn)

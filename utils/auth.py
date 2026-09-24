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


def es_miembro_organizador(usuario, organizador_id, roles_permitidos=("propietario", "administrador")):
    """¿El usuario pertenece al equipo de ese organizador, con rol suficiente?"""
    from models import OrganizadorMiembro  # import local: evita ciclo de imports

    if organizador_id is None:
        return False
    miembro = OrganizadorMiembro.query.get((organizador_id, usuario.id))
    return miembro is not None and miembro.rol in roles_permitidos


def puede_gestionar_organizador(usuario, organizador_id):
    """Admin, o miembro (propietario/administrador) de ese organizador."""
    if usuario.rol == "admin":
        return True
    return es_miembro_organizador(usuario, organizador_id)


def puede_gestionar_evento(usuario, evento):
    """Admin, o miembro del organizador dueño del evento. Un evento sin
    organizador_id (creado directo por la plataforma) solo lo gestiona admin."""
    if usuario.rol == "admin":
        return True
    if evento.organizador_id is None:
        return False
    return es_miembro_organizador(usuario, evento.organizador_id)

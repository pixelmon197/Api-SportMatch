"""Reglas compartidas del módulo social (perfiles, seguidores, amistades y
bloqueos): quién consulta, quién es amigo de quién, quién bloqueó a quién y
quién puede ver un perfil."""

from math import ceil

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from database import db
from models import Amistad, Bloqueo, Perfil, Seguidor, Usuario


def usuario_que_consulta():
    """Quien hace la petición, o None si no mandó token (los perfiles
    públicos se pueden ver sin iniciar sesión)."""
    verify_jwt_in_request(optional=True)
    identidad = get_jwt_identity()
    return Usuario.query.get(int(identidad)) if identidad else None


def son_amigos(a_id, b_id):
    """Amistad aceptada en cualquiera de los dos sentidos."""
    return (
        Amistad.query.filter(
            Amistad.estado == "aceptada",
            db.or_(
                db.and_(Amistad.usuario_id == a_id, Amistad.amigo_id == b_id),
                db.and_(Amistad.usuario_id == b_id, Amistad.amigo_id == a_id),
            ),
        ).first()
        is not None
    )


def yo_bloquee(yo_id, otro_id):
    return Bloqueo.query.get((yo_id, otro_id)) is not None


def hay_bloqueo(a_id, b_id):
    """¿Alguno de los dos bloqueó al otro?"""
    return yo_bloquee(a_id, b_id) or yo_bloquee(b_id, a_id)


def cuenta_disponible(usuario):
    return usuario is not None and usuario.estado_cuenta == "activa" and usuario.eliminado_en is None


def perfil_o_valores_por_defecto(usuario):
    """Para consultar el perfil de OTRA persona sin escribir en la base en
    una petición GET: si no tiene fila en `perfiles`, se arma uno con los
    defaults de Neon (no se guarda)."""
    perfil = Perfil.query.get(usuario.id)
    if perfil:
        return perfil
    return Perfil(
        usuario_id=usuario.id,
        visibilidad_perfil="publico",
        visibilidad_ubicacion="amigos",
        quien_puede_escribir="publico",
        aparecer_en_cercanos=True,
    )


def error_de_acceso_al_perfil(consulta, usuario, perfil):
    """None si `consulta` puede ver el perfil de `usuario`; si no, una
    tupla (mensaje, código_http). El dueño y los administradores siempre
    pueden. Un bloqueo en cualquier sentido o una cuenta no disponible dan
    404 (no se revela que existe); un perfil privado o solo para amigos, 403."""
    if consulta is not None and (consulta.id == usuario.id or consulta.rol == "administrador"):
        return None
    if not cuenta_disponible(usuario):
        return "Perfil no encontrado", 404
    if consulta is not None and hay_bloqueo(consulta.id, usuario.id):
        return "Perfil no encontrado", 404
    if perfil.visibilidad_perfil == "privado":
        return "Este perfil es privado", 403
    if perfil.visibilidad_perfil == "amigos" and not (
        consulta is not None and son_amigos(consulta.id, usuario.id)
    ):
        return "Este perfil solo es visible para sus amigos", 403
    return None


def contadores(usuario_id):
    amigos = Amistad.query.filter(
        Amistad.estado == "aceptada",
        db.or_(Amistad.usuario_id == usuario_id, Amistad.amigo_id == usuario_id),
    ).count()
    return {
        "seguidores": Seguidor.query.filter_by(seguido_id=usuario_id).count(),
        "siguiendo": Seguidor.query.filter_by(seguidor_id=usuario_id).count(),
        "amigos": amigos,
    }


def relacion_con(consulta, usuario):
    """Cómo se relaciona quien consulta con `usuario` (para que el cliente
    sepa si mostrar 'Seguir', 'Agregar amigo', 'Aceptar'...)."""
    if consulta is None or consulta.id == usuario.id:
        return None
    amistad, amistad_id = "ninguna", None
    filas = Amistad.query.filter(
        db.or_(
            db.and_(Amistad.usuario_id == consulta.id, Amistad.amigo_id == usuario.id),
            db.and_(Amistad.usuario_id == usuario.id, Amistad.amigo_id == consulta.id),
        )
    ).all()
    for fila in filas:
        if fila.estado == "aceptada":
            amistad, amistad_id = "aceptada", fila.id
            break
        if fila.estado == "pendiente":
            enviada = fila.usuario_id == consulta.id
            amistad, amistad_id = ("solicitud_enviada" if enviada else "solicitud_recibida"), fila.id
    return {
        "yo_sigo": Seguidor.query.get((consulta.id, usuario.id)) is not None,
        "me_sigue": Seguidor.query.get((usuario.id, consulta.id)) is not None,
        "amistad": amistad,
        "amistad_id": amistad_id,
    }


def ids_con_bloqueo_respecto_a(usuario_id):
    """Subconsulta con los ids de quienes bloquearon a `usuario_id` o
    fueron bloqueados por él, para excluirlos de sus listados."""
    bloqueados = db.session.query(Bloqueo.bloqueado_id).filter(Bloqueo.bloqueador_id == usuario_id)
    bloqueadores = db.session.query(Bloqueo.bloqueador_id).filter(Bloqueo.bloqueado_id == usuario_id)
    return bloqueados.union(bloqueadores)


def tarjetas(usuarios):
    """Datos mínimos y públicos de varios usuarios (con su avatar), sin
    hacer una consulta por cada uno."""
    ids = [u.id for u in usuarios]
    perfiles = {p.usuario_id: p for p in Perfil.query.filter(Perfil.usuario_id.in_(ids)).all()} if ids else {}
    resultado = {}
    for u in usuarios:
        perfil = perfiles.get(u.id)
        resultado[u.id] = {
            "id": u.id,
            "nombre_completo": u.nombre_completo,
            "nombre_usuario": u.nombre_usuario,
            "avatar_url": perfil.avatar.url if perfil and perfil.avatar else None,
        }
    return resultado


def paginar(query, nombre_items, armar_item):
    """Paginación simple con el mismo formato que el resto de la API
    (`total`, `page`, `per_page`, `paginas`). `query` debe devolver filas
    cuya primera columna es el Usuario; `armar_item(tarjeta, fila)` arma
    cada elemento."""
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    total = query.count()
    filas = query.limit(per_page).offset((page - 1) * per_page).all()
    fichas = tarjetas([f[0] for f in filas])
    return {
        nombre_items: [armar_item(fichas[f[0].id], f) for f in filas],
        "total": total,
        "page": page,
        "per_page": per_page,
        "paginas": ceil(total / per_page) if total else 0,
    }

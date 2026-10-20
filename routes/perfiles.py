from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request

from database import db
from models import (
    Amistad,
    Bloqueo,
    Perfil,
    Usuario,
    UsuarioDeporte,
    VISIBILIDADES,
    BIOGRAFIA_MAX,
)
from utils.auth import get_usuario_actual
from utils.validaciones import validar_archivo

perfiles_bp = Blueprint("perfiles", __name__, url_prefix="/api/perfiles")


# ============ Utilidades ============

def _usuario_que_consulta():
    """Quien hace la petición, o None si no mandó token (los perfiles
    públicos se pueden ver sin iniciar sesión)."""
    verify_jwt_in_request(optional=True)
    identidad = get_jwt_identity()
    return Usuario.query.get(int(identidad)) if identidad else None


def _son_amigos(a_id, b_id):
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


def _hay_bloqueo(a_id, b_id):
    """¿Alguno de los dos bloqueó al otro?"""
    return (
        Bloqueo.query.filter(
            db.or_(
                db.and_(Bloqueo.bloqueador_id == a_id, Bloqueo.bloqueado_id == b_id),
                db.and_(Bloqueo.bloqueador_id == b_id, Bloqueo.bloqueado_id == a_id),
            )
        ).first()
        is not None
    )


def _perfil_propio(usuario):
    """El perfil del usuario; si todavía no tiene fila en `perfiles` (se
    crea de forma perezosa, no en el registro), se crea con los valores
    por defecto de Neon."""
    perfil = Perfil.query.get(usuario.id)
    if not perfil:
        perfil = Perfil(usuario_id=usuario.id)
        db.session.add(perfil)
        db.session.commit()
    return perfil


def _perfil_o_valores_por_defecto(usuario):
    """Para consultar el perfil de OTRA persona sin escribir en la base en
    una petición GET: si no tiene fila, se arma uno con los defaults (no
    se guarda)."""
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


def _datos_publicos_usuario(usuario):
    """Solo lo que es seguro mostrar a terceros (nada de correo, teléfono,
    fecha de nacimiento ni rol)."""
    return {
        "id": usuario.id,
        "nombre_completo": usuario.nombre_completo,
        "nombre_usuario": usuario.nombre_usuario,
        "ciudad": usuario.ciudad.to_dict() if usuario.ciudad else None,
    }


def _deportes_de(usuario_id):
    filas = UsuarioDeporte.query.filter_by(usuario_id=usuario_id).all()
    return [f.to_dict() for f in filas]


def _vista_completa(usuario, perfil):
    """Lo que ve el dueño de su propio perfil (o un admin)."""
    data = usuario.to_dict()
    data["perfil"] = perfil.to_dict(con_ubicacion=True, con_ajustes=True)
    data["deportes"] = _deportes_de(usuario.id)
    return data


def _vista_para(consulta, usuario, perfil):
    """Aplica las reglas de visibilidad. Regresa (respuesta, codigo_http)."""
    es_dueno = consulta is not None and consulta.id == usuario.id
    es_admin = consulta is not None and consulta.rol == "administrador"
    if es_dueno or es_admin:
        return _vista_completa(usuario, perfil), 200

    # Cuenta no disponible (suspendida/eliminada): se trata como inexistente.
    if usuario.estado_cuenta != "activa" or usuario.eliminado_en is not None:
        return {"error": "Perfil no encontrado"}, 404

    # Bloqueos en cualquier sentido: tampoco se revela que el perfil existe.
    if consulta is not None and _hay_bloqueo(consulta.id, usuario.id):
        return {"error": "Perfil no encontrado"}, 404

    amigos = consulta is not None and _son_amigos(consulta.id, usuario.id)

    if perfil.visibilidad_perfil == "privado":
        return {"error": "Este perfil es privado"}, 403
    if perfil.visibilidad_perfil == "amigos" and not amigos:
        return {"error": "Este perfil solo es visible para sus amigos"}, 403

    ver_ubicacion = perfil.visibilidad_ubicacion == "publico" or (
        perfil.visibilidad_ubicacion == "amigos" and amigos
    )
    data = _datos_publicos_usuario(usuario)
    data["perfil"] = perfil.to_dict(con_ubicacion=ver_ubicacion, con_ajustes=False)
    data["deportes"] = _deportes_de(usuario.id)
    return data, 200


# ============ Mi perfil ============

@perfiles_bp.route("/me", methods=["GET"])
@jwt_required()
def mi_perfil():
    """Mi usuario y mi perfil juntos (con mi ubicación y mis ajustes de
    privacidad). Si todavía no tenía perfil, se crea con los valores por
    defecto."""
    usuario = get_usuario_actual()
    return jsonify(_vista_completa(usuario, _perfil_propio(usuario))), 200


@perfiles_bp.route("/me", methods=["PUT"])
@jwt_required()
def actualizar_mi_perfil():
    """Edita mi perfil. Todos los campos son opcionales: solo cambia lo que
    se mande. Mandar `null` en `biografia`, `avatar_id` o `portada_id` los
    borra. Los datos de la cuenta (nombre, teléfono, ciudad, sexo...) se
    editan en PUT /api/usuarios/me."""
    usuario = get_usuario_actual()
    perfil = _perfil_propio(usuario)
    data = request.get_json(force=True, silent=True) or {}

    if "biografia" in data and data["biografia"] is not None:
        if not isinstance(data["biografia"], str):
            return jsonify({"error": "biografia debe ser texto"}), 400
        if len(data["biografia"]) > BIOGRAFIA_MAX:
            return jsonify({"error": f"biografia no puede tener más de {BIOGRAFIA_MAX} caracteres"}), 400

    for campo in ("visibilidad_perfil", "visibilidad_ubicacion", "quien_puede_escribir"):
        if campo in data and data[campo] not in VISIBILIDADES:
            return jsonify({"error": f"{campo} debe ser uno de: {', '.join(VISIBILIDADES)}"}), 400

    if "aparecer_en_cercanos" in data and not isinstance(data["aparecer_en_cercanos"], bool):
        return jsonify({"error": "aparecer_en_cercanos debe ser true o false"}), 400

    for campo in ("avatar_id", "portada_id"):
        if campo in data and (error := validar_archivo(data[campo], ("imagen",), campo)):
            return jsonify({"error": error}), 400

    for campo in (
        "biografia", "avatar_id", "portada_id", "visibilidad_perfil",
        "visibilidad_ubicacion", "quien_puede_escribir", "aparecer_en_cercanos",
    ):
        if campo in data:
            setattr(perfil, campo, data[campo])
    db.session.commit()
    return jsonify(_vista_completa(usuario, perfil)), 200


def _es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


@perfiles_bp.route("/me/ubicacion", methods=["PUT"])
@jwt_required()
def actualizar_mi_ubicacion():
    """Guarda mi ubicación actual (latitud/longitud) y la hora en que se
    actualizó. Quién la puede ver lo decide `visibilidad_ubicacion`."""
    usuario = get_usuario_actual()
    perfil = _perfil_propio(usuario)
    data = request.get_json(force=True, silent=True) or {}

    latitud, longitud = data.get("latitud"), data.get("longitud")
    if latitud is None or longitud is None:
        return jsonify({"error": "latitud y longitud son obligatorias"}), 400
    if not _es_numero(latitud) or not _es_numero(longitud):
        return jsonify({"error": "latitud y longitud deben ser números"}), 400
    if not -90 <= latitud <= 90:
        return jsonify({"error": "latitud debe estar entre -90 y 90"}), 400
    if not -180 <= longitud <= 180:
        return jsonify({"error": "longitud debe estar entre -180 y 180"}), 400

    perfil.latitud = latitud
    perfil.longitud = longitud
    perfil.ubicacion_actualizada_en = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(_vista_completa(usuario, perfil)), 200


@perfiles_bp.route("/me/ubicacion", methods=["DELETE"])
@jwt_required()
def borrar_mi_ubicacion():
    """Borra mi ubicación guardada."""
    usuario = get_usuario_actual()
    perfil = _perfil_propio(usuario)
    perfil.latitud = None
    perfil.longitud = None
    perfil.ubicacion_actualizada_en = None
    db.session.commit()
    return jsonify(_vista_completa(usuario, perfil)), 200


# ============ Perfil de otras personas ============

@perfiles_bp.route("/<int:usuario_id>", methods=["GET"])
def ver_perfil(usuario_id):
    """Perfil de otro usuario, respetando su visibilidad (público / amigos /
    privado), los bloqueos y el estado de su cuenta. Se puede consultar sin
    iniciar sesión mientras el perfil sea público."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"error": "Perfil no encontrado"}), 404
    respuesta, codigo = _vista_para(_usuario_que_consulta(), usuario, _perfil_o_valores_por_defecto(usuario))
    return jsonify(respuesta), codigo


@perfiles_bp.route("/usuario/<string:nombre_usuario>", methods=["GET"])
def ver_perfil_por_nombre_usuario(nombre_usuario):
    """Igual que GET /api/perfiles/{usuario_id}, pero buscando por
    `nombre_usuario` (sin importar mayúsculas)."""
    usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario.strip().lower()).first()
    if not usuario:
        return jsonify({"error": "Perfil no encontrado"}), 404
    respuesta, codigo = _vista_para(_usuario_que_consulta(), usuario, _perfil_o_valores_por_defecto(usuario))
    return jsonify(respuesta), codigo

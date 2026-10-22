import re
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import Comision, Cupon, Organizador, CONCEPTOS, TIPOS_DESCUENTO
from utils.auth import admin_required, get_usuario_actual, puede_gestionar_organizador
from utils.fechas import parse_date, parse_datetime
from utils.paginacion import paginar_query
from utils.pagos import comision_vigente, usos_de_cupon

cupones_bp = Blueprint("cupones", __name__, url_prefix="/api")

_CODIGO = re.compile(r"^[A-Z0-9_-]{3,30}$")


def _es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


# ============ Comisiones ============

@cupones_bp.route("/comisiones", methods=["GET"])
@admin_required
def listar_comisiones():
    """Historial de comisiones de la plataforma (admin)."""
    filas = Comision.query.order_by(Comision.concepto, Comision.vigente_desde.desc()).all()
    return jsonify([c.to_dict() for c in filas]), 200


@cupones_bp.route("/comisiones/vigente", methods=["GET"])
@jwt_required()
def comision_actual():
    """El porcentaje que hoy se queda la plataforma. Query param: concepto
    (por defecto `inscripcion`). `por_defecto: true` significa que no hay
    ninguna registrada y se está usando el valor de configuración."""
    concepto = request.args.get("concepto", "inscripcion")
    if concepto not in CONCEPTOS:
        return jsonify({"error": f"concepto debe ser uno de: {', '.join(CONCEPTOS)}"}), 400
    porcentaje, por_defecto = comision_vigente(concepto)
    return jsonify({"concepto": concepto, "porcentaje": float(porcentaje), "por_defecto": por_defecto}), 200


@cupones_bp.route("/comisiones", methods=["POST"])
@admin_required
def crear_comision():
    """Define una nueva comisión (admin). Cierra la anterior del mismo
    concepto el día antes de la nueva. Body: {"concepto": "inscripcion",
    "porcentaje": 12.5, "vigente_desde": "2026-11-01"} (vigente_desde es
    opcional, por defecto hoy)."""
    data = request.get_json(force=True, silent=True) or {}
    concepto = data.get("concepto")
    if concepto not in CONCEPTOS:
        return jsonify({"error": f"concepto debe ser uno de: {', '.join(CONCEPTOS)}"}), 400
    porcentaje = data.get("porcentaje")
    if not _es_numero(porcentaje) or not 0 <= porcentaje <= 100:
        return jsonify({"error": "porcentaje debe ser un número entre 0 y 100"}), 400
    try:
        desde = parse_date(data.get("vigente_desde")) or date.today()
    except (ValueError, TypeError):
        return jsonify({"error": "vigente_desde debe tener formato YYYY-MM-DD"}), 400

    ultima = Comision.query.filter_by(concepto=concepto).order_by(Comision.vigente_desde.desc()).first()
    if ultima is not None:
        if desde <= ultima.vigente_desde:
            return jsonify({
                "error": f"vigente_desde debe ser posterior al de la comisión actual ({ultima.vigente_desde.isoformat()})"
            }), 409
        if ultima.vigente_hasta is None or ultima.vigente_hasta >= desde:
            ultima.vigente_hasta = desde - timedelta(days=1)

    comision = Comision(concepto=concepto, porcentaje=porcentaje, vigente_desde=desde)
    db.session.add(comision)
    db.session.commit()
    return jsonify(comision.to_dict()), 201


# ============ Cupones ============

def _puede_gestionar_cupon(usuario, organizador_id):
    """Los cupones de la plataforma (sin organizador) solo los maneja un
    admin; los de un organizador, también sus miembros con permisos."""
    if usuario.rol == "administrador":
        return True
    return organizador_id is not None and puede_gestionar_organizador(usuario, organizador_id)


def _cupon_json(cupon):
    return {**cupon.to_dict(), "usos": usos_de_cupon(cupon.id)}


def _validar_valor(tipo, valor):
    if not _es_numero(valor) or valor <= 0:
        return "valor debe ser un número mayor a 0"
    if tipo == "porcentaje" and valor > 100:
        return "un cupón de porcentaje no puede pasar de 100"
    return None


@cupones_bp.route("/cupones", methods=["POST"])
@jwt_required()
def crear_cupon():
    """Crea un cupón de descuento. Un admin puede crear cupones de la
    plataforma (sin `organizador_id`, valen en cualquier evento); un
    organizador, solo para sus propios eventos (`organizador_id`
    obligatorio). El código se guarda en mayúsculas."""
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}

    codigo = str(data.get("codigo") or "").strip().upper()
    if not _CODIGO.match(codigo):
        return jsonify({"error": "codigo debe tener de 3 a 30 caracteres: letras, números, guion o guion bajo"}), 400
    tipo = data.get("tipo_descuento")
    if tipo not in TIPOS_DESCUENTO:
        return jsonify({"error": f"tipo_descuento debe ser uno de: {', '.join(TIPOS_DESCUENTO)}"}), 400
    if error := _validar_valor(tipo, data.get("valor")):
        return jsonify({"error": error}), 400
    concepto = data.get("concepto")
    if concepto is not None and concepto not in CONCEPTOS:
        return jsonify({"error": f"concepto debe ser uno de: {', '.join(CONCEPTOS)}"}), 400
    descripcion = data.get("descripcion")
    if descripcion is not None and (not isinstance(descripcion, str) or len(descripcion) > 200):
        return jsonify({"error": "descripcion debe ser texto de máximo 200 caracteres"}), 400

    organizador_id = data.get("organizador_id")
    if organizador_id is None and usuario.rol != "administrador":
        return jsonify({"error": "organizador_id es obligatorio (solo un admin crea cupones de toda la plataforma)"}), 400
    if organizador_id is not None:
        if Organizador.query.get(organizador_id) is None:
            return jsonify({"error": "organizador_id no corresponde a un organizador existente"}), 400
    if not _puede_gestionar_cupon(usuario, organizador_id):
        return jsonify({"error": "No perteneces a ese organizador"}), 403

    try:
        desde = parse_datetime(data.get("vigente_desde"))
        hasta = parse_datetime(data.get("vigente_hasta"))
    except (ValueError, TypeError):
        return jsonify({"error": "vigente_desde y vigente_hasta deben ser fechas ISO (YYYY-MM-DDTHH:MM:SS)"}), 400
    if desde and hasta and hasta <= desde:
        return jsonify({"error": "vigente_hasta debe ser posterior a vigente_desde"}), 400

    usos_maximos = data.get("usos_maximos")
    if usos_maximos is not None and (not isinstance(usos_maximos, int) or isinstance(usos_maximos, bool) or usos_maximos < 1):
        return jsonify({"error": "usos_maximos debe ser un entero mayor o igual a 1"}), 400
    por_usuario = data.get("usos_por_usuario", 1)
    if not isinstance(por_usuario, int) or isinstance(por_usuario, bool) or por_usuario < 1:
        return jsonify({"error": "usos_por_usuario debe ser un entero mayor o igual a 1"}), 400

    if Cupon.query.filter_by(codigo=codigo).first():
        return jsonify({"error": "Ya existe un cupón con ese código"}), 409

    cupon = Cupon(
        codigo=codigo, descripcion=descripcion, tipo_descuento=tipo, concepto=concepto,
        organizador_id=organizador_id, valor=data["valor"], usos_maximos=usos_maximos,
        usos_por_usuario=por_usuario, activo=data.get("activo", True) is not False,
        vigente_hasta=hasta,
    )
    if desde:
        cupon.vigente_desde = desde
    db.session.add(cupon)
    db.session.commit()
    return jsonify(_cupon_json(cupon)), 201


@cupones_bp.route("/cupones", methods=["GET"])
@jwt_required()
def listar_cupones():
    """Un admin ve todos (y puede filtrar por `organizador_id`); un
    organizador debe mandar `organizador_id` de un organizador suyo. Query
    params: organizador_id, activo (true/false), page, per_page."""
    usuario = get_usuario_actual()
    organizador_id = request.args.get("organizador_id", type=int)
    if not _puede_gestionar_cupon(usuario, organizador_id):
        if organizador_id is None:
            return jsonify({"error": "Manda organizador_id para ver los cupones de tu organizador"}), 400
        return jsonify({"error": "No perteneces a ese organizador"}), 403
    query = Cupon.query
    if organizador_id is not None:
        query = query.filter_by(organizador_id=organizador_id)
    activo = request.args.get("activo")
    if activo is not None:
        query = query.filter_by(activo=activo.lower() in ("1", "true", "si", "sí"))
    return jsonify(paginar_query(query.order_by(Cupon.id.desc()), "cupones", _cupon_json)), 200


@cupones_bp.route("/cupones/<int:cupon_id>", methods=["PUT"])
@jwt_required()
def actualizar_cupon(cupon_id):
    """Edita un cupón. Se puede cambiar: descripcion, valor, vigente_hasta,
    usos_maximos, usos_por_usuario y activo (el código y el tipo no)."""
    usuario = get_usuario_actual()
    cupon = Cupon.query.get_or_404(cupon_id)
    if not _puede_gestionar_cupon(usuario, cupon.organizador_id):
        return jsonify({"error": "No tienes permisos sobre este cupón"}), 403
    data = request.get_json(force=True, silent=True) or {}

    if "valor" in data and (error := _validar_valor(cupon.tipo_descuento, data["valor"])):
        return jsonify({"error": error}), 400
    if "descripcion" in data and data["descripcion"] is not None and (
        not isinstance(data["descripcion"], str) or len(data["descripcion"]) > 200
    ):
        return jsonify({"error": "descripcion debe ser texto de máximo 200 caracteres"}), 400
    if "usos_maximos" in data and data["usos_maximos"] is not None and (
        not isinstance(data["usos_maximos"], int) or isinstance(data["usos_maximos"], bool) or data["usos_maximos"] < 1
    ):
        return jsonify({"error": "usos_maximos debe ser un entero mayor o igual a 1"}), 400
    if "usos_por_usuario" in data and (
        not isinstance(data["usos_por_usuario"], int) or isinstance(data["usos_por_usuario"], bool) or data["usos_por_usuario"] < 1
    ):
        return jsonify({"error": "usos_por_usuario debe ser un entero mayor o igual a 1"}), 400
    if "activo" in data and not isinstance(data["activo"], bool):
        return jsonify({"error": "activo debe ser true o false"}), 400
    if "vigente_hasta" in data:
        try:
            hasta = parse_datetime(data["vigente_hasta"])
        except (ValueError, TypeError):
            return jsonify({"error": "vigente_hasta debe ser una fecha ISO (YYYY-MM-DDTHH:MM:SS)"}), 400
        if hasta and cupon.vigente_desde and hasta <= cupon.vigente_desde:
            return jsonify({"error": "vigente_hasta debe ser posterior a vigente_desde"}), 400
        cupon.vigente_hasta = hasta

    for campo in ("descripcion", "valor", "usos_maximos", "usos_por_usuario", "activo"):
        if campo in data:
            setattr(cupon, campo, data[campo])
    db.session.commit()
    return jsonify(_cupon_json(cupon)), 200

from datetime import datetime, time, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import CuentaCobro, Evento, Inscripcion, Liquidacion, Organizador, Pago, PagoInscripcion, ESTADOS_LIQUIDACION
from utils.auth import admin_required, get_usuario_actual, puede_gestionar_organizador
from utils.fechas import parse_date
from utils.paginacion import paginar_query
from utils.pagos import CERO

liquidaciones_bp = Blueprint("liquidaciones", __name__, url_prefix="/api")


@liquidaciones_bp.route("/liquidaciones", methods=["POST"])
@admin_required
def crear_liquidacion():
    """Arma la liquidación de un organizador: junta lo cobrado por sus
    eventos (pagos `pagado`, aún sin liquidar) en un periodo y lo registra
    para pagárselo a su cuenta de cobro verificada.

    Body: {"organizador_id": 1, "cuenta_cobro_id": 1,
           "periodo_desde": "2026-10-01", "periodo_hasta": "2026-10-31",
           "moneda": "MXN"}  (moneda es opcional, por defecto MXN).
    El periodo se compara contra la fecha en que se pagó cada pago.
    """
    data = request.get_json(force=True, silent=True) or {}
    faltantes = [c for c in ("organizador_id", "cuenta_cobro_id", "periodo_desde", "periodo_hasta") if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Campos requeridos faltantes: {', '.join(faltantes)}"}), 400

    organizador = Organizador.query.get(data["organizador_id"])
    if organizador is None:
        return jsonify({"error": "organizador_id no corresponde a un organizador existente"}), 400
    cuenta = CuentaCobro.query.get(data["cuenta_cobro_id"])
    if cuenta is None or cuenta.organizador_id != organizador.id or cuenta.eliminado_en is not None:
        return jsonify({"error": "cuenta_cobro_id no es una cuenta de cobro de ese organizador"}), 400
    if not cuenta.verificada:
        return jsonify({"error": "La cuenta de cobro todavía no está verificada"}), 409

    try:
        desde, hasta = parse_date(data["periodo_desde"]), parse_date(data["periodo_hasta"])
    except (ValueError, TypeError):
        return jsonify({"error": "periodo_desde y periodo_hasta deben tener formato YYYY-MM-DD"}), 400
    if desde > hasta:
        return jsonify({"error": "periodo_desde no puede ser posterior a periodo_hasta"}), 400
    moneda = str(data.get("moneda", "MXN")).strip().upper()
    if len(moneda) != 3:
        return jsonify({"error": "moneda debe ser un código de 3 letras (p. ej. MXN)"}), 400

    inicio = datetime.combine(desde, time.min)
    fin = datetime.combine(hasta + timedelta(days=1), time.min)
    items = (
        db.session.query(PagoInscripcion)
        .join(Pago, Pago.id == PagoInscripcion.pago_id)
        .join(Inscripcion, Inscripcion.id == PagoInscripcion.inscripcion_id)
        .join(Evento, Evento.id == Inscripcion.evento_id)
        .filter(
            Evento.organizador_id == organizador.id,
            Pago.estado == "pagado",
            Pago.moneda == moneda,
            Pago.pagado_en >= inicio,
            Pago.pagado_en < fin,
            PagoInscripcion.liquidacion_id.is_(None),
            PagoInscripcion.monto_bruto > 0,
        )
        .all()
    )
    if not items:
        return jsonify({"error": "No hay pagos pendientes de liquidar de ese organizador en ese periodo"}), 409

    liquidacion = Liquidacion(
        organizador_id=organizador.id,
        cuenta_cobro_id=cuenta.id,
        estado="pendiente",
        periodo_desde=desde,
        periodo_hasta=hasta,
        monto_bruto=sum((i.monto_bruto for i in items), CERO),
        monto_comision=sum((i.comision_plataforma for i in items), CERO),
        monto_neto=sum((i.monto_organizador for i in items), CERO),
        moneda=moneda,
    )
    db.session.add(liquidacion)
    db.session.flush()
    for item in items:
        item.liquidacion_id = liquidacion.id
    db.session.commit()
    return jsonify(liquidacion.to_dict(detalle=True)), 201


@liquidaciones_bp.route("/liquidaciones", methods=["GET"])
@admin_required
def listar_liquidaciones():
    """Todas las liquidaciones (admin). Query params: organizador_id,
    estado, page, per_page."""
    query = Liquidacion.query
    if request.args.get("organizador_id", type=int):
        query = query.filter_by(organizador_id=request.args.get("organizador_id", type=int))
    estado = request.args.get("estado")
    if estado:
        if estado not in ESTADOS_LIQUIDACION:
            return jsonify({"error": f"estado debe ser uno de: {', '.join(ESTADOS_LIQUIDACION)}"}), 400
        query = query.filter_by(estado=estado)
    return jsonify(paginar_query(query.order_by(Liquidacion.id.desc()), "liquidaciones", lambda l: l.to_dict())), 200


@liquidaciones_bp.route("/liquidaciones/<int:liquidacion_id>", methods=["GET"])
@jwt_required()
def ver_liquidacion(liquidacion_id):
    """Detalle con los pagos incluidos (admin o miembro con permisos del
    organizador)."""
    usuario = get_usuario_actual()
    liquidacion = Liquidacion.query.get(liquidacion_id)
    if liquidacion is None or not puede_gestionar_organizador(usuario, liquidacion.organizador_id):
        return jsonify({"error": "Liquidación no encontrada"}), 404
    return jsonify(liquidacion.to_dict(detalle=True)), 200


@liquidaciones_bp.route("/liquidaciones/<int:liquidacion_id>/pagar", methods=["PUT"])
@admin_required
def pagar_liquidacion(liquidacion_id):
    """Registra que ya se le pagó al organizador. Body: {"referencia_pago":
    "SPEI-123456"} (folio o referencia de la transferencia)."""
    liquidacion = Liquidacion.query.get_or_404(liquidacion_id)
    if liquidacion.estado != "pendiente":
        return jsonify({"error": f"Esa liquidación ya estaba '{liquidacion.estado}'"}), 409
    referencia = (request.get_json(force=True, silent=True) or {}).get("referencia_pago")
    if not isinstance(referencia, str) or not referencia.strip():
        return jsonify({"error": "referencia_pago es obligatoria"}), 400
    if len(referencia) > 100:
        return jsonify({"error": "referencia_pago no puede tener más de 100 caracteres"}), 400
    liquidacion.estado = "pagada"
    liquidacion.referencia_pago = referencia.strip()
    liquidacion.pagada_en = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(liquidacion.to_dict()), 200


@liquidaciones_bp.route("/organizadores/<int:organizador_id>/liquidaciones", methods=["GET"])
@jwt_required()
def liquidaciones_de_organizador(organizador_id):
    """Liquidaciones de un organizador (admin o miembro con permisos).
    Query params: estado, page, per_page."""
    usuario = get_usuario_actual()
    if Organizador.query.get(organizador_id) is None:
        return jsonify({"error": "Organizador no encontrado"}), 404
    if not puede_gestionar_organizador(usuario, organizador_id):
        return jsonify({"error": "No perteneces a ese organizador"}), 403
    query = Liquidacion.query.filter_by(organizador_id=organizador_id)
    if request.args.get("estado"):
        query = query.filter_by(estado=request.args["estado"])
    return jsonify(paginar_query(query.order_by(Liquidacion.id.desc()), "liquidaciones", lambda l: l.to_dict())), 200

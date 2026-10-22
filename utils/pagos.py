"""Cálculo de precios, cupones y comisiones. Todo el dinero se maneja con
Decimal (nunca float) y se redondea a centavos con ROUND_HALF_UP."""

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from flask import current_app

from database import db
from models import Comision, Cupon, CuponUso, Inscripcion, Pago, PagoInscripcion

CENTAVOS = Decimal("0.01")
CERO = Decimal("0.00")


class ErrorDeNegocio(Exception):
    """Una regla de negocio que no se cumple; las rutas la convierten en
    una respuesta JSON con el código HTTP indicado."""

    def __init__(self, mensaje, codigo=400, extra=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.extra = extra or {}

    def a_respuesta(self):
        return {"error": self.mensaje, **self.extra}, self.codigo


def q2(valor):
    return Decimal(str(valor)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def ahora_naive():
    """UTC sin zona horaria (como se guardan los `timestamp` en Neon)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def comision_vigente(concepto="inscripcion", hoy=None):
    """(porcentaje, es_valor_por_defecto) de la comisión vigente."""
    hoy = hoy or date.today()
    fila = (
        Comision.query.filter(
            Comision.concepto == concepto,
            Comision.vigente_desde <= hoy,
            db.or_(Comision.vigente_hasta.is_(None), Comision.vigente_hasta >= hoy),
        )
        .order_by(Comision.vigente_desde.desc())
        .first()
    )
    if fila:
        return Decimal(str(fila.porcentaje)), False
    return Decimal(str(current_app.config.get("COMISION_POR_DEFECTO", "10"))), True


def usos_de_cupon(cupon_id, usuario_id=None):
    """Usos que cuentan: los de pagos pendientes o pagados (los cancelados
    o fallidos liberan el cupón)."""
    q = (
        CuponUso.query.join(Pago, Pago.id == CuponUso.pago_id)
        .filter(CuponUso.cupon_id == cupon_id, Pago.estado.in_(("pendiente", "pagado", "reembolsado")))
    )
    if usuario_id is not None:
        q = q.filter(CuponUso.usuario_id == usuario_id)
    return q.count()


def _validar_cupon(cupon, usuario):
    ahora = ahora_naive()
    if not cupon.activo:
        raise ErrorDeNegocio("Ese cupón no está activo", 409)
    if cupon.vigente_desde and cupon.vigente_desde > ahora:
        raise ErrorDeNegocio("Ese cupón todavía no está vigente", 409)
    if cupon.vigente_hasta and cupon.vigente_hasta < ahora:
        raise ErrorDeNegocio("Ese cupón ya venció", 409)
    if cupon.concepto not in (None, "inscripcion"):
        raise ErrorDeNegocio("Ese cupón no aplica a inscripciones", 409)
    if cupon.usos_maximos is not None and usos_de_cupon(cupon.id) >= cupon.usos_maximos:
        raise ErrorDeNegocio("Ese cupón ya alcanzó su límite de usos", 409)
    if usos_de_cupon(cupon.id, usuario.id) >= cupon.usos_por_usuario:
        raise ErrorDeNegocio("Ya usaste este cupón el máximo de veces permitido", 409)


def cotizar(usuario, inscripcion_ids, cupon_codigo=None):
    """Calcula cuánto cuesta pagar esas inscripciones. No escribe nada.

    Regresa un dict con `items`, `subtotal`, `descuento_total`, `total`,
    `moneda`, `cupon` y `comision_porcentaje` (valores Decimal), o lanza
    ErrorDeNegocio.
    """
    if not isinstance(inscripcion_ids, list) or not inscripcion_ids:
        raise ErrorDeNegocio("inscripcion_ids debe ser una lista con al menos una inscripción")
    if any(not isinstance(i, int) or isinstance(i, bool) for i in inscripcion_ids):
        raise ErrorDeNegocio("inscripcion_ids solo puede contener números enteros")
    if len(set(inscripcion_ids)) != len(inscripcion_ids):
        raise ErrorDeNegocio("inscripcion_ids tiene inscripciones repetidas")

    filas = []
    for iid in inscripcion_ids:
        ins = Inscripcion.query.get(iid)
        if not ins or ins.usuario_id != usuario.id:
            raise ErrorDeNegocio(f"Inscripción {iid} no encontrada", 404)
        if ins.estado == "lista_espera":
            raise ErrorDeNegocio(f"La inscripción {iid} está en lista de espera: todavía no se puede pagar", 409)
        if ins.estado != "pendiente_pago":
            raise ErrorDeNegocio(f"La inscripción {iid} está en estado '{ins.estado}', no 'pendiente_pago'", 409)
        evento = ins.evento
        if evento is None or evento.eliminado_en is not None or evento.estado != "publicado":
            raise ErrorDeNegocio(f"El evento de la inscripción {iid} ya no está publicado", 409)
        previo = PagoInscripcion.query.get(iid)
        if previo and previo.pago.estado in ("pendiente", "pagado", "reembolsado"):
            raise ErrorDeNegocio(
                f"La inscripción {iid} ya tiene un pago ({previo.pago_id}, {previo.pago.estado})", 409,
                {"pago_id": previo.pago_id},
            )
        boleto, paquete = ins.boleto, ins.paquete
        if boleto is None or not boleto.activo:
            raise ErrorDeNegocio(f"El boleto de la inscripción {iid} ya no está disponible", 409)
        if paquete is not None and not paquete.activo:
            raise ErrorDeNegocio(f"El paquete de la inscripción {iid} ya no está disponible", 409)
        precio_boleto = q2(boleto.precio)
        precio_paquete = q2(paquete.precio) if paquete is not None else CERO
        monedas = {boleto.moneda} | ({paquete.moneda} if paquete is not None else set())
        if len(monedas) > 1:
            raise ErrorDeNegocio(f"El boleto y el paquete de la inscripción {iid} están en monedas distintas", 409)
        filas.append({
            "inscripcion": ins,
            "inscripcion_id": iid,
            "evento_id": evento.id,
            "evento_titulo": evento.titulo,
            "organizador_id": evento.organizador_id,
            "moneda": monedas.pop(),
            "precio_boleto": precio_boleto,
            "precio_paquete": precio_paquete,
            "precio": precio_boleto + precio_paquete,
            "descuento": CERO,
        })

    monedas = {f["moneda"] for f in filas}
    if len(monedas) > 1:
        raise ErrorDeNegocio("Todas las inscripciones de un pago deben estar en la misma moneda", 409)
    moneda = monedas.pop()
    subtotal = sum((f["precio"] for f in filas), CERO)

    cupon_info = None
    if cupon_codigo:
        cupon = Cupon.query.filter_by(codigo=str(cupon_codigo).strip().upper()).first()
        if not cupon:
            raise ErrorDeNegocio("Ese cupón no existe", 404)
        _validar_cupon(cupon, usuario)
        elegibles = [f for f in filas if cupon.organizador_id in (None, f["organizador_id"])]
        base = sum((f["precio"] for f in elegibles), CERO)
        if not elegibles or base <= 0:
            raise ErrorDeNegocio("Ese cupón no aplica a estas inscripciones", 409)
        if cupon.tipo_descuento == "porcentaje":
            descuento = q2(base * Decimal(str(cupon.valor)) / 100)
        else:
            descuento = min(q2(cupon.valor), base)
        # Se reparte proporcionalmente entre las inscripciones elegibles; el
        # último absorbe los centavos del redondeo.
        repartido = CERO
        for i, f in enumerate(elegibles):
            if i == len(elegibles) - 1:
                parte = min(f["precio"], descuento - repartido)
            else:
                parte = min(f["precio"], q2(descuento * f["precio"] / base))
            f["descuento"] = parte
            repartido += parte
        cupon_info = {"cupon": cupon, "codigo": cupon.codigo, "tipo_descuento": cupon.tipo_descuento,
                      "valor": float(cupon.valor)}

    porcentaje, _ = comision_vigente("inscripcion")
    for f in filas:
        f["monto_bruto"] = f["precio"] - f["descuento"]
        f["comision_plataforma"] = q2(f["monto_bruto"] * porcentaje / 100)
        f["monto_organizador"] = f["monto_bruto"] - f["comision_plataforma"]

    descuento_total = sum((f["descuento"] for f in filas), CERO)
    return {
        "items": filas,
        "moneda": moneda,
        "subtotal": subtotal,
        "descuento_total": descuento_total,
        "total": subtotal - descuento_total,
        "cupon": cupon_info,
        "comision_porcentaje": porcentaje,
    }


def cotizacion_a_json(cot):
    """Lo que ve quien paga: sin la comisión ni lo que le toca al organizador."""
    return {
        "moneda": cot["moneda"],
        "items": [
            {
                "inscripcion_id": f["inscripcion_id"],
                "evento_titulo": f["evento_titulo"],
                "precio_boleto": float(f["precio_boleto"]),
                "precio_paquete": float(f["precio_paquete"]),
                "precio": float(f["precio"]),
                "descuento": float(f["descuento"]),
                "monto": float(f["monto_bruto"]),
            }
            for f in cot["items"]
        ],
        "subtotal": float(cot["subtotal"]),
        "descuento_total": float(cot["descuento_total"]),
        "total": float(cot["total"]),
        "cupon": ({k: v for k, v in cot["cupon"].items() if k != "cupon"} if cot["cupon"] else None),
    }

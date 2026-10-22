import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import (
    CuponUso,
    Evento,
    Inscripcion,
    Organizador,
    Pago,
    PagoInscripcion,
    Reembolso,
    ESTADOS_PAGO,
    ESTADOS_REEMBOLSO,
    METODOS_PAGO,
    METODO_GRATUITO,
    PASARELA_MANUAL,
    PASARELA_NINGUNA,
    PASARELA_SIMULADA,
)
from utils.auth import admin_required, get_usuario_actual, puede_gestionar_organizador
from utils.inscripciones import promover_lista_espera
from utils.paginacion import paginar_query
from utils.pagos import CERO, ErrorDeNegocio, ahora_naive, cotizacion_a_json, cotizar

pagos_bp = Blueprint("pagos", __name__, url_prefix="/api")


def _es_admin(usuario):
    return usuario.rol == "administrador"


def _pago_de(usuario, pago_id):
    """El pago, si es del usuario o es admin; si no, 404 (no se revela)."""
    pago = Pago.query.get(pago_id)
    if pago is None or (pago.usuario_id != usuario.id and not _es_admin(usuario)):
        raise ErrorDeNegocio("Pago no encontrado", 404)
    return pago


def _marcar_pagado(pago, referencia=None):
    """Pasa el pago a `pagado` y sus inscripciones a `inscrito`. Solo se
    puede si el pago sigue pendiente y todas las inscripciones siguen
    esperando pago (si alguna cambió de estado, hay que armar otro pago)."""
    if pago.estado != "pendiente":
        raise ErrorDeNegocio(f"Ese pago está '{pago.estado}', no 'pendiente'", 409)
    for item in pago.items:
        if item.inscripcion.estado != "pendiente_pago":
            raise ErrorDeNegocio(
                f"La inscripción {item.inscripcion_id} ya no está pendiente de pago "
                f"(estado '{item.inscripcion.estado}'); cancela este pago y crea otro", 409,
            )
    pago.estado = "pagado"
    pago.pagado_en = ahora_naive()
    if referencia:
        pago.referencia_externa = referencia
    for item in pago.items:
        item.inscripcion.estado = "inscrito"


def _respuesta_error(error):
    cuerpo, codigo = error.a_respuesta()
    return jsonify(cuerpo), codigo


# ============ Cotizar y pagar ============

@pagos_bp.route("/pagos/cotizar", methods=["POST"])
@jwt_required()
def cotizar_pago():
    """Cuánto costaría pagar esas inscripciones (con cupón opcional). No
    crea nada. Body: {"inscripcion_ids": [1, 2], "cupon_codigo": "VERANO10"}."""
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    try:
        cot = cotizar(usuario, data.get("inscripcion_ids"), data.get("cupon_codigo"))
    except ErrorDeNegocio as e:
        return _respuesta_error(e)
    return jsonify(cotizacion_a_json(cot)), 200


@pagos_bp.route("/pagos", methods=["POST"])
@jwt_required()
def crear_pago():
    """Crea el pago de una o varias inscripciones mías en `pendiente_pago`.

    Body: {"inscripcion_ids": [1], "metodo": "tarjeta", "cupon_codigo": "X"}.
    El monto lo calcula el servidor (el cliente nunca lo manda). Si el
    total es $0 (evento gratis o cupón del 100%) el pago queda pagado de
    inmediato y no hace falta `metodo`.
    """
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    try:
        cot = cotizar(usuario, data.get("inscripcion_ids"), data.get("cupon_codigo"))
    except ErrorDeNegocio as e:
        return _respuesta_error(e)

    total = cot["total"]
    if total == CERO:
        metodo, pasarela = METODO_GRATUITO, PASARELA_NINGUNA
    else:
        metodo = data.get("metodo")
        if metodo not in METODOS_PAGO:
            return jsonify({"error": f"metodo debe ser uno de: {', '.join(METODOS_PAGO)}"}), 400
        if metodo == "tarjeta":
            if not current_app.config.get("SIMULAR_PASARELA"):
                return jsonify({"error": "El pago con tarjeta todavía no está disponible en este entorno"}), 501
            pasarela = PASARELA_SIMULADA
        else:
            pasarela = PASARELA_MANUAL

    ids = [f["inscripcion_id"] for f in cot["items"]]
    # Una inscripción solo puede tener UNA fila en `pagos_inscripciones`
    # (es su PK): se limpian los restos de intentos cancelados o fallidos.
    for iid in ids:
        previo = PagoInscripcion.query.get(iid)
        if previo is not None and previo.pago.estado in ("cancelado", "fallido"):
            db.session.delete(previo)
    db.session.flush()

    pago = Pago(
        usuario_id=usuario.id, metodo=metodo, pasarela=pasarela, estado="pendiente",
        monto_total=total, moneda=cot["moneda"],
    )
    db.session.add(pago)
    db.session.flush()
    if pasarela == PASARELA_MANUAL:
        pago.referencia_externa = f"SM-{pago.id:08d}"

    for f in cot["items"]:
        db.session.add(PagoInscripcion(
            inscripcion_id=f["inscripcion_id"], pago_id=pago.id,
            monto_bruto=f["monto_bruto"], comision_plataforma=f["comision_plataforma"],
            monto_organizador=f["monto_organizador"],
        ))
    if cot["cupon"]:
        db.session.add(CuponUso(cupon_id=cot["cupon"]["cupon"].id, usuario_id=usuario.id, pago_id=pago.id))
    db.session.flush()
    db.session.refresh(pago)

    if total == CERO:
        try:
            _marcar_pagado(pago)
        except ErrorDeNegocio as e:
            db.session.rollback()
            return _respuesta_error(e)
    db.session.commit()

    respuesta = pago.to_dict(detalle=True)
    if pasarela == PASARELA_MANUAL:
        respuesta["instrucciones"] = (
            f"Realiza el pago por {metodo} indicando la referencia {pago.referencia_externa}. "
            "Cuando un administrador confirme el depósito, tus inscripciones quedarán confirmadas."
        )
    elif pasarela == PASARELA_SIMULADA:
        respuesta["instrucciones"] = (
            f"Pasarela simulada: confirma el pago con POST /api/pagos/{pago.id}/simular-pago."
        )
    return jsonify(respuesta), 201


# ============ Consultar ============

def _filtrar_pagos(query):
    estado = request.args.get("estado")
    if estado:
        query = query.filter(Pago.estado == estado)
    metodo = request.args.get("metodo")
    if metodo:
        query = query.filter(Pago.metodo == metodo)
    return query


@pagos_bp.route("/pagos/me", methods=["GET"])
@jwt_required()
def mis_pagos():
    """Mis pagos, del más reciente al más antiguo. Query params: estado,
    metodo, page, per_page."""
    usuario = get_usuario_actual()
    query = _filtrar_pagos(Pago.query.filter_by(usuario_id=usuario.id)).order_by(Pago.id.desc())
    return jsonify(paginar_query(query, "pagos", lambda p: p.to_dict(detalle=True))), 200


@pagos_bp.route("/pagos", methods=["GET"])
@admin_required
def listar_pagos():
    """Todos los pagos (admin). Query params: estado, metodo, usuario_id,
    page, per_page."""
    query = _filtrar_pagos(Pago.query)
    if request.args.get("usuario_id", type=int):
        query = query.filter(Pago.usuario_id == request.args.get("usuario_id", type=int))
    query = query.order_by(Pago.id.desc())
    return jsonify(paginar_query(query, "pagos", lambda p: p.to_dict(detalle=True, interno=True))), 200


@pagos_bp.route("/pagos/<int:pago_id>", methods=["GET"])
@jwt_required()
def ver_pago(pago_id):
    usuario = get_usuario_actual()
    try:
        pago = _pago_de(usuario, pago_id)
    except ErrorDeNegocio as e:
        return _respuesta_error(e)
    return jsonify(pago.to_dict(detalle=True, interno=_es_admin(usuario))), 200


# ============ Confirmar / cancelar ============

@pagos_bp.route("/pagos/<int:pago_id>/simular-pago", methods=["POST"])
@jwt_required()
def simular_pago(pago_id):
    """SOLO PARA PRUEBAS: simula la respuesta de la pasarela de tarjeta.
    Body opcional: {"resultado": "aprobado" | "rechazado"} (por defecto
    aprobado). Está apagado cuando SIMULAR_PASARELA=false."""
    if not current_app.config.get("SIMULAR_PASARELA"):
        return jsonify({"error": "La pasarela simulada está desactivada en este entorno"}), 403
    usuario = get_usuario_actual()
    try:
        pago = _pago_de(usuario, pago_id)
        if pago.usuario_id != usuario.id:
            raise ErrorDeNegocio("Solo quien hizo el pago puede simularlo", 403)
        if pago.pasarela != PASARELA_SIMULADA:
            raise ErrorDeNegocio("Ese pago no es de la pasarela simulada", 409)
        if pago.estado != "pendiente":
            raise ErrorDeNegocio(f"Ese pago está '{pago.estado}', no 'pendiente'", 409)
        resultado = (request.get_json(force=True, silent=True) or {}).get("resultado", "aprobado")
        if resultado not in ("aprobado", "rechazado"):
            raise ErrorDeNegocio("resultado debe ser 'aprobado' o 'rechazado'")
        if resultado == "rechazado":
            pago.estado = "fallido"
        else:
            _marcar_pagado(pago, referencia=f"SIM-{uuid.uuid4().hex[:12]}")
    except ErrorDeNegocio as e:
        db.session.rollback()
        return _respuesta_error(e)
    db.session.commit()
    return jsonify(pago.to_dict(detalle=True)), 200


@pagos_bp.route("/pagos/<int:pago_id>/confirmar", methods=["PUT"])
@admin_required
def confirmar_pago(pago_id):
    """Un administrador confirma un pago (p. ej. verificó la transferencia o
    el depósito). Body opcional: {"referencia_externa": "SPEI-123"}."""
    pago = Pago.query.get_or_404(pago_id)
    referencia = (request.get_json(force=True, silent=True) or {}).get("referencia_externa")
    if referencia is not None and (not isinstance(referencia, str) or len(referencia) > 100):
        return jsonify({"error": "referencia_externa debe ser texto de máximo 100 caracteres"}), 400
    try:
        _marcar_pagado(pago, referencia=referencia)
    except ErrorDeNegocio as e:
        db.session.rollback()
        return _respuesta_error(e)
    db.session.commit()
    return jsonify(pago.to_dict(detalle=True, interno=True)), 200


@pagos_bp.route("/pagos/<int:pago_id>/cancelar", methods=["PUT"])
@jwt_required()
def cancelar_pago(pago_id):
    """Cancela un pago que sigue pendiente (quien lo hizo, o un admin). Las
    inscripciones quedan en `pendiente_pago` para poder pagarlas de nuevo, y
    el cupón usado se libera."""
    usuario = get_usuario_actual()
    try:
        pago = _pago_de(usuario, pago_id)
        if pago.estado != "pendiente":
            raise ErrorDeNegocio(f"Ese pago está '{pago.estado}'; solo se cancelan los pendientes", 409)
    except ErrorDeNegocio as e:
        return _respuesta_error(e)
    pago.estado = "cancelado"
    db.session.commit()
    return jsonify(pago.to_dict(detalle=True, interno=_es_admin(usuario))), 200


# ============ Reembolsos ============

def _liquidacion_de(pago):
    return next((i.liquidacion_id for i in pago.items if i.liquidacion_id is not None), None)


@pagos_bp.route("/pagos/<int:pago_id>/reembolsos", methods=["POST"])
@jwt_required()
def solicitar_reembolso(pago_id):
    """Pido que me devuelvan un pago ya pagado (siempre por el total; el
    reembolso parcial todavía no está soportado). Body: {"motivo": "..."}.
    Lo resuelve un administrador."""
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    motivo = data.get("motivo")
    if not isinstance(motivo, str) or not motivo.strip():
        return jsonify({"error": "motivo es obligatorio"}), 400
    if len(motivo) > 500:
        return jsonify({"error": "motivo no puede tener más de 500 caracteres"}), 400
    try:
        pago = _pago_de(usuario, pago_id)
        if pago.estado != "pagado":
            raise ErrorDeNegocio(f"Solo se reembolsan pagos pagados (este está '{pago.estado}')", 409)
        if pago.monto_total <= 0:
            raise ErrorDeNegocio("Un pago gratuito no se reembolsa", 409)
        if Reembolso.query.filter(
            Reembolso.pago_id == pago.id, Reembolso.estado.in_(("solicitado", "aprobado"))
        ).first():
            raise ErrorDeNegocio("Ese pago ya tiene un reembolso solicitado o aprobado", 409)
        liquidacion = _liquidacion_de(pago)
        if liquidacion is not None:
            raise ErrorDeNegocio(
                f"Ese pago ya está incluido en la liquidación {liquidacion} del organizador; "
                "contacta a un administrador", 409,
            )
    except ErrorDeNegocio as e:
        return _respuesta_error(e)

    reembolso = Reembolso(pago_id=pago.id, monto=pago.monto_total, motivo=motivo.strip(), solicitado_por=usuario.id)
    db.session.add(reembolso)
    db.session.commit()
    return jsonify(reembolso.to_dict()), 201


@pagos_bp.route("/reembolsos/me", methods=["GET"])
@jwt_required()
def mis_reembolsos():
    """Reembolsos que solicité. Query params: estado, page, per_page."""
    usuario = get_usuario_actual()
    query = Reembolso.query.filter_by(solicitado_por=usuario.id)
    if request.args.get("estado"):
        query = query.filter_by(estado=request.args["estado"])
    return jsonify(paginar_query(query.order_by(Reembolso.id.desc()), "reembolsos", lambda r: r.to_dict())), 200


@pagos_bp.route("/reembolsos", methods=["GET"])
@admin_required
def listar_reembolsos():
    """Bandeja de reembolsos (admin). Query params: estado (por defecto
    `solicitado`), page, per_page."""
    estado = request.args.get("estado", "solicitado")
    if estado not in ESTADOS_REEMBOLSO:
        return jsonify({"error": f"estado debe ser uno de: {', '.join(ESTADOS_REEMBOLSO)}"}), 400
    query = Reembolso.query.filter_by(estado=estado).order_by(Reembolso.id)
    return jsonify(paginar_query(query, "reembolsos", lambda r: r.to_dict())), 200


def _resolver_reembolso(reembolso_id, aprobar):
    admin = get_usuario_actual()
    reembolso = Reembolso.query.get_or_404(reembolso_id)
    if reembolso.estado != "solicitado":
        return jsonify({"error": f"Ese reembolso ya estaba '{reembolso.estado}'"}), 409

    if aprobar:
        pago = reembolso.pago
        if pago.estado != "pagado":
            return jsonify({"error": f"El pago está '{pago.estado}', ya no se puede reembolsar"}), 409
        liquidacion = _liquidacion_de(pago)
        if liquidacion is not None:
            return jsonify({"error": f"El pago ya está incluido en la liquidación {liquidacion}"}), 409
        # Reembolso total: el pago se da por devuelto y las inscripciones
        # se cancelan (ya no hay dinero que respalde el lugar).
        pago.estado = "reembolsado"
        ahora = datetime.now(timezone.utc)
        categorias = set()
        for item in pago.items:
            ins = item.inscripcion
            if ins.estado != "cancelado":
                ins.estado = "cancelado"
                ins.cancelada_en = ahora
                categorias.add(ins.categoria_id)
        for categoria_id in categorias:
            promover_lista_espera(categoria_id)

    reembolso.estado = "aprobado" if aprobar else "rechazado"
    reembolso.aprobado_por = admin.id
    reembolso.procesado_en = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(reembolso.to_dict()), 200


@pagos_bp.route("/reembolsos/<int:reembolso_id>/aprobar", methods=["PUT"])
@admin_required
def aprobar_reembolso(reembolso_id):
    """Aprueba el reembolso: el pago queda `reembolsado` y sus inscripciones
    `cancelado`. Ojo: aquí se REGISTRA la decisión; devolver el dinero por la
    pasarela o el banco es un paso aparte (no hay pasarela real conectada)."""
    return _resolver_reembolso(reembolso_id, aprobar=True)


@pagos_bp.route("/reembolsos/<int:reembolso_id>/rechazar", methods=["PUT"])
@admin_required
def rechazar_reembolso(reembolso_id):
    return _resolver_reembolso(reembolso_id, aprobar=False)


# ============ Ingresos del organizador ============

@pagos_bp.route("/organizadores/<int:organizador_id>/pagos", methods=["GET"])
@jwt_required()
def pagos_de_organizador(organizador_id):
    """Lo cobrado por los eventos de un organizador (solo pagos `pagado`),
    con la comisión de la plataforma y lo que le toca al organizador. Lo
    ven los miembros con permisos y los admins. Query params:
    por_liquidar=true (solo lo que aún no se liquidó), page, per_page."""
    usuario = get_usuario_actual()
    if Organizador.query.get(organizador_id) is None:
        return jsonify({"error": "Organizador no encontrado"}), 404
    if not puede_gestionar_organizador(usuario, organizador_id):
        return jsonify({"error": "No perteneces a ese organizador"}), 403

    base = (
        db.session.query(PagoInscripcion)
        .join(Pago, Pago.id == PagoInscripcion.pago_id)
        .join(Inscripcion, Inscripcion.id == PagoInscripcion.inscripcion_id)
        .join(Evento, Evento.id == Inscripcion.evento_id)
        .filter(Evento.organizador_id == organizador_id, Pago.estado == "pagado")
    )
    if request.args.get("por_liquidar", "").lower() in ("1", "true", "si", "sí"):
        # Los pagos de $0 nunca entran a una liquidación, así que tampoco
        # cuentan como "por liquidar" (mismo criterio que POST /liquidaciones).
        base = base.filter(PagoInscripcion.liquidacion_id.is_(None), PagoInscripcion.monto_bruto > 0)

    todos = base.all()
    resumen = {
        "monto_bruto": float(sum((i.monto_bruto for i in todos), CERO)),
        "comision_plataforma": float(sum((i.comision_plataforma for i in todos), CERO)),
        "monto_organizador": float(sum((i.monto_organizador for i in todos), CERO)),
        "por_liquidar": float(sum((i.monto_organizador for i in todos if i.liquidacion_id is None), CERO)),
    }

    def fila(i):
        return {**i.to_dict(interno=True), "pago_id": i.pago_id,
                "pagado_en": i.pago.pagado_en.isoformat() if i.pago.pagado_en else None,
                "comision_plataforma": float(i.comision_plataforma)}

    resultado = paginar_query(base.order_by(Pago.pagado_en.desc(), PagoInscripcion.inscripcion_id), "pagos", fila)
    resultado["resumen"] = resumen
    return jsonify(resultado), 200

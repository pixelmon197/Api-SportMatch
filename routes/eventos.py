import re
import unicodedata
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from database import db
from models import (
    Evento,
    EventoDeporte,
    EventoRequisito,
    EventoSede,
    EventoFecha,
    EventoCategoria,
    EventoBoleto,
    Deporte,
    ESTADOS_EVENTO,
    DIFICULTADES_EVENTO,
    TIPOS_SEDE,
    TIPOS_BOLETO,
)
from utils.auth import admin_required
from utils.fechas import parse_datetime

eventos_bp = Blueprint("eventos", __name__, url_prefix="/api/eventos")


def _slugificar(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto


def _generar_slug_unico(titulo):
    base = _slugificar(titulo) or "evento"
    slug = base
    i = 2
    while Evento.query.filter_by(slug=slug).first():
        slug = f"{base}-{i}"
        i += 1
    return slug


# ============ CONSULTA (público) ============

@eventos_bp.route("", methods=["GET"])
def listar_eventos():
    """Filtros: estado, tipo, deporte_id, ciudad_id, q (busca en título). Paginado."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Evento.query.filter(Evento.eliminado_en.is_(None))

    estado = request.args.get("estado")
    query = query.filter_by(estado=estado) if estado else query.filter_by(estado="publicado")

    if tipo := request.args.get("tipo"):
        query = query.filter_by(tipo=tipo)
    if q := request.args.get("q"):
        query = query.filter(Evento.titulo.ilike(f"%{q}%"))
    if deporte_id := request.args.get("deporte_id", type=int):
        query = query.join(EventoDeporte).filter(EventoDeporte.deporte_id == deporte_id)
    if ciudad_id := request.args.get("ciudad_id", type=int):
        query = query.join(EventoSede).filter(EventoSede.ciudad_id == ciudad_id)

    paginado = query.order_by(Evento.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "eventos": [e.to_dict() for e in paginado.items],
            "total": paginado.total,
            "page": page,
            "per_page": per_page,
            "paginas": paginado.pages,
        }
    ), 200


@eventos_bp.route("/<int:evento_id>", methods=["GET"])
def obtener_evento(evento_id):
    evento = Evento.query.filter_by(id=evento_id).filter(Evento.eliminado_en.is_(None)).first_or_404()
    return jsonify(evento.to_dict(detalle=True)), 200


@eventos_bp.route("/slug/<string:slug>", methods=["GET"])
def obtener_evento_por_slug(slug):
    evento = Evento.query.filter_by(slug=slug).filter(Evento.eliminado_en.is_(None)).first_or_404()
    return jsonify(evento.to_dict(detalle=True)), 200


# ============ CREAR / EDITAR (solo admin por ahora; el módulo "organizadores"
# aún no existe, se conectará en una fase posterior) ============

@eventos_bp.route("", methods=["POST"])
@admin_required
def crear_evento():
    """Crea el evento y, opcionalmente, sus sub-recursos en un solo request:
    deportes: [deporte_id, ...]
    requisitos: [{descripcion, orden}]
    sedes: [{tipo, nombre, direccion, ciudad_id, latitud, longitud}]
    fechas: [{inicia_en, termina_en}]
    categorias: [{nombre, distancia_km, cupo_total, ..., boletos: [{tipo, precio, ...}]}]
    """
    data = request.get_json(force=True, silent=True) or {}
    titulo = data.get("titulo")
    tipo = data.get("tipo")
    if not titulo or not tipo:
        return jsonify({"error": "titulo y tipo son obligatorios"}), 400
    if data.get("dificultad") and data["dificultad"] not in DIFICULTADES_EVENTO:
        return jsonify({"error": f"dificultad debe ser una de: {', '.join(DIFICULTADES_EVENTO)}"}), 400

    evento = Evento(
        organizador_id=data.get("organizador_id"),
        tipo=tipo,
        dificultad=data.get("dificultad"),
        titulo=titulo,
        slug=data.get("slug") or _generar_slug_unico(titulo),
        descripcion=data.get("descripcion"),
        edad_minima=data.get("edad_minima"),
        es_publico=data.get("es_publico", True),
        estado="borrador",
    )
    db.session.add(evento)
    db.session.flush()  # asigna evento.id sin cerrar la transacción

    for deporte_id in data.get("deportes", []):
        db.session.add(EventoDeporte(evento_id=evento.id, deporte_id=deporte_id))

    for req in data.get("requisitos", []):
        db.session.add(
            EventoRequisito(evento_id=evento.id, descripcion=req["descripcion"], orden=req.get("orden", 0))
        )

    for sede in data.get("sedes", []):
        db.session.add(
            EventoSede(
                evento_id=evento.id,
                tipo=sede.get("tipo", "sede_unica"),
                nombre=sede["nombre"],
                direccion=sede.get("direccion"),
                ciudad_id=sede.get("ciudad_id"),
                latitud=sede.get("latitud"),
                longitud=sede.get("longitud"),
            )
        )

    for fecha in data.get("fechas", []):
        db.session.add(
            EventoFecha(
                evento_id=evento.id,
                inicia_en=parse_datetime(fecha["inicia_en"]),
                termina_en=parse_datetime(fecha.get("termina_en")),
            )
        )

    for cat in data.get("categorias", []):
        categoria = EventoCategoria(
            evento_id=evento.id,
            nombre=cat["nombre"],
            distancia_km=cat.get("distancia_km"),
            edad_minima=cat.get("edad_minima"),
            edad_maxima=cat.get("edad_maxima"),
            cupo_total=cat.get("cupo_total"),
            permite_lista_espera=cat.get("permite_lista_espera", False),
        )
        db.session.add(categoria)
        db.session.flush()
        for boleto in cat.get("boletos", []):
            db.session.add(
                EventoBoleto(
                    categoria_id=categoria.id,
                    tipo=boleto.get("tipo", "general"),
                    precio=boleto.get("precio", 0),
                    moneda=boleto.get("moneda", "MXN"),
                    disponible_desde=parse_datetime(boleto.get("disponible_desde")),
                    disponible_hasta=parse_datetime(boleto.get("disponible_hasta")),
                    cantidad_maxima=boleto.get("cantidad_maxima"),
                )
            )

    db.session.commit()
    return jsonify(evento.to_dict(detalle=True)), 201


@eventos_bp.route("/<int:evento_id>", methods=["PUT"])
@admin_required
def actualizar_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    data = request.get_json(force=True, silent=True) or {}

    if "estado" in data:
        if data["estado"] not in ESTADOS_EVENTO:
            return jsonify({"error": f"estado debe ser uno de: {', '.join(ESTADOS_EVENTO)}"}), 400
        if data["estado"] == "publicado" and evento.publicado_en is None:
            evento.publicado_en = datetime.now(timezone.utc)

    for campo in ("tipo", "dificultad", "titulo", "descripcion", "edad_minima", "es_publico", "estado"):
        if campo in data:
            setattr(evento, campo, data[campo])

    db.session.commit()
    return jsonify(evento.to_dict(detalle=True)), 200


@eventos_bp.route("/<int:evento_id>", methods=["DELETE"])
@admin_required
def eliminar_evento(evento_id):
    """Borrado suave: hay inscripciones/pagos que dependerán de este evento."""
    evento = Evento.query.get_or_404(evento_id)
    evento.eliminado_en = datetime.now(timezone.utc)
    evento.estado = "cancelado"
    db.session.commit()
    return jsonify(evento.to_dict()), 200


# ============ SUB-RECURSOS (edición fina, solo admin) ============

@eventos_bp.route("/<int:evento_id>/deportes", methods=["POST"])
@admin_required
def agregar_deporte_evento(evento_id):
    Evento.query.get_or_404(evento_id)
    data = request.get_json(force=True, silent=True) or {}
    deporte_id = data.get("deporte_id")
    if not deporte_id or not Deporte.query.get(deporte_id):
        return jsonify({"error": "deporte_id inválido"}), 400

    db.session.add(EventoDeporte(evento_id=evento_id, deporte_id=deporte_id))
    db.session.commit()
    return jsonify({"mensaje": "Deporte agregado al evento"}), 201


@eventos_bp.route("/<int:evento_id>/deportes/<int:deporte_id>", methods=["DELETE"])
@admin_required
def quitar_deporte_evento(evento_id, deporte_id):
    ed = EventoDeporte.query.filter_by(evento_id=evento_id, deporte_id=deporte_id).first_or_404()
    db.session.delete(ed)
    db.session.commit()
    return "", 204


@eventos_bp.route("/<int:evento_id>/requisitos", methods=["POST"])
@admin_required
def agregar_requisito(evento_id):
    Evento.query.get_or_404(evento_id)
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("descripcion"):
        return jsonify({"error": "descripcion es obligatoria"}), 400
    req = EventoRequisito(evento_id=evento_id, descripcion=data["descripcion"], orden=data.get("orden", 0))
    db.session.add(req)
    db.session.commit()
    return jsonify(req.to_dict()), 201


@eventos_bp.route("/requisitos/<int:requisito_id>", methods=["PUT"])
@admin_required
def actualizar_requisito(requisito_id):
    req = EventoRequisito.query.get_or_404(requisito_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("descripcion", "orden"):
        if campo in data:
            setattr(req, campo, data[campo])
    db.session.commit()
    return jsonify(req.to_dict()), 200


@eventos_bp.route("/requisitos/<int:requisito_id>", methods=["DELETE"])
@admin_required
def eliminar_requisito(requisito_id):
    req = EventoRequisito.query.get_or_404(requisito_id)
    db.session.delete(req)
    db.session.commit()
    return "", 204


@eventos_bp.route("/<int:evento_id>/sedes", methods=["POST"])
@admin_required
def agregar_sede(evento_id):
    Evento.query.get_or_404(evento_id)
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("nombre"):
        return jsonify({"error": "nombre es obligatorio"}), 400
    if data.get("tipo") and data["tipo"] not in TIPOS_SEDE:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_SEDE)}"}), 400

    sede = EventoSede(
        evento_id=evento_id,
        tipo=data.get("tipo", "sede_unica"),
        nombre=data["nombre"],
        direccion=data.get("direccion"),
        ciudad_id=data.get("ciudad_id"),
        latitud=data.get("latitud"),
        longitud=data.get("longitud"),
    )
    db.session.add(sede)
    db.session.commit()
    return jsonify(sede.to_dict()), 201


@eventos_bp.route("/sedes/<int:sede_id>", methods=["PUT"])
@admin_required
def actualizar_sede(sede_id):
    sede = EventoSede.query.get_or_404(sede_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("tipo", "nombre", "direccion", "ciudad_id", "latitud", "longitud"):
        if campo in data:
            setattr(sede, campo, data[campo])
    db.session.commit()
    return jsonify(sede.to_dict()), 200


@eventos_bp.route("/sedes/<int:sede_id>", methods=["DELETE"])
@admin_required
def eliminar_sede(sede_id):
    sede = EventoSede.query.get_or_404(sede_id)
    db.session.delete(sede)
    db.session.commit()
    return "", 204


@eventos_bp.route("/<int:evento_id>/fechas", methods=["POST"])
@admin_required
def agregar_fecha(evento_id):
    Evento.query.get_or_404(evento_id)
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("inicia_en"):
        return jsonify({"error": "inicia_en es obligatorio"}), 400
    fecha = EventoFecha(
        evento_id=evento_id,
        inicia_en=parse_datetime(data["inicia_en"]),
        termina_en=parse_datetime(data.get("termina_en")),
    )
    db.session.add(fecha)
    db.session.commit()
    return jsonify(fecha.to_dict()), 201


@eventos_bp.route("/fechas/<int:fecha_id>", methods=["PUT"])
@admin_required
def actualizar_fecha(fecha_id):
    fecha = EventoFecha.query.get_or_404(fecha_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("inicia_en", "termina_en", "cancelada_en"):
        if campo in data:
            setattr(fecha, campo, parse_datetime(data[campo]))
    db.session.commit()
    return jsonify(fecha.to_dict()), 200


@eventos_bp.route("/fechas/<int:fecha_id>", methods=["DELETE"])
@admin_required
def eliminar_fecha(fecha_id):
    fecha = EventoFecha.query.get_or_404(fecha_id)
    db.session.delete(fecha)
    db.session.commit()
    return "", 204


@eventos_bp.route("/<int:evento_id>/categorias", methods=["POST"])
@admin_required
def agregar_categoria(evento_id):
    Evento.query.get_or_404(evento_id)
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("nombre"):
        return jsonify({"error": "nombre es obligatorio"}), 400

    categoria = EventoCategoria(
        evento_id=evento_id,
        nombre=data["nombre"],
        distancia_km=data.get("distancia_km"),
        edad_minima=data.get("edad_minima"),
        edad_maxima=data.get("edad_maxima"),
        cupo_total=data.get("cupo_total"),
        permite_lista_espera=data.get("permite_lista_espera", False),
    )
    db.session.add(categoria)
    db.session.commit()
    return jsonify(categoria.to_dict()), 201


@eventos_bp.route("/categorias/<int:categoria_id>", methods=["PUT"])
@admin_required
def actualizar_categoria(categoria_id):
    categoria = EventoCategoria.query.get_or_404(categoria_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in (
        "nombre", "distancia_km", "edad_minima", "edad_maxima", "cupo_total", "permite_lista_espera",
    ):
        if campo in data:
            setattr(categoria, campo, data[campo])
    db.session.commit()
    return jsonify(categoria.to_dict(con_boletos=True)), 200


@eventos_bp.route("/categorias/<int:categoria_id>", methods=["DELETE"])
@admin_required
def eliminar_categoria(categoria_id):
    categoria = EventoCategoria.query.get_or_404(categoria_id)
    db.session.delete(categoria)
    db.session.commit()
    return "", 204


@eventos_bp.route("/categorias/<int:categoria_id>/boletos", methods=["POST"])
@admin_required
def agregar_boleto(categoria_id):
    EventoCategoria.query.get_or_404(categoria_id)
    data = request.get_json(force=True, silent=True) or {}
    if data.get("tipo") and data["tipo"] not in TIPOS_BOLETO:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_BOLETO)}"}), 400

    boleto = EventoBoleto(
        categoria_id=categoria_id,
        tipo=data.get("tipo", "general"),
        precio=data.get("precio", 0),
        moneda=data.get("moneda", "MXN"),
        disponible_desde=parse_datetime(data.get("disponible_desde")),
        disponible_hasta=parse_datetime(data.get("disponible_hasta")),
        cantidad_maxima=data.get("cantidad_maxima"),
    )
    db.session.add(boleto)
    db.session.commit()
    return jsonify(boleto.to_dict()), 201


@eventos_bp.route("/boletos/<int:boleto_id>", methods=["PUT"])
@admin_required
def actualizar_boleto(boleto_id):
    boleto = EventoBoleto.query.get_or_404(boleto_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("tipo", "precio", "moneda", "cantidad_maxima", "activo"):
        if campo in data:
            setattr(boleto, campo, data[campo])
    for campo in ("disponible_desde", "disponible_hasta"):
        if campo in data:
            setattr(boleto, campo, parse_datetime(data[campo]))
    db.session.commit()
    return jsonify(boleto.to_dict()), 200


@eventos_bp.route("/boletos/<int:boleto_id>", methods=["DELETE"])
@admin_required
def eliminar_boleto(boleto_id):
    boleto = EventoBoleto.query.get_or_404(boleto_id)
    db.session.delete(boleto)
    db.session.commit()
    return "", 204

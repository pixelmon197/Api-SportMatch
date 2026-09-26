import re
import unicodedata
from functools import wraps
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import jwt_required

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
    Organizador,
    TIPOS_EVENTO,
    ESTADOS_EVENTO,
    DIFICULTADES_EVENTO,
    TIPOS_SEDE,
    TIPOS_BOLETO,
)
from utils.auth import get_usuario_actual, puede_gestionar_evento, puede_gestionar_organizador
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


def _validar_categoria(datos):
    """Valida los CHECK reales de `evento_categorias`. Regresa un mensaje
    de error (str) o None si todo está bien."""
    edad_minima = datos.get("edad_minima")
    edad_maxima = datos.get("edad_maxima")
    distancia_km = datos.get("distancia_km")
    cupo_total = datos.get("cupo_total")
    if edad_minima is not None and edad_maxima is not None and edad_maxima < edad_minima:
        return "edad_maxima no puede ser menor que edad_minima"
    if distancia_km is not None and distancia_km <= 0:
        return "distancia_km debe ser mayor a 0"
    if cupo_total is not None and cupo_total <= 0:
        return "cupo_total debe ser mayor a 0"
    return None


def _validar_boleto(datos):
    """Valida los CHECK reales de `evento_boletos`. Regresa un mensaje de
    error (str) o None si todo está bien."""
    tipo = datos.get("tipo", "general")
    if tipo not in TIPOS_BOLETO:
        return f"tipo de boleto debe ser uno de: {', '.join(TIPOS_BOLETO)}"
    precio = datos.get("precio", 0)
    if precio is not None and precio < 0:
        return "precio no puede ser negativo"
    desde, hasta = datos.get("disponible_desde"), datos.get("disponible_hasta")
    if desde and hasta and parse_datetime(hasta) <= parse_datetime(desde):
        return "disponible_hasta debe ser posterior a disponible_desde"
    return None


def evento_gestion_required(resolver):
    """Requiere JWT y que el usuario pueda gestionar el evento que resuelve
    `resolver(kwargs)` (admin, o miembro del organizador dueño del evento).
    Deja el evento ya cargado en `g.evento` para que la vista lo reuse.
    """

    def decorador(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            usuario = get_usuario_actual()
            evento = resolver(kwargs)
            if evento is None:
                return jsonify({"error": "No encontrado"}), 404
            if not puede_gestionar_evento(usuario, evento):
                return jsonify({"error": "No tienes permisos para gestionar este evento"}), 403
            g.evento = evento
            g.usuario_actual = usuario
            return fn(*args, **kwargs)

        return wrapper

    return decorador


def _evento_por_id(kw):
    return Evento.query.get(kw["evento_id"])


def _evento_de_requisito(kw):
    r = EventoRequisito.query.get(kw["requisito_id"])
    return Evento.query.get(r.evento_id) if r else None


def _evento_de_sede(kw):
    s = EventoSede.query.get(kw["sede_id"])
    return Evento.query.get(s.evento_id) if s else None


def _evento_de_fecha(kw):
    f = EventoFecha.query.get(kw["fecha_id"])
    return Evento.query.get(f.evento_id) if f else None


def _evento_de_categoria(kw):
    c = EventoCategoria.query.get(kw["categoria_id"])
    return Evento.query.get(c.evento_id) if c else None


def _evento_de_boleto(kw):
    b = EventoBoleto.query.get(kw["boleto_id"])
    if not b:
        return None
    c = EventoCategoria.query.get(b.categoria_id)
    return Evento.query.get(c.evento_id) if c else None


# ============ CONSULTA (público) ============

@eventos_bp.route("", methods=["GET"])
def listar_eventos():
    """Filtros: estado, tipo, deporte_id, ciudad_id, organizador_id, q (busca en título). Paginado."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = Evento.query.filter(Evento.eliminado_en.is_(None))

    estado = request.args.get("estado")
    query = query.filter_by(estado=estado) if estado else query.filter_by(estado="publicado")

    if tipo := request.args.get("tipo"):
        query = query.filter_by(tipo=tipo)
    if q := request.args.get("q"):
        query = query.filter(Evento.titulo.ilike(f"%{q}%"))
    if organizador_id := request.args.get("organizador_id", type=int):
        query = query.filter_by(organizador_id=organizador_id)
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


# ============ CREAR / EDITAR ============
# Un admin siempre puede. Un usuario normal puede si es miembro
# (propietario/administrador) de un organizador ya "aprobado".

@eventos_bp.route("", methods=["POST"])
@jwt_required()
def crear_evento():
    """Crea el evento y, opcionalmente, sus sub-recursos en un solo request:
    deportes: [deporte_id, ...]
    requisitos: [{descripcion, orden}]
    sedes: [{tipo, nombre, direccion, ciudad_id, latitud, longitud}]
    fechas: [{inicia_en, termina_en}]
    categorias: [{nombre, distancia_km, cupo_total, ..., boletos: [{tipo, precio, ...}]}]
    """
    usuario = get_usuario_actual()
    data = request.get_json(force=True, silent=True) or {}
    titulo = data.get("titulo")
    tipo = data.get("tipo")
    organizador_id = data.get("organizador_id")

    if not titulo or not tipo:
        return jsonify({"error": "titulo y tipo son obligatorios"}), 400
    if tipo not in TIPOS_EVENTO:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_EVENTO)}"}), 400
    if data.get("dificultad") and data["dificultad"] not in DIFICULTADES_EVENTO:
        return jsonify({"error": f"dificultad debe ser una de: {', '.join(DIFICULTADES_EVENTO)}"}), 400
    edad_minima = data.get("edad_minima")
    if edad_minima is not None and edad_minima < 0:
        return jsonify({"error": "edad_minima no puede ser negativa"}), 400

    # organizador_id es NOT NULL en Neon: todo evento (incluso uno creado
    # por un admin) debe pertenecer a un organizador ya existente.
    if not organizador_id:
        return jsonify({"error": "organizador_id es obligatorio para crear un evento"}), 400
    organizador = Organizador.query.get(organizador_id)
    if not organizador:
        return jsonify({"error": "organizador_id inválido"}), 400
    if usuario.rol != "admin":
        if not puede_gestionar_organizador(usuario, organizador_id):
            return jsonify({"error": "No perteneces a ese organizador"}), 403
        if organizador.estado_validacion != "aprobada":
            return jsonify({"error": "Ese organizador todavía no está aprobado para publicar eventos"}), 403

    evento = Evento(
        organizador_id=organizador_id,
        tipo=tipo,
        dificultad=data.get("dificultad"),
        titulo=titulo,
        slug=data.get("slug") or _generar_slug_unico(titulo),
        descripcion=data.get("descripcion"),
        edad_minima=edad_minima,
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
        tipo_sede = sede.get("tipo", "punto_encuentro")
        if tipo_sede not in TIPOS_SEDE:
            db.session.rollback()
            return jsonify({"error": f"tipo de sede debe ser uno de: {', '.join(TIPOS_SEDE)}"}), 400
        db.session.add(
            EventoSede(
                evento_id=evento.id,
                tipo=tipo_sede,
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
        error = _validar_categoria(cat)
        if error:
            db.session.rollback()
            return jsonify({"error": error}), 400
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
            error = _validar_boleto(boleto)
            if error:
                db.session.rollback()
                return jsonify({"error": error}), 400
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
@evento_gestion_required(_evento_por_id)
def actualizar_evento(evento_id):
    evento = g.evento
    data = request.get_json(force=True, silent=True) or {}

    if "estado" in data:
        if data["estado"] not in ESTADOS_EVENTO:
            return jsonify({"error": f"estado debe ser uno de: {', '.join(ESTADOS_EVENTO)}"}), 400
        if data["estado"] == "publicado" and evento.publicado_en is None:
            evento.publicado_en = datetime.now(timezone.utc)
    if "tipo" in data and data["tipo"] not in TIPOS_EVENTO:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_EVENTO)}"}), 400
    if data.get("dificultad") and data["dificultad"] not in DIFICULTADES_EVENTO:
        return jsonify({"error": f"dificultad debe ser una de: {', '.join(DIFICULTADES_EVENTO)}"}), 400
    if data.get("edad_minima") is not None and data["edad_minima"] < 0:
        return jsonify({"error": "edad_minima no puede ser negativa"}), 400

    for campo in ("tipo", "dificultad", "titulo", "descripcion", "edad_minima", "es_publico", "estado"):
        if campo in data:
            setattr(evento, campo, data[campo])

    db.session.commit()
    return jsonify(evento.to_dict(detalle=True)), 200


@eventos_bp.route("/<int:evento_id>", methods=["DELETE"])
@evento_gestion_required(_evento_por_id)
def eliminar_evento(evento_id):
    """Borrado suave: hay inscripciones/pagos que dependerán de este evento."""
    evento = g.evento
    evento.eliminado_en = datetime.now(timezone.utc)
    evento.estado = "cancelado"
    db.session.commit()
    return jsonify(evento.to_dict()), 200


# ============ SUB-RECURSOS (edición fina: admin o miembro del organizador dueño) ============

@eventos_bp.route("/<int:evento_id>/deportes", methods=["POST"])
@evento_gestion_required(_evento_por_id)
def agregar_deporte_evento(evento_id):
    data = request.get_json(force=True, silent=True) or {}
    deporte_id = data.get("deporte_id")
    if not deporte_id or not Deporte.query.get(deporte_id):
        return jsonify({"error": "deporte_id inválido"}), 400
    if EventoDeporte.query.get((evento_id, deporte_id)):
        return jsonify({"error": "Ese deporte ya está asociado al evento"}), 409

    db.session.add(EventoDeporte(evento_id=evento_id, deporte_id=deporte_id))
    db.session.commit()
    return jsonify({"mensaje": "Deporte agregado al evento"}), 201


@eventos_bp.route("/<int:evento_id>/deportes/<int:deporte_id>", methods=["DELETE"])
@evento_gestion_required(_evento_por_id)
def quitar_deporte_evento(evento_id, deporte_id):
    ed = EventoDeporte.query.filter_by(evento_id=evento_id, deporte_id=deporte_id).first_or_404()
    db.session.delete(ed)
    db.session.commit()
    return "", 204


@eventos_bp.route("/<int:evento_id>/requisitos", methods=["POST"])
@evento_gestion_required(_evento_por_id)
def agregar_requisito(evento_id):
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("descripcion"):
        return jsonify({"error": "descripcion es obligatoria"}), 400
    req = EventoRequisito(evento_id=evento_id, descripcion=data["descripcion"], orden=data.get("orden", 0))
    db.session.add(req)
    db.session.commit()
    return jsonify(req.to_dict()), 201


@eventos_bp.route("/requisitos/<int:requisito_id>", methods=["PUT"])
@evento_gestion_required(_evento_de_requisito)
def actualizar_requisito(requisito_id):
    req = EventoRequisito.query.get_or_404(requisito_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("descripcion", "orden"):
        if campo in data:
            setattr(req, campo, data[campo])
    db.session.commit()
    return jsonify(req.to_dict()), 200


@eventos_bp.route("/requisitos/<int:requisito_id>", methods=["DELETE"])
@evento_gestion_required(_evento_de_requisito)
def eliminar_requisito(requisito_id):
    req = EventoRequisito.query.get_or_404(requisito_id)
    db.session.delete(req)
    db.session.commit()
    return "", 204


@eventos_bp.route("/<int:evento_id>/sedes", methods=["POST"])
@evento_gestion_required(_evento_por_id)
def agregar_sede(evento_id):
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("nombre"):
        return jsonify({"error": "nombre es obligatorio"}), 400
    tipo_sede = data.get("tipo", "punto_encuentro")
    if tipo_sede not in TIPOS_SEDE:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_SEDE)}"}), 400

    sede = EventoSede(
        evento_id=evento_id,
        tipo=tipo_sede,
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
@evento_gestion_required(_evento_de_sede)
def actualizar_sede(sede_id):
    sede = EventoSede.query.get_or_404(sede_id)
    data = request.get_json(force=True, silent=True) or {}
    if "tipo" in data and data["tipo"] not in TIPOS_SEDE:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_SEDE)}"}), 400
    for campo in ("tipo", "nombre", "direccion", "ciudad_id", "latitud", "longitud"):
        if campo in data:
            setattr(sede, campo, data[campo])
    db.session.commit()
    return jsonify(sede.to_dict()), 200


@eventos_bp.route("/sedes/<int:sede_id>", methods=["DELETE"])
@evento_gestion_required(_evento_de_sede)
def eliminar_sede(sede_id):
    sede = EventoSede.query.get_or_404(sede_id)
    db.session.delete(sede)
    db.session.commit()
    return "", 204


@eventos_bp.route("/<int:evento_id>/fechas", methods=["POST"])
@evento_gestion_required(_evento_por_id)
def agregar_fecha(evento_id):
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
@evento_gestion_required(_evento_de_fecha)
def actualizar_fecha(fecha_id):
    fecha = EventoFecha.query.get_or_404(fecha_id)
    data = request.get_json(force=True, silent=True) or {}
    for campo in ("inicia_en", "termina_en", "cancelada_en"):
        if campo in data:
            setattr(fecha, campo, parse_datetime(data[campo]))
    db.session.commit()
    return jsonify(fecha.to_dict()), 200


@eventos_bp.route("/fechas/<int:fecha_id>", methods=["DELETE"])
@evento_gestion_required(_evento_de_fecha)
def eliminar_fecha(fecha_id):
    fecha = EventoFecha.query.get_or_404(fecha_id)
    db.session.delete(fecha)
    db.session.commit()
    return "", 204


@eventos_bp.route("/<int:evento_id>/categorias", methods=["POST"])
@evento_gestion_required(_evento_por_id)
def agregar_categoria(evento_id):
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("nombre"):
        return jsonify({"error": "nombre es obligatorio"}), 400
    error = _validar_categoria(data)
    if error:
        return jsonify({"error": error}), 400

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
@evento_gestion_required(_evento_de_categoria)
def actualizar_categoria(categoria_id):
    categoria = EventoCategoria.query.get_or_404(categoria_id)
    data = request.get_json(force=True, silent=True) or {}
    datos_completos = {
        "edad_minima": data.get("edad_minima", categoria.edad_minima),
        "edad_maxima": data.get("edad_maxima", categoria.edad_maxima),
        "distancia_km": data.get("distancia_km", categoria.distancia_km),
        "cupo_total": data.get("cupo_total", categoria.cupo_total),
    }
    error = _validar_categoria(datos_completos)
    if error:
        return jsonify({"error": error}), 400
    for campo in (
        "nombre", "distancia_km", "edad_minima", "edad_maxima", "cupo_total", "permite_lista_espera",
    ):
        if campo in data:
            setattr(categoria, campo, data[campo])
    db.session.commit()
    return jsonify(categoria.to_dict(con_boletos=True)), 200


@eventos_bp.route("/categorias/<int:categoria_id>", methods=["DELETE"])
@evento_gestion_required(_evento_de_categoria)
def eliminar_categoria(categoria_id):
    categoria = EventoCategoria.query.get_or_404(categoria_id)
    db.session.delete(categoria)
    db.session.commit()
    return "", 204


@eventos_bp.route("/categorias/<int:categoria_id>/boletos", methods=["POST"])
@evento_gestion_required(_evento_de_categoria)
def agregar_boleto(categoria_id):
    data = request.get_json(force=True, silent=True) or {}
    error = _validar_boleto(data)
    if error:
        return jsonify({"error": error}), 400

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
@evento_gestion_required(_evento_de_boleto)
def actualizar_boleto(boleto_id):
    boleto = EventoBoleto.query.get_or_404(boleto_id)
    data = request.get_json(force=True, silent=True) or {}
    datos_completos = {
        "tipo": data.get("tipo", boleto.tipo),
        "precio": data.get("precio", boleto.precio),
        "disponible_desde": data.get("disponible_desde", boleto.disponible_desde),
        "disponible_hasta": data.get("disponible_hasta", boleto.disponible_hasta),
    }
    error = _validar_boleto(datos_completos)
    if error:
        return jsonify({"error": error}), 400
    for campo in ("tipo", "precio", "moneda", "cantidad_maxima", "activo"):
        if campo in data:
            setattr(boleto, campo, data[campo])
    for campo in ("disponible_desde", "disponible_hasta"):
        if campo in data:
            setattr(boleto, campo, parse_datetime(data[campo]))
    db.session.commit()
    return jsonify(boleto.to_dict()), 200


@eventos_bp.route("/boletos/<int:boleto_id>", methods=["DELETE"])
@evento_gestion_required(_evento_de_boleto)
def eliminar_boleto(boleto_id):
    boleto = EventoBoleto.query.get_or_404(boleto_id)
    db.session.delete(boleto)
    db.session.commit()
    return "", 204

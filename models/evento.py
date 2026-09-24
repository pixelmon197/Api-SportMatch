from datetime import datetime, timezone

from database import db

# Valores válidos (ver docs/entidades_completas.md).
ESTADOS_EVENTO = ("borrador", "publicado", "cancelado", "finalizado")
DIFICULTADES_EVENTO = ("principiante", "intermedio", "avanzado", "elite")
TIPOS_SEDE = ("salida", "meta", "punto_control", "sede_unica")
TIPOS_BOLETO = ("general", "early_bird", "vip", "grupal")


class Evento(db.Model):
    """Tabla `eventos`."""

    __tablename__ = "eventos"

    id = db.Column(db.Integer, primary_key=True)
    organizador_id = db.Column(db.Integer, db.ForeignKey("organizadores.id"), nullable=True)
    tipo = db.Column(db.String(50), nullable=False)  # carrera, torneo, clinica, etc.
    estado = db.Column(db.String(20), nullable=False, default="borrador")
    dificultad = db.Column(db.String(20), nullable=True)
    titulo = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(170), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    portada_id = db.Column(db.Integer, nullable=True)  # futura FK a `archivos`
    edad_minima = db.Column(db.Integer, nullable=True)
    es_publico = db.Column(db.Boolean, nullable=False, default=True)
    publicado_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    actualizado_en = db.Column(
        db.DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc)
    )
    eliminado_en = db.Column(db.DateTime, nullable=True)  # borrado suave

    deportes = db.relationship("EventoDeporte", cascade="all, delete-orphan")
    requisitos = db.relationship(
        "EventoRequisito", order_by="EventoRequisito.orden", cascade="all, delete-orphan"
    )
    sedes = db.relationship("EventoSede", cascade="all, delete-orphan")
    fechas = db.relationship("EventoFecha", back_populates="evento", cascade="all, delete-orphan")
    categorias = db.relationship("EventoCategoria", cascade="all, delete-orphan")
    organizador = db.relationship("Organizador")

    def to_dict(self, detalle=False):
        data = {
            "id": self.id,
            "organizador_id": self.organizador_id,
            "tipo": self.tipo,
            "estado": self.estado,
            "dificultad": self.dificultad,
            "titulo": self.titulo,
            "slug": self.slug,
            "descripcion": self.descripcion,
            "edad_minima": self.edad_minima,
            "es_publico": self.es_publico,
            "publicado_en": self.publicado_en.isoformat() if self.publicado_en else None,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
        if detalle:
            data["deportes"] = [ed.deporte.to_dict() for ed in self.deportes if ed.deporte]
            data["requisitos"] = [r.to_dict() for r in self.requisitos]
            data["sedes"] = [s.to_dict() for s in self.sedes]
            data["fechas"] = [f.to_dict() for f in self.fechas]
            data["categorias"] = [c.to_dict(con_boletos=True) for c in self.categorias]
        return data


class EventoDeporte(db.Model):
    __tablename__ = "evento_deportes"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id"), nullable=False)
    deporte_id = db.Column(db.Integer, db.ForeignKey("deportes.id"), nullable=False)

    deporte = db.relationship("Deporte")


class EventoRequisito(db.Model):
    __tablename__ = "eventos_requisitos"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id"), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    orden = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {"id": self.id, "descripcion": self.descripcion, "orden": self.orden}


class EventoSede(db.Model):
    __tablename__ = "evento_sedes"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id"), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="sede_unica")
    nombre = db.Column(db.String(150), nullable=False)
    direccion = db.Column(db.String(255), nullable=True)
    ciudad_id = db.Column(db.Integer, db.ForeignKey("ciudades.id"), nullable=True)
    latitud = db.Column(db.Numeric(9, 6), nullable=True)
    longitud = db.Column(db.Numeric(9, 6), nullable=True)

    ciudad = db.relationship("Ciudad")

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "nombre": self.nombre,
            "direccion": self.direccion,
            "ciudad": self.ciudad.to_dict() if self.ciudad else None,
            "latitud": float(self.latitud) if self.latitud is not None else None,
            "longitud": float(self.longitud) if self.longitud is not None else None,
        }


class EventoFecha(db.Model):
    __tablename__ = "eventos_fechas"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id"), nullable=False)
    inicia_en = db.Column(db.DateTime, nullable=False)
    termina_en = db.Column(db.DateTime, nullable=True)
    cancelada_en = db.Column(db.DateTime, nullable=True)

    evento = db.relationship("Evento", back_populates="fechas")

    def to_dict(self):
        return {
            "id": self.id,
            "inicia_en": self.inicia_en.isoformat() if self.inicia_en else None,
            "termina_en": self.termina_en.isoformat() if self.termina_en else None,
            "cancelada_en": self.cancelada_en.isoformat() if self.cancelada_en else None,
        }


class EventoCategoria(db.Model):
    __tablename__ = "evento_categorias"

    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id"), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)  # "5K", "Rama varonil 20-29", etc.
    distancia_km = db.Column(db.Numeric(6, 2), nullable=True)
    edad_minima = db.Column(db.Integer, nullable=True)
    edad_maxima = db.Column(db.Integer, nullable=True)
    cupo_total = db.Column(db.Integer, nullable=True)
    permite_lista_espera = db.Column(db.Boolean, nullable=False, default=False)

    boletos = db.relationship("EventoBoleto", cascade="all, delete-orphan")

    def to_dict(self, con_boletos=False):
        data = {
            "id": self.id,
            "evento_id": self.evento_id,
            "nombre": self.nombre,
            "distancia_km": float(self.distancia_km) if self.distancia_km is not None else None,
            "edad_minima": self.edad_minima,
            "edad_maxima": self.edad_maxima,
            "cupo_total": self.cupo_total,
            "permite_lista_espera": self.permite_lista_espera,
        }
        if con_boletos:
            data["boletos"] = [b.to_dict() for b in self.boletos]
        return data


class EventoBoleto(db.Model):
    __tablename__ = "evento_boletos"

    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("evento_categorias.id"), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="general")
    precio = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    moneda = db.Column(db.String(3), nullable=False, default="MXN")
    disponible_desde = db.Column(db.DateTime, nullable=True)
    disponible_hasta = db.Column(db.DateTime, nullable=True)
    cantidad_maxima = db.Column(db.Integer, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "categoria_id": self.categoria_id,
            "tipo": self.tipo,
            "precio": float(self.precio) if self.precio is not None else None,
            "moneda": self.moneda,
            "disponible_desde": self.disponible_desde.isoformat() if self.disponible_desde else None,
            "disponible_hasta": self.disponible_hasta.isoformat() if self.disponible_hasta else None,
            "cantidad_maxima": self.cantidad_maxima,
            "activo": self.activo,
        }

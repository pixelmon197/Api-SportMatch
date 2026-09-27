from datetime import datetime, timezone

from database import db

# Valores válidos (deben coincidir con los CHECK reales de Neon).
TIPOS_PUNTO_RUTA = ("inicio", "meta", "hidratacion", "punto_interes", "mirador", "peligro")
DIFICULTADES_RUTA = ("facil", "moderada", "dificil", "extrema")


class Ruta(db.Model):
    """Tabla `rutas`: recorridos (GPX) creados por un usuario, reutilizables
    en distintas categorías de eventos vía `evento_rutas`.
    """

    __tablename__ = "rutas"

    id = db.Column(db.Integer, primary_key=True)
    creador_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    deporte_id = db.Column(db.Integer, db.ForeignKey("deportes.id"), nullable=False)
    gpx_archivo_id = db.Column(db.Integer, nullable=True)  # futura FK a `archivos`
    dificultad = db.Column(db.String(20), nullable=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    distancia_m = db.Column(db.Integer, nullable=True)
    desnivel_positivo_m = db.Column(db.Integer, nullable=True)
    es_publica = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    eliminado_en = db.Column(db.DateTime, nullable=True)

    deporte = db.relationship("Deporte")
    puntos = db.relationship(
        "RutaPunto", order_by="RutaPunto.orden", cascade="all, delete-orphan"
    )

    def to_dict(self, con_puntos=False):
        data = {
            "id": self.id,
            "creador_id": self.creador_id,
            "deporte": self.deporte.to_dict() if self.deporte else None,
            "dificultad": self.dificultad,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "distancia_m": self.distancia_m,
            "desnivel_positivo_m": self.desnivel_positivo_m,
            "es_publica": self.es_publica,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if con_puntos:
            data["puntos"] = [p.to_dict() for p in self.puntos]
        return data


class RutaPunto(db.Model):
    __tablename__ = "ruta_puntos"

    id = db.Column(db.Integer, primary_key=True)
    ruta_id = db.Column(db.Integer, db.ForeignKey("rutas.id"), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="punto_interes")
    orden = db.Column(db.Integer, nullable=False, default=0)
    nombre = db.Column(db.String(100), nullable=True)
    latitud = db.Column(db.Numeric(9, 6), nullable=False)
    longitud = db.Column(db.Numeric(9, 6), nullable=False)
    altitud_m = db.Column(db.Numeric(7, 2), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "orden": self.orden,
            "nombre": self.nombre,
            "latitud": float(self.latitud),
            "longitud": float(self.longitud),
            "altitud_m": float(self.altitud_m) if self.altitud_m is not None else None,
        }


class EventoRuta(db.Model):
    """Liga una ruta a un evento (y, opcionalmente, a una categoría
    específica de ese evento). Tabla `evento_rutas`: PK compuesta real en
    Neon (evento_id + ruta_id), sin columna `id` propia. `categoria_id` es
    opcional pero, cuando se manda, Neon exige que esa categoría
    pertenezca al mismo evento (FK compuesta categoria_id+evento_id).
    """

    __tablename__ = "evento_rutas"

    evento_id = db.Column(db.Integer, db.ForeignKey("eventos.id"), primary_key=True)
    ruta_id = db.Column(db.Integer, db.ForeignKey("rutas.id"), primary_key=True)
    categoria_id = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ["categoria_id", "evento_id"],
            ["evento_categorias.id", "evento_categorias.evento_id"],
        ),
    )

    ruta = db.relationship("Ruta")

    def to_dict(self):
        return {
            "evento_id": self.evento_id,
            "ruta_id": self.ruta_id,
            "categoria_id": self.categoria_id,
            "ruta": self.ruta.to_dict() if self.ruta else None,
        }

from datetime import datetime, timezone

from database import db

TIPOS_PUNTO_RUTA = ("inicio", "fin", "control", "paso")


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
    distancia_m = db.Column(db.Numeric(10, 2), nullable=True)
    desnivel_positivo_m = db.Column(db.Numeric(10, 2), nullable=True)
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
            "distancia_m": float(self.distancia_m) if self.distancia_m is not None else None,
            "desnivel_positivo_m": float(self.desnivel_positivo_m)
            if self.desnivel_positivo_m is not None
            else None,
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
    tipo = db.Column(db.String(20), nullable=False, default="paso")
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
    """Liga una ruta a una categoría de evento (tabla `evento_rutas`)."""

    __tablename__ = "evento_rutas"

    id = db.Column(db.Integer, primary_key=True)
    ruta_id = db.Column(db.Integer, db.ForeignKey("rutas.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("evento_categorias.id"), nullable=False)

    ruta = db.relationship("Ruta")

    def to_dict(self):
        return {
            "id": self.id,
            "categoria_id": self.categoria_id,
            "ruta": self.ruta.to_dict() if self.ruta else None,
        }

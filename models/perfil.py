from datetime import datetime, timezone

from database import db

# Valores válidos para los tres campos de visibilidad de `perfiles`
# (coincide con los CHECK reales de Neon).
VISIBILIDADES = ("publico", "amigos", "privado")

BIOGRAFIA_MAX = 500  # límite de la API (en Neon es `text`, sin límite)


class Perfil(db.Model):
    """Tabla `perfiles` (relación 1 a 1 con `usuarios`). Ojo: su llave
    primaria real es `usuario_id`; no tiene columna `id` propia (la
    documentación del proyecto decía lo contrario)."""

    __tablename__ = "perfiles"

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), primary_key=True)
    biografia = db.Column(db.Text, nullable=True)
    avatar_id = db.Column(db.Integer, db.ForeignKey("archivos.id"), nullable=True)
    portada_id = db.Column(db.Integer, db.ForeignKey("archivos.id"), nullable=True)
    visibilidad_perfil = db.Column(db.String(20), nullable=False, default="publico")
    visibilidad_ubicacion = db.Column(db.String(20), nullable=False, default="amigos")
    quien_puede_escribir = db.Column(db.String(20), nullable=False, default="publico")
    aparecer_en_cercanos = db.Column(db.Boolean, nullable=False, default=True)
    latitud = db.Column(db.Numeric(9, 6), nullable=True)
    longitud = db.Column(db.Numeric(9, 6), nullable=True)
    ubicacion_actualizada_en = db.Column(db.DateTime, nullable=True)
    # NOT NULL DEFAULT CURRENT_TIMESTAMP en Neon: se declara también aquí
    # (SQLAlchemy no conoce el default de la BD y mandaría NULL).
    actualizado_en = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    usuario = db.relationship("Usuario")
    avatar = db.relationship("Archivo", foreign_keys=[avatar_id])
    portada = db.relationship("Archivo", foreign_keys=[portada_id])

    def to_dict(self, con_ubicacion=True, con_ajustes=True):
        data = {
            "usuario_id": self.usuario_id,
            "biografia": self.biografia,
            "avatar_id": self.avatar_id,
            "avatar_url": self.avatar.url if self.avatar else None,
            "portada_id": self.portada_id,
            "portada_url": self.portada.url if self.portada else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
        if con_ajustes:
            data["visibilidad_perfil"] = self.visibilidad_perfil
            data["visibilidad_ubicacion"] = self.visibilidad_ubicacion
            data["quien_puede_escribir"] = self.quien_puede_escribir
            data["aparecer_en_cercanos"] = self.aparecer_en_cercanos
        if con_ubicacion:
            data["latitud"] = float(self.latitud) if self.latitud is not None else None
            data["longitud"] = float(self.longitud) if self.longitud is not None else None
            data["ubicacion_actualizada_en"] = (
                self.ubicacion_actualizada_en.isoformat() if self.ubicacion_actualizada_en else None
            )
        return data

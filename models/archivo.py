from datetime import datetime, timezone

from database import db

# Valores válidos para `archivos.tipo` (coincide con el CHECK real de Neon).
TIPOS_ARCHIVO = ("imagen", "video", "documento", "gpx", "audio")

# Extensiones que se aceptan para cada tipo. No es una regla de Neon (la
# tabla no la tiene), es una validación de la API para no guardar
# cualquier binario bajo un tipo que no le corresponde.
EXTENSIONES_PERMITIDAS = {
    "imagen": {"jpg", "jpeg", "png", "webp", "gif"},
    "video": {"mp4", "mov", "webm"},
    "documento": {"pdf"},
    "gpx": {"gpx"},
    "audio": {"mp3", "wav", "m4a"},
}

# Tamaño máximo por tipo, en bytes. También por la API, no por Neon.
TAMANO_MAXIMO_BYTES = {
    "imagen": 8 * 1024 * 1024,
    "video": 200 * 1024 * 1024,
    "documento": 15 * 1024 * 1024,
    "gpx": 5 * 1024 * 1024,
    "audio": 30 * 1024 * 1024,
}


class Archivo(db.Model):
    """Tabla `archivos`: imágenes, videos, documentos, GPX o audio ya
    subidos, listos para referenciarse por id desde otras tablas
    (`eventos.portada_id`, `organizadores.logo_id`, `rutas.gpx_archivo_id`,
    `documentos_validacion.archivo_id`, etc.)."""

    __tablename__ = "archivos"

    id = db.Column(db.Integer, primary_key=True)
    propietario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    nombre_original = db.Column(db.String(200), nullable=True)
    tipo_mime = db.Column(db.String(100), nullable=True)
    tamano_bytes = db.Column(db.BigInteger, nullable=True)
    ancho_px = db.Column(db.Integer, nullable=True)
    alto_px = db.Column(db.Integer, nullable=True)
    duracion_segundos = db.Column(db.Integer, nullable=True)
    subido_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    eliminado_en = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "propietario_id": self.propietario_id,
            "tipo": self.tipo,
            "url": self.url,
            "nombre_original": self.nombre_original,
            "tipo_mime": self.tipo_mime,
            "tamano_bytes": self.tamano_bytes,
            "ancho_px": self.ancho_px,
            "alto_px": self.alto_px,
            "duracion_segundos": self.duracion_segundos,
            "subido_en": self.subido_en.isoformat() if self.subido_en else None,
        }

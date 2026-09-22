from database import db


class Ciudad(db.Model):
    """Catálogo de ciudades (tabla `ciudades` en el modelo entidad-relación).

    Es el dato "padre" del que derivan usuarios y organizadores.
    """

    __tablename__ = "ciudades"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    estado = db.Column(db.String(120), nullable=True)
    pais = db.Column(db.String(120), nullable=False, default="México")
    codigo_postal = db.Column(db.String(10), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "estado": self.estado,
            "pais": self.pais,
            "codigo_postal": self.codigo_postal,
        }

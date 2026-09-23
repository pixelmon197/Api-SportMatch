from database import db

# Niveles válidos para `usuarios_deportes.nivel`.
NIVELES_DEPORTE = ("principiante", "intermedio", "avanzado", "profesional")


class Deporte(db.Model):
    """Catálogo de deportes (tabla `Deportes` del modelo entidad-relación).

    Es el catálogo base del que dependen usuarios_deportes, rutas,
    evento_deportes y las opciones del cuestionario de registro.
    """

    __tablename__ = "deportes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False, unique=True)
    categoria = db.Column(db.String(50), nullable=True)  # ej. "resistencia", "equipo"
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "activo": self.activo,
        }


class UsuarioDeporte(db.Model):
    """Deportes que practica cada usuario (tabla `usuarios_deportes`, PK compuesta)."""

    __tablename__ = "usuarios_deportes"

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), primary_key=True)
    deporte_id = db.Column(db.Integer, db.ForeignKey("deportes.id"), primary_key=True)
    nivel = db.Column(db.String(20), nullable=False, default="principiante")
    es_principal = db.Column(db.Boolean, nullable=False, default=False)

    deporte = db.relationship("Deporte")

    def to_dict(self):
        return {
            "deporte": self.deporte.to_dict() if self.deporte else None,
            "nivel": self.nivel,
            "es_principal": self.es_principal,
        }

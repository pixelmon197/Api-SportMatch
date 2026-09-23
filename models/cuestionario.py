from datetime import datetime, timezone

from database import db

# Tipos válidos para `preguntas.tipo`.
TIPOS_PREGUNTA = ("opcion_unica", "opcion_multiple", "texto_libre", "escala")


class Cuestionario(db.Model):
    """Cuestionario de registro (tabla `cuestionarios`). Ej: el cuestionario
    que llena un usuario nuevo para definir sus deportes/nivel/intereses.
    """

    __tablename__ = "cuestionarios"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    preguntas = db.relationship(
        "Pregunta", backref="cuestionario", order_by="Pregunta.orden", cascade="all, delete-orphan"
    )

    def to_dict(self, con_preguntas=False):
        data = {
            "id": self.id,
            "codigo": self.codigo,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "activo": self.activo,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
        if con_preguntas:
            data["preguntas"] = [p.to_dict(con_opciones=True) for p in self.preguntas]
        return data


class Pregunta(db.Model):
    __tablename__ = "preguntas"

    id = db.Column(db.Integer, primary_key=True)
    cuestionario_id = db.Column(db.Integer, db.ForeignKey("cuestionarios.id"), nullable=False)
    codigo = db.Column(db.String(50), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="opcion_unica")
    obligatoria = db.Column(db.Boolean, nullable=False, default=True)
    orden = db.Column(db.Integer, nullable=False, default=0)
    activa = db.Column(db.Boolean, nullable=False, default=True)

    opciones = db.relationship(
        "OpcionRespuesta", backref="pregunta", order_by="OpcionRespuesta.orden", cascade="all, delete-orphan"
    )

    def to_dict(self, con_opciones=False):
        data = {
            "id": self.id,
            "cuestionario_id": self.cuestionario_id,
            "codigo": self.codigo,
            "texto": self.texto,
            "tipo": self.tipo,
            "obligatoria": self.obligatoria,
            "orden": self.orden,
            "activa": self.activa,
        }
        if con_opciones:
            data["opciones"] = [o.to_dict() for o in self.opciones]
        return data


class OpcionRespuesta(db.Model):
    __tablename__ = "opciones_respuesta"

    id = db.Column(db.Integer, primary_key=True)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("preguntas.id"), nullable=False)
    # Si la pregunta es del tipo "¿qué deporte practicas?", la opción puede
    # apuntar directo al catálogo de deportes en vez de tener texto libre.
    deporte_id = db.Column(db.Integer, db.ForeignKey("deportes.id"), nullable=True)
    codigo_id = db.Column(db.String(50), nullable=True)
    texto = db.Column(db.String(150), nullable=False)
    orden = db.Column(db.Integer, nullable=False, default=0)

    deporte = db.relationship("Deporte")

    def to_dict(self):
        return {
            "id": self.id,
            "pregunta_id": self.pregunta_id,
            "deporte_id": self.deporte_id,
            "codigo_id": self.codigo_id,
            "texto": self.texto,
            "orden": self.orden,
        }


class RespuestaUsuario(db.Model):
    """Respuesta de un usuario a una pregunta del cuestionario (tabla `respuesta_usuario`)."""

    __tablename__ = "respuesta_usuario"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("preguntas.id"), nullable=False)
    opcion_id = db.Column(db.Integer, db.ForeignKey("opciones_respuesta.id"), nullable=True)
    respuesta_texto = db.Column(db.Text, nullable=True)  # para preguntas tipo texto_libre
    respondida_en = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    pregunta = db.relationship("Pregunta")
    opcion = db.relationship("OpcionRespuesta")

    def to_dict(self):
        return {
            "id": self.id,
            "pregunta_id": self.pregunta_id,
            "pregunta_codigo": self.pregunta.codigo if self.pregunta else None,
            "opcion": self.opcion.to_dict() if self.opcion else None,
            "respuesta_texto": self.respuesta_texto,
            "respondida_en": self.respondida_en.isoformat() if self.respondida_en else None,
        }

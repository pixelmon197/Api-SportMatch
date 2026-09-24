import json

from flask import request

from database import db
from models import AuditoriaLog


def registrar_auditoria(usuario_id, accion, tipo_entidad, entidad_id, antes=None, despues=None):
    """Guarda una entrada en `auditoria_log`. Se llama explícitamente desde
    las acciones administrativas sensibles (no en cada request)."""
    log = AuditoriaLog(
        usuario_id=usuario_id,
        accion=accion,
        tipo_entidad=tipo_entidad,
        entidad_id=entidad_id,
        datos_anteriores=json.dumps(antes, default=str) if antes is not None else None,
        datos_nuevos=json.dumps(despues, default=str) if despues is not None else None,
        ip=request.remote_addr if request else None,
    )
    db.session.add(log)
    db.session.commit()
    return log

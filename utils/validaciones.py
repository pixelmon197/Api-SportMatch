import re

# Los teléfonos se guardan como texto (varchar(20) en Neon) porque un
# entero perdería ceros a la izquierda; por eso la restricción de "solo
# números" se hace aquí, no en el tipo de columna. 7-15 dígitos cubre desde
# un fijo local hasta el máximo internacional (E.164).
_PATRON_TELEFONO = re.compile(r"^[0-9]{7,15}$")


def validar_telefono(valor, campo="telefono"):
    """Regresa un mensaje de error (str) si `valor` no es un teléfono
    válido, o None si está bien. Un valor vacío/None se considera "no
    enviado" (los teléfonos son opcionales)."""
    if valor is None or valor == "":
        return None
    if not isinstance(valor, str) or not _PATRON_TELEFONO.match(valor):
        return f"{campo} debe contener solo números (entre 7 y 15 dígitos)"
    return None


def validar_archivo(archivo_id, tipos_permitidos, campo="archivo_id"):
    """Valida que `archivo_id` sea un archivo existente (no eliminado) de
    alguno de los `tipos_permitidos`. Regresa un mensaje de error (str) o
    None si está bien (o si no se mandó: None se considera "sin archivo").
    Los ids se obtienen con POST /api/archivos."""
    if archivo_id is None:
        return None
    from models import Archivo  # import local: evita ciclos de imports

    archivo = Archivo.query.filter_by(id=archivo_id).filter(Archivo.eliminado_en.is_(None)).first()
    if not archivo:
        return f"{campo} no corresponde a un archivo existente (súbelo primero con POST /api/archivos)"
    if archivo.tipo not in tipos_permitidos:
        return f"{campo} debe ser un archivo de tipo: {', '.join(tipos_permitidos)} (el enviado es '{archivo.tipo}')"
    return None

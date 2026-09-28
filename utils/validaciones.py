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

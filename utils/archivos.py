import os
import uuid
from io import BytesIO

from flask import current_app
from werkzeug.utils import secure_filename

from database import db
from models import Archivo, TIPOS_ARCHIVO, EXTENSIONES_PERMITIDAS, TAMANO_MAXIMO_BYTES

# Mapa inverso: extensión -> tipo, para adivinar el tipo si no lo manda el
# cliente (p. ej. "video.mp4" -> "video").
EXTENSION_A_TIPO = {
    ext: tipo for tipo, extensiones in EXTENSIONES_PERMITIDAS.items() for ext in extensiones
}


def extension_de(nombre_archivo):
    if "." not in nombre_archivo:
        return ""
    return nombre_archivo.rsplit(".", 1)[-1].lower()


def dimensiones_imagen(datos):
    """Intenta leer ancho/alto con Pillow; si no está instalado o el
    archivo no se puede leer como imagen, regresa (None, None) sin
    tronar — son columnas opcionales en Neon."""
    try:
        from PIL import Image

        with Image.open(BytesIO(datos)) as img:
            return img.width, img.height
    except Exception:
        return None, None


def guardar_archivo_subido(usuario, archivo, tipo=None, duracion_segundos=None):
    """Valida y guarda en disco un archivo recibido por multipart
    (`FileStorage`) y crea su fila en `archivos` (con commit).

    `tipo` es opcional: si no se manda se adivina por la extensión. Para
    forzar un tipo (p. ej. "imagen" en la foto de perfil) basta pasarlo.

    Regresa `(registro, None)` si todo salió bien, o `(None, (mensaje,
    codigo_http))` si la validación falló.
    """
    if not archivo or archivo.filename == "":
        return None, ("No se seleccionó ningún archivo", 400)

    nombre_original = secure_filename(archivo.filename) or archivo.filename
    extension = extension_de(nombre_original)
    tipo = (tipo or EXTENSION_A_TIPO.get(extension) or "").strip().lower()

    if tipo not in TIPOS_ARCHIVO:
        return None, (f"tipo debe ser uno de: {', '.join(TIPOS_ARCHIVO)}", 400)
    if extension not in EXTENSIONES_PERMITIDAS[tipo]:
        permitidas = ", ".join(sorted(EXTENSIONES_PERMITIDAS[tipo]))
        return None, (f"Extensión '.{extension}' no permitida para tipo '{tipo}' (permitidas: {permitidas})", 400)

    # Se lee completo para medir el tamaño real (Content-Length puede
    # faltar o no coincidir) y para, si es imagen, sacar ancho/alto.
    datos = archivo.read()
    tamano = len(datos)
    if tamano == 0:
        return None, ("El archivo está vacío", 400)
    maximo = TAMANO_MAXIMO_BYTES[tipo]
    if tamano > maximo:
        return None, (f"El archivo supera el máximo permitido para '{tipo}' ({maximo // (1024 * 1024)} MB)", 400)

    carpeta = os.path.join(current_app.static_folder, "uploads", tipo)
    os.makedirs(carpeta, exist_ok=True)
    nombre_disco = f"{uuid.uuid4().hex}.{extension}"
    with open(os.path.join(carpeta, nombre_disco), "wb") as f:
        f.write(datos)

    ancho_px = alto_px = None
    if tipo == "imagen":
        ancho_px, alto_px = dimensiones_imagen(datos)

    registro = Archivo(
        propietario_id=usuario.id,
        tipo=tipo,
        url=f"/static/uploads/{tipo}/{nombre_disco}",
        nombre_original=nombre_original,
        tipo_mime=archivo.mimetype,
        tamano_bytes=tamano,
        ancho_px=ancho_px,
        alto_px=alto_px,
        duracion_segundos=duracion_segundos,
    )
    db.session.add(registro)
    db.session.commit()
    return registro, None

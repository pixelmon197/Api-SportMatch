import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from database import db
from models import Archivo, TIPOS_ARCHIVO, EXTENSIONES_PERMITIDAS, TAMANO_MAXIMO_BYTES
from utils.auth import get_usuario_actual

archivos_bp = Blueprint("archivos", __name__, url_prefix="/api/archivos")

# Mapa inverso: extensión -> tipo, para adivinar el tipo si no lo manda el
# cliente (p. ej. "video.mp4" -> "video").
_EXTENSION_A_TIPO = {
    ext: tipo for tipo, extensiones in EXTENSIONES_PERMITIDAS.items() for ext in extensiones
}


def _extension_de(nombre_archivo):
    if "." not in nombre_archivo:
        return ""
    return nombre_archivo.rsplit(".", 1)[-1].lower()


def _dimensiones_imagen(datos):
    """Intenta leer ancho/alto con Pillow; si no está instalado o el
    archivo no se puede leer como imagen, regresa (None, None) sin
    tronar — son columnas opcionales en Neon."""
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(datos)) as img:
            return img.width, img.height
    except Exception:
        return None, None


@archivos_bp.route("", methods=["POST"])
@jwt_required()
def subir_archivo():
    """Sube un archivo (imagen, video, documento, GPX o audio) y regresa
    su registro, incluido el `id`. Ese `id` es lo que después se manda
    como `portada_id` (eventos), `logo_id` (organizadores),
    `gpx_archivo_id` (rutas) o `archivo_id` (documentos de validación de
    organizador).

    Body: multipart/form-data con el campo `archivo`. `tipo` es opcional
    (si no se manda, se adivina por la extensión del archivo).
    """
    usuario = get_usuario_actual()

    if "archivo" not in request.files:
        return jsonify({"error": "Falta el archivo (campo 'archivo', multipart/form-data)"}), 400
    archivo = request.files["archivo"]
    if not archivo or archivo.filename == "":
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    nombre_original = secure_filename(archivo.filename) or archivo.filename
    extension = _extension_de(nombre_original)
    tipo = (request.form.get("tipo") or _EXTENSION_A_TIPO.get(extension) or "").strip().lower()

    if tipo not in TIPOS_ARCHIVO:
        return jsonify({"error": f"tipo debe ser uno de: {', '.join(TIPOS_ARCHIVO)}"}), 400
    if extension not in EXTENSIONES_PERMITIDAS[tipo]:
        permitidas = ", ".join(sorted(EXTENSIONES_PERMITIDAS[tipo]))
        return jsonify(
            {"error": f"Extensión '.{extension}' no permitida para tipo '{tipo}' (permitidas: {permitidas})"}
        ), 400

    # Se lee completo para medir el tamaño real (Content-Length puede
    # faltar o no coincidir) y para, si es imagen, sacar ancho/alto.
    datos = archivo.read()
    tamano = len(datos)
    if tamano == 0:
        return jsonify({"error": "El archivo está vacío"}), 400
    maximo = TAMANO_MAXIMO_BYTES[tipo]
    if tamano > maximo:
        return jsonify(
            {"error": f"El archivo supera el máximo permitido para '{tipo}' ({maximo // (1024 * 1024)} MB)"}
        ), 400

    carpeta = os.path.join(current_app.static_folder, "uploads", tipo)
    os.makedirs(carpeta, exist_ok=True)
    nombre_disco = f"{uuid.uuid4().hex}.{extension}"
    with open(os.path.join(carpeta, nombre_disco), "wb") as f:
        f.write(datos)

    ancho_px = alto_px = None
    if tipo == "imagen":
        ancho_px, alto_px = _dimensiones_imagen(datos)

    duracion_segundos = request.form.get("duracion_segundos", type=int)

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
    return jsonify(registro.to_dict()), 201


@archivos_bp.route("/<int:archivo_id>", methods=["GET"])
def obtener_archivo(archivo_id):
    archivo = Archivo.query.filter_by(id=archivo_id).filter(Archivo.eliminado_en.is_(None)).first_or_404()
    return jsonify(archivo.to_dict()), 200


@archivos_bp.route("/<int:archivo_id>", methods=["DELETE"])
@jwt_required()
def eliminar_archivo(archivo_id):
    """Borrado suave: el archivo puede estar referenciado desde otra
    tabla (portada de un evento, logo de un organizador, etc.), así que
    no se borra la fila ni el archivo en disco, solo se marca."""
    usuario = get_usuario_actual()
    archivo = Archivo.query.filter_by(id=archivo_id).filter(Archivo.eliminado_en.is_(None)).first_or_404()
    if archivo.propietario_id != usuario.id and usuario.rol != "administrador":
        return jsonify({"error": "No puedes eliminar un archivo que no es tuyo"}), 403

    archivo.eliminado_en = datetime.now(timezone.utc)
    db.session.commit()
    return "", 204

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from models import Archivo
from utils.archivos import guardar_archivo_subido
from utils.auth import get_usuario_actual

archivos_bp = Blueprint("archivos", __name__, url_prefix="/api/archivos")


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
    registro, error = guardar_archivo_subido(
        usuario,
        request.files["archivo"],
        tipo=request.form.get("tipo"),
        duracion_segundos=request.form.get("duracion_segundos", type=int),
    )
    if error:
        return jsonify({"error": error[0]}), error[1]
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

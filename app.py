from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_swagger_ui import get_swaggerui_blueprint

from config import Config
from database import db

from routes.auth import auth_bp
from routes.usuarios import usuarios_bp
from routes.deportes import deportes_bp
from routes.cuestionarios import cuestionarios_bp
from routes.eventos import eventos_bp
from routes.rutas import rutas_bp
from routes.inscripciones import inscripciones_bp
from routes.organizadores import organizadores_bp
from routes.soporte import soporte_bp

SWAGGER_URL = "/api/docs"
OPENAPI_SPEC_URL = "/static/openapi.yaml"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)

    db.init_app(app)
    JWTManager(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(deportes_bp)
    app.register_blueprint(cuestionarios_bp)
    app.register_blueprint(eventos_bp)
    app.register_blueprint(rutas_bp)
    app.register_blueprint(inscripciones_bp)
    app.register_blueprint(organizadores_bp)
    app.register_blueprint(soporte_bp)

    swagger_ui_bp = get_swaggerui_blueprint(
        SWAGGER_URL,
        OPENAPI_SPEC_URL,
        config={"app_name": "Api-SportMatch", "persistAuthorization": True},
    )
    app.register_blueprint(swagger_ui_bp, url_prefix=SWAGGER_URL)

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "proyecto": "SportMatch"}), 200

    with app.app_context():
        import models  # noqa: F401  (registra los modelos antes de create_all)

        db.create_all()

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Recurso no encontrado"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Error interno del servidor"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", debug=True, port=5000)

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_swagger_ui import get_swaggerui_blueprint

from config import Config
from database import db

# Aquí se importan los blueprints conforme se vayan creando en routes/:
# from routes.auth import auth_bp
# from routes.usuarios import usuarios_bp

SWAGGER_URL = "/api/docs"
OPENAPI_SPEC_URL = "/static/openapi.yaml"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)

    db.init_app(app)
    JWTManager(app)

    # Registro de blueprints:
    # app.register_blueprint(auth_bp)
    # app.register_blueprint(usuarios_bp)

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

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", debug=True, port=5000)

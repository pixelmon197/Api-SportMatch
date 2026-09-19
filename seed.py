"""
Datos iniciales de Api-SportMatch (roles, catálogos, usuarios de ejemplo...).

Uso:
    python seed.py
"""
from app import create_app
from database import db  # noqa: F401


def seed():
    # TODO: agregar aquí los datos iniciales cuando existan los modelos.
    # Ejemplo:
    #   db.session.add(Rol(nombre="admin", nivel_privilegio=9))
    #   db.session.commit()
    print("Seed ejecutado (sin datos por ahora).")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()

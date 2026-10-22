"""
Datos iniciales de Api-SportMatch: una ciudad de ejemplo y el primer
usuario administrador.

Uso:
    python seed.py
"""
from app import create_app
from database import db
from datetime import date

from models import Ciudad, Comision, Usuario


def seed():
    if not Ciudad.query.filter_by(nombre="Toluca").first():
        ciudad = Ciudad(nombre="Toluca", estado="México", pais="México")
        db.session.add(ciudad)
        db.session.commit()
        print(f"Ciudad creada: {ciudad.nombre} (id={ciudad.id})")
    else:
        ciudad = Ciudad.query.filter_by(nombre="Toluca").first()
        print("Ciudad demo ya existía.")

    if not Usuario.query.filter_by(correo="admin@sportmatch.com").first():
        admin = Usuario(
            nombre_completo="Administrador SportMatch",
            nombre_usuario="admin",
            correo="admin@sportmatch.com",
            rol="administrador",
            estado_cuenta="activa",
            ciudad_id=ciudad.id,
        )
        admin.set_password("Admin123!")
        db.session.add(admin)
        db.session.commit()
        print("Usuario admin creado -> correo: admin@sportmatch.com / password: Admin123!")
        print("IMPORTANTE: cambia esta contraseña en cuanto inicies sesión.")
    else:
        print("El usuario admin ya existía.")

    # Comisión inicial de la plataforma (10 % por inscripción). Un admin la
    # cambia después con POST /api/comisiones.
    if not Comision.query.filter_by(concepto="inscripcion").first():
        db.session.add(Comision(concepto="inscripcion", porcentaje=10, vigente_desde=date(2026, 1, 1)))
        db.session.commit()
        print("Comisión inicial creada: 10 % por inscripción.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()

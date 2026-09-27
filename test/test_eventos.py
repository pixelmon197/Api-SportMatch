import os, sys, sqlite3

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_eventos.sqlite3"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "test"
os.environ["JWT_SECRET_KEY"] = "test"

DDL = """
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL, correo TEXT UNIQUE, contrasena TEXT,
    fecha_nacimiento DATE, sexo TEXT, rol TEXT NOT NULL DEFAULT 'usuario',
    estado_cuenta TEXT NOT NULL DEFAULT 'pendiente_verificacion',
    correo_verificado_en TIMESTAMP, ultimo_acceso TIMESTAMP,
    nombre_usuario TEXT UNIQUE, telefono TEXT, ciudad_id INTEGER,
    idioma TEXT DEFAULT 'es', zona_horaria TEXT DEFAULT 'America/Mexico_City',
    codigo_referido TEXT UNIQUE, registro_completo_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
CREATE TABLE organizadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    nombre_comercial TEXT NOT NULL,
    descripcion TEXT, correo_contacto TEXT, telefono_contacto TEXT,
    ciudad_id INTEGER, logo_id INTEGER,
    estado_validacion TEXT NOT NULL DEFAULT 'sin_solicitud',
    validado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP,
    CHECK (estado_validacion IN ('sin_solicitud','pendiente','en_revision','aprobada','rechazada','revocada'))
);
CREATE TABLE organizador_miembros (
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    rol TEXT NOT NULL DEFAULT 'colaborador',
    agregado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organizador_id, usuario_id)
);
CREATE TABLE deportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE,
    categoria TEXT, activo BOOLEAN NOT NULL DEFAULT 1
);
CREATE TABLE ciudades (
    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
    estado TEXT NOT NULL, pais TEXT NOT NULL DEFAULT 'México'
);
CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id),
    tipo TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'borrador',
    dificultad TEXT,
    titulo TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    portada_id INTEGER,
    edad_minima INTEGER,
    es_publico BOOLEAN NOT NULL DEFAULT 1,
    publicado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP,
    CHECK (estado <> 'publicado' OR publicado_en IS NOT NULL),
    CHECK (dificultad IN ('facil','moderada','dificil','extrema') OR dificultad IS NULL),
    CHECK (edad_minima >= 0 OR edad_minima IS NULL),
    CHECK (estado IN ('borrador','en_revision','publicado','cancelado','finalizado')),
    CHECK (tipo IN ('carrera','ruta','torneo','liga','entrenamiento','experiencia_grupal'))
);
CREATE TABLE evento_sedes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL, nombre TEXT NOT NULL, direccion TEXT,
    ciudad_id INTEGER, latitud NUMERIC, longitud NUMERIC,
    CHECK (tipo IN ('salida','meta','punto_encuentro','entrega_kit'))
);
CREATE TABLE evento_categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL, distancia_km NUMERIC, edad_minima INTEGER,
    edad_maxima INTEGER, cupo_total INTEGER,
    permite_lista_espera BOOLEAN NOT NULL DEFAULT 0,
    UNIQUE (id, evento_id),
    CHECK (edad_minima IS NULL OR edad_maxima IS NULL OR edad_maxima >= edad_minima),
    CHECK (cupo_total IS NULL OR cupo_total > 0),
    CHECK (distancia_km IS NULL OR distancia_km > 0)
);
CREATE TABLE evento_boletos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER NOT NULL REFERENCES evento_categorias(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL, precio NUMERIC NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'MXN',
    disponible_desde TIMESTAMP, disponible_hasta TIMESTAMP,
    cantidad_maxima INTEGER, activo BOOLEAN NOT NULL DEFAULT 1,
    UNIQUE (id, categoria_id),
    CHECK (disponible_desde IS NULL OR disponible_hasta IS NULL OR disponible_hasta > disponible_desde),
    CHECK (precio >= 0),
    CHECK (tipo IN ('general','preventa','estudiante','grupal'))
);
CREATE TABLE evento_deportes (
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    deporte_id INTEGER NOT NULL REFERENCES deportes(id),
    PRIMARY KEY (evento_id, deporte_id)
);
CREATE TABLE evento_requisitos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    descripcion TEXT NOT NULL, orden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE evento_fechas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    inicia_en TIMESTAMP NOT NULL, termina_en TIMESTAMP, cancelada_en TIMESTAMP,
    UNIQUE (id, evento_id),
    CHECK (termina_en IS NULL OR termina_en > inicia_en)
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Ana Perez','ana@correo.com','x','2000-01-01','femenino','anaperez','usuario','activa',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Admin Uno','admin@correo.com','x','1990-01-01','masculino','admin1','admin','activa',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO organizadores (usuario_id, nombre_comercial, estado_validacion) VALUES (1, 'Carreras del Valle', 'aprobada')")
conn.execute("INSERT INTO organizador_miembros (organizador_id, usuario_id, rol) VALUES (1, 1, 'propietario')")
conn.execute("INSERT INTO deportes (nombre, categoria) VALUES ('Running', 'resistencia')")
conn.commit()
conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
client = app.test_client()
with app.app_context():
    H_ANA = {"Authorization": f"Bearer {create_access_token(identity='1', additional_claims={'rol': 'usuario'})}"}
    H_ADMIN = {"Authorization": f"Bearer {create_access_token(identity='2', additional_claims={'rol': 'admin'})}"}

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

# 1) Crear evento completo (deportes, requisitos, sedes, fechas, categorias+boletos)
payload = {
    "titulo": "5K Nocturna",
    "tipo": "carrera",
    "organizador_id": 1,
    "dificultad": "moderada",
    "edad_minima": 12,
    "deportes": [1],
    "requisitos": [{"descripcion": "Certificado medico", "orden": 1}],
    "sedes": [{"tipo": "salida", "nombre": "Parque Central"}],
    "fechas": [{"inicia_en": "2026-11-15T19:00:00", "termina_en": "2026-11-15T22:00:00"}],
    "categorias": [{
        "nombre": "5K Varonil", "distancia_km": 5, "cupo_total": 100,
        "boletos": [{"tipo": "general", "precio": 250}],
    }],
}
r = client.post("/api/eventos", json=payload, headers=H_ANA)
show("CREAR EVENTO (completo)", r)
assert r.status_code == 201, r.get_json()
evento = r.get_json()
evento_id = evento["id"]
assert evento["deportes"][0]["nombre"] == "Running"
assert evento["requisitos"][0]["descripcion"] == "Certificado medico"
assert evento["sedes"][0]["tipo"] == "salida"
assert evento["categorias"][0]["boletos"][0]["precio"] == 250

# 2) tipo invalido debe rechazarse con 400 (antes: sin validar -> 500 en Neon real)
r = client.post("/api/eventos", json={"titulo": "X", "tipo": "clinica", "organizador_id": 1}, headers=H_ANA)
show("CREAR EVENTO (tipo invalido)", r)
assert r.status_code == 400

# 3) dificultad vieja ('avanzado') ya no es valida
r = client.post("/api/eventos", json={"titulo": "X", "tipo": "carrera", "organizador_id": 1, "dificultad": "avanzado"}, headers=H_ANA)
show("CREAR EVENTO (dificultad vieja invalida)", r)
assert r.status_code == 400

# 4) sede con tipo viejo 'sede_unica' ya no es valido
r = client.post("/api/eventos", json={"titulo": "Y", "tipo": "carrera", "organizador_id": 1,
                                        "sedes": [{"nombre": "Plaza"}]}, headers=H_ANA)
show("CREAR EVENTO (sede sin tipo -> default nuevo)", r)
assert r.status_code == 201
assert r.get_json()["sedes"][0]["tipo"] == "punto_encuentro"

# 5) evento sin organizador_id (ni admin) debe rechazarse (antes: NULL permitido)
r = client.post("/api/eventos", json={"titulo": "Z", "tipo": "carrera"}, headers=H_ADMIN)
show("CREAR EVENTO (admin sin organizador_id, debe fallar)", r)
assert r.status_code == 400

# 6) agregar deporte ya asociado -> antes rompía por EventoDeporte.id
# inexistente (500); ahora debe responder 409 de forma controlada.
r = client.post(f"/api/eventos/{evento_id}/deportes", json={"deporte_id": 1}, headers=H_ANA)
show("AGREGAR DEPORTE (ya asociado)", r)
assert r.status_code == 409, r.get_json()

# 6b) agregar un deporte distinto (aún no asociado) -> debe funcionar
conn2 = sqlite3.connect(DB_PATH)
conn2.execute("INSERT INTO deportes (nombre, categoria) VALUES ('Ciclismo', 'resistencia')")
conn2.commit()
conn2.close()
r = client.post(f"/api/eventos/{evento_id}/deportes", json={"deporte_id": 2}, headers=H_ANA)
show("AGREGAR DEPORTE (nuevo)", r)
assert r.status_code == 201

# 6c) quitar deporte
r = client.delete(f"/api/eventos/{evento_id}/deportes/1", headers=H_ANA)
show("QUITAR DEPORTE", r)
assert r.status_code == 204

# 7) boleto con tipo viejo 'vip' ya no es valido
r = client.post(f"/api/eventos/categorias/{evento['categorias'][0]['id']}/boletos",
                 json={"tipo": "vip", "precio": 500}, headers=H_ANA)
show("AGREGAR BOLETO (tipo viejo invalido)", r)
assert r.status_code == 400

# 8) boleto con precio negativo
r = client.post(f"/api/eventos/categorias/{evento['categorias'][0]['id']}/boletos",
                 json={"tipo": "preventa", "precio": -10}, headers=H_ANA)
show("AGREGAR BOLETO (precio negativo)", r)
assert r.status_code == 400

# 9) publicar evento -> debe fijar publicado_en (CHECK real lo exige)
r = client.put(f"/api/eventos/{evento_id}", json={"estado": "publicado"}, headers=H_ANA)
show("PUBLICAR EVENTO", r)
assert r.status_code == 200 and r.get_json()["publicado_en"] is not None

# 10) categoria con edad_maxima menor que edad_minima
r = client.post(f"/api/eventos/{evento_id}/categorias",
                 json={"nombre": "Infantil", "edad_minima": 10, "edad_maxima": 5}, headers=H_ANA)
show("AGREGAR CATEGORIA (edades invertidas)", r)
assert r.status_code == 400

print("\nTODAS LAS PRUEBAS DE EVENTOS PASARON")

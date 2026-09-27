import os, sys, sqlite3

sys.path.insert(0, "/home/claude/work/api_sportmatch/Api-SportMatch")

DB_PATH = "/home/claude/work/test_rutas.sqlite3"
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
    estado_validacion TEXT NOT NULL DEFAULT 'sin_solicitud',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organizador_id INTEGER NOT NULL REFERENCES organizadores(id),
    tipo TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'borrador',
    dificultad TEXT, titulo TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
    descripcion TEXT, portada_id INTEGER, edad_minima INTEGER,
    es_publico BOOLEAN NOT NULL DEFAULT 1, publicado_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
CREATE TABLE evento_categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL, distancia_km NUMERIC, edad_minima INTEGER,
    edad_maxima INTEGER, cupo_total INTEGER,
    permite_lista_espera BOOLEAN NOT NULL DEFAULT 0,
    UNIQUE (id, evento_id)
);
CREATE TABLE rutas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creador_id INTEGER REFERENCES usuarios(id),
    deporte_id INTEGER REFERENCES deportes(id),
    gpx_archivo_id INTEGER,
    dificultad TEXT, nombre TEXT NOT NULL, descripcion TEXT,
    distancia_m INTEGER, desnivel_positivo_m INTEGER,
    es_publica BOOLEAN NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP,
    CHECK (dificultad IN ('facil','moderada','dificil','extrema') OR dificultad IS NULL),
    CHECK (distancia_m IS NULL OR distancia_m > 0),
    CHECK (desnivel_positivo_m IS NULL OR desnivel_positivo_m >= 0)
);
CREATE TABLE ruta_puntos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ruta_id INTEGER NOT NULL REFERENCES rutas(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL, orden INTEGER NOT NULL, nombre TEXT,
    latitud NUMERIC NOT NULL, longitud NUMERIC NOT NULL, altitud_m NUMERIC,
    UNIQUE (ruta_id, orden),
    CHECK (tipo IN ('inicio','meta','hidratacion','punto_interes','mirador','peligro'))
);
CREATE TABLE evento_rutas (
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    ruta_id INTEGER NOT NULL REFERENCES rutas(id),
    categoria_id INTEGER,
    PRIMARY KEY (evento_id, ruta_id),
    FOREIGN KEY (categoria_id, evento_id) REFERENCES evento_categorias(id, evento_id)
);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Ana Perez','ana@correo.com','x','2000-01-01','femenino','anaperez','usuario','activa',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES ('Luis Gomez','luis@correo.com','x','1998-01-01','masculino','luisg','usuario','activa',CURRENT_TIMESTAMP)")
conn.execute("INSERT INTO organizadores (usuario_id, nombre_comercial, estado_validacion) VALUES (1,'Carreras del Valle','aprobada')")
conn.execute("INSERT INTO organizador_miembros (organizador_id, usuario_id, rol) VALUES (1,1,'propietario')")
conn.execute("INSERT INTO deportes (nombre, categoria) VALUES ('Running','resistencia')")
conn.execute("INSERT INTO eventos (organizador_id, tipo, titulo, slug) VALUES (1,'carrera','5K Nocturna','5k-nocturna')")
conn.execute("INSERT INTO evento_categorias (evento_id, nombre) VALUES (1, '5K Varonil')")
conn.commit()
conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
client = app.test_client()
with app.app_context():
    H_ANA = {"Authorization": f"Bearer {create_access_token(identity='1', additional_claims={'rol': 'usuario'})}"}
    H_LUIS = {"Authorization": f"Bearer {create_access_token(identity='2', additional_claims={'rol': 'usuario'})}"}

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

# 1) Crear ruta completa con puntos
payload = {
    "nombre": "Sendero del Bosque", "deporte_id": 1, "dificultad": "moderada",
    "distancia_m": 5000, "desnivel_positivo_m": 120,
    "puntos": [
        {"tipo": "inicio", "orden": 1, "latitud": 19.4, "longitud": -99.1},
        {"tipo": "meta", "orden": 2, "latitud": 19.5, "longitud": -99.2},
    ],
}
r = client.post("/api/rutas", json=payload, headers=H_ANA)
show("CREAR RUTA (completa)", r)
assert r.status_code == 201, r.get_json()
ruta = r.get_json()
ruta_id = ruta["id"]
assert ruta["puntos"][0]["tipo"] == "inicio"
assert ruta["distancia_m"] == 5000 and ruta["desnivel_positivo_m"] == 120

# 2) dificultad vieja ('avanzado') ya no es valida
r = client.post("/api/rutas", json={"nombre": "X", "deporte_id": 1, "dificultad": "avanzado"}, headers=H_ANA)
show("CREAR RUTA (dificultad vieja invalida)", r)
assert r.status_code == 400

# 3) tipo de punto viejo ('fin'/'paso') ya no es valido
r = client.post("/api/rutas", json={"nombre": "Y", "deporte_id": 1,
                                      "puntos": [{"tipo": "fin", "latitud": 1, "longitud": 1}]}, headers=H_ANA)
show("CREAR RUTA (tipo de punto viejo invalido)", r)
assert r.status_code == 400

# 4) distancia_m negativa o cero
r = client.post("/api/rutas", json={"nombre": "Z", "deporte_id": 1, "distancia_m": 0}, headers=H_ANA)
show("CREAR RUTA (distancia_m = 0, invalido)", r)
assert r.status_code == 400

# 5) distancia_m fraccionaria (columna real es entera)
r = client.post("/api/rutas", json={"nombre": "W", "deporte_id": 1, "distancia_m": 5000.5}, headers=H_ANA)
show("CREAR RUTA (distancia_m fraccionaria, invalido)", r)
assert r.status_code == 400

# 6) desnivel negativo
r = client.post("/api/rutas", json={"nombre": "V", "deporte_id": 1, "desnivel_positivo_m": -10}, headers=H_ANA)
show("CREAR RUTA (desnivel negativo, invalido)", r)
assert r.status_code == 400

# 7) agregar punto con orden repetido -> 409 (antes: 500 por UNIQUE)
r = client.post(f"/api/rutas/{ruta_id}/puntos", json={"tipo": "mirador", "orden": 1, "latitud": 1, "longitud": 1}, headers=H_ANA)
show("AGREGAR PUNTO (orden repetido)", r)
assert r.status_code == 409

# 8) agregar punto con tipo valido (mirador, peligro, hidratacion son "vocabulario nuevo")
r = client.post(f"/api/rutas/{ruta_id}/puntos", json={"tipo": "peligro", "orden": 3, "latitud": 1, "longitud": 1}, headers=H_ANA)
show("AGREGAR PUNTO (tipo nuevo valido)", r)
assert r.status_code == 201

# 9) Ligar ruta a categoria de evento -> antes rompía por EventoRuta.id inexistente
r = client.post("/api/rutas/categorias/1/rutas", json={"ruta_id": ruta_id}, headers=H_ANA)
show("LIGAR RUTA A CATEGORIA", r)
assert r.status_code == 201, r.get_json()
assert r.get_json()["evento_id"] == 1 and r.get_json()["ruta_id"] == ruta_id

# 10) Ligar la misma ruta otra vez al mismo evento -> 409 (PK compuesta evento_id+ruta_id)
r = client.post("/api/rutas/categorias/1/rutas", json={"ruta_id": ruta_id}, headers=H_ANA)
show("LIGAR RUTA (repetida, debe fallar)", r)
assert r.status_code == 409

# 11) Listar rutas de la categoria
r = client.get("/api/rutas/categorias/1/rutas")
show("LISTAR RUTAS DE CATEGORIA", r)
assert r.status_code == 200 and len(r.get_json()) == 1

# 12) Desligar (con la nueva ruta compuesta evento_id/ruta_id)
r = client.delete(f"/api/rutas/eventos-rutas/1/{ruta_id}", headers=H_ANA)
show("DESLIGAR RUTA", r)
assert r.status_code == 204

# 13) Usuario ajeno no puede editar la ruta de otro
r = client.put(f"/api/rutas/{ruta_id}", json={"nombre": "hackeo"}, headers=H_LUIS)
show("EDITAR RUTA (usuario ajeno, debe fallar)", r)
assert r.status_code == 403

print("\nTODAS LAS PRUEBAS DE RUTAS PASARON")

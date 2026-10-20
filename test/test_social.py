import os, sys, sqlite3

# Rutas relativas a este archivo: funciona sin importar desde dónde se
# ejecute ni en qué máquina, siempre que este script viva en test/ dentro
# del proyecto (Api-SportMatch/test/este_archivo.py).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_DIR)

DB_PATH = os.path.join(BASE_DIR, "test_social.sqlite3")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "test"
os.environ["JWT_SECRET_KEY"] = "test"

DDL = """
CREATE TABLE ciudades (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'México', pais TEXT NOT NULL DEFAULT 'México', codigo_postal TEXT);
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL, correo TEXT UNIQUE, contrasena TEXT,
    fecha_nacimiento DATE, sexo TEXT, rol TEXT NOT NULL DEFAULT 'usuario',
    estado_cuenta TEXT NOT NULL DEFAULT 'pendiente_verificacion',
    correo_verificado_en TIMESTAMP, ultimo_acceso TIMESTAMP,
    nombre_usuario TEXT UNIQUE, telefono TEXT, ciudad_id INTEGER REFERENCES ciudades(id),
    idioma TEXT DEFAULT 'es', zona_horaria TEXT DEFAULT 'America/Mexico_City',
    codigo_referido TEXT UNIQUE, registro_completo_en TIMESTAMP,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eliminado_en TIMESTAMP
);
CREATE TABLE archivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, propietario_id INTEGER REFERENCES usuarios(id),
    tipo VARCHAR(20) NOT NULL, url VARCHAR(500) NOT NULL, nombre_original VARCHAR(200), tipo_mime VARCHAR(100),
    tamano_bytes BIGINT, ancho_px INTEGER, alto_px INTEGER, duracion_segundos INTEGER,
    subido_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, eliminado_en TIMESTAMP
);
CREATE TABLE deportes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE, categoria TEXT, activo BOOLEAN NOT NULL DEFAULT 1);
CREATE TABLE usuario_deportes (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    deporte_id INTEGER NOT NULL REFERENCES deportes(id),
    nivel TEXT, es_principal BOOLEAN NOT NULL DEFAULT 0, PRIMARY KEY (usuario_id, deporte_id)
);
CREATE TABLE perfiles (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    biografia TEXT, avatar_id INTEGER REFERENCES archivos(id), portada_id INTEGER REFERENCES archivos(id),
    visibilidad_perfil VARCHAR(20) NOT NULL DEFAULT 'publico',
    visibilidad_ubicacion VARCHAR(20) NOT NULL DEFAULT 'amigos',
    quien_puede_escribir VARCHAR(20) NOT NULL DEFAULT 'publico',
    aparecer_en_cercanos BOOLEAN NOT NULL DEFAULT 1,
    latitud NUMERIC, longitud NUMERIC, ubicacion_actualizada_en TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE amistades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    amigo_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, respondida_en TIMESTAMP,
    UNIQUE (usuario_id, amigo_id), CHECK (usuario_id <> amigo_id)
);
CREATE TABLE seguidores (
    seguidor_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    seguido_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (seguidor_id, seguido_id), CHECK (seguidor_id <> seguido_id)
);
CREATE TABLE bloqueos (
    bloqueador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    bloqueado_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bloqueador_id, bloqueado_id), CHECK (bloqueador_id <> bloqueado_id)
);
"""

def sql(consulta, *params):
    c = sqlite3.connect(DB_PATH)
    try:
        filas = c.execute(consulta, params).fetchall(); c.commit(); return filas
    finally:
        c.close()

conn = sqlite3.connect(DB_PATH)
conn.executescript(DDL)
def usuario(nombre, correo, nick, rol="usuario", estado="activa"):
    conn.execute("INSERT INTO usuarios (nombre_completo, correo, contrasena, fecha_nacimiento, sexo, nombre_usuario, rol, estado_cuenta, registro_completo_en) VALUES (?,?,'x','2000-01-01','femenino',?,?,?,CURRENT_TIMESTAMP)", (nombre, correo, nick, rol, estado))
usuario("Ana Perez", "ana@correo.com", "anaperez")                   # 1
usuario("Luis Gomez", "luis@correo.com", "luisg")                    # 2
usuario("Marta Diaz", "marta@correo.com", "martad")                  # 3
usuario("Pablo Ruiz", "pablo@correo.com", "pabloruiz")               # 4
usuario("Admin Uno", "admin@correo.com", "admin1", "administrador")  # 5
usuario("Suspendido", "susp@correo.com", "suspendido", estado="suspendida")  # 6
conn.execute("INSERT INTO archivos (id, propietario_id, tipo, url) VALUES (1, 2, 'imagen', '/static/uploads/imagen/luis.png')")
conn.execute("INSERT INTO perfiles (usuario_id, avatar_id) VALUES (2, 1)")  # Luis tiene avatar
conn.commit(); conn.close()

from app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
client = app.test_client()
with app.app_context():
    tok = lambda i, rol="usuario": {"Authorization": "Bearer " + create_access_token(identity=str(i), additional_claims={"rol": rol})}
    ANA, LUIS, MARTA, PABLO, ADMIN = tok(1), tok(2), tok(3), tok(4), tok(5, "administrador")

def show(label, resp):
    print(f"--- {label} [{resp.status_code}] ---")
    print(resp.get_json())

ids = lambda lista, clave="id": [x[clave] for x in lista]

# ======================= SEGUIDORES =======================
r = client.post("/api/seguidores/2", headers=ANA)
show("SEGUIR (Ana -> Luis)", r); assert r.status_code == 201 and r.get_json()["seguido_id"] == 2
assert client.post("/api/seguidores/2", headers=ANA).status_code == 409           # repetido
assert client.post("/api/seguidores/1", headers=ANA).status_code == 400           # a si misma
assert client.post("/api/seguidores/999", headers=ANA).status_code == 404         # no existe
assert client.post("/api/seguidores/6", headers=ANA).status_code == 404           # cuenta suspendida
assert client.post("/api/seguidores/2").status_code == 401                        # sin token
client.post("/api/seguidores/2", headers=MARTA)
client.post("/api/seguidores/2", headers=PABLO)
print("--- reglas de seguir OK ---")

# Listas propias, con avatar y fecha, y paginacion con el mismo formato del resto de la API
r = client.get("/api/seguidores/me/seguidores", headers=LUIS)
show("MIS SEGUIDORES (Luis)", r)
b = r.get_json()
assert b["total"] == 3 and sorted(ids(b["seguidores"])) == [1, 3, 4] and b["paginas"] == 1 and "desde" in b["seguidores"][0]
r = client.get("/api/seguidores/me/seguidores?per_page=2&page=2", headers=LUIS)
assert len(r.get_json()["seguidores"]) == 1 and r.get_json()["paginas"] == 2
r = client.get("/api/seguidores/me/siguiendo", headers=ANA)
assert ids(r.get_json()["siguiendo"]) == [2] and r.get_json()["siguiendo"][0]["avatar_url"] == "/static/uploads/imagen/luis.png"

# Listas de otra persona: respetan la visibilidad de su perfil
assert client.get("/api/seguidores/2/seguidores").status_code == 200              # anonimo, perfil publico
client.put("/api/perfiles/me", json={"visibilidad_perfil": "privado"}, headers=LUIS)
assert client.get("/api/seguidores/2/seguidores", headers=ANA).status_code == 403
assert client.get("/api/seguidores/2/siguiendo").status_code == 403
assert client.get("/api/seguidores/2/seguidores", headers=LUIS).status_code == 200  # el dueno
client.put("/api/perfiles/me", json={"visibilidad_perfil": "publico"}, headers=LUIS)
assert client.get("/api/seguidores/999/seguidores").status_code == 404

# Los contadores y la relacion aparecen en el perfil
r = client.get("/api/perfiles/2", headers=ANA); v = r.get_json()
show("PERFIL DE LUIS (visto por Ana)", r)
assert v["contadores"] == {"seguidores": 3, "siguiendo": 0, "amigos": 0}
assert v["relacion"] == {"yo_sigo": True, "me_sigue": False, "amistad": "ninguna", "amistad_id": None}
assert client.get("/api/perfiles/2").get_json()["relacion"] is None                # anonimo: sin relacion

# Dejar de seguir
assert client.delete("/api/seguidores/2", headers=PABLO).status_code == 204
assert client.delete("/api/seguidores/2", headers=PABLO).status_code == 404
assert client.get("/api/perfiles/2").get_json()["contadores"]["seguidores"] == 2
print("--- seguidores OK ---")

# ======================= AMISTADES =======================
r = client.post("/api/amistades/solicitudes", json={"usuario_id": 3}, headers=ANA)
show("SOLICITUD (Ana -> Marta)", r)
assert r.status_code == 201 and r.get_json()["estado"] == "pendiente"
sol_ana_marta = r.get_json()["id"]
assert client.post("/api/amistades/solicitudes", json={"usuario_id": 3}, headers=ANA).status_code == 409  # repetida
r = client.post("/api/amistades/solicitudes", json={"usuario_id": 1}, headers=MARTA)  # ya me la envio ella
show("SOLICITUD cruzada (Marta -> Ana, ya existe la de Ana)", r)
assert r.status_code == 409 and r.get_json()["solicitud_id"] == sol_ana_marta
for body, codigo in (({}, 400), ({"usuario_id": "3"}, 400), ({"usuario_id": True}, 400), ({"usuario_id": 1}, 400),
                     ({"usuario_id": 999}, 404), ({"usuario_id": 6}, 404)):
    assert client.post("/api/amistades/solicitudes", json=body, headers=ANA).status_code == codigo, body

# Bandejas
r = client.get("/api/amistades/solicitudes/recibidas", headers=MARTA)
show("RECIBIDAS (Marta)", r)
assert ids(r.get_json()["solicitudes"], "solicitud_id") == [sol_ana_marta] and r.get_json()["solicitudes"][0]["usuario"]["id"] == 1
assert ids(client.get("/api/amistades/solicitudes/enviadas", headers=ANA).get_json()["solicitudes"], "solicitud_id") == [sol_ana_marta]
assert client.get("/api/amistades/solicitudes/recibidas", headers=ANA).get_json()["total"] == 0

# El perfil refleja la solicitud segun quien mira
assert client.get("/api/perfiles/3", headers=ANA).get_json()["relacion"]["amistad"] == "solicitud_enviada"
rel = client.get("/api/perfiles/1", headers=MARTA).get_json()["relacion"]
assert rel["amistad"] == "solicitud_recibida" and rel["amistad_id"] == sol_ana_marta

# Solo quien la recibe puede responder
r = client.put(f"/api/amistades/solicitudes/{sol_ana_marta}/aceptar", headers=ANA)
show("ACEPTAR (la que la envio, no puede)", r); assert r.status_code == 403
assert client.put(f"/api/amistades/solicitudes/{sol_ana_marta}/aceptar", headers=LUIS).status_code == 403
assert client.put("/api/amistades/solicitudes/9999/aceptar", headers=MARTA).status_code == 404
r = client.put(f"/api/amistades/solicitudes/{sol_ana_marta}/aceptar", headers=MARTA)
show("ACEPTAR (Marta)", r); assert r.status_code == 200 and r.get_json()["estado"] == "aceptada" and r.get_json()["respondida_en"]
assert client.put(f"/api/amistades/solicitudes/{sol_ana_marta}/aceptar", headers=MARTA).status_code == 409
assert client.put(f"/api/amistades/solicitudes/{sol_ana_marta}/rechazar", headers=MARTA).status_code == 409
assert client.post("/api/amistades/solicitudes", json={"usuario_id": 3}, headers=ANA).status_code == 409  # ya son amigos

# Lista de amigos (para ambas) y efecto en perfiles
for headers, esperado in ((ANA, 3), (MARTA, 1)):
    r = client.get("/api/amistades", headers=headers)
    assert ids(r.get_json()["amigos"]) == [esperado] and r.get_json()["amigos"][0]["desde"]
show("MIS AMIGOS (Ana)", client.get("/api/amistades", headers=ANA))
assert client.get("/api/perfiles/1", headers=MARTA).get_json()["relacion"]["amistad"] == "aceptada"
assert client.get("/api/perfiles/1").get_json()["contadores"]["amigos"] == 1
# ...y ahora SI funciona la visibilidad 'amigos' de los perfiles
client.put("/api/perfiles/me", json={"visibilidad_perfil": "amigos"}, headers=ANA)
assert client.get("/api/perfiles/1", headers=MARTA).status_code == 200
assert client.get("/api/perfiles/1", headers=LUIS).status_code == 403
client.put("/api/perfiles/me", json={"visibilidad_perfil": "publico"}, headers=ANA)

# Rechazar, volver a enviar (se reutiliza la fila) y cancelar
r = client.post("/api/amistades/solicitudes", json={"usuario_id": 4}, headers=LUIS); sol_luis_pablo = r.get_json()["id"]
r = client.put(f"/api/amistades/solicitudes/{sol_luis_pablo}/rechazar", headers=PABLO)
show("RECHAZAR (Pablo)", r); assert r.get_json()["estado"] == "rechazada"
assert client.get("/api/amistades/solicitudes/recibidas", headers=PABLO).get_json()["total"] == 0
r = client.post("/api/amistades/solicitudes", json={"usuario_id": 4}, headers=LUIS)
show("REENVIAR tras rechazo", r)
assert r.status_code == 201 and r.get_json()["id"] == sol_luis_pablo and r.get_json()["estado"] == "pendiente"
assert sql("SELECT COUNT(*) FROM amistades WHERE usuario_id=2 AND amigo_id=4")[0][0] == 1   # sin fila duplicada
assert client.delete(f"/api/amistades/solicitudes/{sol_luis_pablo}", headers=PABLO).status_code == 403  # no la envio
assert client.delete(f"/api/amistades/solicitudes/{sol_luis_pablo}", headers=LUIS).status_code == 204   # cancelar
assert client.delete(f"/api/amistades/solicitudes/{sol_luis_pablo}", headers=LUIS).status_code == 404

# Eliminar amigo
r = client.delete("/api/amistades/amigos/3", headers=ANA)
assert r.status_code == 204
assert client.delete("/api/amistades/amigos/3", headers=ANA).status_code == 404
assert client.get("/api/amistades", headers=MARTA).get_json()["total"] == 0
print("--- amistades OK ---")

# ======================= BLOQUEOS =======================
# Preparar: Ana y Luis son amigos, y se siguen mutuamente
client.post("/api/seguidores/1", headers=LUIS)   # Luis -> Ana (Ana -> Luis ya existia)
r = client.post("/api/amistades/solicitudes", json={"usuario_id": 2}, headers=ANA)
client.put(f"/api/amistades/solicitudes/{r.get_json()['id']}/aceptar", headers=LUIS)
assert sql("SELECT COUNT(*) FROM seguidores WHERE (seguidor_id=1 AND seguido_id=2) OR (seguidor_id=2 AND seguido_id=1)")[0][0] == 2
assert sql("SELECT COUNT(*) FROM amistades WHERE estado='aceptada'")[0][0] == 1

r = client.post("/api/bloqueos/2", headers=ANA)
show("BLOQUEAR (Ana -> Luis)", r); assert r.status_code == 201 and r.get_json()["bloqueado_id"] == 2
assert sql("SELECT COUNT(*) FROM seguidores WHERE (seguidor_id=1 AND seguido_id=2) OR (seguidor_id=2 AND seguido_id=1)")[0][0] == 0, "bloquear debe borrar los seguimientos"
assert sql("SELECT COUNT(*) FROM amistades WHERE (usuario_id=1 AND amigo_id=2) OR (usuario_id=2 AND amigo_id=1)")[0][0] == 0, "bloquear debe borrar la amistad"
assert sql("SELECT COUNT(*) FROM seguidores WHERE seguidor_id=3 AND seguido_id=2")[0][0] == 1, "no debe tocar a terceros"

assert client.post("/api/bloqueos/2", headers=ANA).status_code == 409             # ya bloqueado
assert client.post("/api/bloqueos/1", headers=ANA).status_code == 400             # a si misma
assert client.post("/api/bloqueos/999", headers=ANA).status_code == 404
assert client.post("/api/bloqueos/2").status_code == 401

# Para el bloqueado, Ana "no existe"
assert client.get("/api/perfiles/1", headers=LUIS).status_code == 404
assert client.post("/api/seguidores/1", headers=LUIS).status_code == 404
r = client.post("/api/amistades/solicitudes", json={"usuario_id": 1}, headers=LUIS)
show("SOLICITUD del bloqueado", r); assert r.status_code == 404
# Para quien bloqueo, hay que desbloquear primero
r = client.post("/api/seguidores/2", headers=ANA)
show("SEGUIR a quien bloquee", r); assert r.status_code == 409
assert client.post("/api/amistades/solicitudes", json={"usuario_id": 2}, headers=ANA).status_code == 409
assert client.get("/api/perfiles/2", headers=ANA).status_code == 404

# Lista de bloqueados
r = client.get("/api/bloqueos", headers=ANA)
show("MIS BLOQUEADOS", r)
assert ids(r.get_json()["bloqueados"]) == [2] and r.get_json()["bloqueados"][0]["bloqueado_en"]
assert client.get("/api/bloqueos", headers=LUIS).get_json()["total"] == 0

# Las listas de seguidores excluyen a quien tiene un bloqueo con quien consulta
client.post("/api/seguidores/1", headers=MARTA)                 # Marta sigue a Ana
client.post("/api/bloqueos/3", headers=PABLO)                   # Pablo bloquea a Marta
seg_vistos_por_pablo = ids(client.get("/api/seguidores/1/seguidores", headers=PABLO).get_json()["seguidores"])
seg_vistos_por_luis = ids(client.get("/api/seguidores/1/seguidores", headers=ADMIN).get_json()["seguidores"])
assert 3 not in seg_vistos_por_pablo, "Pablo no debe ver a Marta (la bloqueo)"
assert 3 in seg_vistos_por_luis
print("--- listas excluyen bloqueados OK ---")

# Desbloquear: se puede volver a ver el perfil, pero NO se restauran seguimientos ni amistad
r = client.delete("/api/bloqueos/2", headers=ANA); assert r.status_code == 204
assert client.delete("/api/bloqueos/2", headers=ANA).status_code == 404
assert client.get("/api/perfiles/1", headers=LUIS).status_code == 200
c = client.get("/api/perfiles/1", headers=LUIS).get_json()
assert c["relacion"] == {"yo_sigo": False, "me_sigue": False, "amistad": "ninguna", "amistad_id": None}
assert client.post("/api/seguidores/1", headers=LUIS).status_code == 201          # ya puede volver a seguir

# Un administrador tambien puede ser bloqueado, y las cuentas suspendidas aparecen en la lista de bloqueados
r = client.post("/api/bloqueos/6", headers=ANA)
assert r.status_code == 201
assert 6 in ids(client.get("/api/bloqueos", headers=ANA).get_json()["bloqueados"])

print("\nTODAS LAS PRUEBAS SOCIALES (SEGUIDORES, AMISTADES Y BLOQUEOS) PASARON")

# Pruebas de compatibilidad con Neon

Cada archivo prueba un módulo contra un esquema **SQLite** que replica
las columnas, `NOT NULL`, `CHECK`, `UNIQUE` y llaves foráneas (incluidas
las compuestas) reales de `Neon.sql`. No necesitan la base de datos real
ni variables de entorno previas — cada script configura su propia
`DATABASE_URL` apuntando a un `.sqlite3` temporal en esta misma carpeta.

## Requisitos

Los mismos paquetes del proyecto (`Flask`, `Flask-SQLAlchemy`,
`Flask-JWT-Extended`, `Flask-Cors`, etc.). Si ya corres la API
normalmente, ya los tienes. Si no:

```bash
pip install -r ../requirements.txt
```

## Cómo correrlos

Desde la raíz del proyecto (`Api-SportMatch/`):

```bash
python3 test/test_neon_like.py
python3 test/test_organizadores.py
python3 test/test_eventos.py
python3 test/test_rutas.py
python3 test/test_cuestionarios.py
python3 test/test_inscripciones.py
python3 test/test_deportes.py
python3 test/test_soporte.py
python3 test/test_administradores.py
```

O, parado dentro de `test/`:

```bash
cd test
python3 test_neon_like.py
# ...y así con cada uno
```

Cada script imprime el detalle de cada paso (`--- NOMBRE [status] ---`)
y termina con una línea `TODAS LAS PRUEBAS DE ... PASARON` si todo salió
bien. Si algo falla, el traceback señala exactamente en qué `assert` se
detuvo.

## Qué prueba cada uno

| Archivo | Módulo |
|---|---|
| `test_neon_like.py` | Login, Register, Olvidé/Restablecer contraseña, perfil propio |
| `test_organizadores.py` | Organizadores, miembros, solicitudes, cuentas de cobro |
| `test_eventos.py` | Eventos, deportes/requisitos/sedes/fechas/categorías/boletos |
| `test_rutas.py` | Rutas, puntos, liga a categorías de evento |
| `test_cuestionarios.py` | Cuestionarios, preguntas, opciones, respuestas |
| `test_inscripciones.py` | Inscripciones, paquetes de recuperación, valoraciones, calendario |
| `test_deportes.py` | Catálogo de deportes y deportes por usuario |
| `test_soporte.py` | Reportes y tickets de soporte |
| `test_administradores.py` | Rol de administrador y sus permisos |

## Notas

- Cada script crea su propio `test_<nombre>.sqlite3` en esta carpeta al
  correr y lo borra/recrea en cada ejecución — puedes agregar `test/*.sqlite3`
  a tu `.gitignore`.
- Como son independientes entre sí, puedes correr solo el que te
  interese sin ejecutar los demás.
- Estas pruebas **no sustituyen** una corrida final contra el Neon real:
  validan que los nombres de columna, tipos y restricciones del código
  coinciden con `Neon.sql`, pero no pueden replicar cada detalle del
  motor de Postgres.

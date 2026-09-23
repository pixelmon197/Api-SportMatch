# Api-SportMatch

API REST de **SportMatch**. Construida en **Flask + Flask-SQLAlchemy**, con
**PostgreSQL** (Neon) como base de datos, autenticación con **JWT** y
documentación **Swagger / OpenAPI 3.0**.

## Estructura

```
Api-SportMatch/
├── app.py                       # Application factory, JWT, blueprints y Swagger UI
├── config.py                    # Conexión PostgreSQL + configuración JWT
├── database.py                  # Instancia única de SQLAlchemy
├── seed.py                      # Ciudad demo + primer usuario admin
├── requirements.txt
├── .env.example
├── static/
│   └── openapi.yaml             # Spec OpenAPI 3.0 (Fase 2)
├── models/
│   ├── ciudad.py                  # Ciudad
│   ├── usuario.py                 # Usuario (rol, estado_cuenta, borrado suave)
│   ├── token_verificacion.py      # TokenVerificacion (verificar correo / recuperar password)
│   ├── dispositivo.py             # Dispositivo (para push notifications)
│   ├── aceptacion_legal.py        # AceptacionLegal (términos y privacidad)
│   ├── deporte.py                 # Deporte, UsuarioDeporte
│   ├── cuestionario.py            # Cuestionario, Pregunta, OpcionRespuesta, RespuestaUsuario
│   ├── evento.py                  # Evento, EventoDeporte, EventoRequisito, EventoSede,
│   │                               #   EventoFecha, EventoCategoria, EventoBoleto
│   └── ruta.py                    # Ruta, RutaPunto, EventoRuta
├── routes/
│   ├── auth.py                    # /api/auth/register, /login, /me
│   ├── usuarios.py                # /api/usuarios (perfil propio + administración)
│   ├── deportes.py                # /api/deportes (catálogo + deportes del usuario)
│   ├── cuestionarios.py           # /api/cuestionarios (registro guiado)
│   ├── eventos.py                 # /api/eventos (evento + todos sus sub-recursos)
│   └── rutas.py                   # /api/rutas (rutas GPS + su liga a categorías de evento)
├── utils/
│   ├── auth.py                    # @admin_required / @roles_required
│   └── fechas.py                  # parse_datetime / parse_date (JSON string -> datetime)
└── docs/
    ├── fase1_analisis.md          # Qué se analizó y por qué se decidió así
    ├── entidades_completas.md     # Catálogo de las 89 entidades del modelo (columnas)
    └── relaciones_completas.md    # Las 135 relaciones entre entidades
```

## 1. Base de datos

Ya está creada en Neon (PostgreSQL). Solo necesitas la cadena de conexión
(pídela al equipo o revisa tu panel de Neon) para tu `.env`. Las tablas de
esta fase (`usuarios`, `ciudades`, `tockens_verificacion`, `dispositivos`,
`aceptaciones_legales`) las crea la propia API la primera vez que arranca
(`db.create_all()`), sin necesidad de correr ningún script SQL.

## Instalación

```bash
cd Api-SportMatch
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

## Configuración

```bash
cp .env.example .env
```

| Variable         | Descripción                              | Valor por defecto |
|------------------|-------------------------------------------|-------------------|
| `SECRET_KEY`     | Clave secreta de Flask                    | (cámbiala)        |
| `JWT_SECRET_KEY` | Clave para firmar los tokens JWT          | (cámbiala)        |
| `DATABASE_URL`   | Cadena de conexión a PostgreSQL (Neon)    | —                 |

## Ejecución

```bash
python app.py
```

- API: `http://localhost:5000`
- Swagger UI: `http://localhost:5000/api/docs`

Para crear el primer administrador y una ciudad de ejemplo:

```bash
python seed.py
```

Esto crea `admin@sportmatch.com` / `Admin123!` — **cambia esa contraseña**
en cuanto inicies sesión (`PUT /api/usuarios/me/password`).

## Endpoints 

| Método | Ruta                           | Acceso        | Descripción                          |
|--------|--------------------------------|---------------|--------------------------------------|
| GET    | `/api/health`                  | Público       | Estado del servicio                  |
| POST   | `/api/auth/register`           | Público       | Autoregistro (siempre rol `usuario`) |
| POST   | `/api/auth/login`              | Público       | Inicio de sesión, regresa JWT        |
| GET    | `/api/auth/me`                 | Autenticado   | Datos del usuario en sesión          |
| PUT    | `/api/usuarios/me`             | Autenticado   | Editar mi propio perfil              |
| PUT    | `/api/usuarios/me/password`    | Autenticado   | Cambiar mi contraseña                |
| GET    | `/api/usuarios`                | Admin         | Listar usuarios (filtros: `rol`, `estado_cuenta`, `q`; paginado) |
| GET    | `/api/usuarios/<id>`           | Admin         | Ver un usuario                       |
| PUT    | `/api/usuarios/<id>/rol`       | Admin         | Cambiar rol (`usuario` / `admin`)    |
| PUT    | `/api/usuarios/<id>/estado`    | Admin         | Activar / suspender / eliminar       |
| POST   | `/api/usuarios/admins`         | Admin         | Dar de alta a otro administrador     |

Detalle completo de request/response en `/api/docs` (Swagger UI) o en
`static/openapi.yaml`.

**Deportes** — catálogo público; el registro/edición del catálogo es de admin,
cada usuario administra sus propios deportes practicados:

| Método       | Ruta                            |  Acceso                  |
|--------------|---------------------------------|--------------------------|
| GET          | `/api/deportes`                 | Público                  |
| POST / PUT   | `/api/deportes`, `/api/deportes/<id>` | Admin              |
| DELETE       | `/api/deportes/<id>`            | Admin                    |
| GET / POST   | `/api/deportes/me`              | Autenticado              |
| PUT / DELETE | `/api/deportes/me/<deporte_id>` | Autenticado              |

**Cuestionario de registro** — un cuestionario tiene preguntas, y cada
pregunta puede tener opciones (algunas ligadas directo a un deporte del
catálogo):

| Método | Ruta | Acceso |
|---------------|-------------------------------------------|----------------------|
| GET           | `/api/cuestionarios`, `/api/cuestionarios/<codigo>` | Público    |
| POST          | `/api/cuestionarios`                      | Admin                |
| POST          | `/api/cuestionarios/<id>/preguntas`       | Admin                |
| PUT / DELETE  | `/api/cuestionarios/preguntas/<id>`       | Admin                |
| POST / DELETE | `/api/cuestionarios/preguntas/<id>/opciones`, `/api/cuestionarios/opciones/<id>` | Admin |
| POST          | `/api/cuestionarios/<codigo>/responder`   | Autenticado          |
| GET           | `/api/cuestionarios/me/respuestas`        | Autenticado          |

**Eventos** — el evento se crea con todos sus sub-recursos anidados en un
solo request (deportes, requisitos, sedes, fechas, categorías + boletos), y
luego cada sub-recurso se puede editar por separado:

| Método          | Ruta                                    | Acceso                |
|-----------------|-----------------------------------------|-----------------------|
| GET             | `/api/eventos`, `/api/eventos/<id>`, `/api/eventos/slug/<slug>` | Público 
| POST / PUT / DELETE | `/api/eventos`, `/api/eventos/<id>` | Admin*                |
| POST/PUT/DELETE | `/api/eventos/<id>/deportes`, `/requisitos`, `/sedes`, `/fechas`, `/categorias` y sus `/<id>` | Admin* |
| POST/PUT/DELETE | `/api/eventos/categorias/<id>/boletos`, `/api/eventos/boletos/<id>` | Admin* |

**Rutas GPS** — cualquier usuario puede crear y administrar sus propias
rutas; ligarlas a una categoría de evento es solo de admin:

| Método        | Ruta                                      | Acceso                                 |
|---------------|-------------------------------------------|----------------------------------------|
| GET           | `/api/rutas`, `/api/rutas/<id>`           | Público (solo rutas `es_publica=true`) |
| POST          | `/api/rutas`                              | Autenticado                            |
| PUT / DELETE  | `/api/rutas/<id>`                         | Dueño de la ruta o admin               |
| POST / DELETE | `/api/rutas/<id>/puntos`, `/api/rutas/puntos/<id>` | Dueño de la ruta o admin      |
| GET / POST    | `/api/rutas/categorias/<categoria_id>/rutas` | GET público, POST admin             |
| DELETE        | `/api/rutas/eventos-rutas/<id>`           | Admin                                  |


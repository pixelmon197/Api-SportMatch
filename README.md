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
│   ├── ruta.py                    # Ruta, RutaPunto, EventoRuta
│   ├── inscripcion.py             # PaqueteRecuperacion, Inscripcion, ValoracionEvento,
│   │                               #   CalendarioUsuario
│   ├── organizador.py             # Organizador, OrganizadorMiembro, SolicitudValidacion,
│   │                               #   DocumentoValidacion, CuentaCobro
│   └── soporte.py                 # AuditoriaLog, Reporte, TicketSoporte, TicketMensaje
├── routes/
│   ├── auth.py                    # /api/auth/register, /login, /me
│   ├── usuarios.py                # /api/usuarios (perfil propio + administración)
│   ├── deportes.py                # /api/deportes (catálogo + deportes del usuario)
│   ├── cuestionarios.py           # /api/cuestionarios (registro guiado)
│   ├── eventos.py                 # /api/eventos (evento + todos sus sub-recursos)
│   ├── rutas.py                   # /api/rutas (rutas GPS + su liga a categorías de evento)
│   ├── inscripciones.py           # /api/inscripciones, /paquetes, /valoraciones, /calendario
│   ├── organizadores.py           # /api/organizadores (equipo, cuentas de cobro, validación)
│   └── soporte.py                 # /api/reportes, /api/tickets, /api/admin/auditoria
├── utils/
│   ├── auth.py                    # @admin_required / @roles_required / permisos de organizador
│   ├── auditoria.py               # registrar_auditoria() para acciones administrativas sensibles
│   └── fechas.py                  # parse_datetime / parse_date (JSON string -> datetime)
└── docs/
    ├── fase1_analisis.md          # Qué se analizó y por qué se decidió así
    ├── entidades_completas.md     # Catálogo de las 89 entidades del modelo (columnas)
    └── relaciones_completas.md    # Las 135 relaciones entre entidades
```

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

| Método | Ruta                          | Acceso        | Descripción |
|--------|-------------------------------|---------------|-------------|
| GET    | `/api/health`                 | Público       | Estado del servicio |
| POST   | `/api/auth/register`          | Público       | Autoregistro (siempre rol `usuario`) |
| POST   | `/api/auth/login`             | Público       | Inicio de sesión, regresa JWT |
| GET    | `/api/auth/me`                | Autenticado   | Datos del usuario en sesión |
| PUT    | `/api/usuarios/me`             | Autenticado   | Editar mi propio perfil |
| PUT    | `/api/usuarios/me/password`    | Autenticado   | Cambiar mi contraseña |
| GET    | `/api/usuarios`                | Admin         | Listar usuarios (filtros: `rol`, `estado_cuenta`, `q`; paginado) |
| GET    | `/api/usuarios/<id>`           | Admin         | Ver un usuario |
| PUT    | `/api/usuarios/<id>/rol`       | Admin         | Cambiar rol (`usuario` / `admin`) |
| PUT    | `/api/usuarios/<id>/estado`    | Admin         | Activar / suspender / eliminar (borrado suave) |
| POST   | `/api/usuarios/admins`         | Admin         | Dar de alta a otro administrador |

Detalle completo de request/response en `/api/docs` (Swagger UI) o en
`static/openapi.yaml`.

**Deportes** — catálogo público; el registro/edición del catálogo es de admin,
cada usuario administra sus propios deportes practicados:

| Método | Ruta | Acceso |
|---|---|---|
| GET | `/api/deportes` | Público |
| POST / PUT | `/api/deportes`, `/api/deportes/<id>` | Admin |
| DELETE | `/api/deportes/<id>` | Admin (desactiva, no borra) |
| GET / POST | `/api/deportes/me` | Autenticado |
| PUT / DELETE | `/api/deportes/me/<deporte_id>` | Autenticado |

**Cuestionario de registro** — un cuestionario tiene preguntas, y cada
pregunta puede tener opciones (algunas ligadas directo a un deporte del
catálogo):

| Método | Ruta | Acceso |
|---|---|---|
| GET | `/api/cuestionarios`, `/api/cuestionarios/<codigo>` | Público |
| POST | `/api/cuestionarios` | Admin |
| POST | `/api/cuestionarios/<id>/preguntas` (puede incluir `opciones` anidadas) | Admin |
| PUT / DELETE | `/api/cuestionarios/preguntas/<id>` | Admin |
| POST / DELETE | `/api/cuestionarios/preguntas/<id>/opciones`, `/api/cuestionarios/opciones/<id>` | Admin |
| POST | `/api/cuestionarios/<codigo>/responder` | Autenticado |
| GET | `/api/cuestionarios/me/respuestas` | Autenticado |

**Eventos** — el evento se crea con todos sus sub-recursos anidados en un
solo request (deportes, requisitos, sedes, fechas, categorías + boletos), y
luego cada sub-recurso se puede editar por separado:

| Método | Ruta | Acceso |
|---|---|---|
| GET | `/api/eventos`, `/api/eventos/<id>`, `/api/eventos/slug/<slug>` | Público (solo `estado=publicado` por defecto) |
| POST / PUT / DELETE | `/api/eventos`, `/api/eventos/<id>` | Admin* |
| POST/PUT/DELETE | `/api/eventos/<id>/deportes`, `/requisitos`, `/sedes`, `/fechas`, `/categorias` y sus `/<id>` | Admin* |
| POST/PUT/DELETE | `/api/eventos/categorias/<id>/boletos`, `/api/eventos/boletos/<id>` | Admin* |

**Rutas GPS** — cualquier usuario puede crear y administrar sus propias
rutas; ligarlas a una categoría de evento es solo de admin:

| Método | Ruta | Acceso |
|---|---|---|
| GET | `/api/rutas`, `/api/rutas/<id>` | Público (solo rutas `es_publica=true`) |
| POST | `/api/rutas` (puede incluir `puntos` anidados) | Autenticado |
| PUT / DELETE | `/api/rutas/<id>` | Dueño de la ruta o admin |
| POST / DELETE | `/api/rutas/<id>/puntos`, `/api/rutas/puntos/<id>` | Dueño de la ruta o admin |
| GET / POST | `/api/rutas/categorias/<categoria_id>/rutas` | GET público, POST admin |
| DELETE | `/api/rutas/eventos-rutas/<id>` | Admin |

**Inscripciones y valoraciones** — el usuario se inscribe a una categoría
con un boleto y, opcionalmente, un paquete de recuperación; si la categoría
tiene cupo y lo alcanza, cae en lista de espera automáticamente (o se
rechaza si la categoría no admite lista de espera). Al cancelar una
inscripción confirmada, el primero en la lista de espera sube
automáticamente. La valoración solo se puede dejar una vez que la
inscripción quedó `completada` (el admin la marca así el día del evento):

| Método | Ruta | Acceso |
|---|---|---|
| GET / POST | `/api/eventos/<id>/paquetes` | GET público, POST admin |
| PUT / DELETE | `/api/paquetes/<id>` | Admin |
| POST | `/api/inscripciones` | Autenticado |
| GET | `/api/inscripciones/me` | Autenticado |
| GET | `/api/inscripciones/<id>` | Dueño o admin |
| PUT | `/api/inscripciones/<id>/cancelar` | Dueño o admin |
| PUT | `/api/inscripciones/<id>/estado` | Admin (confirmar/rechazar mientras no hay módulo de pagos) |
| PUT | `/api/inscripciones/<id>/resultado` | Admin (asistencia, tiempo, posiciones) |
| GET | `/api/eventos/<id>/inscripciones` | Admin |
| POST | `/api/inscripciones/<id>/valoracion` | Dueño, solo si `estado=completada` |
| GET | `/api/eventos/<id>/valoraciones` | Público |
| PUT | `/api/valoraciones/<id>/responder` | Admin (simula respuesta del organizador) |
| GET / POST | `/api/usuarios/me/calendario` | Autenticado |
| DELETE | `/api/usuarios/me/calendario/<fecha_id>` | Autenticado |

**Nota:** `pago_id` no está conectado todavía — el módulo de pagos y
liquidaciones (`pagos`, `pagos_inscripciones`, `cupones`, `liquidaciones`)
es de una fase posterior. Por ahora las inscripciones se confirman a mano
vía `PUT /api/inscripciones/<id>/estado`.

**Organizadores y validación** — cualquier usuario puede crear su perfil de
organizador (queda `pendiente`); solo puede crear/publicar eventos una vez
que un admin aprueba su solicitud de validación. Desde aquí en adelante,
`PUT`/`DELETE`/sub-recursos de `/api/eventos` los puede usar tanto un admin
como un miembro (`propietario`/`administrador`) del organizador dueño del
evento — ya no es exclusivo de admin:

| Método | Ruta | Acceso |
|---|---|---|
| GET | `/api/organizadores`, `/api/organizadores/<id>` | Público (solo `aprobado`; `?estado_validacion=` para admin) |
| POST | `/api/organizadores` | Autenticado (crea el propio, uno por usuario) |
| PUT / DELETE | `/api/organizadores/<id>` | Miembro (propietario/admin) o admin |
| POST / DELETE | `/api/organizadores/<id>/miembros`, `/miembros/<usuario_id>` | Miembro o admin |
| GET / POST | `/api/organizadores/<id>/cuentas-cobro` | Miembro o admin |
| PUT | `/api/organizadores/cuentas-cobro/<id>/verificar` | Admin |
| POST | `/api/organizadores/<id>/solicitudes` (puede incluir `documentos`) | Miembro o admin |
| POST | `/api/organizadores/solicitudes/<id>/documentos` | Miembro o admin |
| GET | `/api/organizadores/solicitudes` | Admin (bandeja de revisión) |
| PUT | `/api/organizadores/solicitudes/<id>/revisar` (`decision: aprobar/rechazar`) | Admin |

**Administración y soporte** — reportes (moderación de contenido/usuarios),
tickets de soporte con mensajes (algunos internos, invisibles al usuario),
y una bitácora de auditoría de solo lectura para acciones administrativas
sensibles (cambios de rol/estado de usuario, revisión de organizadores,
resolución de reportes):

| Método | Ruta | Acceso |
|---|---|---|
| POST | `/api/reportes` | Autenticado |
| GET | `/api/reportes/me` | Autenticado (mis reportes) |
| GET | `/api/reportes` | Admin (bandeja; filtros `estado`, `tipo_entidad`) |
| GET / PUT | `/api/reportes/<id>` | GET: dueño o admin. PUT: admin |
| POST | `/api/tickets` (con mensaje inicial) | Autenticado |
| GET | `/api/tickets/me` | Autenticado |
| GET | `/api/tickets` | Admin (filtros `estado`, `prioridad`, `asignado_a`) |
| GET | `/api/tickets/<id>` | Dueño o admin (dueño no ve mensajes `es_interno`) |
| POST | `/api/tickets/<id>/mensajes` | Dueño o admin (solo admin puede `es_interno`) |
| PUT | `/api/tickets/<id>` | Admin (estado, prioridad, asignación) |
| GET | `/api/admin/auditoria` | Admin (filtros `tipo_entidad`, `entidad_id`, `usuario_id`) |

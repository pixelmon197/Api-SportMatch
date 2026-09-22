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
│   ├── ciudad.py                 # Ciudad
│   ├── usuario.py                 # Usuario (rol, estado_cuenta, borrado suave)
│   ├── token_verificacion.py      # TokenVerificacion (verificar correo / recuperar password)
│   ├── dispositivo.py             # Dispositivo (para push notifications, Fase 3+)
│   └── aceptacion_legal.py        # AceptacionLegal (términos y privacidad)
├── routes/
│   ├── auth.py                    # /api/auth/register, /login, /me
│   └── usuarios.py                # /api/usuarios (perfil propio + administración)
├── utils/
│   └── auth.py                    # @admin_required / @roles_required
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

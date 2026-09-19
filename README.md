# Api-SportMatch

API REST de **SportMatch**.

Construida en **Flask + Flask-SQLAlchemy**, con **MySQL** como base de datos,
autenticación con **JWT** y documentación **Swagger / OpenAPI 3.0**.

## Estructura

```
Api-SportMatch/
├── app.py                  # Application factory, JWT, blueprints y Swagger UI
├── config.py               # Conexión MySQL + configuración JWT
├── database.py             # Instancia única de SQLAlchemy
├── seed.py                 # Datos iniciales (roles, catálogos, usuarios de ejemplo)
├── requirements.txt
├── .env.example            # Plantilla de variables de entorno
├── static/
│   └── openapi.yaml        # Spec OpenAPI 3.0
├── models/                 # Modelos SQLAlchemy (una entidad por archivo)
├── routes/                 # Blueprints con los endpoints (/api/...)
└── utils/
    └── auth.py             # Decoradores @admin_required / @roles_required
```

## 1. Crear la base de datos

```bash
mysql -u root -p < sportmatch_schema.sql
```

## 2. Instalación

```bash
cd Api-SportMatch
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

## 3. Configuración

Copia la plantilla y ajusta tus valores:

```bash
cp .env.example .env
```
           |
## 4. Ejecución

```bash
python app.py
```

- API: `http://localhost:5000`
- Swagger UI: `http://localhost:5000/api/docs`

## Endpoints

| Método | Ruta          | Descripción         |
|--------|---------------|---------------------|
| GET    | `/api/health` | Estado del servicio |

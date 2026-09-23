# Fase 1 — Análisis

## 1. Fuentes revisadas

- **`Modelo_entidad_relacion.mdj`** (StarUML): fuente de verdad. Se extrajo
  de forma programática (JSON) el catálogo completo de **89 entidades** y
  **135 relaciones**. Volcado íntegro en:
  - [`entidades_completas.md`](./entidades_completas.md) — cada entidad con
    sus columnas, PK/FK.
  - [`relaciones_completas.md`](./relaciones_completas.md) — cada relación
    con su cardinalidad.
  - Nota: el diagrama no trae tipos SQL explícitos (solo las PK están
    tipadas como `INTEGER`); los tipos del resto de columnas se definen al
    construir cada modelo, en cada fase.
- **`SportMatch_Modelo_Entidad_Relacion.docx`**: mismo modelo pero como
  diagrama visual paginado por módulo (Usuarios, Comunidades, Eventos,
  Tienda, Contenido, Mensajería, Gamificación, Publicidad, Administración...).
  Confirma que la base de datos es **PostgreSQL**.
- **`Base_de_datos_de_SPORTMATCH.docx`**: documento de contexto/flujo del
  diseño (capturas de pantalla, no texto). Confirma que la BD ya está
  **instanciada en Neon** (Postgres administrado). Las credenciales que
  incluye se usaron solo para armar tu `.env` local; no se repiten aquí ni
  se subieron a ningún archivo del repo — revísalas en el documento
  original y considera rotarlas si el archivo se compartió por un canal no
  seguro.
- **`arsh_cssi_api`** (Flask + MySQL, tu ejemplo anterior): patrón de
  *application factory*, blueprints, JWT con roles simples, Swagger UI
  servido desde `static/openapi.yaml`, borrado suave, y separación
  `models/ / routes/ / utils/`. Es la base estructural que se siguió aquí.
- **`Api-Crazy-Lettuces-main`** (Flask, dual MySQL/Mongo): patrón más
  elaborado de **repositorio** (`UserRepository` con `to_dict`,
  `find_by_credentials`, etc.), JWT con claims de rol, y un módulo
  `Controllers/analisisController.py` con PySpark para analítica (relevante
  para la Fase 4). Se tomó como referencia para el flujo de `login` y la
  forma de estructurar el `to_dict()` de usuario, simplificando el patrón
  dual de base de datos porque SportMatch usa solo PostgreSQL.

## 2. Decisiones de diseño para las fases 2 y 3

- **Stack:** Flask + Flask-SQLAlchemy + PostgreSQL (`psycopg2-binary`),
  JWT con `Flask-JWT-Extended`, documentación con Swagger UI
  (`flask-swagger-ui` + `static/openapi.yaml`), igual que `arsh_cssi_api`.
- **Rol de usuario:** el diagrama no tiene una tabla `roles` aparte (a
  diferencia de `arsh_cssi_api`); `usuarios.rol` es un campo simple. Se
  definió como `usuario` | `admin`. **"Organizador" no es un rol**: es un
  perfil aparte (tabla `organizadores`, con su propio
  `estado_validacion`), ligado 1-a-1 a un usuario — se implementará en la
  Fase 3 junto con `solicitudes_validacion`.
- **Contraseña:** el diagrama la nombra `constrasena` (así, con esa
  ortografía). En el modelo se usa `contrasena_hash`, porque solo se
  guarda el hash (nunca la contraseña en claro); el resto de nombres de
  columna se respetan tal cual el diagrama.
- **Borrado suave:** `usuarios.eliminado_en` + `estado_cuenta` (como en
  `arsh_cssi_api`), en vez de `DELETE` físico.

## 3. Qué se construyó en la Fase 2

Ver el README principal → sección "Fase 2 (implementada)". Entidades del
modelo cubiertas: `usuarios`, `ciudades`, `tockens_verificacion`,
`Dispositivos`, `aceptaciones_legales`.

## 4. Qué falta (fases 3 y 4)

- **Fase 3:** CRUD del resto de las 89 entidades — agrupadas por módulo:
  perfil social (`perfiles`, `Seguidores`, `amistades`, `bloqueos`),
  comunidades y publicaciones, tarjetas de conexión, deportes y
  cuestionario, organizadores y validación, eventos (sedes, fechas,
  categorías, boletos, rutas), inscripciones y valoraciones, pagos y
  liquidaciones, cupones, tienda (catálogo, carrito, órdenes), contenido
  (videos, artículos), mensajería y notificaciones, gamificación y
  referidos, publicidad, y administración/soporte (auditoría, reportes,
  tickets). El detalle exacto de columnas de cada una ya está en
  `entidades_completas.md`.
- **Fase 4:** análisis de datos y gráficas, tomando como referencia
  `Controllers/analisisController.py` de Api-Crazy-Lettuces (usa PySpark
  sobre los datos de suplementos/órdenes). Para SportMatch el candidato
  natural es analítica sobre `inscripciones`, `eventos`, `pagos` y
  `valoraciones_evento`.

## 5. Actualización — Fase 3 en curso

Módulos ya implementados (con CRUD probado end-to-end):

- **Deportes**: `Deportes` → `Deporte`; `usuarios_deportes` → `UsuarioDeporte`.
- **Cuestionario de registro**: `cuestionarios`, `preguntas`,
  `opciones_respuesta`, `respuesta_usuario` → mapeo 1 a 1.
- **Eventos**: `eventos`, `evento_deportes`, `eventos_requisitos`,
  `evento_sedes`, `eventos_fechas`, `evento_categorias`, `evento_boletos`,
  `rutas`, `ruta_puntos`, `evento_rutas` → mapeo 1 a 1. Se descartaron del
  diagrama columnas duplicadas/artefacto como `Column2`, `Column3`,
  `Column12` (evidentemente residuos de ediciones en StarUML, no campos
  reales — por ejemplo `eventos` traía dos columnas marcadas como PK).
- `eventos.organizador_id` se dejó como entero simple, sin FK todavía,
  porque el módulo `organizadores` (con su tabla de validación) es de una
  fase posterior — se conectará ahí sin romper esta tabla.
- Se creó `utils/fechas.py` porque SQLAlchemy exige objetos `datetime`, no
  los strings ISO que manda el JSON del cliente (se detectó al probar
  con datos reales, tanto en SQLite como aplicaría igual en Postgres).

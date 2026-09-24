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

## 6. Actualización — Inscripciones y valoraciones

Módulo implementado (con CRUD y reglas de negocio probadas end-to-end:
cupo, lista de espera, promoción automática al cancelar, resultado del
evento, valoración condicionada a asistencia, calendario personal):

- `inscripciones` → `Inscripcion`. `numero_particpante` (typo del diagrama)
  se guarda como `numero_participante`, mismo criterio que
  `contrasena_hash` en Fase 2.
- `valoraciones_evento` → `ValoracionEvento`. El diagrama la modela como
  `inscripciones 1 -- 0..*`, pero a nivel de aplicación se limita a una
  valoración por inscripción (si ya existe, se actualiza en vez de
  duplicarse) — así evitamos reseñas repetidas del mismo usuario sobre el
  mismo evento.
- `paquete_recuperacion` → `PaqueteRecuperacion`. Se dejó fuera
  `paquete_items`, porque liga a `variante_id` (una variante de producto
  de la tienda), y el módulo de tienda todavía no existe.
- `calendario_usuario` → `CalendarioUsuario`. El diagrama marca la relación
  como `usuarios 1 -- 1`, pero eso no tiene sentido para un calendario (un
  usuario guarda varias fechas); se implementó como `1 -- N` con llave
  compuesta (`usuario_id`, `fecha_id`).
- `inscripciones.pago_id` no existe todavía como columna: el módulo de
  pagos (`pagos`, `pagos_inscripciones`, `cupones`, `liquidaciones`) es
  bastante más grande (pasarelas de pago, comisiones, reembolsos) y queda
  para una fase dedicada. Mientras tanto, el estado de una inscripción se
  mueve a mano con `PUT /api/inscripciones/<id>/estado`.

## 7. Actualización — Organizadores y validación, Administración y soporte

Módulos implementados y probados end-to-end (registro de organizador →
bloqueo de creación de eventos hasta aprobación → solicitud con documentos
→ revisión admin → creación de evento ligado al organizador → verificación
de que un tercero no puede tocar ese evento → reporte de moderación →
ticket de soporte con nota interna oculta al usuario → bitácora de
auditoría):

- `organizadores`, `organizador_miembros`, `solicitudes_validacion`,
  `documentos_validacion`, `cuentas_cobro` → mapeo 1 a 1 con el diagrama.
- **`eventos.organizador_id` ahora es una llave foránea real** hacia
  `organizadores.id` (antes era un entero simple, como se dejó anotado en
  la Fase 3 parte 1). Todo `routes/eventos.py`, y los endpoints de
  paquetes/inscripciones/valoraciones que tocan un evento, se movieron de
  "solo admin" a "admin o miembro (propietario/administrador) del
  organizador dueño del evento" vía `utils.auth.puede_gestionar_evento`.
- `auditoria_log`, `reportes`, `tickets_soporte` → mapeo 1 a 1.
- `ticket_mensaje` traía en el diagrama columnas duplicadas de
  `tickets_soporte` (categoria, prioridad, estado, asunto, creado_en,
  cerrado_en) — claro artefacto de StarUML (copy-paste al crear la
  entidad); se modelaron solo los campos propios: `ticket_id`, `autor_id`,
  `mensaje`, `es_interno`, `creado_en`.
- La auditoría (`utils/auditoria.py: registrar_auditoria`) no se dispara en
  cada request; se llamó explícitamente en las acciones administrativas
  sensibles ya existentes: cambiar rol/estado de un usuario (Fase 2),
  revisar una solicitud de validación, y cambiar el estado de un reporte.
- Se descartó `paquete_items` de nuevo en este contexto: pertenece al
  módulo de tienda (liga a `variante_id`), que sigue pendiente.

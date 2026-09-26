# Fase 4 — Módulo Eventos

## Bugs corregidos (confirmados con pruebas contra un esquema que replica los CHECK/NOT NULL reales de Neon)

1. **`Evento.actualizado_en` sin `default`** (mismo patrón de `Usuario`/
   `Organizador`): `NOT NULL DEFAULT CURRENT_TIMESTAMP` en Neon, el
   modelo no traía `default` → `POST /api/eventos` rompía siempre.

2. **`Evento.organizador_id` permitía `NULL`, pero en Neon es `NOT NULL`**.
   El código dejaba crear eventos "de la plataforma" sin organizador si
   quien creaba era admin. Eso no es posible en Neon: **todo evento
   pertenece a un organizador**. Se quitó ese caso especial: ahora
   `organizador_id` es obligatorio siempre (también para admin), que solo
   debe apuntar a un organizador existente (ya no necesita pertenecer a
   él ni que esté aprobado, a diferencia de un usuario normal).

3. **`EventoDeporte` definía una columna `id` que no existe** — la tabla
   real `evento_deportes` tiene PK compuesta (`evento_id`+`deporte_id`),
   sin id propio. Rompía `POST /<id>/deportes` y
   `DELETE /<id>/deportes/<deporte_id>`. Se quitó `id` del modelo y se
   usa la PK compuesta real. De paso, agregar un deporte que ya estaba
   asociado ahora responde `409` en vez de un `500` por violar la PK.

4. **Tablas legacy**: `EventoRequisito` apuntaba a `eventos_requisitos`
   (sin `ON DELETE CASCADE`) en vez de la vigente `evento_requisitos`;
   `EventoFecha` apuntaba a `eventos_fechas` en vez de `evento_fechas`
   (que además sí valida `termina_en > inicia_en`). Se corrigieron los
   `__tablename__`. Como consecuencia, también se actualizaron las
   referencias `ForeignKey("eventos_fechas.id")` en
   `models/inscripcion.py` (`Inscripcion.fecha_id` y
   `CalendarioUsuario.fecha_id`) a `"evento_fechas.id"` — si no, las
   fechas de evento se guardarían en una tabla y las inscripciones
   seguirían apuntando a la otra.

5. **Catálogos de valores completamente distintos a los `CHECK` reales**
   (esto es lo más grave: no eran solo nombres parecidos, eran
   vocabularios distintos):

   | Campo | Valores que usaba la API | Valores reales en Neon |
   |---|---|---|
   | `eventos.tipo` | *(sin validar, comentario decía "carrera, torneo, clinica")* | `carrera, ruta, torneo, liga, entrenamiento, experiencia_grupal` |
   | `eventos.estado` | `borrador, publicado, cancelado, finalizado` | + `en_revision` (faltaba) |
   | `eventos.dificultad` | `principiante, intermedio, avanzado, elite` | `facil, moderada, dificil, extrema` |
   | `evento_sedes.tipo` | `salida, meta, punto_control, sede_unica` | `salida, meta, punto_encuentro, entrega_kit` |
   | `evento_boletos.tipo` | `general, early_bird, vip, grupal` | `general, preventa, estudiante, grupal` |

   Se agregó `TIPOS_EVENTO` (no existía) y se corrigieron
   `DIFICULTADES_EVENTO`, `TIPOS_SEDE`, `TIPOS_BOLETO`. También se
   corrigieron los **valores por defecto** que usaba el código
   (`tipo` de sede por defecto era `"sede_unica"`, que ya no existe;
   ahora es `"punto_encuentro"`) — incluyendo un default que estaba a
   nivel de columna en el propio modelo (`EventoSede.tipo`), no solo en
   las rutas.

   Se agregó validación de `tipo` en `crear_evento` (antes no se
   validaba en absoluto) y de `tipo`/`dificultad`/`edad_minima` también
   en `actualizar_evento` (antes el `PUT` solo validaba `estado`, dejando
   colar cualquier `tipo`/`dificultad` inválido directo a la base).

6. **CHECK numéricos de `evento_categorias` y `evento_boletos` sin
   validar**: `edad_maxima >= edad_minima`, `distancia_km > 0`,
   `cupo_total > 0`, `precio >= 0`, `disponible_hasta > disponible_desde`.
   Se agregaron `_validar_categoria()` y `_validar_boleto()`, usadas
   tanto en la creación embebida de evento (categorías/boletos dentro de
   `POST /api/eventos`) como en los endpoints sueltos
   (`POST/PUT categorias`, `POST/PUT boletos`).

## Verificación

`test_eventos.py` (adjunto) monta un esquema SQLite con las columnas y
`CHECK`/`NOT NULL` reales de `eventos`, `evento_sedes`,
`evento_categorias`, `evento_boletos`, `evento_deportes`,
`evento_requisitos` y `evento_fechas`, y prueba: creación de un evento
completo (deportes + requisitos + sedes + fechas + categorías + boletos
en un solo request), `tipo`/`dificultad` inválidos (400, ya no 500),
sede sin `tipo` explícito (usa el nuevo default válido), evento sin
`organizador_id` incluso como admin (400), agregar un deporte duplicado
(409) y uno nuevo (201), boleto con tipo viejo o precio negativo (400),
publicar un evento (fija `publicado_en`), y categoría con edades
invertidas (400). Todo pasa. También se re-corrieron las pruebas de
Fase 2 (auth) y Fase 3 (organizadores) para confirmar que no hay
regresiones.

## Pendiente / fuera de este módulo

- `EventoRuta` (en `models/ruta.py`) tiene el mismo problema que tenía
  `EventoDeporte`: define un `id` que no existe (la tabla real
  `evento_rutas` tiene PK compuesta `evento_id`+`ruta_id`+`categoria_id`
  nullable). Se deja para la fase de **Rutas**.
- Las tablas `evento_sedes`, `evento_categorias` y `evento_boletos`
  tienen columnas de latitud/longitud/distancia con más precisión
  (`numeric`) que lo típico; no se encontraron mismatches ahí, solo se
  revisaron sus `CHECK`.

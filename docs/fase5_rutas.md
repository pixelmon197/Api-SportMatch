# Fase 5 — Módulo Rutas

## Bugs corregidos (confirmados con pruebas contra un esquema que replica los CHECK/NOT NULL/PK reales de Neon)

1. **`EventoRuta` definía una columna `id` que no existe** — igual que
   pasó con `EventoDeporte` en Eventos. La tabla real `evento_rutas`
   tiene PK compuesta (`evento_id` + `ruta_id`), y además le faltaba la
   columna `evento_id` por completo (el modelo solo tenía `ruta_id` y
   `categoria_id`, y encima `categoria_id` estaba mal como obligatorio
   cuando en Neon es opcional). Esto rompía **todos** los endpoints de
   ligar/listar/desligar rutas de un evento. Se reconstruyó el modelo con
   la PK compuesta real y se agregó la restricción compuesta que exige
   Neon: si se manda `categoria_id`, tiene que pertenecer al mismo
   `evento_id` (`FOREIGN KEY (categoria_id, evento_id) REFERENCES
   evento_categorias(id, evento_id)`).

   Como consecuencia, `DELETE /api/rutas/eventos-rutas/<id>` (que
   buscaba por un `id` que ya no existe) cambió a
   `DELETE /api/rutas/eventos-rutas/<evento_id>/<ruta_id>`.

2. **`ruta_puntos.tipo` con vocabulario totalmente distinto al `CHECK`
   real**: la API usaba `inicio/fin/control/paso`; Neon exige
   `inicio/meta/hidratacion/punto_interes/mirador/peligro`. El *default*
   del código (`"paso"`) tampoco era válido. Se corrigió
   `TIPOS_PUNTO_RUTA` y el default pasó a `"punto_interes"`.

3. **`rutas.dificultad` no se validaba** contra el `CHECK` real
   (`facil/moderada/dificil/extrema`) — no existía ni la constante. Se
   agregó `DIFICULTADES_RUTA` y su validación en crear y actualizar ruta.

4. **`rutas.distancia_m` / `desnivel_positivo_m` son enteros (`int4`) en
   Neon**, pero el modelo los declaraba `Numeric(10,2)` (con decimales).
   Un valor fraccionario (`5000.5`) se habría rechazado en Postgres.
   Se cambiaron a `Integer` y se agregó validación explícita: debe ser un
   número entero, `distancia_m > 0` (estricto) y `desnivel_positivo_m >= 0`.

5. **`UNIQUE(ruta_id, orden)` en `ruta_puntos` sin manejar**: agregar dos
   puntos con el mismo `orden` (o repetir uno ya existente) producía un
   error de base de datos sin control. Ahora responde `409` con un
   mensaje claro, tanto al crear la ruta completa (puntos embebidos) como
   al agregar un punto suelto.

6. **Ligar la misma ruta dos veces al mismo evento**: ahora responde
   `409` en vez de un error de integridad por PK duplicada.

## Verificación

`test_rutas.py` (adjunto) monta un esquema SQLite con las columnas,
`CHECK`, `UNIQUE` y PKs compuestas reales de `rutas`, `ruta_puntos` y
`evento_rutas`, y prueba: crear una ruta completa con puntos, dificultad
inválida, tipo de punto inválido, `distancia_m` en 0 o fraccionaria,
desnivel negativo, punto con orden repetido (409), tipo de punto nuevo
válido, ligar una ruta a una categoría de evento, volver a ligar la
misma (409), listar, desligar (con la nueva URL compuesta), y que un
usuario ajeno no pueda editar la ruta de otro. Todo pasa. Se
re-corrieron también las pruebas de Fase 2, 3 y 4 — sin regresiones.

## Pendiente / fuera de este módulo

- `Ruta.creador_id` y `Ruta.deporte_id` son `NOT NULL` en el modelo pero
  Neon los permite `NULL` (el modelo es más estricto que la BD). Se dejó
  así a propósito: la app siempre exige un creador y un deporte al crear
  una ruta, así que no rompe nada; solo se documenta por transparencia.

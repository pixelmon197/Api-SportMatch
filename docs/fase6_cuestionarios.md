# Fase 6 — Módulo Cuestionarios

## Bugs corregidos (confirmados con pruebas contra un esquema que replica los CHECK/UNIQUE/FK compuestas reales de Neon)

1. **`OpcionRespuesta.codigo_id` no existe** — la columna real en Neon es
   `codigo` (`NOT NULL`, `varchar(50)`). El código mandaba
   `codigo_id=op.get("codigo_id")` a una columna que la base de datos no
   tiene: rompía **todos** los endpoints que crean opciones
   (`POST /<id>/preguntas` con opciones embebidas y
   `POST /preguntas/<id>/opciones`). Se renombró el atributo del modelo y
   se actualizaron ambas rutas; ahora además `codigo` es obligatorio (como
   en Neon) y se valida que no se repita entre las opciones de una misma
   pregunta (`UNIQUE(pregunta_id, codigo)`), regresando 400/409 en vez de
   un error de base de datos.

2. **`preguntas.tipo` con catálogo incompleto**: la API solo aceptaba
   `opcion_unica, opcion_multiple, texto_libre, escala`; el `CHECK` real
   es `opcion_unica, opcion_multiple, escala, texto, numero, si_no`
   (`texto_libre` no existe, y faltaban `numero`/`si_no`). Se corrigió
   `TIPOS_PREGUNTA`.

3. **`preguntas.texto` es `varchar(255)`** en Neon, el modelo lo
   declaraba `Text` (sin límite) — un texto más largo habría sido
   rechazado por Postgres. Se ajustó a `String(255)`.

4. **Tabla legacy `respuesta_usuario`**: el modelo apuntaba a la vieja
   (sin `CHECK`, sin `CASCADE`, sin la FK compuesta) en vez de la vigente
   `respuestas_usuario`. Se corrigió el `__tablename__` y, con eso, salió
   a la luz todo lo que la tabla vieja no obligaba a validar:

   - **CHECK real**: cada respuesta necesita `opcion_id` o
     `respuesta_texto` (no puede ir vacía). Antes el código podía guardar
     una respuesta completamente vacía. Ahora se valida antes de tocar la
     base (400 con mensaje claro).
   - **FK compuesta real** `(opcion_id, pregunta_id) → opciones_respuesta(id, pregunta_id)`:
     Neon exige que la opción elegida en verdad pertenezca a esa
     pregunta. Antes se podía mandar el `opcion_id` de una pregunta
     distinta y la base lo habría rechazado con un error crudo; ahora se
     valida antes (400).
   - **`respuesta_texto`** es `varchar(255)` en la tabla vigente (no
     `text`); se ajustó el modelo.

5. **Preguntas de opción múltiple perdían respuestas**: la lógica anterior
   buscaba "la" respuesta existente de una pregunta y la sobrescribía —
   sirve para `opcion_unica`/`texto`/`numero`/`si_no`/`escala`, pero para
   `opcion_multiple` el `UNIQUE(usuario_id, pregunta_id, opcion_id)` de
   Neon está diseñado para permitir **varias filas** (una por opción
   elegida). Si el cliente mandaba dos opciones para la misma pregunta
   multiple, la segunda pisaba a la primera en la misma llamada (por el
   autoflush de SQLAlchemy). Se reescribió `responder_cuestionario` para
   agrupar las respuestas por pregunta y, para cada una, **reemplazar por
   completo** el conjunto de respuestas previas (borra y vuelve a
   insertar) — funciona igual que antes para preguntas de una sola
   respuesta, y ahora sí conserva todas las opciones marcadas en una
   pregunta de opción múltiple. De paso, una pregunta que no es
   `opcion_multiple` ahora rechaza (400) que le manden más de una
   respuesta, en vez de quedarse solo con la última en silencio.

6. **`preguntas.codigo` sin validar su `UNIQUE(cuestionario_id, codigo)`**:
   se agregó el chequeo (409) tanto al crear como al renombrar el código
   de una pregunta existente.

## Verificación

`test_cuestionarios.py` (adjunto) monta un esquema SQLite con las
columnas, `CHECK`, `UNIQUE` y la FK compuesta reales de `cuestionarios`,
`preguntas`, `opciones_respuesta` y `respuestas_usuario`, y prueba: crear
cuestionario y preguntas (opción única con opciones embebidas, tipo
`numero`, tipo `opcion_multiple`), tipo de pregunta viejo inválido,
código de opción repetido dentro de una pregunta, código de pregunta
repetido en el cuestionario, responder con una opción que no pertenece a
la pregunta (400), responder sin opción ni texto (400), responder
correctamente incluyendo una pregunta de opción múltiple con dos
opciones marcadas (y confirmar que **ambas** quedan guardadas), rechazar
dos respuestas para una pregunta que no es múltiple, y volver a responder
la pregunta múltiple con un subconjunto distinto (reemplazo limpio).
Todo pasa. Se re-corrieron las pruebas de las Fases 2 a 5 — sin
regresiones.

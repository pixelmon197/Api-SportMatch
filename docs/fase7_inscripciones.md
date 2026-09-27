# Fase 7 — Módulo Inscripciones

## Bugs corregidos (confirmados con pruebas contra un esquema que replica los CHECK/FKs compuestas reales de Neon)

1. **`ESTADOS_INSCRIPCION` con vocabulario completamente distinto al
   `CHECK` real** — el más grave del módulo, en la misma línea de lo que
   pasó con `dificultad`/`tipo` en Eventos:

   | Usaba la API | Valor real en Neon |
   |---|---|
   | `pendiente` | `pendiente_pago` |
   | `confirmada` | `inscrito` (también existe `activo`, no usado por ahora) |
   | `cancelada` | `cancelado` |
   | `completada` | `completado` |
   | *(no existía)* | `no_asistio` |
   | `lista_espera` | `lista_espera` *(coincidía)* |

   Esto significa que **toda inscripción creada** (`estado="pendiente"`
   por default) habría violado el `CHECK` real desde el primer
   `POST /api/inscripciones`. Se corrigió el catálogo y cada lugar del
   código que ponía un estado a mano: creación, cancelación (incluida la
   promoción automática de lista de espera), cambio manual de estado, y
   marcar una inscripción como completada al registrar el resultado.

2. **`Inscripcion.tiempo_oficial` es tipo `time` en Neon**, el modelo lo
   declaraba `String(20)`. Se cambió a `db.Time` y se agregó
   `parse_time()` en `utils/fechas.py` para convertir el `"HH:MM:SS"` que
   manda el cliente (igual que ya existía `parse_date`/`parse_datetime`).
   Nota documentada: el tipo `time` de Postgres no admite 24 horas o
   más, así que un ultramaratón que cruce la medianoche del reloj no cabe
   ahí — es una limitación del propio esquema de Neon, no de la API.

3. **`posicion_general`/`posicion_categoria` sin validar** su `CHECK`
   real (`> 0`). Ahora `PUT /resultado` responde 400 en vez de dejar
   pasar un valor inválido a la base.

4. **Tabla legacy `paquete_recuperacion`**: apuntaba a la vieja (sin
   `CHECK` de `nivel`, sin `UNIQUE(evento_id, nivel)`, `nivel` opcional)
   en vez de la vigente `paquetes_recuperacion`. Se corrigió el
   `__tablename__` y, con eso, se agregó lo que la tabla vieja no exigía:
   `nivel` ahora es obligatorio y se valida contra el catálogo real
   (`basico`/`medio`/`premium`), `precio >= 0`, y no se permiten dos
   paquetes con el mismo nivel en el mismo evento (`UNIQUE`, 409 en vez
   de error de base de datos). También se corrigió la FK de
   `Inscripcion.paquete_id`, que seguía apuntando a la tabla vieja.

5. **`ValoracionEvento` definía una columna `id` que no existe** —igual
   que pasó con `EventoDeporte`/`EventoRuta`. La tabla real
   `valoraciones_evento` **no tiene `id` propio**: su PK es
   `inscripcion_id` directamente (relación 1 a 1 real con la
   inscripción, reforzada por el propio esquema, no solo "a nivel de
   aplicación" como decía el comentario anterior). Se reconstruyó el
   modelo con `inscripcion_id` como PK, se renombró el atributo
   `inscripciones_id` → `inscripcion_id` en todo el código, y
   `PUT /valoraciones/<id>/responder` ahora usa ese mismo id (ya no
   existía un id distinto que buscar).

## Verificación

`test_inscripciones.py` (adjunto) monta un esquema SQLite con las
columnas, `CHECK` y las 4 FKs compuestas reales de `inscripciones`
(categoría+evento, fecha+evento, boleto+categoría, paquete+evento), más
`paquetes_recuperacion` y `valoraciones_evento`, y prueba: paquete con
nivel inválido y duplicado, inscripción normal, cupo lleno → lista de
espera, cancelar la primera y confirmar que la de lista de espera sube
automáticamente, cambiar a un estado con el vocabulario viejo (400) y
con uno real (200), registrar resultado con `tiempo_oficial` real y
posición inválida, valorar el evento, listar valoraciones, responder una
valoración, y el calendario personal. Todo pasa. Se re-corrieron las
pruebas de las Fases 2 a 6 — sin regresiones.

## Pendiente / fuera de este módulo

- `Inscripcion.boleto_id` es `NOT NULL` en el modelo pero Neon lo permite
  `NULL`. Se dejó así a propósito: la API ya exige `boleto_id` en el
  body de `POST /inscripciones`, así que no rompe nada; es el modelo
  siendo más estricto que la base, no al revés.

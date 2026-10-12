# Fase 13 — Subida de archivos (imágenes, videos, PDF, GPX, audio) y revisión de Neon2.sql

## Qué cambió en Neon2.sql respecto a Neon.sql

Se comparó archivo contra archivo: son las mismas 103 tablas. Solo hay dos
diferencias, ninguna es una tabla nueva de archivos:

1. `usuarios.firebase_uid varchar(128) NULL` (+ `UNIQUE`). Es opcional, así
   que **no rompe nada**: el modelo `Usuario` no la mapea y los INSERT
   siguen funcionando. Solo hará falta mapearla si se va a iniciar sesión
   con Firebase (no hay endpoint para eso todavía).
2. `cuentas_externas.proveedor` ahora acepta también `'github'`. Esa tabla
   no la usa ningún endpoint actual.

La tabla **`archivos` ya existía** en Neon.sql, pero nunca se había
construido nada sobre ella: cuatro campos del proyecto decían
"futura FK a archivos" y quedaban como un entero suelto.

## Lo que se construyó

**Modelo `Archivo`** (`models/archivo.py`) fiel a la tabla real: `tipo` con su
`CHECK` (`imagen`, `video`, `documento`, `gpx`, `audio`), `tamano_bytes` como
`BigInteger` (en Neon es `int8`), `ancho_px`/`alto_px`/`duracion_segundos`
opcionales y `eliminado_en` para borrado suave.

**Endpoints** (`routes/archivos.py`):

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/api/archivos` | Autenticado | Sube un archivo (`multipart/form-data`, campo `archivo`) y regresa su registro con el `id` y la `url` |
| GET | `/api/archivos/{id}` | Público | Datos de un archivo |
| DELETE | `/api/archivos/{id}` | Dueño o admin | Borrado suave |

El mismo `POST` sirve para imágenes **y videos** (y PDF, GPX y audio): el tipo
se deduce de la extensión, o se manda en el campo opcional `tipo`.

| Tipo | Extensiones | Máximo |
|---|---|---|
| imagen | jpg, jpeg, png, webp, gif | 8 MB |
| video | mp4, mov, webm | 200 MB |
| documento | pdf | 15 MB |
| gpx | gpx | 5 MB |
| audio | mp3, wav, m4a | 30 MB |

Estos límites son de la API (Neon no los define); se pueden ajustar en
`models/archivo.py`. En imágenes se leen `ancho_px`/`alto_px` con Pillow
(si no está instalado, simplemente quedan vacíos). La duración de un video
no la calcula el servidor; el cliente puede mandarla en `duracion_segundos`.

**Dónde se guardan:** en disco, en `static/uploads/<tipo>/<uuid>.<ext>` (nombre
aleatorio, nunca el que manda el usuario), y Flask los sirve solo desde
`/static/uploads/...`. `static/uploads/` se agregó al `.gitignore`.

> Importante para producción: en servicios como Render/Heroku el disco es
> temporal y los archivos se pierden al reiniciar. Si el proyecto se va a
> desplegar así, la siguiente mejora es guardarlos en un bucket (Cloudinary,
> S3, Supabase Storage). Solo cambiaría el bloque que escribe el archivo en
> `subir_archivo`; el modelo y los demás endpoints quedan igual.

## Cómo se usa (flujo de 2 pasos)

1. `POST /api/archivos` con el archivo → copiar el `id` de la respuesta.
2. Mandar ese `id` donde se necesite:

| Campo | Endpoints | Tipo de archivo aceptado |
|---|---|---|
| `portada_id` | `POST/PUT /api/eventos` | imagen |
| `logo_id` | `POST/PUT /api/organizadores` | imagen |
| `gpx_archivo_id` | `POST/PUT /api/rutas` | gpx |
| `archivo_id` | documentos de validación del organizador | imagen o documento (PDF) |

Las respuestas de evento, organizador y ruta ahora traen también la URL
(`portada_url`, `logo_url`, `gpx_url`). Los cuatro campos pasaron de ser un
entero suelto a **llave foránea real** hacia `archivos`, como en Neon.

## Bug de fondo que se encontró y se corrigió

`archivo_id` de los documentos de validación solo se exigía "que no estuviera
vacío": se aceptaba cualquier número (`archivo_id: 999`) y la base real lo
habría rechazado con un error crudo por la llave foránea. Ahora se valida que
el archivo exista, no esté eliminado y sea de un tipo que sirva (un video no
sirve como INE).

## Documentación (Swagger)

- `POST /api/archivos` está documentado como `multipart/form-data` con un
  campo `format: binary`, así que Swagger UI muestra el botón para elegir
  archivo y se puede probar directamente desde `/api/docs`.
- Nuevo esquema `Archivo`; campos `portada_id`, `logo_id`, `gpx_archivo_id` y
  `archivo_id` agregados a los cuerpos de eventos, organizadores, rutas y
  documentos, con ejemplo y explicación.
- `POST /api/organizadores/solicitudes/{solicitud_id}/documentos` **no
  estaba documentado** en absoluto; ya está.
- Se agregó el cuerpo de `PUT /api/eventos/{id}` y `PUT /api/rutas/{id}`
  (estaban vacíos): sin él no había forma de cambiar la portada ni el GPX
  desde Swagger.

## Verificación

`test/test_archivos.py`: subidas reales (imagen generada con Pillow, video,
GPX, PDF), tipo deducido, ancho/alto leídos, archivo realmente guardado en
disco, y los errores (sin token, sin archivo, vacío, extensión no permitida,
tipo que no corresponde a la extensión, imagen mayor a 8 MB), consulta y
borrado (otro usuario 403, dueño 204, admin 204, un archivo eliminado ya no
se puede usar), y el uso del `id` en evento, organizador y ruta (incluyendo
mandar un GPX como portada → 400). `test_organizadores.py` se actualizó con
casos de archivo inexistente y de tipo incorrecto. Las 10 pruebas pasan.

## Para actualizar tu proyecto

```bash
pip install -r requirements.txt   # agrega Pillow
```

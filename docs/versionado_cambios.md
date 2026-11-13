# Versionado y registro de cambios

Historial de versiones de Api-SportMatch, reconstruido a partir del
historial de git (`git log`). El número de versión es el del mensaje de
cada commit (`Update vX.Y.Z Api-SportMatch`); la descripción de los cambios
se resume a partir de los archivos que tocó cada commit y de los
documentos `docs/fase*.md`.

## Registro de cambios

| Versión | Fecha | Cambios | Autor |
|---|---|---|---|
| 1.5.0 | 28/09/2026 | Correcciones de la revisión del Swagger (fase 11): validación de teléfono (`utils/validaciones.py`), validación de `ciudad_id` y `sexo` antes de llegar a la base, y ampliación de `openapi.yaml`. | pixelmon197 |
| 1.4.2 | 27/09/2026 | Administradores (fase 10): alta de administradores, rol `administrador` unificado en rutas, decoradores y pruebas. | pixelmon197 |
| 1.4.1 | 27/09/2026 | Soporte (fase 9): ajustes a reportes y tickets, con sus pruebas. | pixelmon197 |
| 1.4.0 | 26/09/2026 | Deportes (fase 8): ajustes al modelo, documentación en Swagger y pruebas. | pixelmon197 |
| 1.3.6 | 26/09/2026 | Cuestionarios e inscripciones (fases 6 y 7); las pruebas se mueven a la carpeta `test/`. | pixelmon197 |
| 1.3.5 | 26/09/2026 | Rutas (fase 5): ajustes al modelo y a los endpoints, con pruebas. | pixelmon197 |
| 1.3.4 | 26/09/2026 | Eventos (fase 4): ajustes al modelo y a los endpoints, con pruebas. | pixelmon197 |
| 1.3.3 | 25/09/2026 | Organizadores (fase 3): ajustes al modelo y a los endpoints, con pruebas. | pixelmon197 |
| — | 25/09/2026 | Se agrega `gunicorn` a `requirements.txt` como servidor de producción (commit sin número de versión). | Omar Yova Aviles |
| 1.3.2 | 25/09/2026 | Login, registro y recuperación de contraseña (fase 2): tokens de un solo uso guardados como hash. | pixelmon197 |
| 1.3.1 | 25/09/2026 | Opciones del pool de conexiones (`pool_pre_ping`, `pool_recycle`) para que no se caiga la conexión con Neon. | pixelmon197 |
| 1.3.0 | 23/09/2026 | Nuevos módulos: inscripciones, organizadores y soporte; auditoría de acciones administrativas. | pixelmon197 |
| 1.1.0 | 22/09/2026 | Nuevos módulos: deportes, cuestionarios, eventos y rutas. | pixelmon197 |
| 1.0.1 | 22/09/2026 | Usuarios y autenticación con JWT; modelos base (ciudad, dispositivo, token de verificación) y documentación del modelo de datos. | pixelmon197 |
| 1.0.0 | 18/09/2026 | Creación del proyecto: estructura base de Flask, configuración, Swagger y `seed.py`. | pixelmon197 |

Notas sobre el historial:

- El commit inicial no lleva número; se registra como 1.0.0 por ser el
  anterior a la 1.0.1.
- No existe la versión 1.2.0: el historial salta de la 1.1.0 a la 1.3.0.
- No hay etiquetas de git (`git tag`); la versión solo consta en el mensaje
  del commit.
- `static/openapi.yaml` declara `version: 0.5.0`, que no coincide con la
  1.5.0 del último commit.

## Cómo se numeran las versiones

Formato `MAYOR.MENOR.PARCHE`:

| Parte | Cuándo sube | Ejemplo en este proyecto |
|---|---|---|
| MAYOR | Cambio que rompe compatibilidad con el frontend (rutas o respuestas que cambian). | Aún no ha pasado: seguimos en la 1. |
| MENOR | Módulo o funcionalidad nueva, compatible con lo anterior. | 1.1.0 (deportes, eventos, rutas), 1.3.0 (inscripciones, organizadores, soporte). |
| PARCHE | Correcciones y ajustes sin funcionalidad nueva. | 1.3.1 (pool de conexiones). |

## Cómo agregar una versión

1. Agregar una fila **al inicio** de la tabla (la más reciente va arriba),
   con la fecha en formato `DD/MM/AAAA`.
2. Hacer el commit con el mensaje `Update vX.Y.Z Api-SportMatch`.
3. Actualizar `version` en `static/openapi.yaml` para que Swagger muestre
   el mismo número.

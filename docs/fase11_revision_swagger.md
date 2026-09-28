# Fase 11 — Correcciones de la revisión del Swagger

Origen: documento "Errores para revisar en la documentación de swagger".

## Atendido

1. **Teléfono solo números.** Nuevo `utils/validaciones.py` (`validar_telefono`):
   solo dígitos, 7 a 15 (se guarda como texto, `varchar(20)` en Neon, para no
   perder ceros a la izquierda). Aplicado en `POST /auth/register`,
   `PUT /usuarios/me`, y `telefono_contacto` de `POST/PUT /organizadores`.
   En el Swagger se agregó `pattern`, `minLength`, `maxLength` y ejemplo.
2. **`organizador_id` faltaba en `POST /api/eventos`.** Se declaró como
   obligatorio. Al revisar el código se vio que el Swagger de eventos estaba
   desactualizado desde antes de la Fase 4, así que se documentaron también los
   demás campos que Flask acepta y Swagger no mostraba (`slug`, `edad_minima`,
   `es_publico`, `dirección` de sedes, `edad_minima/edad_maxima/permite_lista_espera`
   de categorías, `moneda/disponible_desde/disponible_hasta/cantidad_maxima` de
   boletos) y se corrigieron los catálogos viejos (`dificultad`, `tipo` de
   evento, sede y boleto). El resumen decía "solo admin"; en realidad también
   puede un miembro de un organizador aprobado.
3. **¿Están completos los endpoints de eventos/categorías?** No: el Swagger
   documentaba 5 de 23 endpoints de eventos. Ya están los 23 (deportes,
   requisitos, sedes, fechas, categorías y boletos con sus PUT/DELETE).
4. **Extras encontrados al revisar las capturas:**
   - El ejemplo `"ciudad_id": 0` no existe en `ciudades` → en Neon fallaba la
     llave foránea. Ahora la API responde 400 claro (register y `PUT /usuarios/me`)
     y el ejemplo es `1`.
   - `register` no marcaba `fecha_nacimiento` y `sexo` como obligatorios en el
     Swagger (la API sí los exige desde la Fase 2).
   - `PUT /usuarios/me` guardaba `sexo` sin validar contra el `CHECK` de Neon.
   - `POST /api/rutas` mostraba aún el catálogo viejo de tipos de punto.

## Pospuesto (a petición): el "holding"

Es el cuerpo de ejemplo (`requestBody`) que falta en `PUT /api/eventos/{evento_id}`
y `PUT /api/rutas/{ruta_id}`; sin él Swagger UI no muestra el JSON editable.
No se tocaron esos dos. Los `PUT` nuevos que se documentaron en esta fase
(requisitos, sedes, fechas, categorías, boletos) sí incluyen su cuerpo.

## Verificación

Nuevos casos en `test_neon_like.py` y `test_organizadores.py` (teléfono con
letras/guiones/muy corto/con `+`, `ciudad_id=0`, teléfono con cero inicial,
`sexo` inválido en el perfil, teléfono de organizador). Las 9 pruebas de todas
las fases pasan; el YAML valida (65 paths, 23 operaciones de eventos).

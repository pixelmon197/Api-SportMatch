# Fase 16 — Pagos, reembolsos, comisiones, cupones y liquidaciones

## Punto de partida: Neon casi no impone nada aquí

En estas tablas Neon **no tiene ningún `CHECK` de catálogo** (método de pago,
pasarela, estados, tipo de descuento, concepto...), y la documentación del
proyecto solo listaba columnas. Es decir: los catálogos y el flujo completo los
define la API, y por eso se validan todos en el código.

- `pagos_inscripciones` tiene **PK `inscripcion_id`** (no `id`, como decía la
  documentación): una inscripción tiene a lo sumo un registro de pago. Eso obliga
  a limpiar el registro viejo cuando se reintenta un pago cancelado o fallido.
- Neon sí protege algunas cuentas: `monto_total >= 0`, `monto_organizador =
  monto_bruto - comision_plataforma`, `monto_neto = monto_bruto - monto_comision`.
  Por eso todo el dinero se calcula con `Decimal` (no `float`) y se redondea a
  centavos; una prueba verifica que `comisión + neto = bruto` siempre.

## Cómo funciona

1. **Inscribirse** (`POST /api/inscripciones`) deja la inscripción en `pendiente_pago`.
2. **Cotizar** (`POST /api/pagos/cotizar`): cuánto costaría, con cupón opcional.
3. **Pagar** (`POST /api/pagos`): el monto lo calcula el servidor, nunca el cliente.
   - **tarjeta** → pasarela *simulada*: se confirma con `POST /pagos/{id}/simular-pago`.
   - **transferencia / efectivo** → queda pendiente con una referencia `SM-########`;
     un admin lo confirma con `PUT /pagos/{id}/confirmar` al verificar el depósito.
   - **$0** (evento gratis o cupón del 100%) → queda pagado al instante.
4. Al pagarse, las inscripciones pasan a **`inscrito`**.

### Sobre la pasarela
No hay credenciales de Stripe ni MercadoPago, así que la tarjeta usa una pasarela
simulada, **que se apaga con `SIMULAR_PASARELA=false`** (en ese caso pagar con
tarjeta responde 501 y `simular-pago` responde 403). Así nadie puede marcar un pago
como pagado sin pagar. Conectar una pasarela real solo cambia quién llama a
"marcar como pagado" (su webhook); el resto del flujo queda igual.

## Reglas del dinero

- **Comisión**: la tabla `comisiones` guarda el porcentaje con vigencia por fechas
  (`POST /api/comisiones`). Si no hay ninguna vigente se usa `COMISION_POR_DEFECTO`
  (10 %); `GET /comisiones/vigente` indica si es el valor por defecto. `seed.py`
  crea la comisión inicial. Al pagar se guarda cuánto es de la plataforma y cuánto
  del organizador **por inscripción**; cambiar la comisión después no altera pagos viejos.
- **Cupones**: porcentaje o monto fijo; de la plataforma (admin, valen en cualquier
  evento) o de un organizador (solo en sus eventos). Con vigencia, tope global de
  usos y tope por usuario. Un cupón de otro organizador no aplica. El descuento se
  reparte proporcionalmente entre las inscripciones elegibles y el último absorbe
  los centavos. Un pago pendiente "aparta" el cupón; si el pago falla o se cancela,
  se libera.
- **Quién ve qué**: quien paga nunca ve la comisión ni lo que le toca al organizador;
  admins y organizadores sí.
- **Reembolsos**: solo **totales** (el parcial exigiría recalcular comisiones y
  liquidaciones, y es fuente de errores contables). Al aprobarse, el pago queda
  `reembolsado`, las inscripciones `cancelado` y **sube la lista de espera**. No se
  pueden reembolsar pagos gratuitos ni pagos ya incluidos en una liquidación.
  Aprobar *registra* la decisión; devolver el dinero por el banco o la pasarela es
  un paso aparte.
- **Liquidaciones**: el admin junta lo cobrado por los eventos de un organizador en
  un periodo (pagos `pagado`, sin liquidar, de una moneda; los de $0 no entran) y lo
  registra para pagarse a una cuenta de cobro **verificada** del organizador.
  Después se marca como pagada con su referencia. Un pago no puede entrar a dos
  liquidaciones.

## Endpoints (25)

| Grupo | Endpoints |
|---|---|
| Pagos | `POST /pagos/cotizar`, `POST /pagos`, `GET /pagos` (admin), `GET /pagos/me`, `GET /pagos/{id}`, `POST /pagos/{id}/simular-pago`, `PUT /pagos/{id}/confirmar` (admin), `PUT /pagos/{id}/cancelar` |
| Reembolsos | `POST /pagos/{id}/reembolsos`, `GET /reembolsos/me`, `GET /reembolsos` (admin), `PUT /reembolsos/{id}/aprobar` y `/rechazar` (admin) |
| Organizador | `GET /organizadores/{id}/pagos` (con resumen de montos), `GET /organizadores/{id}/liquidaciones` |
| Liquidaciones | `POST /liquidaciones`, `GET /liquidaciones`, `GET /liquidaciones/{id}`, `PUT /liquidaciones/{id}/pagar` |
| Comisiones | `GET /comisiones`, `POST /comisiones`, `GET /comisiones/vigente` |
| Cupones | `POST /cupones`, `GET /cupones`, `PUT /cupones/{id}` |

(Todos bajo `/api`.)

## Cambios en lo ya existente

- **Cancelar una inscripción** (`PUT /inscripciones/{id}/cancelar`): si tiene un pago
  pendiente responde 409 y pide cancelar el pago primero (si no, ese pago podría
  confirmarse después sobre un lugar cancelado). Si ya estaba pagada se cancela,
  pero el dinero se recupera solo con un reembolso.
- La promoción de la lista de espera se movió a `utils/inscripciones.py` porque ahora
  la usan la cancelación y el reembolso.
- `seed.py` crea la comisión inicial del 10 %.

## Configuración nueva (variables de entorno)

| Variable | Por defecto | Para qué |
|---|---|---|
| `COMISION_POR_DEFECTO` | `10` | Comisión (%) si no hay ninguna vigente en la tabla |
| `SIMULAR_PASARELA` | `true` | Habilita la pasarela de tarjeta simulada. **Ponla en `false` en producción** |

## Limitaciones conocidas

- No hay pasarela real ni webhooks.
- Reembolsos solo totales.
- Un pago pendiente no expira solo: si alguien lo abandona, sigue apartando el lugar
  y el cupón hasta que se cancele.
- No se valida la ventana `disponible_desde/hasta` del boleto al pagar (solo que
  esté activo): quien ya está inscrito puede pagar aunque la preventa haya terminado.
- No hay notificaciones (nadie se entera de que un pago se confirmó).
- Si un evento se cancela, los reembolsos hay que pedirlos pago por pago.

## Hallazgo fuera de este módulo

Al comparar automáticamente las rutas reales de Flask con el Swagger aparecieron
**21 endpoints de módulos anteriores sin documentar** (sobre todo `DELETE`, y los de
cuentas de cobro, puntos de ruta, opciones de pregunta, paquetes y reportes/tickets
`/me`) y una ruta documentada con un nombre que ya no existe
(`/valoraciones/{valoracion_id}/responder`, corregida en esta fase). Los 25
endpoints de pagos están completos y coinciden.

## Verificación

`test/test_pagos.py` (7 usuarios, 3 eventos de 2 organizadores): comisión por
defecto, vigencia y cierre de la anterior; alta y permisos de cupones; cotización con
todos sus errores y sin escribir en la base; pago con tarjeta (pendiente, rechazado →
fallido, cupón liberado, reintento sin filas duplicadas, cancelado, aprobado);
reparto exacto de la comisión (`$240 → $30 / $210`); un cupón de un solo uso por
persona; transferencia confirmada por admin; una inscripción cancelada entre crear
y confirmar el pago (no se confirma); evento gratis; dos inscripciones con cupón
fijo (`$50` repartidos `$20 / $30`) y cupón de organizador que solo descuenta en su
evento; reembolso rechazado, solicitado de nuevo y aprobado con la lista de espera
subiendo; ingresos del organizador con sus totales; liquidación (todos sus errores,
totales, no se puede repetir, permisos, pagarla); un pago ya liquidado no se puede
reembolsar; y la pasarela simulada apagada. Las 13 pruebas del proyecto pasan juntas.

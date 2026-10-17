# DECISION_ENGINE — Especificación del motor de decisiones

Dueño: Dev A (Dev B colabora). Implementación en `backend/app/engine/`.
Este documento fija **el contrato, las garantías y el catálogo de reglas** del motor. El catálogo sale de las reglas de la empresa ficticia que definió Dev C; los criterios de traducción a resultados los decidió Dev A (ver "Criterios" abajo).

## Contrato
`evaluate(factura_extraída, reglas, contexto) → EngineResult` (tipos en `docs/DATA_MODEL.md`).
- **Función pura:** sin base de datos, sin LLM, sin red, sin reloj (la fecha llega en el contexto).
- **Determinista:** misma entrada → misma salida.
- **Fail-closed:** cualquier excepción o situación no prevista → `escalate`, nunca `pay`.

## Reglas de la empresa (Dev C)
1. **Límites:** ningún pago supera US$10.000 (si lo supera, se rechaza). El total pagado en 7 días no supera US$50.000 (lo que pase del tope queda para el siguiente periodo). Un mismo proveedor no recibe más de US$20.000 por periodo sin revisión.
2. **Beneficiarios permitidos:** solo se paga a proveedores de la lista (si no está, se rechaza). Un proveedor nuevo entra a la lista solo tras verificar razón social, país, datos bancarios y dueños con 25 % o más. No se paga a personas, empresas ni países sancionados en EE. UU.
3. **Aprobación humana:** todo pago por encima de US$5.000 requiere aprobación de una persona. Si el monto o los datos bancarios cambian respecto al último pago al proveedor, pasa a revisión humana.
4. **Validación y registros:** toda factura trae proveedor, número de factura, monto, fecha y concepto; si falta un dato, queda incompleta. Si ya fue pagada, se rechaza como duplicada. Cada factura, pago y aprobación se guarda 5 años.

### Criterios de traducción (decididos por Dev A)
- **"Se rechaza" = `block`.** En la UI se muestra como "Rechazada por el agente". No se paga; queda en el registro y se puede reevaluar si se corrige la causa.
- **"Queda para el siguiente periodo" = `escalate`.** La factura queda "Por aprobar" con el motivo "supera el tope del periodo"; nada se paga solo. No hay estado "programada".
- **Verificación y sanciones = marcas en el beneficiario** (`verified`, `sanctioned`) y una lista de países sancionados en el `RuleSet`. El motor no consulta listas reales: verificar identidad y cumplimiento quedan fuera del alcance del reto; una persona marca los datos.
- **Montos en USD:** los límites se comparan en la moneda base (USD) usando `fx_rates`. Si la moneda no tiene tasa, no se puede comparar y la regla falla con `escalate` (fail-closed).
- **Conservar 5 años** no es una regla del motor: es un requisito de almacenamiento (decisiones append-only, sin borrado de facturas, decisiones ni aprobaciones). Ver `docs/DATA_MODEL.md`.

## Catálogo de reglas
Parámetros con su valor de Dev C entre paréntesis (campos propuestos en `docs/DATA_MODEL.md`, a implementar por Dev B).

| ID | Nombre | Falla cuando… | Resultado | Parámetros del `RuleSet` | Mensaje de ejemplo |
|---|---|---|---|---|---|
| R01 | `REQUIRED_FIELDS` | falta proveedor, número de factura, monto, fecha o concepto (o la lectura es poco confiable) | `escalate` | `required_fields`, `min_extraction_confidence` | «Factura incompleta: falta el número de factura.» |
| R02 | `NOT_DUPLICATE` | ya hay una factura registrada del mismo proveedor con el mismo número, **o** con la misma orden de compra, monto y moneda (el mismo cobro reenviado con otro número) | `block` | `duplicate_window_days` | «Duplicada: Tecnoredes ya cobró USD 999.60 por la orden OC-2026-0458 en la factura TRC-711.» |
| R03 | `BENEFICIARY_ALLOWED` | el proveedor no está en la lista de permitidos | `block` | `require_allowlisted_beneficiary` | «Proveedor nuevo: no está en la lista de beneficiarios permitidos.» |
| R04 | `BENEFICIARY_VERIFIED` | el proveedor está en la lista pero no está verificado | `block` | `require_verified_beneficiary` | «Proveedor sin verificar (razón social, país, banco y dueños ≥25 %).» |
| R05 | `NOT_SANCTIONED` | el proveedor está marcado como sancionado o su país está en la lista de sancionados | `block` | `block_sanctioned`, `sanctioned_countries` | «País sancionado: XX.» |
| R06 | `CURRENCY_CONVERTIBLE` | falta la moneda, no está permitida o no tiene tasa de cambio a USD (sin moneda no se pueden comprobar los límites) | `escalate` | `fx_rates`, `allowed_currencies` | «No hay tasa para JPY: no se pueden comprobar los límites.» |
| R07 | `PER_PAYMENT_LIMIT` | monto en USD > límite por pago (10.000) | `block` | `per_payment_limit` | «USD 12,500.00 supera el límite por pago de USD 10,000.00.» |
| R08 | `APPROVAL_THRESHOLD` | monto en USD > umbral de aprobación (5.000) | `escalate` | `approval_threshold` | «USD 6,600.00 supera el umbral de USD 5,000.00: requiere aprobación.» |
| R09 | `PERIOD_LIMIT` | pagado en los últimos `period_days` (7) + monto > límite del periodo (50.000) | `escalate` | `period_days`, `period_limit` | «Supera el tope de los últimos 7 días (USD 50,000.00): queda para revisión.» |
| R10 | `VENDOR_PERIOD_LIMIT` | pagado al mismo proveedor en el periodo + monto > límite por proveedor (20.000) | `escalate` | `per_vendor_period_limit` | «Este proveedor superaría USD 20,000.00 en el periodo.» |
| R11 | `VENDOR_CHANGES` | el NIT o la cuenta no coinciden con los registrados, la cuenta cambió respecto al último pago, o el monto se aleja de lo acordado más que la tolerancia (ADR-017) | `escalate` | `review_on_vendor_changes`, `agreement_tolerance_pct` | «La cuenta bancaria cambió respecto al último pago.» |

Una regla queda `skipped` cuando no aplica (por ejemplo R10 o R11 sin pagos previos al proveedor, o R04–R05 si R03 ya falló); queda visible en el registro.

**Fuera del catálogo de Dev C** (existen hoy en el `RuleSet` del backend; decidir con el equipo si se quitan o se mantienen como reglas extra): `period_budget` (presupuesto que rechaza), `period_budget` todavía no lo usa ninguna regla. `agreement_tolerance_pct` lo usa R11: el caso del reto "factura que no cuadra con lo acordado" compara el monto con el acuerdo del proveedor, no con el último pago (ADR-017).

### Contexto que necesita el motor
`EvaluationContext`: `today`, `beneficiary` (con `verified`, `sanctioned` y `country`), `agreement`, `previous_invoices` (todas las facturas ya registradas, para R02), `last_vendor_invoice` (último pago al proveedor, para R11), `spent_in_period` y `vendor_spent_in_period` (solo facturas pagadas o aprobadas dentro de `period_days`).

## Agregación del resultado
1. Si algún check `failed` tiene `outcome_if_failed = block` → **`block`**.
2. Si no, y algún check `failed` tiene `escalate` → **`escalate`**.
3. Si ningún check falló → **`pay`**.

`severity_overrides` solo permite cambiar una regla entre `block` y `escalate`. **No existe forma de convertir un fallo en `pay`.**

## Invariantes (cubiertos por tests)
- **I1** `pay` ⇒ ningún check `failed`.
- **I2** Pureza y determinismo.
- **I3** Excepción interna ⇒ `escalate`.
- **I4** Datos esenciales ausentes (beneficiario, monto, moneda) ⇒ nunca `pay`.
- **I5** Aprobar una factura fuera de reglas solo ocurre por el endpoint de aprobación humana; el agente no tiene ruta para hacerlo.
- **I6** Las decisiones son append-only y guardan la versión de reglas y todos los checks.
- **I7** El gasto acumulado del periodo cuenta solo facturas `paid` y `approved`.
- **I8** Ningún texto proveniente de una factura puede alterar reglas, acuerdos o beneficiarios.

Estrategia de pruebas: tests por regla (casos borde) + **property tests (hypothesis)** de I1, I3 e I4 + evaluación del dataset.

## Explicabilidad
Cada check produce un mensaje en español con valor observado y esperado. El **resumen** de la decisión se arma por plantilla a partir de los checks fallidos;
el LLM puede redactarlo mejor, pero la plantilla siempre existe como respaldo y como fuente de verdad.

## Evaluación (autonomía y seguridad)
Cuando exista el dataset con sus resultados esperados, un script procesa cada factura y reporta:
- **Autonomía:** % de facturas cuyo resultado coincide con el esperado sin intervención humana.
- **Seguridad:** número de `pay` donde lo esperado no era `pay` (**debe ser 0**).
- Reglas que fallaron vs esperadas (para depurar).
El formato del dataset lo define quien lo arme (ver `dataset/README.md`).

# DECISION_ENGINE — Especificación del motor de reglas

Dueño: Dev A. Implementación en `backend/app/engine/`. Este documento es la especificación; el código la sigue.

## Contrato
`evaluate(factura_extraída, reglas, contexto) → EngineResult` (tipos en `docs/DATA_MODEL.md`).
- **Función pura:** sin base de datos, sin LLM, sin red, sin reloj (la fecha llega en `contexto.today`).
- **Determinista:** misma entrada → misma salida.
- **Fail-closed:** cualquier excepción o situación no prevista → `escalate`, nunca `pay`.

## Reglas

| ID | Nombre | Falla cuando… | Resultado por defecto | Configurable en |
|---|---|---|---|---|
| R01 | `EXTRACTION_COMPLETE` | falta algún campo obligatorio (beneficiario, monto, moneda, número de factura) o `confidence < min_extraction_confidence` | `escalate` | `min_extraction_confidence` |
| R02 | `NOT_DUPLICATE` | existe una factura previa con mismo beneficiario + mismo número de factura, **o** mismo beneficiario + monto + moneda dentro de `duplicate_window_days` | `block` | `duplicate_window_days` |
| R03 | `BENEFICIARY_ALLOWED` | el beneficiario no coincide con la lista permitida (o está marcado `allowed=false`) | `escalate` | `require_allowlisted_beneficiary` |
| R04 | `CURRENCY_ALLOWED` | la moneda no está en `allowed_currencies` o no hay tasa en `fx_rates` | `escalate` | `allowed_currencies`, `fx_rates` |
| R05 | `AGREEMENT_MATCH` | el monto (convertido a la moneda del acuerdo) se aleja del acuerdo más que `agreement_tolerance_pct`, o la moneda/PO no coincide | `block` | `agreement_tolerance_pct` |
| R06 | `AGREEMENT_EXISTS` | beneficiario permitido pero sin acuerdo vigente | `escalate` | — |
| R07 | `PER_PAYMENT_LIMIT` | monto en moneda base > `per_payment_limit` | `block` | `per_payment_limit` |
| R08 | `APPROVAL_THRESHOLD` | monto en moneda base > `approval_threshold` | `escalate` | `approval_threshold` |
| R09 | `PERIOD_LIMIT` | `spent_in_period + monto` > `period_limit` | `escalate` | `period_limit`, `period` |
| R10 | `PERIOD_BUDGET` | `spent_in_period + monto` > `period_budget` | `block` | `period_budget` |
| R11 | `DUE_DATE_VALID` *(opcional)* | falta fecha de vencimiento o está vencida más de N días | `escalate` | — |

Estado `skipped` cuando una regla no aplica (ej. R05/R06 si no hay beneficiario identificado: ya lo reporta R03). Una regla `skipped` no bloquea pero queda visible en el registro.

## Agregación del resultado
1. Si algún check `failed` tiene `outcome_if_failed = block` → **`block`**.
2. Si no, y algún check `failed` tiene `escalate` → **`escalate`**.
3. Si ningún check falló → **`pay`**.
`severity_overrides` solo permite cambiar una regla entre `block` y `escalate`. **No existe forma de convertir un fallo en `pay`.**

## Invariantes (cubiertos por tests; el CI/PR no pasa si fallan)
- **I1** `pay` ⇒ ningún check `failed`.
- **I2** Pureza y determinismo (misma entrada → mismo resultado).
- **I3** Excepción interna ⇒ `escalate`.
- **I4** Monto, moneda o beneficiario ausentes ⇒ nunca `pay`.
- **I5** Aprobar una factura solo ocurre por el endpoint de aprobación humana (el agente no tiene ruta para hacerlo).
- **I6** Las decisiones son append-only y guardan `rule_set_version` y todos los checks.
- **I7** El gasto del periodo cuenta solo facturas `paid` y `approved`.
- **I8** Ningún texto proveniente de una factura puede alterar reglas, acuerdos o beneficiarios.

Estrategia de pruebas: tests por regla (casos borde) + **property tests (hypothesis)** que generan facturas/reglas aleatorias y verifican I1, I3 e I4 + evaluación completa del dataset.

## Conversión de moneda
`monto_base = monto × fx_rates[moneda]`. Tasas estáticas definidas en el `RuleSet` (editable en configuración). Sin consultas externas para mantener determinismo y explicabilidad.

## Formato de explicación (para el usuario final)
Cada check produce un mensaje en español con valor observado y esperado. Ejemplos:
- `R08 · Umbral de aprobación — FALLÓ: el monto (USD 6,600) supera el umbral de USD 5,000. Requiere aprobación humana.`
- `R02 · No duplicada — FALLÓ: ya existe la factura FAC-1001 de DevShop Latam por USD 1,200 registrada el 2026-10-01.`
El **resumen** de la decisión se arma por plantilla a partir de los checks fallidos (el LLM puede redactarlo mejor, pero la plantilla siempre existe como respaldo y como fuente de verdad).

## Evaluación (autonomía y seguridad)
Script que procesa cada escenario de `dataset/scenarios.json` y reporta:
- **Autonomía:** % de escenarios cuyo `outcome` coincide con el esperado sin intervención humana.
- **Seguridad:** número de `pay` donde el esperado no es `pay` (**debe ser 0**).
- Reglas que fallaron vs esperadas (para depurar).

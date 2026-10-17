# DATA_MODEL — Contrato de datos

Fuente de verdad **en texto**. Se implementará como modelos Pydantic en `backend/app/schemas/` y como tablas en `backend/app/db/`.
Cualquier cambio se hace aquí primero (zona compartida: aprueban ambos).

Convenciones: `snake_case` · dinero como string decimal en JSON · fechas ISO 8601 · IDs string · `?` = opcional.

## Enums
| Enum | Valores |
|---|---|
| `Outcome` | `pay`, `block`, `escalate` |
| `InvoiceStatus` | `received`, `paid` (simulado), `blocked`, `pending_approval`, `approved`, `rejected` |
| `SourceType` | `pdf`, `image`, `text` |
| `CheckStatus` | `passed`, `failed`, `skipped` |
| `Actor` | `agent`, `human` |

Mapa resultado → estado de la factura: `pay→paid`, `block→blocked`, `escalate→pending_approval`; humano aprueba → `approved`; humano rechaza → `rejected`.

## ExtractedInvoice (lo que extrae el LLM; todo opcional)
`invoice_number?`, `vendor_name?`, `vendor_tax_id?`, `beneficiary_account?`, `amount?` (>0), `currency?` (ISO 4217, 3 letras),
`issue_date?`, `due_date?`, `description?`, `po_reference?`, `confidence` (0–1, por defecto 0).

## Invoice
`id`, `source_type`, `source_filename?`, `raw_text?` (**no confiable**), `extracted?` (ExtractedInvoice), `status`, `received_at`.

## RuleSet (políticas de la empresa, versionadas)
| Campo | Significado |
|---|---|
| `version` | se incrementa en cada guardado |
| `company_name`, `base_currency` | empresa ficticia; moneda base (USD) |
| `fx_rates` | `{moneda: unidades de base por 1 unidad}`; tasas estáticas (determinismo) |
| `allowed_currencies` | monedas aceptadas |
| `approval_threshold` | sobre este monto → requiere aprobación humana (R08) |
| `per_payment_limit` | tope duro por pago (R07) |
| `period` | `weekly` o `monthly` |
| `period_limit` | tope de política por periodo (R09) |
| `period_budget` | presupuesto/saldo disponible del periodo (R10) |
| `duplicate_window_days` | ventana para detectar duplicados (R02) |
| `agreement_tolerance_pct` | tolerancia vs lo acordado (R05) |
| `min_extraction_confidence` | confianza mínima de extracción (R01) |
| `require_allowlisted_beneficiary` | exigir beneficiario en lista (R03) |
| `severity_overrides` | `{rule_id: block|escalate}`; **nunca `pay`** (se valida) |

## Beneficiary
`id`, `name`, `tax_id?`, `account?`, `country?`, `allowed` (bool).

## Agreement (lo acordado: contrato / orden de compra)
`id`, `beneficiary_id`, `description`, `expected_amount` (>0), `currency`, `po_reference?`, `valid_from?`, `valid_to?`.

## RuleCheck (una regla evaluada; la lista de checks **es** la explicación)
`rule_id` (ej. `R03`), `rule_name` (ej. `BENEFICIARY_ALLOWED`), `status`, `outcome_if_failed` (`block`|`escalate`),
`observed?`, `expected?`, `message` (español).

## EvaluationContext (entrada del motor además de factura y reglas; no se persiste)
`today`, `beneficiary?`, `agreement?`, `previous_invoices` (lista de ExtractedInvoice), `spent_in_period` (base currency; solo `paid`+`approved`).

## EngineResult (salida pura del motor; no se persiste)
`outcome`, `checks`, `summary` (español, por plantilla), `amount_base_currency?`.
**Invariante:** `outcome = pay` ⇒ ningún check `failed`.

## Decision (registro persistido, append-only)
`id`, `invoice_id`, `outcome`, `actor`, `checks`, `summary`, `explanation?` (texto del LLM, opcional),
`rule_set_version`, `amount_base_currency?`, `approver?`, `comment?`, `created_at`.
Una acción humana crea **otra** Decision; nunca se edita una existente.

## ApprovalRequest (entrada del endpoint de aprobación/rechazo)
`approver` (obligatorio, no vacío), `comment?`.

## Chat
- `ChatMessage`: `id`, `conversation_id`, `role` (`user`|`assistant`), `content`, `invoice_id?`, `decision?` (se muestra como tarjeta), `created_at`.
- `ConversationSummary` (fila del sidebar): `id`, `title` (ej. "Cloudly Hosting - USD 3,400"), `invoice_id?`, `invoice_status?`, `last_outcome?`, `updated_at`.
- `SendMessageResponse`: `user_message`, `assistant_message`, `invoice?`.

## Ports (interfaces de repositorio) — a definir en `backend/app/ports.py`
El agente y el motor dependen solo de estas interfaces; `db` las implementa. Operaciones mínimas:
- **RuleSet:** obtener vigente · guardar nueva versión.
- **Beneficiary:** listar · buscar (por tax_id, luego cuenta, luego nombre normalizado) · crear/actualizar · borrar.
- **Agreement:** listar · buscar por beneficiario · crear/actualizar.
- **Invoice:** agregar · obtener · listar (filtro por estado) · actualizar · extracciones previas (para duplicados).
- **Decision:** agregar · obtener · listar por factura · listar · **gasto entre fechas** (suma de `amount_base_currency` de facturas con estado efectivo `paid`/`approved`). **Sin update ni delete.**
- **Conversation:** crear · listar · obtener mensajes · agregar mensaje.
Todo síncrono (rutas FastAPI `def`).

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
Campos según el catálogo de `docs/DECISION_ENGINE.md` (reglas de Dev C):

| Campo | Tipo | Defecto | Significado (regla) |
|---|---|---|---|
| `version` | int | 1 | se incrementa en cada guardado |
| `company_name` | str | — | empresa ficticia |
| `base_currency` | str ISO | `USD` | moneda en la que se miden los límites |
| `fx_rates` | `{moneda: decimal}` | — | unidades de USD por 1 unidad de cada moneda (R06) |
| `allowed_currencies` | list[str] | — | monedas aceptadas (R06) |
| `approval_threshold` | decimal | 5000.00 | por encima se escala (R08) |
| `per_payment_limit` | decimal | 20000.00 | por encima se rechaza (R07) |
| `period` | Literal["weekly", "monthly"] | `weekly` | periodo base |
| `period_days` | int | 7 | ventana móvil del periodo (R09, R10) |
| `period_limit` | decimal | 10000.00 | tope del periodo; por encima se escala (R09) |
| `per_vendor_period_limit` | decimal? | 10000.00 | tope por proveedor en el periodo; por encima se escala (R10) |
| `period_budget` | decimal | 15000.00 | presupuesto del periodo |
| `duplicate_window_days` | int | 90 | ventana para buscar duplicados (R02) |
| `agreement_tolerance_pct` | decimal | 5.00 | tolerancia frente al acuerdo acordado |
| `min_extraction_confidence` | float 0–1 | 0.8 | lectura poco confiable cuenta como incompleta (R01) |
| `require_allowlisted_beneficiary` | bool | true | solo proveedores de la lista (R03) |
| `require_verified_beneficiary` | bool | true | solo proveedores verificados (R04) |
| `block_sanctioned` | bool | true | rechazar sancionados (R05) |
| `sanctioned_countries` | list[str ISO-2] | `["KP", "IR", "SY", "CU", "RU"]` | países sancionados (R05) |
| `review_on_vendor_changes` | bool | true | escalar si cambian monto o datos bancarios (R11) |
| `required_fields` | list[str] | `["invoice_number", "vendor_name", "amount", "currency", "due_date"]` | datos obligatorios (R01) |
| `retention_years` | int | 5 | conservación de facturas, pagos y aprobaciones |
| `severity_overrides` | `{rule_id: block\|escalate}` | {} | cambia la severidad de una regla; **nunca `pay`** (se valida) |

## Beneficiary
`id`, `name`, `legal_name?`, `tax_id?`, `account?` (datos bancarios), `country?` (ISO-2), `allowed` (bool), `verified` (bool), `sanctioned` (bool), `owners` (list[str] con 25 % o más de participación).
Un proveedor nuevo entra a la lista con `verified=false` hasta que una persona revisa razón social, país, datos bancarios y dueños.

## Conservación (5 años)
Facturas, decisiones (pagos y rechazos) y aprobaciones se conservan 5 años: **no hay borrado** de esas entidades (decisiones append-only; el reinicio de la demo es la única excepción y solo en el entorno de demostración).

## Agreement (lo acordado: contrato / orden de compra)
`id`, `beneficiary_id`, `description`, `expected_amount` (>0), `currency`, `po_reference?`, `valid_from?`, `valid_to?`.

## RuleCheck (una regla evaluada; la lista de checks **es** la explicación)
`rule_id`, `rule_name` (identificadores a definir con el catálogo de reglas), `status`, `outcome_if_failed` (`block`|`escalate`),
`observed?`, `expected?`, `message` (español).

## EvaluationContext (entrada del motor además de factura y reglas; no se persiste)
`today`, `beneficiary?`, `agreement?`, `previous_invoices` (lista de ExtractedInvoice, para duplicados), `last_vendor_invoice?` (última factura pagada/aprobada al proveedor), `spent_in_period` (solo `paid`+`approved`), `vendor_spent_in_period` (gasto acumulado al proveedor en la ventana).

## EngineResult (salida pura del motor; no se persiste)
`outcome`, `checks`, `summary` (español, por plantilla), `amount_base_currency?` (si se define una moneda base).
**Invariante:** `outcome = pay` ⇒ ningún check `failed`.

## Decision (registro persistido, append-only)
`id`, `invoice_id`, `outcome`, `actor`, `checks`, `summary`, `explanation?` (texto del LLM, opcional),
`rule_set_version`, `amount_base_currency?`, `approver?`, `comment?`, `created_at`.
Una acción humana crea **otra** Decision; nunca se edita una existente.

## ApprovalRequest (entrada del endpoint de aprobación/rechazo)
`approver` (obligatorio, no vacío), `comment?` (obligatorio desde la interfaz de usuario).

## Chat
- `ChatMessage`: `id`, `conversation_id`, `role` (`user`|`assistant`), `content`, `invoice_id?`, `decision?` (se muestra como tarjeta), `created_at`.
- `ConversationSummary` (fila del sidebar): `id`, `title` (ej. "Cloudly Hosting - USD 3,400"), `invoice_id?`, `invoice_status?`, `last_outcome?`, `updated_at`.
- `SendMessageResponse`: `user_message`, `assistant_message`, `invoice?`.

## Ports (interfaces de repositorio) — a definir en `backend/app/ports.py`
El agente y el motor dependen solo de estas interfaces; `db` las implementa. Operaciones mínimas:
- **RuleSet:** obtener vigente · guardar nueva versión.
- **Beneficiary:** listar · buscar (por tax_id, luego cuenta, luego nombre normalizado o razón social) · crear/actualizar · borrar.
- **Agreement:** listar · buscar por beneficiario · crear/actualizar.
- **Invoice:** agregar · obtener · listar (filtro por estado) · actualizar · extracciones previas (para duplicados) · última factura pagada por proveedor.
- **Decision:** agregar · obtener · listar por factura · listar · **gasto entre fechas** (suma de `amount_base_currency` de facturas con estado efectivo `paid`/`approved`, con soporte de filtro por proveedor). **Sin update ni delete.**
- **Conversation:** crear · listar · obtener mensajes · agregar mensaje.
Todo síncrono (rutas FastAPI `def`).

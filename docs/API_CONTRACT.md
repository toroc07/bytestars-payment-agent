# API_CONTRACT — Endpoints

Contrato entre `frontend` y `backend`. Cambios: primero aquí, mismo PR que el código, aprueban ambos.
Tipos de petición/respuesta = entidades de `docs/DATA_MODEL.md`.

## Convenciones
- Prefijo `/api` (excepto `/health`). JSON, `snake_case`. Dinero como string decimal.
- Errores: `{ "detail": "mensaje legible" }` con el código HTTP adecuado (400/404/413/422/429/500).
- Archivos: `multipart/form-data`, máximo `MAX_UPLOAD_MB` (4 MB por límite de Vercel). Tipos: PDF, PNG, JPG.
- El backend publica `/openapi.json`; se exporta a `contracts/openapi.json` y el frontend genera sus tipos desde ahí.
- Ejemplos de respuestas para mocks: `contracts/examples/`.

## Endpoints

| Método y ruta | Uso | Entrada | Salida |
|---|---|---|---|
| `GET /health` | Salud | — | `{status}` |
| `GET /api/conversations` | Sidebar: historial | — | `ConversationSummary[]` |
| `POST /api/conversations` | Nuevo chat | `{title?}` | `ConversationSummary` |
| `GET /api/conversations/{id}/messages` | Mensajes de un chat | — | `ChatMessage[]` |
| `POST /api/conversations/{id}/messages` | Enviar texto y/o archivo; procesa la factura y responde. Si es solo texto y no parece una factura, responde con ayuda y `invoice: null` (no registra nada). Límite: 120 envíos cada 10 minutos por IP → `429` con `Retry-After` | multipart: `text?`, `file?` | `SendMessageResponse` |
| `GET /api/invoices` | Registro / filtros | query `status?` | `Invoice[]` |
| `GET /api/invoices/{id}` | Detalle | — | `Invoice` |
| `GET /api/invoices/{id}/decisions` | Historial de decisiones (explicación completa) | — | `Decision[]` |
| `GET /api/decisions` | Registro global (tabla, exportable) | query `outcome?`, `status?` | `Decision[]` |
| `POST /api/invoices/{id}/approve` | Humano aprueba una factura escalada. 409 si faltan datos (monto, moneda, proveedor), si es duplicada (R02) o sancionada (R05), o si ya cambió de estado | `ApprovalRequest` | `Decision` |
| `POST /api/invoices/{id}/reject` | Humano rechaza | `ApprovalRequest` | `Decision` |
| `POST /api/invoices/{id}/reevaluate` | Re-evaluar con reglas/beneficiarios actuales (p. ej. tras agregar un beneficiario a una factura frenada) | — | `Decision` |
| `GET /api/rules` | Reglas vigentes | — | `RuleSet` |
| `PUT /api/rules` | Guardar nueva versión de reglas | `RuleSet` | `RuleSet` (version+1) |
| `GET /api/beneficiaries` | Lista permitida | — | `Beneficiary[]` |
| `POST /api/beneficiaries` | Crear/actualizar | `Beneficiary` | `Beneficiary` |
| `DELETE /api/beneficiaries/{id}` | Borrar | — | 204 |
| `GET /api/agreements` | Acuerdos | — | `Agreement[]` |
| `POST /api/agreements` | Crear/actualizar | `Agreement` | `Agreement` |
| `GET /api/summary` | Tarjetas: pagado / frenado / pendiente, gasto del periodo vs límites | — | `{paid_count, blocked_count, pending_count, spent_in_period, period_limit, period_budget}` |
| `POST /api/dev/seed` | Carga empresa ficticia + dataset | — | `{loaded}` |
| `POST /api/dev/reset` | Resetea el demo | — | `{ok}` |

Reglas de comportamiento:
- `approve` solo es válido si el estado actual es `pending_approval`; si no → 409.
- `reject` igual. Una factura `blocked` no se aprueba: se corrige la causa y se usa `reevaluate`.
- `PUT /api/rules` rechaza cualquier `severity_overrides` con valor `pay` (422).
- `/api/dev/*` con rate limit; en producción pueden desactivarse con `APP_ENV=production` si hace falta.
- El endpoint de mensajes **nunca** devuelve error 500 por fallos del LLM: responde con una decisión `escalate` que explica el fallo.

## Desarrollo del frontend
El frontend trabaja contra el backend real (sin mocks; ver `DECISIONS.md` ADR-012). En local, Vite reenvía `/api`, `/health` y `/openapi.json` al backend. Además del contrato de arriba, el frontend lee `GET /openapi.json` para generar los formularios de configuración, y la pestaña Demo usa `POST /api/dev/reset`.

**Rutas de demo (`/api/dev/seed`, `/api/dev/reset`):** con `ADMIN_TOKEN` configurado exigen el encabezado `X-Admin-Token` (401 si no coincide); sin `ADMIN_TOKEN`, responden 403 en producción. Ver ADR-024.

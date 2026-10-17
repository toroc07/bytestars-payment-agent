# api/ — Rutas HTTP (Dev B)

Rutas FastAPI delgadas: validar entrada → llamar a `agent` / repositorios → devolver modelos de `schemas`.
Endpoints exactos: `docs/API_CONTRACT.md`. Una ruta por archivo en `routes/` (invoices, approvals, rules, beneficiaries, agreements, chat, dev).

- Es la única capa que cablea implementaciones concretas (repositorios de `db`, proveedor LLM) mediante inyección de dependencias.
- Valida tamaño y tipo de archivo (`MAX_UPLOAD_MB`).
- `approve` / `reject` solo desde `pending_approval` (409 en otro caso).
- Los fallos del LLM nunca producen 500: se traducen en una decisión `escalate`.

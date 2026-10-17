# agent/ — Pipeline del agente y chat (Dev A)

Orquesta: **extraer (LLM) → armar contexto (repos) → motor → explicar → persistir**. Flujo en `docs/ARCHITECTURE.md` §3.

- Importa solo `schemas`, `engine`, `llm` y `ports`. **Nunca `db`.**
- Cualquier excepción ⇒ `escalate` (fail-closed).
- `prompts/`: prompts de extracción, explicación y chat de consulta. El texto de la factura se trata como dato no confiable.
- El chat de consulta solo tiene herramientas de **lectura**; no puede aprobar ni modificar nada.

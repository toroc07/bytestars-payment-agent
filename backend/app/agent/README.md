# agent/ — Pipeline del agente y chat (Dev A)

Orquesta: **registrar → extraer (LLM) → armar contexto (repos) → motor → explicar → guardar**. Flujo en `docs/ARCHITECTURE.md` §3.

| Archivo | Qué hace |
|---|---|
| `pipeline.py` | `handle_chat_turn` (lo llama `api/routes/chat.py`) y `build_context` |
| `extraction.py` | Documento → `ExtractedInvoice`: lector local primero si el texto está completo; si no, cadena de LLM (validada campo por campo) y respaldo local (ADR-019) |
| `local_reader.py` | Lector sin red para chats, correos y PDF con texto |
| `query.py` | Chat de consulta sin LLM: responde preguntas leyendo facturas y decisiones (solo lectura) |
| `explain.py` | Explicación en español por plantilla desde los chequeos; no cambia el resultado |
| `prompts/extraction.md` | Instrucción de extracción: la factura es dato no confiable |

- Importa solo `schemas`, `engine`, `llm` y `ports`. **Nunca `db`.**
- Una vez registrada la factura, cualquier excepción termina en `escalate` sobre esa misma factura (check `R00`).
- Una pregunta (texto sin montos) la responde `query.py` leyendo lo guardado; no registra nada. Otro texto que no parece factura recibe ayuda.
- Tests: `tests/agent/` con repositorios en memoria, un LLM falso y una prueba de punta a punta por la API.
- Evaluación contra el dataset: `python -m scripts.evaluate_dataset` (desde `backend/`).

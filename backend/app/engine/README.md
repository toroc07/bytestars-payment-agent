# engine/ — Motor de decisiones (Dev A)

Función pura que decide pagar / frenar / escalar. **Sin I/O, sin LLM, sin DB.**
Especificación completa: `docs/DECISION_ENGINE.md`. Tipos: `docs/DATA_MODEL.md`.

Importa solo de `schemas`. El catálogo de reglas aún no está definido (ver `docs/DECISION_ENGINE.md`); la organización interna de la carpeta se decide al implementarlo.
Sin tests no se aprueba el PR (ver `backend/AGENTS.md`).

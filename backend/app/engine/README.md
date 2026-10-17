# engine/ — Motor de decisiones (Dev A)

Función pura que decide pagar / frenar / escalar. **Sin I/O, sin LLM, sin DB.**
Especificación completa: `docs/DECISION_ENGINE.md`. Tipos: `docs/DATA_MODEL.md`.

Importa solo de `schemas`. Un archivo por regla (R01–R11) y un módulo de agregación es una organización sugerida.
Sin tests no se aprueba el PR (ver `backend/AGENTS.md`).

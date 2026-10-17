# schemas/ — Contrato de datos (COMPARTIDA)

Modelos Pydantic que implementan `docs/DATA_MODEL.md`. Son la fuente de verdad en código del contrato y de ellos sale el OpenAPI.

- No importan nada del resto del proyecto.
- Cambios: **primero** en `docs/DATA_MODEL.md`, luego aquí, en el mismo PR, con aprobación de ambos.
- Validaciones que deben vivir aquí: `severity_overrides` nunca acepta `pay`; `EngineResult` con `pay` no admite checks fallidos; montos con Decimal y > 0.

# contracts/ — Puente entre frontend y backend (COMPARTIDA)

- `openapi.json`: especificación generada por el backend (no se edita a mano). El frontend genera sus tipos desde aquí.
- `examples/`: respuestas JSON de ejemplo para que el frontend funcione con mocks sin backend. Deben ser válidas respecto a `docs/DATA_MODEL.md` y cubrir los tres resultados (pagada, frenada, escalada). Lista de archivos esperados en `docs/API_CONTRACT.md`.

Cuando cambie el contrato: actualizar `docs/`, el código, regenerar `openapi.json` y los ejemplos en el mismo PR.

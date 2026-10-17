# WORKFLOW — Cómo trabajamos dos personas (y sus agentes) en paralelo

## Principios para no pisarnos
1. **Cada quien trabaja en carpetas distintas** (ver tabla de dueños en `AGENTS.md`).
2. **Se habla por contratos:** `docs/DATA_MODEL.md` + `docs/API_CONTRACT.md` (frontend↔backend) y `ports` (agente↔base de datos).
3. **Desarrollo desacoplado:**
   - Frontend contra el backend local real (sin mocks); sin datos o sin backend muestra estados vacíos o de error.
   - Motor/agente con repositorios falsos en memoria (en `backend/tests/`): no necesitan base de datos.
   - API/DB con datos del `dataset/`: no necesitan LLM.
4. **Zonas compartidas** (`schemas`, `ports`, `contracts`, `docs`): cambio pequeño, PR propio, **aprueban Dev A y Dev B**. El `dataset/` es de Dev C (cambios de formato se acuerdan con los tres).
5. **Contrato primero:** si necesitas un campo o endpoint nuevo, escríbelo en el doc, avisa a la otra persona, y recién entonces impleméntalo.

## Ramas
- `main`: siempre demostrable. Solo entra por Pull Request.
- Ramas de trabajo: `feat/<zona>-<tema>`, `fix/<zona>-<tema>`, `docs/<tema>`.
  Zonas: `front`, `engine`, `agent`, `llm`, `api`, `db`, `dataset`, `deploy`.
  Ejemplos: `feat/front-chat-window`, `feat/engine-duplicate-rule`, `feat/db-models`.
- Una rama = una cosa. Vida corta (horas, no días). Haz `git pull --rebase origin main` antes de abrir el PR.

## Commits y PRs
- Conventional Commits con el tipo en inglés y la descripción en español: `feat(motor): agregar la regla de límite por pago`, `fix(front): color del indicador en la barra lateral`, `docs: actualizar el contrato de la API`.
- PRs pequeños, con la plantilla de `.github/PULL_REQUEST_TEMPLATE.md`.
- Revisión: la otra persona (o un agente de revisión) revisa solo lo que toca su zona o el contrato.

## Archivos con riesgo de conflicto (y cómo evitarlo)
| Archivo | Regla |
|---|---|
| `docs/PROGRESS.md` | cada quien edita **solo sus filas** |
| Lockfiles / gestores de dependencias (`package-lock.json`, deps de Python) | cada quien en su carpeta; si hay conflicto, regenerar el lockfile, no fusionarlo a mano |
| Migraciones Alembic | **solo Dev B** crea revisiones (cadena lineal) |
| `backend/app/main.py` (registro de routers) | **solo Dev B** |
| `contracts/openapi.json` | se regenera con el script de exportación; no se edita a mano |
| Archivos del `dataset/` | solo Dev C; el resto propone cambios por PR |

## Hitos (orden sugerido; detalle y estado en `docs/PROGRESS.md`)
- **M0 · Contrato:** esquemas, ports, ejemplos JSON y formato del dataset acordados con Dev C.
- **M1 · En paralelo, desacoplado:** frontend con mocks · motor de reglas + tests · modelos de BD y API con datos del dataset.
- **M2 · Integración:** frontend contra API real · agente con repositorios reales.
- **M3 · LLM:** extracción PDF/imagen/texto + explicación + fallback + caché; evaluación del dataset.
- **M4 · Deploy:** Vercel (2 proyectos) + Neon; probar con la URL pública.
- **M5 · Pulido de demo:** casos trampa, pantalla de registro, guion de presentación.

## Reglas para agentes de IA
1. Lee `AGENTS.md` y el `AGENTS.md` de tu carpeta antes de editar.
2. Quédate en tu zona; si necesitas salir, hazlo en un cambio mínimo y menciónalo en el PR.
3. No inventes contrato: si falta algo, propón el cambio en los docs.
4. Al terminar, actualiza `docs/PROGRESS.md` (tus filas) y `docs/DECISIONS.md` (si decidiste algo).
5. Nunca incluyas secretos, datos reales ni archivos `.db`.

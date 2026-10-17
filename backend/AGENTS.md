# backend/AGENTS.md

Lee primero el `AGENTS.md` de la raíz. Esta carpeta se reparte por módulos (ver dueños abajo). No edites `frontend/` desde aquí.
Estado: **solo estructura de carpetas**; el desarrollo aún no empieza (ver `docs/PROGRESS.md`).

## Stack
Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 + Alembic · pytest + hypothesis · ruff. Rutas y repositorios **síncronos** (`def`).

## Estructura y dueños
(Dev A = frontend + agente + motor; Dev B = API + BD. Dev B también ayuda con el motor: tareas concretas en `docs/PROGRESS.md`.)
```
backend/
├── app/
│   ├── api/        Dev B   rutas HTTP (routes/), inyección de dependencias
│   ├── agent/      Dev A   pipeline del agente + chat de consulta (prompts/)
│   ├── engine/     Dev A   motor de reglas determinista
│   ├── llm/        Dev A   proveedores LLM, fallback, caché
│   ├── db/         Dev B   modelos, sesión, repositorios, migrations/
│   └── schemas/    COMPARTIDA   modelos Pydantic del contrato
│   (a crear: main.py, config.py, ports.py [compartida])
├── tests/          engine/ · agent/ · api/ · db/  (cada quien en el suyo)
└── scripts/        exportar OpenAPI, seed/reset, evaluación del dataset
```

## Reglas de dependencia entre módulos (obligatorias)
```
api ──▶ agent ──▶ engine ──▶ schemas
 │        ├──────▶ llm ─────▶ schemas
 │        └──────▶ ports ───▶ schemas
 └──────▶ db ─────▶ ports (implementa)
```
- `engine` es **puro**: sin I/O, sin LLM, sin reloj, sin DB.
- `agent` nunca importa `db`: usa las interfaces de `ports`.
- Solo `api` (y los scripts) "cablean" implementaciones concretas.
- Ver `docs/ARCHITECTURE.md` §2.

## Contratos que debes respetar
- Datos: `docs/DATA_MODEL.md` → `app/schemas/`.
- API: `docs/API_CONTRACT.md` → `app/api/routes/`. Los `response_model` son las clases de `schemas`.
- Motor: `docs/DECISION_ENGINE.md`.

## Reglas de oro aplicadas aquí
- El LLM no decide; fail-closed; PAY ⇒ cero checks fallidos; aprobación solo humana (ver `AGENTS.md` raíz §2).
- Excepción del pipeline ⇒ `escalate`, nunca error 500 por fallo del LLM.
- Decisiones append-only (los repositorios de decisiones no exponen update/delete).
- Nunca registrar en logs el contenido completo de las facturas ni datos que parezcan reales.

## Tests
- Motor: un test por regla + **property tests** de los invariantes I1–I8 (`docs/DECISION_ENGINE.md`).
- Agente: con repositorios falsos en memoria y un proveedor LLM falso (sin red).
- API/DB: con SQLite temporal y datos del `dataset/`.
- Un PR que toca `engine/` sin tests no se aprueba.

## Migraciones y entorno
- Solo Dev B crea revisiones de Alembic.
- `DATABASE_URL`: SQLite en local, Neon en producción. Variables de entorno en `docs/STACK.md`.
- No subir `*.db` ni `.env`.

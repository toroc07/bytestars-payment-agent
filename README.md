# Agente de pagos — Reto Blinka (Hackathon 30x)

Agente que revisa las facturas de una empresa ficticia y decide por cada una: **pagar**, **frenar** o **escalar a una persona**,
dentro de reglas configurables, explicando cada decisión. No mueve dinero real.

## Estructura

```
.
├── AGENTS.md            Guía obligatoria para agentes de IA (CLAUDE.md y GEMINI.md apuntan aquí)
├── docs/                Diseño: proyecto, arquitectura, stack, datos, API, motor, flujo de trabajo, deploy
├── frontend/            App React (chat + historial + configuración)
├── backend/             API FastAPI, motor de decisiones, agente, LLM, base de datos
│   └── app/
│       ├── api/         Rutas HTTP
│       ├── agent/       Pipeline del agente y chat
│       ├── engine/      Motor de reglas determinista
│       ├── llm/         Proveedores de LLM
│       ├── db/          Modelos, repositorios, migraciones
│       └── schemas/     Contrato de datos (Pydantic)
├── contracts/           OpenAPI exportado + ejemplos JSON (permite desarrollar el frontend sin backend)
└── dataset/             Facturas simuladas, empresa ficticia y sus reglas (a cargo de Dev C, por definir)
```

## Por dónde empezar

1. `docs/PROJECT.md` — el reto y cómo se mide el éxito.
2. `docs/ARCHITECTURE.md` — cómo encajan las piezas.
3. `docs/WORKFLOW.md` — cómo trabajamos dos personas en paralelo sin pisarnos.
4. `docs/PROGRESS.md` — estado actual y próximos pasos.

## Stack

React + Vite + Tailwind + shadcn/ui · FastAPI + Pydantic · SQLAlchemy (SQLite local, Neon Postgres en producción) ·
Gemini (con respaldo Groq/OpenRouter y caché) · Vercel. Detalle en `docs/STACK.md`.

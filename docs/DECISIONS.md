# DECISIONS — Registro de decisiones de diseño

Formato: contexto → decisión → por qué. Agrega nuevas decisiones al final; no reescribas las anteriores (marca como "reemplazada por ADR-N").

## ADR-001 · Backend en Python + FastAPI
Decisión: Python 3.12 + FastAPI + Pydantic v2. Por qué: mejor ecosistema para PDF/LLM, Pydantic valida facturas y reglas, y el OpenAPI automático sirve como contrato con el frontend.

## ADR-002 · Frontend React + Vite + Tailwind + shadcn/ui
Decisión: SPA sin SSR. Por qué: la UI tipo ChatGPT (sidebar, chat, diálogos, tablas) se arma rápido con shadcn; SSR no aporta nada.

## ADR-003 · SQLAlchemy con SQLite local y Neon Postgres en producción
Decisión: un solo código con `DATABASE_URL`. Por qué: desarrollo sin instalar nada y deploy persistente. SQLite no funciona en Vercel (filesystem efímero).

## ADR-004 · LLM: Gemini principal, Groq/OpenRouter de respaldo, caché
Decisión: capa de proveedores intercambiable; orden por variable de entorno; caché por hash del contenido. Por qué: no hay presupuesto de API; free tier de Gemini + créditos de Google AI Pro; demo público necesita sobrevivir a límites de cuota.

## ADR-005 · El LLM nunca decide
Decisión: el LLM extrae y redacta; el motor determinista decide. Por qué: seguridad (un pago indebido descalifica), explicabilidad y pruebas reproducibles.

## ADR-006 · Fail-closed
Decisión: cualquier error o duda → `escalate`. Por qué: preferimos pedir permiso a pagar mal.

## ADR-007 · Decisiones append-only
Decisión: una acción humana crea una nueva `Decision`; no se edita la anterior. Por qué: auditoría y explicabilidad histórica.

## ADR-008 · Dos proyectos Vercel desde un monorepo
Decisión: `frontend/` y `backend/` como proyectos separados con Root Directory propio. Por qué: despliegues independientes y límites claros entre las dos personas.

## ADR-009 · Capas con puertos (ports)
Decisión: `agent`/`engine` dependen de interfaces de repositorio; `db` las implementa. Por qué: permite desarrollo en paralelo y pruebas sin base de datos.

## ADR-010 · Entrada multi-formato
Decisión: PDF con texto, imagen y mensaje de chat/correo en texto. Por qué: lo pide el reto y el dataset propio cubre los tres casos.

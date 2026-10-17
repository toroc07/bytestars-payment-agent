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

## ADR-011 · Dirección visual «Cheque de seguridad»
Decisión: cada decisión se muestra como un cheque (frente con veredicto y monto, talón perforado con las reglas), sobre una paleta fintech sobria (papel cálido, un acento verde intaglio, cifras tabulares). Elegida por Dev A en la ronda de dirección de Impeccable. Por qué: hace visible la explicabilidad (el porqué va pegado a la decisión) y declara lo simulado. Detalle en `DESIGN.md`.

## ADR-012 · El frontend trabaja contra el backend real, sin mocks
Decisión: no hay modo mock ni `contracts/examples/`; en local Vite reenvía `/api` al backend. Sin datos o sin backend, la UI muestra estados vacíos o de error. Por qué: el backend ya existía y el dataset (de Dev C) no está definido; los mocks habrían obligado a inventar datos.

## ADR-013 · Panel de reglas generado desde el JSON Schema del backend
Decisión: los formularios de reglas, beneficiarios y acuerdos se construyen en tiempo de ejecución desde `/openapi.json` (`RuleSet-Input`, `Beneficiary`, `Agreement-Input`). Por qué: el catálogo de reglas aún no está cerrado; así la UI sigue sola los cambios del backend.

## ADR-015 · Traducción de las reglas de Dev C a resultados del motor
Decisión (Dev A): "se rechaza" = `block` (en la UI, "Rechazada por el agente"; reevaluable); "queda para el siguiente periodo" = `escalate` (sin estado "programada"); verificación de proveedores y sanciones = marcas en el beneficiario (`verified`, `sanctioned`) y `sanctioned_countries` en el `RuleSet`, sin consultar listas reales. Por qué: mantiene tres resultados simples y seguros (nada se paga solo fuera de reglas) y respeta que cumplimiento e identidad están fuera del alcance del reto. Catálogo en `DECISION_ENGINE.md`.

## ADR-014 · Primitivos de UI propios sobre Radix en lugar del CLI de shadcn
Decisión: los componentes de `src/components/ui` se escribieron a mano con `radix-ui` siguiendo el patrón de shadcn. Por qué: el tema es propio (no el de shadcn) y las versiones nuevas del stack (Vite 8, TS 6) hacían innecesario el paso por el CLI.

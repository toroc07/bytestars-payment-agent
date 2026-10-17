# STACK — Herramientas por apartado

Decisiones tomadas (ver justificación en `docs/DECISIONS.md`). Cualquier dependencia nueva se anota aquí.

| Apartado | Herramienta | Notas |
|---|---|---|
| **Frontend** | React + Vite + TypeScript | SPA; sin SSR (no aporta aquí) |
| UI | Tailwind CSS + shadcn/ui | sidebar, dialog/sheet, tabla, badge, form ya hechos |
| Datos del servidor | TanStack Query | caché y estados de carga |
| Routing | React Router | `/` chat, `/log` registro |
| Tipos API | openapi-typescript | genera tipos desde `contracts/openapi.json` |
| Mocks | MSW (o fixtures directos) | alimentados por `contracts/examples/` |
| Tests UI | Vitest + Testing Library | Playwright opcional para el demo |
| **Backend** | Python 3.12 + FastAPI | rutas sync (`def`), OpenAPI automático |
| Validación/contrato | Pydantic v2 | fuente de verdad del contrato de datos |
| Config | pydantic-settings | variables de entorno |
| **Base de datos** | SQLAlchemy 2 + Alembic | SQLite en local, **Neon Postgres** en producción |
| **Motor de decisiones** | Python puro | sin dependencias externas; tests con pytest + hypothesis |
| **Agente / LLM** | `google-genai` (Gemini, principal) | respaldo: Groq / OpenRouter (texto); caché por hash |
| Extracción de PDF | pdfplumber (+ Gemini multimodal) | texto del PDF y/o el PDF completo al modelo |
| Imágenes | Gemini multimodal | facturas en foto/imagen |
| **Generación de dataset** | reportlab + Pillow | PDFs e imágenes simulados |
| **Tests backend** | pytest, hypothesis | invariantes de seguridad con property tests |
| **Calidad** | ruff (Python) · eslint + prettier (front) | |
| **Deploy** | Vercel (2 proyectos) + Neon | ver `docs/DEPLOY.md` |
| **Gestión de entorno** | `venv` + pip (o `uv`) · npm | |

## LLM: política
- Proveedor principal: **Gemini** vía key de AI Studio (free tier + créditos del programa de desarrolladores de Google AI Pro, a confirmar por quien tiene la suscripción).
- Orden configurable por variable de entorno (`LLM_PROVIDER_ORDER`). Si un proveedor falla o se agota la cuota, pasa al siguiente y por último a la **caché**.
- El free tier puede usar los datos para entrenar: **solo datos ficticios**.
- Confirmar el nombre vigente del modelo gratuito en AI Studio (los límites cambian con frecuencia).

## Variables de entorno
Backend: `APP_ENV`, `DATABASE_URL`, `CORS_ORIGINS`, `MAX_UPLOAD_MB`, `LLM_PROVIDER_ORDER`, `LLM_CACHE`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`.
Frontend: `VITE_API_URL`, `VITE_USE_MOCKS`.
Cada carpeta tendrá su `.env.example` (sin valores reales). Nunca se suben los `.env`.

## Herramientas de desarrollo disponibles al equipo
Claude Code, Google AI Pro (Gemini / AI Studio) y ChatGPT Go. Ninguno de los tres incluye por sí mismo créditos de API: por eso el LLM del producto sale del free tier / créditos de Google.

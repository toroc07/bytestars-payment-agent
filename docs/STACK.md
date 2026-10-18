# STACK — Herramientas por apartado

Decisiones tomadas (ver justificación en `docs/DECISIONS.md`). Cualquier dependencia nueva se anota aquí.

| Apartado | Herramienta | Notas |
|---|---|---|
| **Frontend** | React 19 + Vite 8 + TypeScript 6 | SPA; sin SSR (no aporta aquí) |
| UI | Tailwind CSS 4 + `radix-ui` (primitivos escritos al estilo shadcn en `src/components/ui`) | tema en `src/index.css`; sistema visual en `DESIGN.md` |
| Iconos / fuentes | lucide-react · Geist y Geist Mono (`@fontsource-variable`) | fuentes autohospedadas |
| Datos del servidor | TanStack Query 5 | caché, estados de carga y error |
| Routing | React Router 8 | `/` chat, `/c/:id` conversación, `/registro` registro |
| Tipos API | openapi-typescript 7 (vía `npx`, script `npm run gen:api`) | no se instala: pide TypeScript 5 |
| Lint | oxlint | viene con la plantilla de Vite |
| Mocks | ninguno | el frontend usa el backend local real (ADR-012) |
| Tests UI | Vitest + Testing Library (pendiente) · Playwright MCP para revisar en navegador | |
| **Backend** | Python 3.12 + FastAPI | rutas sync (`def`), OpenAPI automático |
| Validación/contrato | Pydantic v2 | fuente de verdad del contrato de datos |
| Config | pydantic-settings | variables de entorno |
| **Base de datos** | SQLAlchemy 2 + Alembic | SQLite en local, **Neon Postgres** en producción |
| **Motor de decisiones** | Python puro | sin dependencias externas; tests con pytest + hypothesis |
| **Agente / LLM** | `google-genai` (Gemini, principal) | respaldo: Groq / OpenRouter (texto); caché por hash |
| Extracción de PDF | pdfplumber (+ Gemini multimodal) | texto del PDF y/o el PDF completo al modelo |
| Imágenes | Gemini multimodal | facturas en foto/imagen |
| **Generación de dataset** | _a decidir por Dev C_ | PDFs, imágenes y textos simulados |
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
Backend: `APP_ENV`, `DATABASE_URL`, `CORS_ORIGINS`, `MAX_UPLOAD_MB`, `LLM_PROVIDER_ORDER`, `LLM_CACHE`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `ADMIN_TOKEN`.
Frontend: `VITE_API_URL` (producción) y `VITE_DEV_BACKEND` (proxy local).
Cada carpeta tendrá su `.env.example` (sin valores reales). Nunca se suben los `.env`.

## Herramientas de desarrollo disponibles al equipo
Claude Code, Google AI Pro (Gemini / AI Studio) y ChatGPT Go. Ninguno de los tres incluye por sí mismo créditos de API: por eso el LLM del producto sale del free tier / créditos de Google.

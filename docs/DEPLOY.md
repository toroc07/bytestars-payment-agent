# DEPLOY — Vercel + Neon

Objetivo: una URL pública para que los participantes del hackathon prueben la demo.

## Topología
Responsables: **Dev A** los proyectos de Vercel; **Dev B** la base de datos en Neon.

Un solo repositorio de GitHub → **dos proyectos Vercel** con *Root Directory* distinto:

| Proyecto | Root Directory | Contenido |
|---|---|---|
| `payments-agent-web` | `frontend` | SPA Vite/React |
| `payments-agent-api` | `backend` | FastAPI (Python) |

Base de datos: **Neon Postgres** (integración con Vercel). **SQLite no sirve en Vercel**: el filesystem es efímero y de solo lectura, así que las decisiones no se guardarían.

## Variables de entorno
| Proyecto | Variable | Valor |
|---|---|---|
| web | `VITE_API_URL` | URL pública del proyecto api |
| api | `DATABASE_URL` | cadena de Neon (la inyecta la integración) |
| api | `CORS_ORIGINS` | URL pública del proyecto web |
| api | `GEMINI_API_KEY`, `GEMINI_MODEL` | key de AI Studio y modelos en orden: `gemini-3.8-flash,gemini-3.5-flash,gemini-3.5-flash-lite` |
| api | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | respaldo cuando Gemini no tiene cuota: key gratuita de openrouter.ai; modelos con visión, p. ej. `google/gemma-4-31b-it:free,nvidia/nemotron-3.5-super-vl:free` |
| api | `GROQ_API_KEY`, `GROQ_MODEL` | respaldo rápido para texto (chats, correos, PDF con texto): `openai/gpt-oss-120b,qwen/qwen3.8-27b` |
| api | `LLM_PROVIDER_ORDER`, `LLM_CACHE` | `gemini,groq,openrouter`, `true` |
| api | `APP_ENV` | `production` |
| api | `ADMIN_TOKEN` | clave larga y aleatoria para sembrar/reiniciar la demo (se escribe en Configuración → Demo, o en el encabezado `X-Admin-Token`). Sin ella, `/api/dev/*` responde 403 en producción |

Las keys viven **solo** en las variables de entorno de Vercel. Nunca en el repo ni en el frontend.

## Limitaciones a tener presentes
- El cuerpo de una petición a una función serverless en Vercel está limitado a ~4.5 MB → `MAX_UPLOAD_MB=4`.
- Las llamadas al LLM pueden tardar varios segundos (leer una imagen con Gemini tomó entre 4 y 40 s en las pruebas): el límite del plan Hobby es 300 s y está configurado en `backend/vercel.json`.
- Neon "duerme" y la primera consulta tras inactividad es más lenta (cold start).
- Memoria local de las funciones no se comparte entre instancias: cualquier estado (rate limit, caché, sesiones) debe ir en la base de datos o en reglas del firewall de Vercel.

## Protecciones de la demo pública
- Límite de tamaño y tipos de archivo permitidos.
- Rate limit por IP (firewall de Vercel o contador en BD).
- Caché de lecturas del LLM en la tabla `llm_cache` (Neon): una factura ya leída no vuelve a gastar cuota, en ninguna instancia, y la caché no se borra al reiniciar la demo. Para precargarla, basta con pasar el dataset una vez por la URL pública (o con `python -m scripts.evaluate_dataset` apuntando a Neon).
- Límite en `POST /api/conversations/{id}/messages`: 120 envíos cada 10 minutos por IP (en memoria de cada instancia). Para un límite común a todas las instancias, crear en Vercel → Firewall una regla de *rate limit* sobre esa ruta.
- Endpoint de reseteo del demo (`/api/dev/reset`) con rate limit.
- Solo datos ficticios (el free tier de Gemini puede usar los datos para entrenar).
- Verificar en AI Studio los límites vigentes del free tier antes del día de la demo, y tener la caché precargada con el dataset como plan B.

## Configuración del backend para Vercel (ya en el repo)
- **Punto de entrada:** Vercel detecta FastAPI sin configuración en `backend/app/main.py`. No hay carpeta `api/` ni reescrituras.
- **Dependencias:** solo `backend/requirements.txt`. Python 3.12 por `backend/.python-version`. **No debe haber `pyproject.toml` ni `uv.lock` en `backend/`:** si hay un `pyproject.toml`, Vercel lo prefiere y corre `uv lock`, que falla sin una tabla `[project]`. La configuración de ruff está en `ruff.toml` y la de pytest en `pytest.ini`.
- **Build:** `buildCommand` en `backend/vercel.json` ejecuta `backend/scripts/vercel_build.py`, que copia `dataset/company.json` a `backend/seed_data/` (ignorado por git), porque solo se despliega `backend/`. Si no encuentra el archivo, **el build falla**: activar en el proyecto *Settings → Build and Deployment → Root Directory → "Include files outside the root directory in the Build Step"*.
- **Función:** `backend/vercel.json` fija `maxDuration` en 300 s, el máximo del plan Hobby (una imagen con Gemini tardó 49 s en la primera prueba en Vercel), y deja fuera del paquete los tests.
- **Base de datos:** la cadena de Neon (`postgresql://...`) se convierte a `postgresql+psycopg2://` en `app/db/session.py`, porque SQLAlchemy 2.1 usaría `psycopg` 3, que no está instalado. Probado contra Neon (Postgres 18) con el flujo completo. Sin `DATABASE_URL`, el backend usa SQLite en `/tmp` (la demo arranca, pero se pierde en cada instancia nueva). Con Neon, las tablas (incluida `llm_cache`) se crean solas al arrancar.
- **Reinicio seguro:** `/api/dev/reset` responde 503 y no borra nada si no encuentra `company.json`.

## Checklist de despliegue
**Proyecto api** (Dev A)
1. Vercel → *Add New Project* → importar el repo → *Root Directory* = `backend` (framework: FastAPI, lo detecta solo) y activar "Include files outside the root directory".
2. Variables de entorno (Production y Preview): `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.8-flash,gemini-3.5-flash,gemini-3.5-flash-lite`, `APP_ENV=production`, `LLM_PROVIDER_ORDER=gemini,groq,openrouter`, `LLM_CACHE=true`, `CORS_ORIGINS` (la URL del web; mientras no exista, cualquier valor) y `DATABASE_URL` cuando Dev B la tenga.
3. Desplegar. Comprobar `https://<api>/health` → `{"status":"ok"}` y `https://<api>/openapi.json`.
4. Sembrar: `curl -X POST https://<api>/api/dev/seed -H "X-Admin-Token: <ADMIN_TOKEN>"` (o Configuración → Demo → escribir la clave → Reiniciar desde el web).

**Proyecto web** (Dev A)
5. *Add New Project* → mismo repo → *Root Directory* = `frontend` (framework: Vite). Variable `VITE_API_URL=https://<api>` (sin `/` final). Desplegar.
6. Volver al api: `CORS_ORIGINS=https://<web>` (sin `/` final; varias separadas por coma) → *Redeploy*.

**Base de datos** (Dev B)
7. Neon → copiar la cadena **con pooling** (host con `-pooler`) → `DATABASE_URL` en el api → *Redeploy* → paso 4 de nuevo (la base nueva está vacía).

**Prueba final** (Dev A)
8. Desde la URL del web: subir el dataset en dos lotes (001–050 y 051–100). Así queda precargada la caché de lecturas en Neon para el día de la demo.
9. Opcional: Vercel → *Firewall* → regla de *rate limit* para `POST /api/conversations/*/messages`.

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
| api | `GROQ_API_KEY`, `OPENROUTER_API_KEY` | respaldos (opcionales) |
| api | `LLM_PROVIDER_ORDER`, `LLM_CACHE` | `gemini,groq,openrouter`, `true` |
| api | `APP_ENV` | `production` |

Las keys viven **solo** en las variables de entorno de Vercel. Nunca en el repo ni en el frontend.

## Limitaciones a tener presentes
- El cuerpo de una petición a una función serverless en Vercel está limitado a ~4.5 MB → `MAX_UPLOAD_MB=4`.
- Las llamadas al LLM pueden tardar varios segundos (leer una imagen con Gemini tomó entre 4 y 40 s en las pruebas): verificar el tiempo máximo de ejecución de la función en el plan y, si hace falta, subir `maxDuration` en `backend/vercel.json`.
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
- **Punto de entrada:** Vercel detecta FastAPI sin configuración en `backend/app/main.py`; `backend/pyproject.toml` lo fija con `[tool.vercel] entrypoint = "app.main:app"`. No hay carpeta `api/` ni reescrituras.
- **Dependencias:** `backend/requirements.txt`. Python 3.12 por `backend/.python-version`. No hay `uv.lock` (el anterior estaba vacío y pedía 3.13).
- **Build:** `backend/scripts/vercel_build.py` copia `dataset/company.json` a `backend/seed_data/` (ignorado por git), porque solo se despliega `backend/`. Si no encuentra el archivo, **el build falla**: activar en el proyecto *Settings → Build and Deployment → Root Directory → "Include files outside the root directory in the Build Step"*.
- **Función:** `backend/vercel.json` sube `maxDuration` a 60 s (leer una imagen con Gemini tomó hasta 40 s) y deja fuera del paquete los tests.
- **Base de datos:** sin `DATABASE_URL`, el backend usa SQLite en `/tmp` (la demo arranca, pero se pierde en cada instancia nueva). Con Neon, las tablas (incluida `llm_cache`) se crean solas al arrancar.
- **Reinicio seguro:** `/api/dev/reset` responde 503 y no borra nada si no encuentra `company.json`.

## Checklist de despliegue
**Proyecto api** (Dev A)
1. Vercel → *Add New Project* → importar el repo → *Root Directory* = `backend` (framework: FastAPI, lo detecta solo) y activar "Include files outside the root directory".
2. Variables de entorno (Production y Preview): `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.8-flash,gemini-3.5-flash,gemini-3.5-flash-lite`, `APP_ENV=production`, `LLM_PROVIDER_ORDER=gemini,groq,openrouter`, `LLM_CACHE=true`, `CORS_ORIGINS` (la URL del web; mientras no exista, cualquier valor) y `DATABASE_URL` cuando Dev B la tenga.
3. Desplegar. Comprobar `https://<api>/health` → `{"status":"ok"}` y `https://<api>/openapi.json`.
4. Sembrar: `curl -X POST https://<api>/api/dev/seed` (o el botón Configuración → Demo → Reiniciar desde el web).

**Proyecto web** (Dev A)
5. *Add New Project* → mismo repo → *Root Directory* = `frontend` (framework: Vite). Variable `VITE_API_URL=https://<api>` (sin `/` final). Desplegar.
6. Volver al api: `CORS_ORIGINS=https://<web>` (sin `/` final; varias separadas por coma) → *Redeploy*.

**Base de datos** (Dev B)
7. Neon → copiar la cadena **con pooling** (host con `-pooler`) → `DATABASE_URL` en el api → *Redeploy* → paso 4 de nuevo (la base nueva está vacía).

**Prueba final** (Dev A)
8. Desde la URL del web: subir el dataset en dos lotes (001–050 y 051–100). Así queda precargada la caché de lecturas en Neon para el día de la demo.
9. Opcional: Vercel → *Firewall* → regla de *rate limit* para `POST /api/conversations/*/messages`.

# DEPLOY — Vercel + Neon

Objetivo: una URL pública para que los participantes del hackathon prueben la demo.

## Topología
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
| web | `VITE_USE_MOCKS` | `false` |
| api | `DATABASE_URL` | cadena de Neon (la inyecta la integración) |
| api | `CORS_ORIGINS` | URL pública del proyecto web |
| api | `GEMINI_API_KEY`, `GEMINI_MODEL` | key de AI Studio y modelo vigente |
| api | `GROQ_API_KEY`, `OPENROUTER_API_KEY` | respaldos (opcionales) |
| api | `LLM_PROVIDER_ORDER`, `LLM_CACHE` | `gemini,groq,openrouter`, `true` |
| api | `APP_ENV` | `production` |

Las keys viven **solo** en las variables de entorno de Vercel. Nunca en el repo ni en el frontend.

## Limitaciones a tener presentes
- El cuerpo de una petición a una función serverless en Vercel está limitado a ~4.5 MB → `MAX_UPLOAD_MB=4`.
- Las llamadas al LLM pueden tardar varios segundos: verificar el tiempo máximo de ejecución de la función en el plan Hobby.
- Neon "duerme" y la primera consulta tras inactividad es más lenta (cold start).
- Memoria local de las funciones no se comparte entre instancias: cualquier estado (rate limit, caché, sesiones) debe ir en la base de datos o en reglas del firewall de Vercel.

## Protecciones de la demo pública
- Límite de tamaño y tipos de archivo permitidos.
- Rate limit por IP (firewall de Vercel o contador en BD).
- Caché de extracciones por hash del contenido: las facturas del dataset no consumen cuota del LLM.
- Endpoint de reseteo del demo (`/api/dev/reset`) con rate limit.
- Solo datos ficticios (el free tier de Gemini puede usar los datos para entrenar).
- Verificar en AI Studio los límites vigentes del free tier antes del día de la demo, y tener la caché precargada con el dataset como plan B.

## Checklist de despliegue
1. Crear base de datos Neon y conectarla al proyecto api.
2. Crear proyecto api (Root = `backend`), cargar variables, desplegar. Comprobar `/health` y `/openapi.json`.
3. Ejecutar migraciones y seed contra Neon.
4. Crear proyecto web (Root = `frontend`), poner `VITE_API_URL`, desplegar.
5. Actualizar `CORS_ORIGINS` en api con la URL del web y redesplegar.
6. Probar el flujo completo con las facturas del dataset desde la URL pública.
7. Despliegues de preview por PR: usar una rama de Neon o la misma BD con datos ficticios.

> Detalles de configuración de Vercel para FastAPI (punto de entrada y archivo de configuración) deben verificarse con la documentación vigente al momento de desplegar.

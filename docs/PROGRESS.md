# PROGRESS — Estado del proyecto

Cada persona (y agente) edita **solo sus filas**. Estados: `pendiente` · `en curso` · `listo` · `bloqueado`.
Roles confirmados: **Dev A** = frontend + agente + motor de decisiones · **Dev B** = backend (API) + base de datos.
Dev B también ayuda con el motor de decisiones: al repartir tareas del motor, anotar en la columna de responsable quién hace cada regla.

## M0 · Contrato (compartido)
| Tarea | Responsable | Estado | Notas |
|---|---|---|---|
| Revisar y acordar `docs/DATA_MODEL.md` | ambos | pendiente | |
| Revisar y acordar `docs/API_CONTRACT.md` | ambos | pendiente | |
| Implementar modelos Pydantic en `backend/app/schemas/` | Dev B | listo | según `DATA_MODEL.md`, serialización Decimal a String, validaciones de invariantes |
| Definir `backend/app/ports.py` | Dev B | listo | según sección Ports de `DATA_MODEL.md` (Protocol síncronos) |
| Crear JSON de ejemplo en `contracts/examples/` | Dev A | pendiente | lista en `API_CONTRACT.md` |
| Dataset base (`company.json`, `scenarios.json`) | ambos | en curso | `dataset/company.json` creado con Nimbus Labs Inc. |

## Frontend (Dev A)
| Tarea | Estado | Notas |
|---|---|---|
| Inicializar Vite + React + TS + Tailwind + shadcn/ui | pendiente | |
| Layout tipo ChatGPT: sidebar + chat + botón de configuración | pendiente | |
| Cliente API + modo mocks | pendiente | |
| Tarjeta de decisión (resultado + checks expandibles) | pendiente | |
| Panel de configuración (reglas, beneficiarios, acuerdos) | pendiente | |
| Aprobar / rechazar pendientes | pendiente | |
| Vista de registro de decisiones | pendiente | |

## Motor, agente y LLM (Dev A; Dev B ayuda en el motor)
| Tarea | Estado | Notas |
|---|---|---|
| Motor de reglas R01–R10 + tests | pendiente | `DECISION_ENGINE.md`. Responsable por regla: _(por repartir entre Dev A y Dev B)_ |
| Property tests de invariantes | pendiente | |
| Repositorios falsos en memoria para tests | pendiente | |
| Pipeline del agente | pendiente | |
| Proveedor Gemini + extracción PDF/imagen/texto | pendiente | |
| Fallback Groq/OpenRouter + caché | pendiente | |
| Chat de consulta (solo lectura) | pendiente | |
| Script de evaluación del dataset | pendiente | |

## Backend y base de datos (Dev B)
| Tarea | Estado | Notas |
|---|---|---|
| Proyecto FastAPI base + `/health` + CORS | listo | `app/main.py`, lifespan con inicialización DB, config y CORS |
| Modelos SQLAlchemy + migraciones | listo | Modelos en `app/db/models.py` para todas las entidades |
| Repositorios (implementan `ports`) | listo | Repositorios SQL síncronos en `app/db/repositories.py` (Decision append-only) |
| Rutas de la API | listo | Rutas en `app/api/routes/` con validación 409, fail-closed y rate limits |
| Seed y reset con el dataset | listo | `app/db/seed.py` carga empresa, beneficiarios y acuerdos |
| Exportar `contracts/openapi.json` | listo | Exportado vía `scripts/export_openapi.py` (2000 líneas) |

## Dataset (compartido)
| Tarea | Estado | Notas |
|---|---|---|
| Empresa ficticia, beneficiarios, acuerdos | pendiente | |
| Escenarios y resultados esperados | pendiente | |
| Generar facturas PDF / imagen / texto | pendiente | |

## Deploy
| Tarea | Estado | Notas |
|---|---|---|
| Cuenta Neon + proyecto Vercel api/web | pendiente | `DEPLOY.md` |
| Confirmar créditos/free tier de Gemini | pendiente | lo revisa quien tiene Google AI Pro |

## Bloqueos y preguntas abiertas
- _(ninguna todavía)_

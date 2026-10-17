# PROGRESS — Estado del proyecto

Cada persona (y agente) edita **solo sus filas**. Estados: `pendiente` · `en curso` · `listo` · `bloqueado`.
Roles confirmados: **Dev A** = frontend + agente + motor de decisiones · **Dev B** = backend (API) + base de datos.
Dev B también ayuda con el motor de decisiones: al repartir tareas del motor, anotar en la columna de responsable quién hace cada regla.
**Dev C** (tercer integrante) = dataset y reglas de la empresa ficticia (facturas simuladas, resultados esperados). Nada de eso está definido aún.

## M0 · Contrato (compartido)
| Tarea | Responsable | Estado | Notas |
|---|---|---|---|
| Revisar y acordar `docs/DATA_MODEL.md` | ambos | pendiente | |
| Revisar y acordar `docs/API_CONTRACT.md` | ambos | pendiente | |
| Implementar modelos Pydantic en `backend/app/schemas/` | Dev B | listo | según `DATA_MODEL.md`, serialización Decimal a String, validaciones de invariantes |
| Definir `backend/app/ports.py` | Dev B | listo | según sección Ports de `DATA_MODEL.md` (Protocol síncronos) |
| Crear JSON de ejemplo en `contracts/examples/` | Dev A | no aplica | el frontend trabaja contra el backend real (ver `DECISIONS.md` ADR-012) |
| Definir formato del dataset y reglas de la empresa ficticia | Dev C | pendiente | ver `dataset/README.md`; acordar formato con Dev A y Dev B |

## Frontend (Dev A)
| Tarea | Estado | Notas |
|---|---|---|
| Inicializar Vite + React + TS + Tailwind + primitivos Radix (estilo shadcn) | listo | Vite 8, React 19, TS 6, Tailwind 4 |
| Dirección visual y sistema de diseño | listo | «Cheque de seguridad»; ver `DESIGN.md` y `PRODUCT.md` |
| Layout tipo ChatGPT: sidebar + chat + botón de configuración | listo | sidebar con filtros por estado; panel móvil |
| Cliente API contra backend real (proxy de Vite) | listo | tipos generados de `contracts/openapi.json` (`npm run gen:api`) |
| Cheque de decisión (veredicto, monto, talón de reglas, endoso humano) | listo | |
| Panel de configuración (reglas, beneficiarios, acuerdos) | listo | formularios generados desde `/openapi.json`; sigue los cambios de reglas solo |
| Aprobar / rechazar pendientes | listo | probado contra el backend local |
| Vista de registro de decisiones + exportar CSV | listo | |
| Entradas de correo y texto (`.eml`, `.txt`) + lotes de hasta 50 archivos | listo | los `.eml` se abren en el navegador: cuerpo decodificado como texto + PDF adjunto como archivo; probado con los 25 correos del dataset |
| Reevaluar facturas frenadas o pendientes | listo | cheque nuevo debajo del anterior |
| Editar beneficiarios y acuerdos, confirmar al quitar, selector de beneficiario | listo | |
| Pestaña Demo: reiniciar la demo | listo | usa `/api/dev/reset` con confirmación |
| `vercel.json` (rutas del SPA) y carga diferida (registro, configuración) | listo | bundle principal 471 KB |
| Tests unitarios (Vitest) | listo | 23 tests de lógica pura (`npm test`) |
| Revisión de diseño (`/impeccable critique`) y correcciones | listo | 25/40 inicial; corregidos los 5 problemas: aprobación con evidencia, motivo obligatorio y bloqueada sin beneficiario/monto; reglas agrupadas con resumen de cambios y aviso al cerrar; móvil sin desbordes; vocabulario único y contraste AA; montos y búsqueda en el sidebar, registro desplegable. Informe en `.impeccable/critique/` |
| Repetir `/impeccable critique` con decisiones reales | pendiente | cuando el pipeline del agente devuelva pagar/frenar/escalar con datos |

## Motor, agente y LLM (Dev A; Dev B ayuda en el motor)
| Tarea | Estado | Notas |
|---|---|---|
| Definir catálogo de reglas y sus campos en `RuleSet` | listo | reglas de Dev C → R01–R11 en `DECISION_ENGINE.md`; campos propuestos en `DATA_MODEL.md` (ADR-015) |
| Implementar motor de reglas + tests | pendiente | responsable por regla: _(por repartir entre Dev A y Dev B)_ |
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
| Modelos SQLAlchemy + migraciones | listo | Modelos en `app/db/models.py` actualizados con reglas de Dev C |
| Repositorios (implementan `ports`) | listo | `app/db/repositories.py` con historial por proveedor y gasto en ventana móvil |
| Rutas de la API | listo | Rutas en `app/api/routes/` con soporte multipart simultáneo, 409 en reevaluación indebida y rate limits solo en demo |
| Seed y reset con el dataset | listo | `dataset/company.json` y `app/db/seed.py` sincronizados con nuevas políticas y atributos |
| Exportar `contracts/openapi.json` | listo | Exportado y sincronizado con tipos frontend (`gen:api`) |

## Dataset y reglas de la empresa ficticia (Dev C)
Tareas por definir por Dev C (empresa ficticia, reglas, beneficiarios, acuerdos, facturas simuladas, resultados esperados). Agregar sus filas aquí.
| Tarea | Estado | Notas |
|---|---|---|
| Dataset de 25 correos `.eml` y facturas | listo | Estructura en `dataset/` |
| Políticas de la empresa (R01–R11) | listo | Definidas en `DECISION_ENGINE.md` y sincronizadas en backend |

## Deploy
| Tarea | Estado | Notas |
|---|---|---|
| Cuenta Neon + proyecto Vercel api/web | pendiente | `DEPLOY.md` |
| Confirmar créditos/free tier de Gemini | pendiente | lo revisa quien tiene Google AI Pro |

## Bloqueos y preguntas abiertas
- ~~(Dev A → Dev B) Implementar en el backend los campos ✱ del `RuleSet` y del `Beneficiary` propuestos en `docs/DATA_MODEL.md` (reglas de Dev C) y regenerar `contracts/openapi.json`.~~ **Completado.**
- ~~(Dev A → Dev B) Actualizar `dataset/company.json` con los valores de Dev C.~~ **Completado.**
- ~~(Dev A → Dev B) `POST /api/invoices/{id}/reevaluate` no restringe el estado.~~ **Resuelto: devuelve 409 en facturas fuera de `blocked` o `pending_approval`.**
- (Dev A → Dev B) El backend devuelve fechas sin zona horaria (`2026-10-17T03:07:07`, SQLite pierde el offset). El frontend las trata como UTC, pero lo correcto es serializarlas con `Z` / offset.
- (Dev A → Dev B) Sugerencia: agregar `title`/`description` en español a los `Field` del `RuleSet` para que el panel de reglas no dependa del diccionario de etiquetas del frontend.
- (Dev A → Dev C) Formatos que el frontend sabe enviar: **PDF, PNG, JPG** (como archivo) y **`.eml`, `.txt`, `.md`** (se leen y se mandan como texto). Otros formatos (`.webp`, `.heic`, `.msg`, `.docx`) se rechazan; máximo 4 MB por archivo. Las 4 carpetas del dataset se pueden cargar como lote desde la pantalla inicial (hasta 50 archivos por vez).


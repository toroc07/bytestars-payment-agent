# PROGRESS — Estado del proyecto

Cada persona (y agente) edita **solo sus filas**. Estados: `pendiente` · `en curso` · `listo` · `bloqueado`.
Roles confirmados: **Dev A** = frontend + agente + motor de decisiones · **Dev B** = backend (API) + base de datos.
Dev B también ayuda con el motor de decisiones: al repartir tareas del motor, anotar en la columna de responsable quién hace cada regla.
**Dev C** (tercer integrante) = dataset y reglas de la empresa ficticia (facturas simuladas, resultados esperados). Nada de eso está definido aún.

## M0 · Contrato (compartido)
| Tarea | Responsable | Estado | Notas |
|---|---|---|---|
| Revisar y acordar `docs/DATA_MODEL.md` | ambos | listo | acordado y sincronizado con schemas y base de datos |
| Revisar y acordar `docs/API_CONTRACT.md` | ambos | listo | OpenAPI y endpoints validados |
| Implementar modelos Pydantic en `backend/app/schemas/` | Dev B | listo | según `DATA_MODEL.md`, serialización Decimal a String, validaciones de invariantes |
| Definir `backend/app/ports.py` | Dev B | listo | según sección Ports de `DATA_MODEL.md` (Protocol síncronos) |
| Crear JSON de ejemplo en `contracts/examples/` | Dev A | no aplica | el frontend trabaja contra el backend real (ver `DECISIONS.md` ADR-012) |
| Definir formato del dataset y reglas de la empresa ficticia | Dev C | listo | `dataset/README.md`, `company.json` y `expected.json` (propuesta de Dev A, ADR-018; Dev C valida) |

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
| Tests unitarios (Vitest) | listo | 56 tests de lógica pura (`npm test`) |
| Revisión de diseño (`/impeccable critique`) y correcciones | listo | 25/40 inicial; corregidos los 5 problemas: aprobación con evidencia, motivo obligatorio y bloqueada sin beneficiario/monto; reglas agrupadas con resumen de cambios y aviso al cerrar; móvil sin desbordes; vocabulario único y contraste AA; montos y búsqueda en el sidebar, registro desplegable. Informe en `.impeccable/critique/` |
| Repetir `/impeccable critique` con decisiones reales | pendiente | la revisión de diseño no se ha repetido; ahora hay decisiones reales para hacerla |

## Motor, agente y LLM (Dev A; Dev B ayuda en el motor)
| Tarea | Estado | Notas |
|---|---|---|
| Definir catálogo de reglas y sus campos en `RuleSet` | listo | reglas de Dev C → R01–R11 en `DECISION_ENGINE.md`; campos propuestos en `DATA_MODEL.md` (ADR-015) |
| Implementar motor de reglas + tests | listo | Dev A: R01–R11 en `backend/app/engine/`, fail-closed (error interno → R00 + escalar); R02 detecta el mismo cobro reenviado con otro número y R11 compara el monto con lo acordado (ADR-017) |
| Property tests de invariantes | listo | hypothesis: nunca `pay` con una regla fallida (I1), determinismo (I2), sin datos esenciales nunca `pay` (I4) |
| Repositorios falsos en memoria para tests | listo | `tests/agent/fakes.py` (repos + proveedor LLM falso); `tests/conftest.py` impide llamar a un LLM real en los tests |
| Pipeline del agente | listo | `app/agent/pipeline.py`: registrar → extraer → contexto → motor → explicar → guardar; cualquier error escala la misma factura (R00) |
| Proveedor Gemini + extracción PDF/imagen/texto | listo | `app/llm/gemini.py` con varios modelos en cadena (ADR-019); evaluación con Gemini: **100/100 iguales a `expected.json`, autonomía 80 %, 0 trampas pagadas, 0 datos mal leídos** (75 por lector local, 25 imágenes con Gemini) |
| Fallback Groq/OpenRouter + caché | listo | `app/llm/openai_compat.py` (solo texto) y caché por hash en memoria + carpeta temporal; lector local sin red de respaldo (ADR-019) |
| Chat de consulta (solo lectura) | pendiente | hoy un texto que no es factura recibe un mensaje de ayuda; falta responder preguntas sobre decisiones guardadas |
| Script de evaluación del dataset | listo | `python -m scripts.evaluate_dataset [--offline]`: pasa las 100 facturas por el pipeline real en orden y compara con `expected.json` (coincidencia, autonomía, trampas pagadas, datos mal leídos); sale con código 1 si se paga una trampa |

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
| Montos del dataset en USD | listo | Dev A, a pedido del equipo: las 100 facturas regeneradas con el mismo contenido (ADR-018) |
| Empresa, allowlist y reglas en `company.json` | listo | Dev A: Distribuciones Andinas S.A.S. con 8 proveedores inferidos del dataset; **Dev C valida** |
| Resultados esperados por factura (`expected.json`) | listo | Dev A: 62 pagar · 18 frenar · 20 escalar; **Dev C valida** las trampas y el criterio de R11 (ADR-017) |
| Casos de monto alto (más de US$5.000 o US$10.000) | pendiente | ninguna factura del set supera el umbral de aprobación ni el límite por pago; faltan casos para R07 y R08 |

## Deploy
| Tarea | Estado | Notas |
|---|---|---|
| Cuenta Neon + proyecto Vercel api/web | pendiente | `DEPLOY.md` |
| Confirmar créditos/free tier de Gemini | pendiente | lo revisa quien tiene Google AI Pro |

## Bloqueos y preguntas abiertas
- ~~(Dev A → Dev B) Implementar en el backend los campos ✱ del `RuleSet` y del `Beneficiary` propuestos en `docs/DATA_MODEL.md` (reglas de Dev C) y regenerar `contracts/openapi.json`.~~ **Completado.**
- ~~(Dev A → Dev B) Actualizar `dataset/company.json` con los valores de Dev C.~~ **Completado.**
- ~~(Dev A → Dev B) `POST /api/invoices/{id}/reevaluate` no restringe el estado.~~ **Resuelto: devuelve 409 en facturas fuera de `blocked` o `pending_approval`.**
- ~~(Dev A → Dev B) `dataset/company.json` y los defaults no tenían los valores de Dev C.~~ **Corregido por Dev A** (schemas, seed por defecto en `repositories.py` y `company.json`).
- ~~(Dev A → Dev B) `Beneficiary.verified` tenía default `true`.~~ **Corregido por Dev A:** default `false` en schema y modelo.
- ~~(Dev A → Dev B) Fechas sin zona horaria.~~ **Corregido por Dev A:** `UtcDatetime` en schemas serializa con offset UTC.
- (Dev A → Dev B) `period` (weekly/monthly) convive con `period_days` y el motor solo usa `period_days`. No se quitó porque es columna NOT NULL y hace falta migración; decidir si se borra.
- (Dev A → Dev B) `POST /api/invoices/{id}/reevaluate` usa `R01` como id del check de error; el motor usa `R00 ENGINE_ERROR` para fallos internos. Conviene unificar.
- (Dev A → Dev C) Validar `dataset/company.json` y `dataset/expected.json` (allowlist inferida, trampas y criterio de R11 en ADR-017), y agregar facturas por encima de US$5.000 y US$10.000 para cubrir R07 y R08.
- (Dev A → Dev B) Sugerencia: agregar `title`/`description` en español a los `Field` del `RuleSet` para que el panel de reglas no dependa del diccionario de etiquetas del frontend.
- (Dev A → Dev C) Formatos que el frontend sabe enviar: **PDF, PNG, JPG** (como archivo) y **`.eml`, `.txt`, `.md`** (se leen y se mandan como texto). Otros formatos (`.webp`, `.heic`, `.msg`, `.docx`) se rechazan; máximo 4 MB por archivo. Las 4 carpetas del dataset se pueden cargar como lote desde la pantalla inicial (hasta 50 archivos por vez).


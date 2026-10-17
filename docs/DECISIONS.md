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

## ADR-016 · Incorporación de políticas de Dev C, soporte .eml simultáneo y guardia de reevaluación
Decisión (Dev B con Dev A y Dev C):
1. **Reglas y beneficiarios ampliados:** `RuleSet` incorpora `period_days` (ventana móvil), `per_vendor_period_limit`, `require_verified_beneficiary`, `block_sanctioned`, `sanctioned_countries`, `review_on_vendor_changes`, `required_fields` y `retention_years`. `Beneficiary` agrega `legal_name`, `verified`, `sanctioned` y `owners`.
2. **Consultas de historial por proveedor:** `InvoiceRepository.get_last_paid_for_vendor` para detectar cambios bancarios o de monto, y `DecisionRepository.sum_spent_between` con filtro de proveedor para control del límite por proveedor en el periodo.
3. **Entrada simultánea texto + adjunto:** `POST /api/conversations/{id}/messages` persiste `raw_text` (cuerpo/encabezados de correo) y `source_filename` (PDF/imagen adjunto) a la vez en la factura.
4. **Protección de reevaluación:** `POST /api/invoices/{id}/reevaluate` devuelve 409 Conflict si la factura está en estado distinto a `blocked` o `pending_approval` para no sobreescribir decisiones humanas (pagadas, aprobadas o rechazadas).
5. **Rate limiting:** Se mantiene exclusivamente en `/api/dev/*` para permitir la ejecución por lotes (`BatchRun` de hasta 50 facturas) en `/api/conversations` e `/api/invoices`.

## ADR-017 · R11 compara el monto con lo acordado, no con el último pago
Decisión (Dev A): la parte de monto de R11 escala solo si el monto se aleja del acuerdo del proveedor más que `agreement_tolerance_pct`. La cuenta bancaria sí se sigue comparando con el registro y con el último pago, y el NIT con el registro. Además, R02 trata como duplicado el mismo cobro reenviado con otro número (mismo proveedor, orden de compra, monto y moneda). Por qué: los proveedores facturan montos distintos cada vez. Con la lectura literal ("si el monto cambia respecto al último pago, revisión"), el dataset daba 8 pagos y 74 escaladas de 100. Con esta lectura da 62 pagos y ninguna trampa pagada. Para volver a la lectura literal basta con restaurar la comparación de monto contra `last_vendor_invoice` en `r11_vendor_changes`. **Pendiente de validar con Dev C.**

## ADR-023 · Backend en Vercel sin reescrituras, con el seed copiado en el build
Decisión (Dev A, responsable del deploy en Vercel): se usa la detección de FastAPI de Vercel (`app/main.py`, fijada en `pyproject.toml`) en lugar de `api/index.py` + reescritura a todas las rutas, que se quitaron. Las dependencias salen solo de `requirements.txt` con Python 3.12 (`.python-version`): se borró `uv.lock`, que estaba vacío y pedía 3.13. Un paso de build copia `dataset/company.json` dentro de `backend/`, porque solo esa carpeta se despliega, y `/api/dev/reset` no borra nada si no lo encuentra. Sin `DATABASE_URL`, el backend usa SQLite en `/tmp`. Por qué: con la configuración anterior, el reinicio de la demo en producción habría borrado la empresa sin poder volver a sembrarla, y el `uv.lock` podía hacer que Vercel instalara dependencias vacías. Pasos en `DEPLOY.md`.

## ADR-022 · Caché de lecturas en la base de datos, límite por IP y reevaluación desde el agente
Decisión (Dev A, con cambios en zonas de Dev B pedidos por el equipo):
1. **Caché en la base:** las respuestas del LLM se guardan en `llm_cache` (clave = sha256 de la petición) y no se borran al reiniciar la demo. La carpeta temporal y la memoria siguen como capas rápidas. Por qué: en Vercel el disco es temporal y por instancia, y la cuota gratuita (20 lecturas al día por modelo) se agotaría releyendo las mismas facturas.
2. **Límite por IP** en el envío de mensajes (120 cada 10 minutos), en memoria. Por qué: cualquiera con la URL podía gastar toda la cuota. Para un límite común a todas las instancias, la regla del Firewall de Vercel (`DEPLOY.md`).
3. **Reevaluar** (`POST /api/invoices/{id}/reevaluate`) llama a `agent.pipeline.reevaluate`, que usa el mismo `build_context` que el chat, guarda una explicación y marca los errores internos como `R00`. Por qué: había dos armados del contexto que ya diferían (el acuerdo vigente y el id del error).
4. **Lo que ve quien aprueba:** R11 muestra los valores lado a lado (cuenta pedida contra cuenta registrada o del último pago, NIT contra NIT registrado). El cheque solo agrega a sus notas cómo se leyó la factura; el veredicto, las reglas y el aviso de pago simulado ya están en el cheque, y el veredicto puede cambiar con el endoso. El registro ya no muestra `period_budget` como «presupuesto que rechaza», porque ninguna regla lo aplica.

## ADR-021 · El símbolo "$" solo no dice la moneda; sin moneda, se escala
Decisión (Dev A): un monto con "$" a secas se lee como COP solo si el texto dice "pesos" o "COP", y como USD solo si dice "USD", "US$" o "dólares". Si el texto no lo dice, la moneda queda vacía, y R06 ahora **falla y escala** cuando falta la moneda (antes quedaba "sin aplicar"). Por qué: en Colombia "$4.500" son pesos (unos US$1), y leerlo como US$4.500 pagaría miles de veces el valor. Además, sin moneda no hay monto en USD, y los límites R07–R10 quedaban sin comprobar, así que una factura completa sin moneda se pagaba. Test de regresión en `tests/engine/test_engine.py` y `tests/agent/test_pipeline.py`.

## ADR-020 · Mensajes de commit en español
Decisión (Dev A, para todo el equipo): los mensajes de commit se escriben en español, conservando el prefijo de Conventional Commits (`feat`, `fix`, `docs`, `test`, `chore`…). El código, los nombres y los endpoints siguen en inglés. Por qué: el equipo escribe y revisa en español, y así el historial se lee igual que la documentación. Actualizados `AGENTS.md` §5 y `docs/WORKFLOW.md`.

## ADR-019 · Lector local primero para facturas con texto; Gemini para imágenes y casos dudosos
Decisión (Dev A, con aprobación del equipo):
1. Si la factura trae texto (chat, cuerpo de correo o PDF con capa de texto) y no trae imagen, `agent/local_reader.py` la lee con patrones fijos de facturas colombianas. Si encuentra número, proveedor, NIT, cuenta, monto, moneda, fecha y concepto, esa lectura se usa y **no se llama al LLM**.
2. Si falta algo, o si es una imagen o un PDF escaneado, se llama a la cadena de LLM. Un PDF con texto se manda como texto.
3. `GEMINI_MODEL` admite varios modelos separados por comas (por defecto `gemini-3.8-flash,gemini-3.5-flash,gemini-3.5-flash-lite`). Cada modelo tiene su propia cuota gratuita, y uno sin cuota diaria se salta durante una hora.
4. Si ningún LLM responde, se usa la lectura local aunque esté incompleta, y el motor escala lo que falte.

Por qué: la cuota gratuita de Gemini es de 20 lecturas al día por modelo y proyecto. Leyendo todo con Gemini, una pasada del dataset gastaría 100 lecturas; así gasta unas 25 (las imágenes). El lector local leyó 72 de las 75 facturas con texto igual que `expected.json` (las otras 3 solo difieren en la orden "No aplica"). No decide nada: el motor valida cada dato igual que si viniera del LLM. Se aparta de "el LLM extrae" de `ARCHITECTURE.md` §3, que ya está actualizado.

## ADR-018 · Dataset en USD, allowlist inferida y resultados esperados
Decisión (Dev A, a pedido del equipo; Dev C valida):
1. **Montos en USD:** las 100 facturas se regeneraron con el mismo contenido y los montos de COP pasados a USD a la tasa ~4.000, con precios unitarios redondeados (menos de 20 → a 1; menos de 100 → a 5; menos de 1.000 → a 10; desde 1.000 → a 100), IVA del 19 % y totales recalculados. Las reglas de Dev C están en USD; así los límites se leen sin conversión.
2. **Allowlist inferida:** `dataset/company.json` lista los 8 proveedores que se repiten con NIT y cuenta coherentes (verificados, no sancionados, país CO). Servicios Logísticos Meridian, Comercializadora Delta Express y la papelería con NIT 901.233.780-5 quedan fuera, porque son las trampas del set. No se inventaron dueños ni acuerdos.
3. **Resultados esperados:** `dataset/expected.json` se calculó con el motor procesando de factura_001 a factura_100 en una sola sesión y se contrastó con una clasificación manual de las trampas. `backend/tests/engine/test_dataset_expected.py` lo vuelve a comprobar en cada corrida de tests.


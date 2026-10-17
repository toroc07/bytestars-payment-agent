# ARCHITECTURE

## 1. Vista general

```
┌──────────────────────┐        HTTPS / JSON          ┌───────────────────────────────────────────┐
│  frontend (React)    │ ───────────────────────────▶ │  backend (FastAPI)                        │
│  chat · sidebar ·    │ ◀─────────────────────────── │                                           │
│  configuración · log │                              │  api/  ──▶  agent/  ──▶  engine/ (puro)   │
└──────────────────────┘                              │             │  └────▶  llm/ (Gemini...)  │
   Vercel proyecto 1                                  │             ▼                             │
                                                      │          ports ◀── db/ (SQLAlchemy)       │
                                                      └───────────────────────────────────────────┘
                                                         Vercel proyecto 2          │
                                                                                    ▼
                                                                       SQLite (local) / Neon (prod)
```

Principio de diseño: **el frontend y el backend solo se hablan a través del contrato** (`docs/API_CONTRACT.md` + `docs/DATA_MODEL.md`).
Dentro del backend, **agente/motor** y **api/db** solo se hablan a través de **ports** (interfaces de repositorios). Así se trabaja en paralelo sin bloquearse.

## 2. Capas del backend y reglas de dependencia

| Capa | Responsabilidad | Puede importar |
|---|---|---|
| `schemas` | Modelos Pydantic del contrato | nada del proyecto |
| `engine` | Reglas y decisión, **función pura** | `schemas` |
| `llm` | Proveedores (extraer, explicar), fallback, caché | `schemas`, `config` |
| `agent` | Orquesta el flujo y el chat | `schemas`, `engine`, `llm`, `ports` |
| `ports` | Interfaces de repositorios | `schemas` |
| `db` | Implementa `ports` con SQLAlchemy | `schemas`, `ports` |
| `api` | Rutas HTTP, DI, validación de entrada | todo lo anterior (es el único que "cablea") |

Prohibido: `engine → llm/db`, `agent → db`, `db → agent/engine`, ciclos.

**Por qué importa:** quien desarrolla `engine`/`agent` puede trabajar con repositorios falsos en memoria (tests) sin esperar a la base de datos; quien desarrolla `db`/`api` puede probar sus rutas sin LLM ni motor real.

## 3. Flujo de una factura (pipeline del agente)

1. **Entrada.** El usuario adjunta un PDF/imagen o pega texto en el chat → `POST` al endpoint de mensajes.
2. **Registro.** `api` guarda la factura con estado `received`.
3. **Extracción.** El documento se convierte en `ExtractedInvoice` (ADR-019). Si trae texto y no trae imagen, el **lector local** (`agent/local_reader.py`) lo lee primero; si encuentra todos los datos clave, no se llama al LLM. Si no, `llm` lo lee: un PDF con capa de texto se manda como texto; las imágenes y los PDF escaneados, como archivo. La cadena es caché por hash del contenido → modelos de Gemini en orden (`GEMINI_MODEL`) → Groq/OpenRouter (solo texto). Si nadie responde, se usa la lectura local aunque esté incompleta; si tampoco hay texto (imagen sin LLM), la factura queda sin datos y el motor la escala. La salida del LLM se valida campo por campo: lo que no tiene forma válida queda vacío.
4. **Contexto (código, sin LLM).** `agent` arma `EvaluationContext`: beneficiario coincidente, acuerdo vigente, facturas previas (duplicados), gasto acumulado del periodo.
5. **Decisión (motor).** `engine.evaluate(extracción, reglas, contexto)` → resultado + lista de chequeos. **Determinista y sin I/O.**
6. **Explicación.** Resumen en español **construido por plantilla desde los chequeos** (siempre). Opcionalmente el LLM lo redacta mejor; el texto del LLM nunca cambia el resultado.
7. **Persistencia.** Se guarda la `Decision` (append-only) y se actualiza el estado de la factura. Se responde al chat con la tarjeta de decisión.
8. **Humano (si escaló).** Botón Aprobar/Rechazar → endpoint de aprobación (identidad + comentario) → se crea **una nueva Decision** con `actor = human`; la anterior no se modifica.

Cualquier excepción en los pasos 3-7 termina en **escalar** (fail-closed), registrando el error en el motivo.

### Chat de consulta
Preguntas como "¿por qué frenaste la factura de Cloudly?" las responde el agente **leyendo decisiones guardadas** (herramientas de solo lectura) y narrándolas. El chat **no tiene herramientas de escritura** que aprueben o modifiquen pagos o reglas.

## 4. Modelo de datos (resumen)
Entidades: `rule_sets` (versionadas), `beneficiaries`, `agreements`, `invoices`, `decisions` (append-only), `conversations`, `messages`.
Campos detallados en `docs/DATA_MODEL.md`.

Notas para la capa `db`:
- Un solo código SQLAlchemy; `DATABASE_URL` decide SQLite (local) o Postgres/Neon (producción).
- Migraciones con Alembic; **solo la persona dueña de `db` crea revisiones** (evita ramas de migración).
- El "gasto del periodo" se calcula sumando `amount_base_currency` de facturas cuyo estado efectivo es `paid` o `approved`.
- Un comando de **seed** carga la empresa ficticia y el dataset (`dataset/`) y otro **resetea** el demo.

## 5. Modelo de seguridad
- **Separación de poderes:** LLM extrae/narra; el motor decide; el humano aprueba excepciones.
- **Fail-closed** y **PAY ⇒ cero chequeos fallidos** (verificado por tests de propiedades).
- **Prompt injection:** el texto de la factura se pasa al LLM como dato dentro de un delimitador y con instrucción explícita de ignorar órdenes; además, aunque el LLM fuera engañado, solo puede alterar los campos extraídos, y el motor los valida contra reglas y acuerdos.
- **Endpoint público (demo):** límite de tamaño de archivo, rate limit, sin secretos en el frontend, solo datos ficticios.
- **Auditoría:** decisiones inmutables con versión de reglas y chequeos.

## 6. Despliegue
Dos proyectos Vercel desde este mismo repo (frontend y backend con *root directory* distinto) + Neon. Detalle en `docs/DEPLOY.md`.

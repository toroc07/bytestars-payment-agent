# llm/ — Proveedores de LLM (Dev A)

Interfaz común para **leer** una factura y devolver JSON. El LLM nunca decide pagar.

| Archivo | Qué hace |
|---|---|
| `base.py` | `LLMRequest` (instrucción, texto, archivo opcional), `Provider`, errores |
| `gemini.py` | Gemini (`GEMINI_API_KEY`, `GEMINI_MODEL`, por defecto `gemini-3.8-flash`; `gemini-2.5-flash` ya no se ofrece a cuentas nuevas): lee texto, PDF e imágenes; respuesta JSON, sin *thinking* (si el modelo no lo admite, lo recuerda y lo usa); timeout de 20 s por llamada; sin cuota por minuto se salta 60 s, sin cuota diaria (o con 404) 1 hora, y si se cuelga o da error de servidor (5xx, conexión cortada) 2 minutos, sin esperar |
| `openai_compat.py` | Groq y OpenRouter (`GROQ_API_KEY`, `OPENROUTER_API_KEY`): solo texto |
| `chain.py` | `LLMChain`: caché por hash de la petición (memoria + carpeta temporal) y luego los proveedores en el orden de `LLM_PROVIDER_ORDER` |
| `__init__.py` | `get_llm()`: arma la cadena desde el entorno |

Si nadie responde, `LLMUnavailable`: el agente usa el lector local (`agent/local_reader.py`) o deja la factura sin datos y el motor la escala.
Los tests usan `tests/agent/fakes.py` (sin red), y `tests/conftest.py` impide llamar a un proveedor real.

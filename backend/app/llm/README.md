# llm/ — Proveedores de LLM (Dev A)

Interfaz común para: (a) **extraer** una factura estructurada desde PDF/imagen/texto y (b) **redactar** explicaciones.
El LLM nunca decide pagar.

Proveedores previstos: Gemini (principal) → Groq / OpenRouter (respaldo, solo texto) → **caché** por hash del contenido.
Orden y claves por variables de entorno (`docs/STACK.md`). Si todo falla, devolver extracción vacía (el motor la escalará).
Para pruebas debe existir un proveedor falso que no use red.

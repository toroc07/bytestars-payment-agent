---
version: 1
slug: "frontend-src-app-tsx"
primary_target: "frontend/src/App.tsx"
related_targets: []
---

# Surface: app shell (chat, sidebar, configuración, registro)

Scope: toda la SPA de `frontend/` (una sola superficie de trabajo). Mode: Operate.
Audiencia y tarea: operador de finanzas que revisa facturas y aprueba excepciones; el jurado debe entender factura → decisión → porqué en segundos.
Contenido: solo datos del backend real (no inventar facturas ni métricas); estados vacíos cuando no hay datos o el backend no responde.
Restricciones: dirección fintech sobria pedida por el equipo; WCAG 2.2 AA; escritorio primero, usable en móvil; UI en español.
Momento memorable: la respuesta del agente llega como un cheque con talón perforado.
Por resolver: reglas y dataset definitivos (Dev C); el panel de reglas se genera desde el esquema del RuleSet.

## Direction contract

THESIS: Cada decisión se emite como un cheque de seguridad: el frente dice qué pasó y cuánto, el talón perforado guarda el porqué. Rechaza el chat gris genérico con píldoras de colores.

OWN-WORLD: Papel de seguridad cálido (#F3F1EA) con barra lateral en papel más oscuro (#E8E4D8), tinta casi negra (#1E1C18), un solo acento: tinta intaglio verde (#1E5A48) para acciones primarias y "pagada". Estados: pendiente ocre (#8C5A00 sobre #F3E3BF), frenada ladrillo (#A23B24). Geist para la UI, Geist Mono con cifras tabulares para montos, números de factura, fechas y versión de reglas. Trama guilloché tenue solo detrás del monto. Bordes de 1px en tono papel, radios 8–10px.

STORY: El operador sube o pega una factura, recibe un cheque con el veredicto y el monto, abre el talón para leer cada regla (observado vs esperado), y aprueba o rechaza lo pendiente con su nombre y comentario. Siempre ve qué falta por hacer.

FIRST VIEWPORT: Izquierda, barra lateral de 288px: marca, "Nueva factura", pestañas Todas/Pendientes/Pagadas/Frenadas con contadores, lista con glifo de estado y monto tabular; la seleccionada iluminada, el resto atenuado. Derecha: cabecera con título de la conversación y, arriba a la derecha, Registro y Configuración. Franja "Lo siguiente" (pendientes de aprobación) sobre el chat. Columna de chat de ~820px; composer fijo abajo con adjuntar y enviar. Sin datos: un cheque en blanco con línea perforada invita a subir la primera factura.

FORM: Cheque de seguridad, posición 4 de mi lista ordenada (asignada por la tirada). seed:239fcf87381106d4. Raises: jerarquía solo por escala (espécimen); seleccionado destacado y resto atenuado (streaming); franja "Lo siguiente" (señalética); cifras tabulares pequeñas en columna (atlas); una forma por estado: círculo lleno, anillo, cuadro (manual); medidor de gasto del periodo que no desborda (j-card).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

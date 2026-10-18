---
target: repetir critique con decisiones reales (app completa)
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:C:\\Users\\carli\\Documents\\hackathon-30x\\frontend\\src\\App.tsx"
target_fingerprint: "sha256:4166580f731e0a436f07a3b60458e15757c0ccff0520a9def0a40ecc1cadcb1c"
target_path: "C:\\Users\\carli\\Documents\\hackathon-30x\\frontend\\src\\App.tsx"
timestamp: 2026-10-18T02-09-44Z
slug: frontend-src-app-tsx
---
Method: dual-agent (A: revisión de diseño · B: detector + navegador)
Datos reales: 104 facturas del dataset, 1 aprobación y 1 rechazo humanos, conversación de consulta.

## Design Health Score
| # | Heurística | Puntos | Problema clave |
|---|---|---|---|
| 1 | Visibilidad del estado | 2 | Tras aprobar, el frente del cheque sigue diciendo «Escalada a una persona»; la aprobación es una franja al pie |
| 2 | Lenguaje del usuario | 3 | Se cuela jerga: «(Dev C: 5 años)», «ADMIN_TOKEN», claves snake_case, «Límite de 7 días (escala)» |
| 3 | Control y libertad | 3 | Bien (diff antes de guardar reglas, reinicio en dos pasos); «Reevaluar» es de un clic sin vista previa |
| 4 | Consistencia | 2 | Un estado con 4 nombres: Por aprobar / Escalada a una persona / esperan tu aprobación / pendiente de aprobación |
| 5 | Prevención de errores | 3 | Nombre y motivo obligatorios; pero el nombre viene precargado del navegador |
| 6 | Reconocer antes que recordar | 2 | Barra lateral sin número de factura ni fecha; filas idénticas «Tecnoredes Colombia…» |
| 7 | Flexibilidad y eficiencia | 2 | Hay atajo «/» y CSV; no hay aprobación en lote, «siguiente pendiente» ni skip link |
| 8 | Estética y minimalismo | 3 | Sobrio; el talón lista 11 reglas por igual (9 «Cumple» antes de las 2 que importan) |
| 9 | Recuperación de errores | 3 | Avisos y búsqueda vacía claros |
| 10 | Ayuda y documentación | 3 | Pasos de inicio y pistas; sin glosario de límite / umbral / tope / presupuesto |
| **Total** | | **26/40** | **Aceptable** |

## Veredicto de especificidad
LLM: el cheque está diseñado para este producto (papel de seguridad, tinta intaglio, guilloché detrás del monto, cifras Mono tabulares, talón perforado, microtexto SIMULADO, una forma por estado). Alrededor, la estructura es la de cualquier app de chat (barra lateral, filtros, composer, cajón de configuración, tabla del registro): la metáfora se queda en el componente.
Detector: 0 hallazgos en el código fuente (`frontend/src`). En el navegador, 5 tipos: cream-palette (falso positivo, es el papel de DESIGN.md), wide-tracking y bajo contraste en la banda «SIMULADO» (decorativa y aria-hidden; contraste 3,1:1, dudoso), flat-type-hierarchy (falso positivo, la jerarquía va por peso y escala) y longitud de línea real: 68ch da ~96 caracteres por línea en las respuestas (MessageList.tsx:85, DecisionCheque.tsx:316).

## Impresión general
El cheque es el acierto y el momento memorable. El problema es lo que rodea a la decisión: se abre en el lugar equivocado, no se actualiza cuando una persona resuelve y el registro cuenta una historia que parece un incumplimiento.

## Lo que funciona
- El cheque: el monto es lo único grande, cada regla con observado vs esperado e id, «Reglas v1 · 2/11 sin cumplir», estados nunca solo por color.
- Copy honesto: «Pago simulado», «Datos leídos con el lector local (sin IA)», «Guardar como versión v2» con diff.
- El diálogo de aprobación enmarca el riesgo («Estás aprobando a pesar de que:» con las reglas fallidas) y la franja «N facturas esperan tu aprobación» está en todas las pantallas.

## Problemas prioritarios
1. [P1] La conversación abre al final: el veredicto y «Aprobar pago» quedan fuera de vista (ConversationPage.tsx:29, scrollIntoView block:'end'). Arreglo: al abrir una conversación existente, llevar el inicio del último cheque a la vista; el scroll al final solo para mensajes nuevos. Comando: /impeccable layout.
2. [P1] La cinta de gasto y el chat presentan una aprobación humana como incumplimiento del límite («USD 56,782.04 pagados» vs «Límite USD 50,000.00», barra llena). Arreglo: separar «pagado por el agente (dentro de reglas)» de «aprobado por personas (excepciones)», renombrar el límite como umbral de revisión y usar la misma frase en el chat. Comando: /impeccable clarify.
3. [P1] El frente del cheque no muestra el estado final tras la decisión humana. Arreglo: sello en el frente «Escalada → Pagada · aprobada por Laura Gómez · hora · motivo», con el veredicto del agente como secundario. Comando: /impeccable polish.
4. [P2] El talón entierra las reglas fallidas y el diálogo no muestra el esperado. Arreglo: fallidas primero y destacadas, las que cumplen plegadas («9 reglas se cumplen · ver»), «Observado X · Esperado ≤ Y» en el diálogo. Comando: /impeccable distill.
5. [P2] Vocabulario de estados que deriva y jerga técnica visible (Dev C, ADMIN_TOKEN, snake_case); el hilo de consulta se titula «Nueva factura». Arreglo: un nombre por estado en toda la app, textos de configuración sin jerga, título de la consulta = primera pregunta. Comando: /impeccable clarify.

## Personas
- Alex (usuario experto): sin aprobación en lote para 20 escalaciones con la misma causa (R09); sin «siguiente pendiente»; filas de la barra lateral sin número ni fecha; registro de 106 filas sin paginar.
- Sam (teclado / lector de pantalla): sin skip link («Aprobar pago» es la parada 115 de 121); al cerrar los diálogos o el panel móvil el foco cae a <body>; el diálogo abre con foco en «Cerrar»; filtros leídos como «Por aprobar20».
- Jurado del hackathon: al abrir una factura aterriza en el final de las reglas; el registro parece mostrar al agente pagando por encima del límite; una factura aprobada sigue diciendo «Escalada»; en móvil la tabla del registro mide 1064 px.

## Observaciones menores
- Respuestas de 96 caracteres por línea (68ch en Geist es ancho); bajar a ~48ch.
- Banda «SIMULADO» a 9 px y 3,1:1: decorativa, pero si comunica, es débil.
- «Reevaluar» desalineado de la fila de botones; leyenda «Periodo» duplicada en Reglas; metadatos de la barra lateral se cortan a 288 px.
- Nombre precargado en el diálogo de aprobación: permite aprobar con la identidad de otra persona sin notarlo.

## Preguntas
1. Si el cheque es la idea del producto, ¿por qué una aprobación no reemite el cheque con un sello en lugar de una nota al pie?
2. Un límite que una persona puede superar, ¿es un límite o un umbral de revisión?
3. Con 20 escalaciones por la misma causa, ¿la unidad de trabajo es la factura o la causa?

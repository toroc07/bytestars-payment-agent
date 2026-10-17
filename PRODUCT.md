# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + TypeScript + Tailwind CSS + shadcn/ui (SPA, sin SSR), consumiendo una API FastAPI. Despliegue en Vercel. Decidido por el equipo; detalle en `docs/STACK.md`.

## Users

Operador del equipo de finanzas de una empresa constituida en EE. UU. que opera en varios países, con proveedores y contratistas en Latinoamérica y otras regiones; hace decenas de pagos al mes. Su trabajo: revisar facturas que llegan por correo, PDF o chat, decidir cuáles pagar dentro de las reglas de la empresa y aprobar a mano las excepciones.

Audiencia secundaria confirmada: el jurado del hackathon 30x, que abre la app por primera vez en la demo y debe entender el flujo (factura → decisión → por qué) en segundos.

Empresa objetivo: **Blinka (Blinka Tech Corp.)**, que plantea el reto "Agentes que pagan por la empresa". Nuestro producto es para ese contexto, pero **no es la app de Blinka**: el diseño de la app de Blinka está fuera del alcance del reto y no se imita su identidad visual.

## Product Purpose

Un agente que revisa las facturas de una empresa y decide por cada una: **pagar**, **frenar** o **escalar a una persona**, dentro de reglas que la empresa configura, y explica cada decisión. Éxito: alta autonomía (decide bien sin intervención), cero pagos fuera de reglas (un pago indebido descalifica) y explicabilidad (cualquiera entiende el porqué leyendo el registro, sin abrir el código). No mueve dinero real: el flujo termina en la decisión registrada.

## Positioning

La decisión la toma un motor de reglas determinista, no el modelo de lenguaje: el LLM solo lee la factura y redacta la explicación. Ante duda o error, escala; nunca paga. Cada decisión muestra las reglas evaluadas con valor observado vs esperado.

## Operating Context

- Interfaz tipo chat: el operador sube un PDF o imagen, o pega el texto de un correo o mensaje, y el agente responde con su decisión.
- Barra lateral con el historial de facturas y su estado (pagada, frenada, pendiente de aprobación).
- Configuración de reglas, beneficiarios permitidos y acuerdos desde un botón arriba a la derecha.
- Vista de registro de todas las decisiones, para conciliar y auditar.
- Las excepciones las aprueba o rechaza una persona, con su nombre y un comentario.

## Capabilities and Constraints

- Entradas: PDF con texto, imagen de factura y texto de chat/correo.
- Resultados posibles: `pay` (pagada, simulada), `block` (frenada), `escalate` (pendiente de aprobación); una persona puede aprobar o rechazar lo escalado.
- La UI nunca decide ni recalcula resultados; solo muestra lo que devuelve el backend.
- Montos como string decimal, monedas ISO 4217, varias monedas (USD y monedas latinoamericanas entre otras).
- **Por definir:** el catálogo de reglas, los campos de configuración, la empresa ficticia y el set de facturas (a cargo de otro integrante del equipo). El panel de reglas se genera dinámicamente desde un esquema que entrega el backend.
- Solo datos ficticios; ningún dato real de personas o empresas.
- Textos de UI en español.

## Brand Commitments

- Nombre del producto: **ByteStars Payment Agent**.
- No usar la marca, logotipo ni identidad visual de Blinka.
- Dirección pedida por el equipo: fintech sobria (neutros, un solo acento, números tabulares, estados muy legibles, transmitir confianza).

## Evidence on Hand

No hay todavía facturas, decisiones, reglas ni datos de ejemplo: el dataset está pendiente. La UI se construye con estados vacíos y no debe inventar facturas, montos, proveedores, testimonios ni métricas.

## Product Principles

1. Confianza antes que velocidad: ante la duda, se escala y se muestra por qué.
2. Toda decisión es legible por alguien que no leyó el código.
3. El estado de cada factura se entiende de un vistazo y nunca solo por color.
4. El operador siempre sabe qué falta por hacer: lo pendiente de aprobación es lo más visible.
5. Nada aparenta ser real si no lo es: los pagos son simulados y así se dice.

## Accessibility & Inclusion

WCAG 2.2 AA básico: contraste AA, foco visible, navegación completa con teclado, etiquetas en formularios y estados que no dependen solo del color. Escritorio primero, usable en móvil (la barra lateral se vuelve un panel desplegable).

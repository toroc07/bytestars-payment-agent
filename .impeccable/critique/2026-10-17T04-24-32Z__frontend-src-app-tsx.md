---
target: frontend completo (frontend/src/App.tsx)
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\carli\\Documents\\hackathon-30x\\frontend\\src\\App.tsx"
target_fingerprint: "sha256:4166580f731e0a436f07a3b60458e15757c0ccff0520a9def0a40ecc1cadcb1c"
target_path: "C:\\Users\\carli\\Documents\\hackathon-30x\\frontend\\src\\App.tsx"
timestamp: 2026-10-17T04-24-32Z
slug: frontend-src-app-tsx
---
Method: dual-agent (A: revisión de diseño · B: detector + navegador). Nota: aislamiento parcial (overlay de B cayó un momento en la pestaña de A); backend sin datos durante la revisión.

## Design Health Score: 25/40 (aceptable)
1 Visibilidad 3 · 2 Mundo real 3 · 3 Control 2 · 4 Consistencia 3 · 5 Prevención de errores 2 · 6 Reconocer 2 · 7 Eficiencia 2 · 8 Estética 3 · 9 Recuperación 3 · 10 Ayuda 2

## Specificity
Diseñada para el producto (cheque con talón, guilloché, endoso, glifos de estado). Configuración es la zona más genérica.
Detector: fuente 0 hallazgos; render: low-contrast 4.49:1 (#6b665b sobre #e8e4d8, Sidebar.tsx:31/84, real), cream-palette (intencional, falso positivo), body-text-viewport-edge en /registro 390px (overflow real).

## Priority issues
- [P1] Aprobar pago sin contexto ni datos mínimos (ApprovalDialog.tsx, DecisionCheque.tsx) → harden
- [P1] Cambios de reglas se pierden; guardar sin cambios; sin resumen de cambios (SettingsSheet.tsx RulesForm) → harden, distill
- [P2] Desbordes móvil 390px: /registro (LogPage.tsx:171 dl sin flex-wrap), cajón de configuración (barra -mx-6), pestañas partidas → adapt
- [P2] Vocabulario de estado inconsistente + contraste 4.49:1 en sidebar → clarify
- [P2] Ritmo de operador: sin montos en sidebar (requiere backend), sin búsqueda/atajos, registro sin detalle → layout

## Personas
Operador avanzado: escaladas una a una, sin montos, severidades a mano. Jurado: todo sale escalado sin pipeline; reiniciar demo escondido. Teclado/lector: rule_id aria-hidden, 11px y 4.49:1, NextUpStrip role=status repetido.

## Minor
Decimales en JPY/COP; acuerdos no borrables; "Moneda base (opcional)"; CSV filtrado sin aviso; cheque-issue 520ms vs <300ms; título duplicado en /registro.

## Questions
Demo sin pipeline; aprobar sin monto ¿imposible?; bandeja vs chat para decenas de facturas.

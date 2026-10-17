# DECISION_ENGINE — Especificación del motor de decisiones

Dueño: Dev A (Dev B colabora). Implementación en `backend/app/engine/`.
Este documento fija **el contrato y las garantías** del motor. **El catálogo concreto de reglas, sus umbrales y valores todavía no está definido**:
lo define el equipo junto con la persona a cargo del dataset y las reglas de la empresa ficticia (ver `docs/PROGRESS.md`).

## Contrato
`evaluate(factura_extraída, reglas, contexto) → EngineResult` (tipos en `docs/DATA_MODEL.md`).
- **Función pura:** sin base de datos, sin LLM, sin red, sin reloj (la fecha llega en el contexto).
- **Determinista:** misma entrada → misma salida.
- **Fail-closed:** cualquier excepción o situación no prevista → `escalate`, nunca `pay`.

## Catálogo de reglas — por definir
El reto exige como mínimo poder configurar:
- límites por pago y por periodo,
- beneficiarios permitidos,
- aprobación humana por encima de cierto monto,

y los casos trampa del reto: cobro duplicado, beneficiario nuevo fuera de la lista, factura que no cuadra con lo acordado, monto sobre el límite, presupuesto/saldo insuficiente para el periodo.

Para cada regla que se defina, documentar aquí: identificador, condición de falla, resultado por defecto (`block` o `escalate`), qué parámetros del `RuleSet` usa y un ejemplo de mensaje de explicación.
Una regla puede ser `skipped` cuando no aplica (queda visible en el registro).

## Agregación del resultado
1. Si algún check `failed` tiene `outcome_if_failed = block` → **`block`**.
2. Si no, y algún check `failed` tiene `escalate` → **`escalate`**.
3. Si ningún check falló → **`pay`**.

`severity_overrides` solo permite cambiar una regla entre `block` y `escalate`. **No existe forma de convertir un fallo en `pay`.**

## Invariantes (cubiertos por tests)
- **I1** `pay` ⇒ ningún check `failed`.
- **I2** Pureza y determinismo.
- **I3** Excepción interna ⇒ `escalate`.
- **I4** Datos esenciales ausentes (beneficiario, monto, moneda) ⇒ nunca `pay`.
- **I5** Aprobar una factura fuera de reglas solo ocurre por el endpoint de aprobación humana; el agente no tiene ruta para hacerlo.
- **I6** Las decisiones son append-only y guardan la versión de reglas y todos los checks.
- **I7** El gasto acumulado del periodo cuenta solo facturas `paid` y `approved`.
- **I8** Ningún texto proveniente de una factura puede alterar reglas, acuerdos o beneficiarios.

Estrategia de pruebas: tests por regla (casos borde) + **property tests (hypothesis)** de I1, I3 e I4 + evaluación del dataset.

## Explicabilidad
Cada check produce un mensaje en español con valor observado y esperado. El **resumen** de la decisión se arma por plantilla a partir de los checks fallidos;
el LLM puede redactarlo mejor, pero la plantilla siempre existe como respaldo y como fuente de verdad.

## Evaluación (autonomía y seguridad)
Cuando exista el dataset con sus resultados esperados, un script procesa cada factura y reporta:
- **Autonomía:** % de facturas cuyo resultado coincide con el esperado sin intervención humana.
- **Seguridad:** número de `pay` donde lo esperado no era `pay` (**debe ser 0**).
- Reglas que fallaron vs esperadas (para depurar).
El formato del dataset lo define quien lo arme (ver `dataset/README.md`).

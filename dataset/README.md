# dataset/ — Facturas simuladas, empresa ficticia y reglas de pago

**Por definir.** Esta carpeta está a cargo de un tercer integrante del equipo (Dev C), que define:
- la empresa ficticia y **sus reglas de pago**,
- los beneficiarios y acuerdos,
- las facturas simuladas (PDF, imagen y mensaje de chat/correo),
- los resultados esperados de cada factura.

Aquí no hay datos todavía, ni estructura de archivos impuesta: Dev C decide formato y organización y la documenta en este README.

## Lo que el reto pide del set
- Ningún dato real de clientes ni empresas.
- Casos normales y casos trampa, por ejemplo: cobro duplicado, beneficiario nuevo fuera de la lista, factura que no cuadra con lo acordado, monto que supera el límite y necesita aprobación humana, saldo/presupuesto insuficiente para el periodo.
- Los tres formatos de entrada: PDF, imagen y mensaje de texto.

## Lo que el resto del equipo necesita de Dev C (a acordar)
- **Para la base de datos (Dev B):** un formato que permita sembrar la empresa ficticia, sus reglas, beneficiarios y acuerdos.
- **Para el motor y la evaluación (Dev A):** por cada factura, el resultado esperado (pagar / frenar / escalar) y por qué, para medir autonomía y comprobar que **nunca se paga fuera de reglas**.
- **Para el catálogo de reglas:** las reglas definidas por Dev C se documentan en `docs/DECISION_ENGINE.md` y sus campos en `docs/DATA_MODEL.md` (RuleSet).

Cuando Dev C defina el formato, actualizar este README, `docs/DATA_MODEL.md` y `docs/PROGRESS.md`.

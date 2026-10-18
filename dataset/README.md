# dataset/ — Facturas simuladas, empresa ficticia y resultados esperados

Todo es **ficticio**: empresas, NIT, cuentas, personas y correos (dominios `.example`). Dev C es el dueño del contenido.
`company.json` y `expected.json` son una propuesta de Dev A que Dev C debe validar (`docs/DECISIONS.md` ADR-018).

## Contenido
| Ruta | Qué es |
|---|---|
| `Textos/` | 26 mensajes de chat (`.txt`), en una línea o con detalle por ítem |
| `Correos/` | 26 correos (`.eml`) con la factura en PDF adjunta |
| `PDFS/` | 26 facturas en PDF |
| `Imagenes/` | 26 facturas escaneadas o fotografiadas (`.png`, `.jpg`) |
| `company.json` | empresa, reglas (`rule_set`), beneficiarios permitidos y acuerdos; lo carga `backend/app/db/seed.py` |
| `expected.json` | por factura: los datos que debería leer el agente y el resultado esperado (pagar / frenar / escalar) con su porqué |

Las facturas se numeran de `factura_001` a `factura_104` repartidas entre las cuatro carpetas (de la 101 a la 104 son los casos de monto alto, una por formato). **El orden canónico es por número.** Los resultados dependen del orden: el duplicado es la segunda copia que llega y el tope semanal se alcanza al final.

## La empresa
**Distribuciones Andinas S.A.S.** (NIT 900.482.117-5, Bogotá). Reglas de pago de Dev C, en USD:

| Regla | Valor | Si no se cumple |
|---|---|---|
| Límite por pago | US$10.000 | frenar |
| Aprobación humana | más de US$5.000 | escalar |
| Tope de 7 días (todas las facturas) | US$50.000 | escalar |
| Tope de 7 días por proveedor | US$20.000 | escalar |
| Solo proveedores de la lista, verificados y no sancionados | — | frenar |
| Cambio de NIT o de cuenta bancaria, o monto fuera de lo acordado | tolerancia 5 % | escalar |
| Duplicados (mismo número, o misma orden de compra y monto) | — | frenar |
| Datos obligatorios: proveedor, número, monto, fecha y concepto | — | escalar |

Catálogo completo (R01–R11) en `docs/DECISION_ENGINE.md`.

## Proveedores permitidos (inferidos del dataset)
| Proveedor | NIT | Cuenta |
|---|---|---|
| Aseo Total Servicios S.A.S. | 901.022.366-3 | Banco de Bogotá, corriente 81629733626 |
| Seguridad Integral Guardianes Ltda. | 830.082.649-1 | Banco de Occidente, corriente 90663776548 |
| Alimentos y Catering El Sabor S.A.S. | 901.350.127-6 | Banco Popular, ahorros 76408675855 |
| Mantenimiento Industrial Cundinamarca S.A.S. | 900.718.452-3 | Bancolombia, corriente 68367326817 |
| Publicidad Creativa Bogotá S.A.S. | 800.199.036-1 | Davivienda, ahorros 72923393128 |
| Papelería y Suministros del Norte S.A.S. | 900.231.584-5 | Bancolombia, ahorros 71091652208 |
| Tecnoredes Colombia Ltda. | 830.114.921-1 | Davivienda, corriente 86447545986 |
| Transportes Rápido Andino S.A. | 860.045.873-7 | BBVA, corriente 14231607409 |

No hay acuerdos cargados: el set no trae montos pactados por proveedor.

## Trampas del set
| Caso | Facturas | Resultado |
|---|---|---|
| Proveedor fuera de la lista: Servicios Logísticos Meridian S.A.S. (NIT 900.964.215-8) | 005, 020, 041 | frenar (R03) |
| Proveedor fuera de la lista: Comercializadora Delta Express S.A.S. (NIT 901.587.432-6, cuenta Nequi, sin orden de compra) | 015, 029, 050 | frenar (R03) |
| Suplantación: se presenta como la papelería con otro NIT (901.233.780-5) y otra cuenta | 008, 088 | frenar (R03) |
| Duplicado con el mismo número | 028, 031, 043, 066, 093 | frenar (R02) |
| Duplicado con otro número (misma orden de compra y monto) | 014, 019, 044, 085, 098 | frenar (R02) |
| El correo pide pagar a una cuenta nueva | 075, 092 | escalar (R11) |
| Tope de 7 días: con todo el set en una sesión, el gasto pasa de US$50.000 desde la factura 078 | 18 facturas a partir de la 078 | escalar (R09) |
| Monto sobre el umbral de aprobación (más de US$5.000): Seguridad Integral US$6.854,40 (PDF) y Tecnoredes US$6.188,00 (correo) | 101, 103 | escalar (R08) |
| Monto sobre el límite por pago (más de US$10.000): Transportes Rápido Andino US$11.352,60 (chat) y Mantenimiento Industrial US$10.043,60 (imagen) | 102, 104 | frenar (R07) |

Las facturas 101 a 104 son de proveedores permitidos y con sus datos correctos: lo único que falla es el monto. Como van al final del orden canónico, también marcan el tope de 7 días (R09); en una demo desde cero (Configuración → Demo → Reiniciar) muestran solo la regla de monto.

## Montos
Los originales estaban en pesos colombianos y se pasaron a USD a la tasa ~4.000, con el mismo contenido. Los precios unitarios se redondearon: menos de 20 → al entero; menos de 100 → a 5; menos de 1.000 → a 10; desde 1.000 → a 100. Después se recalcularon líneas, subtotal, IVA del 19 % y total. Los montos se escriben como `US$1,234.00`.

## `expected.json`
- `invoices[]`: `file`, `format` (`pdf`, `image`, `email`, `text`), `expected_extraction` (los datos que el agente debería leer; `description` es el primer ítem), `expected_outcome` (`pay`, `block` o `escalate`), `failed_rules`, `case` y `reason`.
- `assumptions`: lectura correcta, base recién sembrada y orden canónico en una sola sesión.
- `backend/tests/engine/test_dataset_expected.py` pasa cada factura por el motor y comprueba que coincida y que ninguna trampa se pague. Si cambian las reglas o el dataset, hay que regenerar `expected.json` y revisar las diferencias a mano.

## Para el resto del equipo
- **Base de datos (Dev B):** `POST /api/dev/reset` vuelve a sembrar desde `company.json`.
- **Frontend:** las cuatro carpetas se pueden cargar como lote desde la pantalla inicial (hasta 50 archivos por vez). Para reproducir `expected.json`, cargar de la 001 a la 104 en orden (tres lotes: 001–050, 051–100, 101–104).

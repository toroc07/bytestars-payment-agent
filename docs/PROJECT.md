# PROJECT — El reto

**Reto Blinka: Agentes que pagan por la empresa** (Hackathon 30x · Área Producto · Tipo: crear algo nuevo · Entregable: agente funcionando).

## En una frase
Un agente que revisa las cuentas de una empresa y decide cuáles pagar por ella dentro de las reglas que la empresa define, y que pide permiso a una persona cuando algo se sale de esas reglas.

## Problema hoy (manual)
Llega una factura por correo/PDF/chat → finanzas la revisa y la compara con lo acordado → pide aprobación por chat → crea el pago a mano (a veces en otra moneda y país) → concilia en una hoja de cálculo. Se repite cada mes y depende de que una persona esté disponible.

## Para quién
Empresas constituidas en EE. UU. que operan en varios países, con equipo, proveedores y contratistas en Latinoamérica. Hacen decenas de pagos al mes.

## Alcance
**Entra**
- Leer una factura y extraer: a quién, cuánto, en qué moneda y para cuándo.
- Decidir según reglas configurables: límite por pago y por periodo, beneficiarios permitidos, aprobación humana sobre cierto monto.
- Registrar cada decisión (pagó / frenó / escaló) y por qué.

**No entra**
- Ejecutar pagos reales o mover dinero · abrir cuentas · verificar identidad de empresas · decisiones de cumplimiento o fraude · diseño de la app de Blinka.

El flujo termina cuando el agente **decide y registra**. No hay integración con plataformas de pago.

## Entregable
Un agente funcionando sobre nuestro set de facturas, con una pantalla simple donde la empresa:
1. define sus reglas,
2. ve qué decidió pagar el agente, qué frenó, qué dejó pendiente de aprobación y **por qué**.

## Restricciones
- Ningún dato real de clientes ni empresas.
- El agente nunca aprueba un pago fuera de las reglas sin aprobación humana.
- Cada decisión debe poder explicarse después.
- Libertad total de modelo, lenguaje y framework.

## Cómo se evalúa
| Criterio | Qué significa | Cómo lo medimos |
|---|---|---|
| **Autonomía** | % de facturas del set que el agente decide correctamente sin intervención humana | Script de evaluación contra `dataset/scenarios.json` |
| **Seguridad** | Cero pagos aprobados fuera de reglas (**aprobar un pago indebido descalifica**) | Tests de invariantes del motor + evaluación del dataset |
| **Explicabilidad** | Cualquiera entiende por qué se pagó/frenó/escaló leyendo el registro, sin abrir el código | Cada decisión muestra reglas evaluadas con valor observado vs esperado, en español |

## Los tres resultados posibles
- **Pagar:** todas las reglas pasan. (Simulado.)
- **Frenar:** una regla "dura" falla (duplicado, no cuadra con lo acordado, supera el tope por pago, sin presupuesto). No se paga.
- **Escalar:** requiere una persona (monto sobre umbral de aprobación, beneficiario nuevo, datos incompletos, moneda no permitida, límite del periodo). No se paga hasta que alguien apruebe.

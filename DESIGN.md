---
name: ByteStars Payment Agent
description: Agente que decide pagar, frenar o escalar facturas, con cada decisión emitida como un cheque explicable.
colors:
  paper: "#f3f1ea"
  paper-deep: "#e8e4d8"
  sheet: "#fbfaf6"
  ink: "#1e1c18"
  ink-soft: "#4a463d"
  ink-muted: "#655f53"
  rule: "#d6d0c1"
  rule-strong: "#c4bca8"
  intaglio: "#1e5a48"
  intaglio-deep: "#164536"
  intaglio-tint: "#dbe7e1"
  ochre: "#7a4e00"
  ochre-tint: "#f3e3bf"
  ochre-rule: "#ddbf7e"
  brick: "#a23b24"
  brick-tint: "#f4ddd5"
  brick-rule: "#e2b3a6"
typography:
  display:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 500
    lineHeight: 1.4
  body:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.625
  label:
    fontFamily: "Geist Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
  amount:
    fontFamily: "Geist Mono Variable, ui-monospace, monospace"
    fontSize: "3rem"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "-0.01em"
    fontFeature: "tnum"
  figure:
    fontFamily: "Geist Mono Variable, ui-monospace, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    fontFeature: "tnum"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.intaglio}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    height: "40px"
    padding: "0 16px"
  button-primary-hover:
    backgroundColor: "{colors.intaglio-deep}"
  button-secondary:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "40px"
  button-danger:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.brick}"
    rounded: "{rounded.md}"
  input:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "40px"
  cheque:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
  cheque-stub:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
  verdict-paid:
    backgroundColor: "{colors.intaglio}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
  verdict-pending:
    backgroundColor: "{colors.ochre-tint}"
    textColor: "{colors.ochre}"
    rounded: "{rounded.pill}"
  verdict-blocked:
    backgroundColor: "{colors.brick-tint}"
    textColor: "{colors.brick}"
    rounded: "{rounded.pill}"
---

# Design System: ByteStars Payment Agent

## Overview

**Creative North Star: "El cheque de seguridad"**

Cada decisión del agente se emite como un cheque impreso en papel de seguridad: el frente dice qué pasó y cuánto, y el talón perforado guarda el porqué, regla por regla. El mundo aporta solo cuatro cosas a una herramienta de trabajo: papel cálido, una tinta intaglio verde, cifras tabulares tipo MICR y la perforación. La navegación, los controles y la composición son los de cualquier app web que el operador ya sabe usar.

La densidad es de herramienta de operación: barra lateral con historial, chat centrado de lectura cómoda, paneles laterales para configurar. La confianza sale de la precisión (cifras alineadas, estados inequívocos, nada inventado), no de decoración. Lo simulado se declara simulado: el microtexto «SIMULADO · NO ES UN PAGO REAL» corre por el borde de cada cheque.

Rechazos confirmados: imitar la identidad visual de Blinka; el dashboard SaaS genérico gris con píldoras de colores.

**Key Characteristics:**
- Papel cálido como suelo, un solo acento (intaglio) y colores de estado solo donde significan algo.
- Montos, fechas, números de factura y versiones de reglas siempre en Geist Mono con cifras tabulares.
- Cada estado tiene una forma propia (círculo lleno, anillo, cuadro), nunca solo color.
- Un solo momento de movimiento propio: el cheque «se imprime» al llegar una decisión (360 ms).

## Colors

Neutros de papel tintados hacia el cálido, tinta casi negra y una tinta de seguridad verde; los estados ocre y ladrillo aparecen solo cuando cargan significado.

### Primary
- **Tinta intaglio** (#1e5a48): acciones primarias, foco, selección y el estado «pagada». Su versión profunda (#164536) es el hover; su tinte (#dbe7e1) es la selección de texto y los endosos aprobados.

### Neutral
- **Papel de seguridad** (#f3f1ea): fondo de la app y del talón.
- **Papel profundo** (#e8e4d8): barra lateral, burbujas del usuario, pistas de segmentos.
- **Hoja** (#fbfaf6): el frente del cheque, campos de formulario, tarjetas.
- **Tinta** (#1e1c18), **tinta suave** (#4a463d), **tinta apagada** (#655f53, mínimo para texto secundario; cumple AA también sobre papel profundo).
- **Regla** (#d6d0c1) y **regla fuerte** (#c4bca8): bordes de 1px y la perforación.

### Estados
- **Ocre** (#7a4e00 sobre #f3e3bf, borde #ddbf7e): pendiente de aprobación / escalada.
- **Ladrillo** (#a23b24 sobre #f4ddd5, borde #e2b3a6): frenada o rechazada, errores.

### Named Rules
**Regla del acento único.** Intaglio es el único color de marca. Ocre y ladrillo solo existen para decir estado o error.
**Regla de la forma.** Ningún estado depende solo de su color: pagada = círculo lleno, pendiente = anillo, frenada = cuadro, recibida = anillo punteado.

## Typography

**Interfaz:** Geist Variable (autohospedada con @fontsource).
**Cifras:** Geist Mono Variable con `tabular-nums` (utilidad `tabular`).

Carácter: una sans de trabajo, neutra y precisa, contra una mono que hace de cifra impresa. La mono nunca se usa como disfraz técnico: solo en datos y medidas.

### Hierarchy
- **Display** (600, 1.875rem, 1.2): títulos de página y del estado vacío.
- **Title** (500, 1.125rem): nombre del beneficiario en el cheque, títulos de panel.
- **Body** (400, 0.9375rem, 1.625): mensajes, explicaciones; máximo ~68ch.
- **Label** (500, 0.75rem): etiquetas de campo y pestañas.
- **Amount** (Geist Mono 500, 3rem): el monto del cheque, lo único grande de la pantalla.
- **Figure** (Geist Mono 400, 0.75rem): fechas, números de factura, versión de reglas.

### Named Rules
**Regla de la escala.** En el cheque la jerarquía la da solo la escala: el monto es grande, todo lo demás va a tamaño de texto.

## Layout

- Escritorio: barra lateral fija de 18rem + área principal; la columna de chat se limita a 52rem y el registro a 72rem.
- Móvil (<768px): la barra lateral pasa a un panel deslizable desde la izquierda; el talón del cheque baja debajo del frente con perforación horizontal.
- Ritmo de espaciado 4/8/16/24/40px; más espacio arriba de un encabezado que debajo.
- La franja «Lo siguiente» (facturas que esperan aprobación) siempre va arriba del chat.

## Elevation & Depth

Casi plano, por capas de papel: los planos se distinguen por tono (papel, papel profundo, hoja) y bordes de 1px. Las sombras son ambientales y con desplazamiento, nunca halos: el cheque usa `0 12px 32px -20px` de tinta al 40%, los paneles `0 24px 48px -16px`. Sin sombras duras ni brillos.

## Shapes

Radios medios: 6px en elementos pequeños, 8px en botones e inputs, 12px en el cheque y los diálogos, píldora solo en el veredicto. La perforación es un borde discontinuo de 2px con muescas semicirculares en los extremos.

## Components

- **Cheque de decisión:** frente (beneficiario, factura y vencimiento, monto, veredicto, quién decidió, microtexto de simulado) + talón perforado con cada regla: icono de cumple/no cumple, mensaje, observado vs esperado, id de regla. Un endoso al pie registra la aprobación o el rechazo humano con nombre, comentario y hora.
- **Botones:** primario intaglio, secundario hoja con borde, fantasma, peligro ladrillo. `scale(0.97)` al presionar (140ms).
- **Composer:** hoja con borde que se vuelve intaglio al enfocar; adjuntar PDF o imagen, arrastrar y soltar, Enter envía.
- **Panel de configuración:** cajón derecho con pestañas Reglas / Beneficiarios / Acuerdos; los campos se generan del JSON Schema que publica el backend.
- **Registro:** cinta de gasto del periodo con marcas de límite (ocre) y presupuesto (ladrillo), filtros y tabla exportable a CSV.

## Do's and Don'ts

**Do**
- Usa `tabular` para todo monto, fecha, número de factura o versión.
- Acompaña cada glifo de estado con texto.
- Muestra solo datos que vienen del backend; los estados vacíos lo dicen.
- Mantén el movimiento en CSS, con ease-out fuerte, menos de 300ms en UI y respeto a `prefers-reduced-motion`.

**Don't**
- No uses la marca ni la identidad visual de Blinka.
- No agregues un segundo color de marca ni degradados de texto.
- No inventes facturas, montos, proveedores ni métricas para «llenar» una pantalla.
- No recalcules ni infieras decisiones en la UI: el motor del backend decide.
- No pongas eyebrows o etiquetas encima de los títulos ni tarjetas anidadas.

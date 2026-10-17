# frontend/AGENTS.md

Lee primero el `AGENTS.md` de la raíz. Esta carpeta es **zona de Dev A**. No edites `backend/` desde aquí.
Antes de tocar UI, lee también `DESIGN.md` (sistema visual) y `PRODUCT.md` (producto) en la raíz.

## Qué es
SPA **React 19 + Vite 8 + TypeScript 6 + Tailwind CSS 4**, con primitivos accesibles de **Radix** (`radix-ui`) escritos al estilo shadcn en `src/components/ui/`. Datos con **TanStack Query**, rutas con **React Router 8**, iconos **lucide-react**, fuentes **Geist / Geist Mono** autohospedadas.
Habla con el backend **real** por la API de `docs/API_CONTRACT.md`. No hay modo mock: los estados vacíos y de error cubren la falta de datos o de backend.

## Cómo correrlo
```bash
# backend (otra terminal): cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000
#                           y una vez: curl -X POST http://127.0.0.1:8000/api/dev/seed
cd frontend
npm install
npm run dev        # http://localhost:5173 ; Vite reenvía /api, /health y /openapi.json al backend
npm run typecheck  # tsc -b
npm run lint       # oxlint
npm test           # vitest (lógica pura: hilo de decisiones, archivos, formularios desde schema, formato)
npm run build
npm run gen:api    # regenera src/api/schema.d.ts desde ../contracts/openapi.json
```
Variables (`frontend/.env.example`): `VITE_API_URL` (vacío en local; URL del backend en producción) y `VITE_DEV_BACKEND`.
Deploy: `frontend/vercel.json` reescribe todas las rutas a `index.html` (sin eso, recargar `/c/:id` o `/registro` da 404).

## Pantallas
1. **Chat (`/` y `/c/:id`)**: el usuario adjunta un archivo (máx. 4 MB, también arrastrando) o pega texto.
   - **PDF, PNG y JPG** se envían como archivo al backend.
   - **Correos `.eml`** se abren en el navegador (`lib/eml.ts`): remitente, asunto y fecha decodificados + cuerpo de texto se envían como texto, y el **PDF o imagen adjunto** (la factura) como archivo. Probado con los 25 correos de `dataset/Correos` (`eml.test.ts`).
   - **Textos** (`.txt`, `.md`) se envían como texto (nombre del archivo + contenido). Ver `lib/files.ts`.
   - El frontend no juzga el contenido: los casos trampa del dataset (duplicados, países no permitidos, etc.) los decide el motor.
   - En la pantalla inicial se pueden adjuntar **varios archivos (hasta 50)**: se revisan uno tras otro, cada uno en su propia conversación, con progreso y resumen (`BatchRun`). Pensado para las carpetas del dataset.
   - La respuesta del agente es un **cheque** (`DecisionThread` en `DecisionCheque.tsx`): frente con beneficiario, monto, veredicto; talón perforado con cada regla (observado vs esperado).
   - Si quedó pendiente: **Aprobar / Rechazar** con nombre y comentario; la acción humana aparece como **endoso** al pie del cheque.
   - Si quedó **frenada o pendiente**: **Reevaluar con las reglas actuales** (`POST /api/invoices/{id}/reevaluate`) emite un cheque nuevo debajo; el anterior queda como sustituido. No se ofrece en facturas pagadas, aprobadas ni rechazadas.
2. **Barra lateral**: historial con glifo de estado y filtros Todas / Pendientes / Pagadas / Frenadas. En móvil es un panel deslizable.
3. **Configuración (arriba a la derecha)**: cajón con Reglas / Beneficiarios / Acuerdos / Demo. **Los formularios se generan del JSON Schema** que publica el backend en `/openapi.json` (`RuleSet-Input`, `Beneficiary`, `Agreement-Input`): si cambian los campos de reglas, la UI los sigue sola. Las etiquetas en español viven en `components/settings/schemaFields.ts` (con respaldo automático para campos nuevos). Beneficiarios y acuerdos se pueden agregar y editar (quitar pide confirmación); en acuerdos el beneficiario se elige de la lista. **Demo** reinicia todo (`/api/dev/reset`) con confirmación.
4. **Registro (`/registro`)**: cinta de gasto del periodo (límite y presupuesto), conteos por estado, filtros, tabla y **exportar CSV**.

## Estructura
```
src/
├── api/          schema.d.ts (generado), types.ts (alias), client.ts (fetch + errores), hooks.ts (TanStack Query)
├── components/
│   ├── ui/       button, dialog/sheet, field (input, select, switch...), tabs
│   ├── chat/     Composer, MessageList, EmptyCheque, NextUpStrip
│   ├── decision/ DecisionCheque, ApprovalDialog, StatusGlyph, Guilloche
│   ├── settings/ SettingsSheet, SchemaForm, schemaFields (schema → campos)
│   ├── sidebar/  Sidebar
│   └── AppShell.tsx
├── pages/        ChatHome, ConversationPage, LogPage, NotFoundPage (+ CrashPage)
├── lib/          cn, format (montos, fechas), status (vocabulario de estados), files (tipos de archivo),
│                 thread (decisión → endoso → reevaluación); *.test.ts junto a cada módulo
└── index.css     tokens del tema (@theme), utilidades `tabular` y `pressable`, animaciones
```

## Reglas
- **La UI nunca decide ni recalcula resultados**: solo muestra lo que devuelve el backend.
- **No inventes datos** (facturas, montos, proveedores, métricas). Sin datos → estado vacío.
- **Dinero** llega como string: formatear con `formatAmount`; nunca operar con él para decidir.
- **Fechas**: usar `formatTimestamp` (trata como UTC los timestamps sin zona que manda el backend).
- **Estados**: usar `StatusGlyph` + texto; cada estado tiene una forma (círculo, anillo, cuadro), nunca solo color.
- **Cifras** (montos, fechas, ids, versiones) con la utilidad `tabular`.
- **Colores**: solo los tokens de `index.css` / `DESIGN.md`. Un acento (intaglio); ocre y ladrillo solo para estado.
- **Movimiento**: CSS, ease-out fuerte, <300 ms en UI, respetar `prefers-reduced-motion`. El único momento propio es `cheque-issue`.
- **Accesibilidad (WCAG 2.2 AA)**: foco visible, etiquetas en formularios, contraste AA, todo usable con teclado.
- **Tipos de la API**: no escribirlos a mano; `npm run gen:api` cuando cambie `contracts/openapi.json`.
- Si necesitas un campo o endpoint que no existe: propón el cambio en `docs/API_CONTRACT.md` / `docs/DATA_MODEL.md` y avisa a Dev B.
- Textos de UI en español; código en inglés. Sin secretos en el frontend.

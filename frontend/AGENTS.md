# frontend/AGENTS.md

Lee primero el `AGENTS.md` de la raíz. Esta carpeta es **zona de Dev A**. No edites `backend/` desde aquí.

## Qué es
SPA **React + Vite + TypeScript + Tailwind + shadcn/ui** con apariencia tipo ChatGPT. Solo habla con el backend por la API descrita en `docs/API_CONTRACT.md`.
Estado: **carpeta vacía**, el proyecto Vite aún no se inicializa (ver `docs/PROGRESS.md`).

## Pantallas
1. **Chat (`/`)**
   - Lista de mensajes + caja de entrada con adjuntar (PDF, PNG/JPG) y pegar texto.
   - Cuando el agente procesa una factura, responde con una **tarjeta de decisión**: etiqueta de resultado (Pagada / Frenada / Pendiente de aprobación), resumen en español y lista expandible de reglas evaluadas (valor observado vs esperado).
   - Si la factura quedó pendiente: botones **Aprobar / Rechazar** (piden nombre del aprobador y comentario).
2. **Barra lateral:** historial de facturas/conversaciones con insignia de estado, botón "Nueva factura", filtro por estado.
3. **Configuración (botón arriba a la derecha):** panel/drawer con
   - Reglas (umbral de aprobación, tope por pago, límite y presupuesto del periodo, monedas permitidas, tasas, tolerancia, ventana de duplicados),
   - Beneficiarios permitidos,
   - Acuerdos.
   Guardar crea una **nueva versión** de reglas (mostrar la versión vigente).
4. **Registro (`/log`):** tabla de todas las decisiones con filtros y detalle explicable; tarjetas de resumen (pagado / frenado / pendiente, gasto del periodo vs límites).

## Estructura prevista
```
frontend/
├── public/
└── src/
    ├── api/            cliente HTTP, hooks de TanStack Query, tipos generados, mocks/
    ├── components/
    │   ├── chat/       ventana de chat, mensajes, composer
    │   ├── sidebar/    historial
    │   ├── decision/   tarjeta de decisión, lista de checks, badges
    │   ├── settings/   formularios de reglas, beneficiarios, acuerdos
    │   └── ui/         componentes shadcn
    ├── pages/          ChatPage, LogPage
    └── lib/            utilidades (formato de moneda/fechas)
```

## Reglas
- **Tipos de la API:** se generan desde `contracts/openapi.json` (no escribirlos a mano). Mientras no exista, seguir `docs/DATA_MODEL.md`.
- **Mocks:** con `VITE_USE_MOCKS=true` la app corre sin backend usando `contracts/examples/`. Todo componente nuevo debe funcionar en modo mock.
- **Dinero** llega como string: formatear con `Intl.NumberFormat`, nunca operar con `float` para decisiones.
- **Textos de UI en español.** Nombres de código en inglés.
- La UI **nunca** decide ni recalcula resultados: solo muestra lo que devuelve el backend.
- Accesibilidad básica: contraste, foco visible, etiquetas en formularios, estados de carga y error.
- Si necesitas un campo o endpoint que no existe: propón el cambio en `docs/API_CONTRACT.md` / `docs/DATA_MODEL.md` y avisa a Dev B.
- Variables de entorno: `VITE_API_URL`, `VITE_USE_MOCKS`. Sin secretos en el frontend.

import { Menu, Settings2 } from 'lucide-react'
import { lazy, Suspense, useRef, useState } from 'react'
import { Outlet } from 'react-router'
import { useHealth } from '@/api/hooks'
import { Sidebar } from '@/components/sidebar/Sidebar'

const SettingsSheet = lazy(() =>
  import('@/components/settings/SettingsSheet').then((m) => ({ default: m.SettingsSheet })),
)
import { Button } from '@/components/ui/button'
import { Dialog, SheetContent } from '@/components/ui/dialog'

export interface ShellContext {
  setTitle: (title: string | null) => void
}

function OfflineBanner() {
  const health = useHealth()
  if (!health.isError) return null
  return (
    <div role="alert" className="border-b border-brick-rule bg-brick-tint px-4 py-2 text-center text-sm text-brick">
      No hay conexión con el servidor del agente. Reintentando cada pocos segundos.
    </div>
  )
}

export function AppShell() {
  const [settingsOpen, setSettingsOpen] = useState(false)
  // Load the settings code on first open, then keep it mounted so its close animation plays.
  const [settingsLoaded, setSettingsLoaded] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const [title, setTitle] = useState<string | null>(null)
  // Both panels are opened from the header; closing one returns focus to the button that opened it.
  const menuButton = useRef<HTMLButtonElement>(null)
  const settingsButton = useRef<HTMLButtonElement>(null)

  return (
    <div className="grid h-dvh grid-cols-1 md:grid-cols-[18rem_minmax(0,1fr)]">
      <a
        href="#contenido"
        className="sr-only rounded-lg bg-intaglio px-4 py-2 text-sm font-medium text-paper focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50"
      >
        Saltar al contenido
      </a>
      <aside className="hidden min-h-0 border-r border-rule md:block">
        <Sidebar />
      </aside>

      <Dialog open={navOpen} onOpenChange={setNavOpen}>
        <SheetContent
          side="left"
          title="Historial de facturas"
          hideHeader
          className="md:hidden"
          onCloseAutoFocus={(event) => {
            event.preventDefault()
            menuButton.current?.focus()
          }}
        >
          <Sidebar onNavigate={() => setNavOpen(false)} onClose={() => setNavOpen(false)} />
        </SheetContent>
      </Dialog>

      <div className="flex min-h-0 min-w-0 flex-col">
        <OfflineBanner />
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-rule px-3 sm:px-5">
          <Button
            ref={menuButton}
            variant="ghost"
            size="icon"
            className="md:hidden"
            aria-label="Abrir historial"
            onClick={() => setNavOpen(true)}
          >
            <Menu />
          </Button>
          <p className="min-w-0 flex-1 truncate text-[0.9375rem] font-medium">{title ?? 'Nueva factura'}</p>
          <Button ref={settingsButton} variant="secondary" size="sm" onClick={() => {
              setSettingsLoaded(true)
              setSettingsOpen(true)
            }} aria-label="Configuración">
            <Settings2 />
            <span className="hidden sm:inline">Configuración</span>
          </Button>
        </header>
        <main id="contenido" tabIndex={-1} className="min-h-0 flex-1 outline-none">
          <Outlet context={{ setTitle } satisfies ShellContext} />
        </main>
      </div>

      {settingsLoaded ? (
        <Suspense fallback={null}>
          <SettingsSheet open={settingsOpen} onOpenChange={setSettingsOpen} returnFocusTo={settingsButton} />
        </Suspense>
      ) : null}
    </div>
  )
}

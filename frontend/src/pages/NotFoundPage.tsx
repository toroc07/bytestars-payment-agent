import { useEffect } from 'react'
import { Link, useOutletContext } from 'react-router'
import type { ShellContext } from '@/components/AppShell'

/** Shown when a screen throws: never a blank page in the middle of a demo. */
export function CrashPage() {
  return (
    <div className="grid min-h-dvh place-items-center bg-paper px-6">
      <div className="max-w-md">
        <h1 className="text-2xl font-semibold tracking-tight">Algo falló al mostrar esta pantalla.</h1>
        <p className="mt-2 text-ink-soft">
          Ningún pago se vio afectado: las decisiones ya registradas siguen en el servidor.
        </p>
        <a href="/" className="mt-4 inline-block font-medium text-intaglio underline">
          Volver al inicio
        </a>
      </div>
    </div>
  )
}

export function NotFoundPage() {
  const { setTitle } = useOutletContext<ShellContext>()
  useEffect(() => setTitle('Página no encontrada'), [setTitle])

  return (
    <div className="mx-auto max-w-[52rem] px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Esta página no existe.</h1>
      <p className="mt-2 text-ink-soft">
        <Link to="/" className="font-medium text-intaglio underline">
          Vuelve al chat
        </Link>{' '}
        para revisar una factura.
      </p>
    </div>
  )
}

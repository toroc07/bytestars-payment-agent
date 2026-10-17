import { X } from 'lucide-react'
import { Dialog as D } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { cn } from '@/lib/cn'

export const Dialog = D.Root
export const DialogTrigger = D.Trigger
export const DialogClose = D.Close

function Overlay() {
  return <D.Overlay className="overlay fixed inset-0 z-40 bg-ink/30" />
}

interface PanelProps extends Omit<ComponentProps<typeof D.Content>, 'title'> {
  title: ReactNode
  description?: ReactNode
}

function PanelHeader({ title, description }: Pick<PanelProps, 'title' | 'description'>) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="space-y-1">
        <D.Title className="text-lg font-semibold tracking-tight text-ink">{title}</D.Title>
        {description ? (
          <D.Description className="text-sm text-ink-muted">{description}</D.Description>
        ) : (
          <D.Description className="sr-only">{title}</D.Description>
        )}
      </div>
      <D.Close
        className="pressable -mr-2 -mt-1 grid size-9 place-items-center rounded-lg text-ink-muted hover:bg-paper-deep hover:text-ink"
        aria-label="Cerrar"
      >
        <X className="size-4" />
      </D.Close>
    </div>
  )
}

/** Centered modal: only for tasks that need protected focus (approving a payment). */
export function DialogContent({ title, description, className, children, ...props }: PanelProps) {
  return (
    <D.Portal>
      <Overlay />
      <D.Content
        className={cn(
          'dialog fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-sheet p-6 shadow-[0_24px_48px_-16px_rgb(30_28_24/0.35)] ring-1 ring-rule-strong',
          className,
        )}
        {...props}
      >
        <PanelHeader title={title} description={description} />
        <div className="mt-5">{children}</div>
      </D.Content>
    </D.Portal>
  )
}

/** Side drawer (settings on the right, navigation on the left on small screens). */
export function SheetContent({
  title,
  description,
  side = 'right',
  hideHeader = false,
  className,
  children,
  ...props
}: PanelProps & { side?: 'left' | 'right'; hideHeader?: boolean }) {
  return (
    <D.Portal>
      <Overlay />
      <D.Content
        className={cn(
          'fixed inset-y-0 z-50 flex w-full flex-col bg-paper shadow-[0_0_48px_-12px_rgb(30_28_24/0.35)]',
          side === 'right'
            ? 'sheet-right right-0 max-w-xl border-l border-rule'
            : 'sheet-left left-0 max-w-[19rem] border-r border-rule',
          className,
        )}
        {...props}
      >
        {hideHeader ? (
          // The content brings its own heading; keep the dialog named for assistive tech.
          <>
            <D.Title className="sr-only">{title}</D.Title>
            <D.Description className="sr-only">{description ?? title}</D.Description>
          </>
        ) : (
          <div className="border-b border-rule px-6 pt-5 pb-4">
            <PanelHeader title={title} description={description} />
          </div>
        )}
        <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto">{children}</div>
      </D.Content>
    </D.Portal>
  )
}

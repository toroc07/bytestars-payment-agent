import { Label as L, Switch as Sw } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { cn } from '@/lib/cn'

const control =
  'w-full rounded-lg bg-sheet px-3 text-sm text-ink shadow-[inset_0_0_0_1px_var(--color-rule-strong)] placeholder:text-ink-muted transition-shadow duration-150 hover:shadow-[inset_0_0_0_1px_var(--color-ink-muted)] focus-visible:outline-none focus-visible:shadow-[inset_0_0_0_2px_var(--color-intaglio)] disabled:opacity-60 aria-invalid:shadow-[inset_0_0_0_1px_var(--color-brick)]'

export function Input({ className, ...props }: ComponentProps<'input'>) {
  return <input className={cn(control, 'h-10', className)} {...props} />
}

export function Textarea({ className, ...props }: ComponentProps<'textarea'>) {
  return <textarea className={cn(control, 'min-h-20 py-2 leading-relaxed', className)} {...props} />
}

export function Select({ className, ...props }: ComponentProps<'select'>) {
  return <select className={cn(control, 'h-10 appearance-auto pr-2', className)} {...props} />
}

export function Label({ className, ...props }: ComponentProps<typeof L.Root>) {
  return <L.Root className={cn('text-sm font-medium text-ink', className)} {...props} />
}

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
  className,
}: {
  label: ReactNode
  htmlFor: string
  hint?: ReactNode
  error?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('grid gap-1.5', className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? (
        <p className="text-xs text-brick" id={`${htmlFor}-error`}>
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-ink-muted" id={`${htmlFor}-hint`}>
          {hint}
        </p>
      ) : null}
    </div>
  )
}

export function Switch({ className, ...props }: ComponentProps<typeof Sw.Root>) {
  return (
    <Sw.Root
      className={cn(
        'relative inline-flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-full bg-rule-strong transition-colors duration-150 data-[state=checked]:bg-intaglio disabled:opacity-60',
        className,
      )}
      {...props}
    >
      <Sw.Thumb className="block size-5 translate-x-0.5 rounded-full bg-sheet shadow-[0_1px_2px_rgb(30_28_24/0.3)] transition-transform duration-150 ease-[var(--ease-out-strong)] data-[state=checked]:translate-x-[1.125rem]" />
    </Sw.Root>
  )
}

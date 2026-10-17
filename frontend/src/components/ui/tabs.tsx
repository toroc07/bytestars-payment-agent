import { Tabs as T } from 'radix-ui'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/cn'

export const Tabs = T.Root

export function TabsList({ className, ...props }: ComponentProps<typeof T.List>) {
  return (
    <T.List
      className={cn('inline-flex items-center gap-1 rounded-lg bg-paper-deep p-1', className)}
      {...props}
    />
  )
}

export function TabsTrigger({ className, ...props }: ComponentProps<typeof T.Trigger>) {
  return (
    <T.Trigger
      className={cn(
        'inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium text-ink-muted transition-colors duration-150 hover:text-ink data-[state=active]:bg-sheet data-[state=active]:text-ink data-[state=active]:shadow-[0_1px_2px_rgb(30_28_24/0.12),inset_0_0_0_1px_var(--color-rule)]',
        className,
      )}
      {...props}
    />
  )
}

export const TabsContent = T.Content

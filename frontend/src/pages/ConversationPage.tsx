import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useOutletContext, useParams } from 'react-router'
import { ApiError } from '@/api/client'
import { useConversations, useMessages, useSendMessage } from '@/api/hooks'
import { Composer, type ComposerSubmit } from '@/components/chat/Composer'
import { MessageList, type PendingTurn } from '@/components/chat/MessageList'
import { NextUpStrip } from '@/components/chat/NextUpStrip'
import type { ShellContext } from '@/components/AppShell'
import { toOutgoing } from '@/lib/files'

export function ConversationPage() {
  const { conversationId } = useParams()
  const location = useLocation()
  const { setTitle } = useOutletContext<ShellContext>()
  const messages = useMessages(conversationId)
  const conversations = useConversations()
  const send = useSendMessage()
  const [pending, setPending] = useState<PendingTurn | null>(null)
  const [fresh, setFresh] = useState<string | null>(
    (location.state as { freshMessageId?: string } | null)?.freshMessageId ?? null,
  )
  const endRef = useRef<HTMLDivElement>(null)

  const summary = conversations.data?.find((c) => c.id === conversationId)
  useEffect(() => setTitle(summary?.title ?? 'Factura'), [setTitle, summary?.title])

  const count = messages.data?.length ?? 0
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [count, pending])

  async function submit({ note, files }: ComposerSubmit) {
    setPending({ text: note, fileName: files[0]?.name })
    try {
      const outgoing = await toOutgoing(files[0], note)
      send.mutate(
        { ...outgoing, conversationId },
        {
          onSuccess: ({ result }) => setFresh(result.assistant_message.id),
          onSettled: () => setPending(null),
        },
      )
    } catch {
      setPending(null)
    }
  }

  const notFound = messages.error instanceof ApiError && messages.error.status === 404

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto grid w-full max-w-[52rem] gap-6 px-4 py-6 sm:px-6 sm:py-8">
          <NextUpStrip />
          {messages.isPending ? (
            <div className="space-y-4" aria-hidden="true">
              <div className="ink-pulse ml-auto h-14 w-72 rounded-2xl bg-paper-deep" />
              <div className="ink-pulse h-64 rounded-xl bg-paper-deep" />
            </div>
          ) : notFound ? (
            <div className="rounded-xl bg-sheet p-6 ring-1 ring-rule">
              <p className="font-medium">Esta conversación no existe.</p>
              <p className="mt-1 text-sm text-ink-muted">
                Puede que el demo se haya reiniciado.{' '}
                <Link to="/" className="font-medium text-intaglio underline">
                  Empieza con una factura nueva
                </Link>
                .
              </p>
            </div>
          ) : messages.isError ? (
            <p role="alert" className="rounded-lg bg-brick-tint px-4 py-3 text-sm text-brick">
              No se pudo cargar la conversación: {messages.error.message}
            </p>
          ) : (
            <MessageList messages={messages.data} pending={pending} freshMessageId={fresh} />
          )}
          {send.isError ? (
            <p role="alert" className="rounded-lg bg-brick-tint px-4 py-3 text-sm text-brick">
              No se pudo procesar la factura: {send.error.message}
            </p>
          ) : null}
          <div ref={endRef} />
        </div>
      </div>
      <div className="mx-auto w-full max-w-[52rem] px-4 pb-4 sm:px-6 sm:pb-6">
        <Composer onSubmit={submit} busy={send.isPending} disabled={notFound} />
      </div>
    </div>
  )
}

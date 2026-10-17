import { useEffect, useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router'
import { useSendMessage } from '@/api/hooks'
import { BatchRun } from '@/components/chat/BatchRun'
import { Composer, type ComposerSubmit } from '@/components/chat/Composer'
import { EmptyCheque } from '@/components/chat/EmptyCheque'
import { MessageList, type PendingTurn } from '@/components/chat/MessageList'
import { NextUpStrip } from '@/components/chat/NextUpStrip'
import type { ShellContext } from '@/components/AppShell'
import { toOutgoing } from '@/lib/files'

export function ChatHome() {
  const { setTitle } = useOutletContext<ShellContext>()
  const navigate = useNavigate()
  const send = useSendMessage()
  const [pending, setPending] = useState<PendingTurn | null>(null)
  const [batch, setBatch] = useState<{ id: number; files: File[]; note?: string } | null>(null)

  useEffect(() => setTitle(batch ? 'Lote de facturas' : null), [setTitle, batch])

  async function submit({ note, files }: ComposerSubmit) {
    if (files.length > 1) {
      setBatch({ id: Date.now(), files, note })
      return
    }
    setPending({ text: note, fileName: files[0]?.name })
    try {
      const outgoing = await toOutgoing(files[0], note)
      send.mutate(outgoing, {
        onSuccess: ({ conversationId, result }) =>
          navigate(`/c/${conversationId}`, { state: { freshMessageId: result.assistant_message.id } }),
        onSettled: () => setPending(null),
      })
    } catch {
      setPending(null)
    }
  }

  const batchRunning = batch !== null

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto grid w-full max-w-[52rem] gap-6 px-4 py-6 sm:px-6 sm:py-10">
          <NextUpStrip />
          {batch ? (
            <BatchRun key={batch.id} files={batch.files} note={batch.note} onClose={() => setBatch(null)} />
          ) : pending ? (
            <MessageList messages={[]} pending={pending} freshMessageId={null} />
          ) : (
            <EmptyCheque />
          )}
          {send.isError && !batch ? (
            <p role="alert" className="rounded-lg bg-brick-tint px-4 py-3 text-sm text-brick">
              No se pudo procesar la factura: {send.error.message}
            </p>
          ) : null}
        </div>
      </div>
      <div className="mx-auto w-full max-w-[52rem] px-4 pb-4 sm:px-6 sm:pb-6">
        <Composer onSubmit={submit} busy={send.isPending} disabled={batchRunning} autoFocus multiple />
      </div>
    </div>
  )
}

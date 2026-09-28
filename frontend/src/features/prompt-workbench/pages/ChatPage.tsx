import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Plus, Trash2 } from 'lucide-react'

import { useToastContext } from '@/App'
import {
  createChatSession,
  deleteChatSession,
  listChatMessages,
  listChatSessions,
  sendChatMessage,
  updateChatSession,
} from '@/features/prompt-workbench/api/chat'
import { listPromptItems as fetchLibrary } from '@/features/prompt-workbench/api/library'
import { VariableFillDialog } from '@/features/prompt-workbench/components/VariableFillDialog'
import { extractVariables } from '@/features/prompt-workbench/domain/variables'
import { usePromptModelSelection } from '@/features/prompt-workbench/stores/modelSelection'
import { cn } from '@/lib/utils'

const panel = 'flex min-h-0 flex-col rounded-xl border border-border bg-card'
const field = 'w-full rounded-md border border-input bg-background px-3 text-sm'
const btn =
  'inline-flex h-9 shrink-0 items-center justify-center rounded-md px-3 text-sm transition-colors'
const btnPrimary = cn(btn, 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50')
const btnGhost = cn(btn, 'border border-input hover:bg-accent')

export function ChatPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  const providerId = usePromptModelSelection((s) => s.providerId)
  const [params, setParams] = useSearchParams()
  const sessionId = Number(params.get('session') || 0) || null
  const [draft, setDraft] = useState('')
  const [insertBody, setInsertBody] = useState<string | null>(null)
  const [showLibrary, setShowLibrary] = useState(false)

  const { data: sessions = [] } = useQuery({
    queryKey: ['prompt-chat-sessions'],
    queryFn: listChatSessions,
  })

  const { data: messages = [], isFetching: loadingMessages } = useQuery({
    queryKey: ['prompt-chat-messages', sessionId],
    queryFn: () => listChatMessages(sessionId!),
    enabled: sessionId != null,
  })

  const { data: library = [] } = useQuery({
    queryKey: ['prompt-items'],
    queryFn: () => fetchLibrary(),
    enabled: showLibrary,
  })

  useEffect(() => {
    if (sessionId == null && sessions[0]) {
      setParams({ session: String(sessions[0].id) })
    }
  }, [sessionId, sessions, setParams])

  const sendMutation = useMutation({
    mutationFn: () =>
      sendChatMessage(sessionId!, {
        content: draft.trim(),
        provider_id: providerId,
      }),
    onSuccess: async () => {
      setDraft('')
      await queryClient.invalidateQueries({
        queryKey: ['prompt-chat-messages', sessionId],
      })
      await queryClient.invalidateQueries({ queryKey: ['prompt-chat-sessions'] })
    },
    onError: (err: Error) => toast.error(err.message || '发送失败'),
  })

  async function newSession() {
    const s = await createChatSession({
      title: `对话 ${new Date().toLocaleString()}`,
      provider_id: providerId,
    })
    await queryClient.invalidateQueries({ queryKey: ['prompt-chat-sessions'] })
    setParams({ session: String(s.id) })
  }

  return (
    <div
      className="grid h-full min-h-0 gap-3 overflow-y-auto lg:grid-cols-[15rem_minmax(0,1fr)] lg:overflow-hidden"
      data-testid="prompt-chat-page"
    >
      <section className={cn(panel, 'min-h-[12rem] p-3 lg:min-h-0')}>
        <div className="mb-2 flex shrink-0 items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">会话</h2>
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1 rounded-md border border-input px-2 text-xs hover:bg-accent"
            onClick={() => void newSession()}
          >
            <Plus className="h-3.5 w-3.5" /> 新建
          </button>
        </div>
        <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {sessions.map((s) => (
            <li key={s.id}>
              <div
                className={cn(
                  'group flex items-center gap-1 rounded-md px-2 py-1.5 text-sm',
                  sessionId === s.id ? 'bg-primary/15' : 'hover:bg-accent'
                )}
              >
                <button
                  type="button"
                  className="min-w-0 flex-1 truncate text-left"
                  onClick={() => setParams({ session: String(s.id) })}
                >
                  {s.title}
                </button>
                <button
                  type="button"
                  className="opacity-70 group-hover:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:opacity-100"
                  aria-label="删除会话"
                  onClick={async () => {
                    await deleteChatSession(s.id)
                    await queryClient.invalidateQueries({
                      queryKey: ['prompt-chat-sessions'],
                    })
                    if (sessionId === s.id) setParams({})
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className={cn(panel, 'min-h-[20rem] p-4 lg:min-h-0')}>
        {!sessionId ? (
          <p className="text-sm text-muted-foreground">新建或选择一个会话开始</p>
        ) : (
          <>
            <div className="mb-3 flex shrink-0 items-center gap-2">
              <input
                className={cn(field, 'h-9 flex-1')}
                defaultValue={sessions.find((s) => s.id === sessionId)?.title}
                key={sessionId}
                onBlur={async (e) => {
                  const title = e.target.value.trim()
                  if (!title) return
                  await updateChatSession(sessionId, { title })
                  await queryClient.invalidateQueries({
                    queryKey: ['prompt-chat-sessions'],
                  })
                }}
                aria-label="会话标题"
              />
              <button
                type="button"
                className={btnGhost}
                onClick={() => setShowLibrary((v) => !v)}
              >
                从库插入
              </button>
            </div>

            {showLibrary ? (
              <div className="mb-3 max-h-36 shrink-0 overflow-y-auto rounded-md border border-border p-2">
                {library.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="block w-full truncate rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                    onClick={() => {
                      if (extractVariables(item.body).length) setInsertBody(item.body)
                      else setDraft((d) => (d ? `${d}\n${item.body}` : item.body))
                      setShowLibrary(false)
                    }}
                  >
                    {item.title}
                  </button>
                ))}
              </div>
            ) : null}

            <div className="min-h-0 flex-1 space-y-3 overflow-y-auto">
              {loadingMessages ? (
                <p className="text-sm text-muted-foreground">加载消息…</p>
              ) : (
                messages.map((m) => (
                  <div
                    key={m.id}
                    className={cn(
                      'rounded-lg px-3 py-2 text-sm whitespace-pre-wrap',
                      m.role === 'user' ? 'ml-8 bg-primary/15' : 'mr-8 bg-muted/50'
                    )}
                  >
                    <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                      {m.role === 'user' ? '你' : '助手'}
                    </p>
                    {m.content}
                  </div>
                ))
              )}
            </div>

            <div className="mt-3 flex shrink-0 gap-2">
              <textarea
                className={cn(field, 'min-h-[5rem] flex-1 resize-none py-2')}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="输入消息…"
              />
              <button
                type="button"
                className={cn(btnPrimary, 'self-end')}
                disabled={!draft.trim() || sendMutation.isPending}
                onClick={() => sendMutation.mutate()}
              >
                {sendMutation.isPending ? '…' : '发送'}
              </button>
            </div>
          </>
        )}
      </section>

      <VariableFillDialog
        body={insertBody ?? ''}
        open={insertBody != null}
        onClose={() => setInsertBody(null)}
        onFilled={(text) => setDraft((d) => (d ? `${d}\n${text}` : text))}
      />
    </div>
  )
}

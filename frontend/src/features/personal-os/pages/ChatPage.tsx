import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { List, Plus, Trash2, X } from 'lucide-react'

import { useToastContext } from '@/App'
import {
  createOsChatSession,
  deleteOsChatSession,
  listOsChatMessages,
  listOsChatSessions,
  sendOsChatMessage,
  sendOsChatMessageStream,
  updateOsChatSession,
  type OsChatMessage,
} from '@/features/personal-os/api/chat'
import { PinToDashboardButton } from '@/features/personal-os/components/PinToDashboardButton'
import { useOsPinnedSet } from '@/features/personal-os/hooks/useOsPinnedSet'
import { useOsModelSelection } from '@/features/personal-os/stores/modelSelection'
import { cn } from '@/lib/utils'

const panel = 'flex min-h-0 flex-col rounded-xl border border-border bg-card'
const field = 'w-full rounded-md border border-input bg-background px-3 text-sm'
const btn =
  'inline-flex h-9 shrink-0 items-center justify-center rounded-md px-3 text-sm transition-colors'
const btnPrimary = cn(
  btn,
  'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50'
)

function parseSessionParam(raw: string | null): number | null {
  if (!raw) return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}

export function OsChatPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const providerId = useOsModelSelection((s) => s.providerId)
  const { isPinned } = useOsPinnedSet()
  const [params] = useSearchParams()
  const [sessionId, setSessionId] = useState<number | null>(() =>
    parseSessionParam(params.get('session'))
  )
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [creating, setCreating] = useState(false)
  const [streamText, setStreamText] = useState('')
  const [statusText, setStatusText] = useState('')
  const [localMessages, setLocalMessages] = useState<OsChatMessage[]>([])
  const [showSessions, setShowSessions] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const sendingRef = useRef(false)

  const { data: sessions = [] } = useQuery({
    queryKey: ['os-chat-sessions'],
    queryFn: listOsChatSessions,
  })

  const { data: messages = [], isFetching: loadingMessages } = useQuery({
    queryKey: ['os-chat-messages', sessionId],
    queryFn: () => listOsChatMessages(sessionId!),
    enabled: sessionId != null,
  })

  function selectSession(id: number) {
    setSessionId(id)
    setShowSessions(false)
    navigate(`/os/chat?session=${id}`, { replace: true })
  }

  useEffect(() => {
    // 发送过程中不要用服务端列表覆盖乐观更新
    if (sendingRef.current) return
    setLocalMessages(messages)
  }, [messages])

  // URL → state（浏览器前进/后退）
  useEffect(() => {
    const fromUrl = parseSessionParam(params.get('session'))
    if (fromUrl != null && fromUrl !== sessionId) {
      setSessionId(fromUrl)
    }
  }, [params, sessionId])

  // 有会话但未选中时，自动选第一个
  useEffect(() => {
    if (sessionId != null) return
    if (!sessions[0]) return
    selectSession(sessions[0].id)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when list arrives / selection empty
  }, [sessionId, sessions])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [localMessages, streamText])

  async function newSession() {
    if (creating) return
    setCreating(true)
    try {
      const s = await createOsChatSession({
        title: `对话 ${new Date().toLocaleString()}`,
        provider_id: providerId,
      })
      await queryClient.invalidateQueries({ queryKey: ['os-chat-sessions'] })
      selectSession(s.id)
    } catch (err) {
      toast.error((err as Error).message || '新建会话失败')
    } finally {
      setCreating(false)
    }
  }

  async function send() {
    if (!sessionId || !draft.trim() || sending) return
    if (providerId == null) {
      toast.error('请先在右上角选择一个已启用的模型')
      return
    }
    const content = draft.trim()
    setDraft('')
    setSending(true)
    sendingRef.current = true
    setStreamText('')
    setStatusText('正在发送…')
    setLocalMessages((prev) => [
      ...prev,
      {
        id: -Date.now(),
        session_id: sessionId,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      },
    ])
    let streamStarted = false
    try {
      try {
        await sendOsChatMessageStream(
          sessionId,
          { content, provider_id: providerId },
          (event) => {
            if (event.type === 'start' || event.type === 'status') {
              streamStarted = true
              if (event.type === 'status') setStatusText(event.message)
              else setStatusText('已连接，等待模型…')
            } else if (event.type === 'delta') {
              streamStarted = true
              setStatusText('')
              setStreamText((t) => t + event.text)
            } else if (event.type === 'done') {
              streamStarted = true
              setStatusText('')
              setStreamText(event.result)
            }
          }
        )
      } catch (streamErr) {
        // 仅在流式尚未真正开始时回退；开始后用户消息已落库，再发会重复
        if (!streamStarted) {
          setStatusText('流式不可用，改用普通请求…')
          setStreamText('')
          const msg = await sendOsChatMessage(sessionId, {
            content,
            provider_id: providerId,
          })
          setLocalMessages((prev) => [
            ...prev.filter((m) => m.id > 0 || m.content !== content),
            {
              id: -Date.now(),
              session_id: sessionId,
              role: 'user',
              content,
              created_at: new Date().toISOString(),
            },
            msg,
          ])
          setStreamText('')
        } else {
          throw streamErr
        }
      }
      await queryClient.invalidateQueries({
        queryKey: ['os-chat-messages', sessionId],
      })
      await queryClient.invalidateQueries({ queryKey: ['os-chat-sessions'] })
    } catch (err) {
      toast.error((err as Error).message || '发送失败，请检查模型设置')
      await queryClient.invalidateQueries({
        queryKey: ['os-chat-messages', sessionId],
      })
    } finally {
      sendingRef.current = false
      setSending(false)
      setStreamText('')
      setStatusText('')
    }
  }

  const sessionList = (
    <>
      <div className="mb-2 flex shrink-0 items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">会话</h2>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="inline-flex h-9 items-center gap-1 rounded-md border border-input px-2 text-xs hover:bg-accent disabled:opacity-50"
            disabled={creating}
            onClick={() => void newSession()}
          >
            <Plus className="h-3.5 w-3.5" /> {creating ? '创建中…' : '新建'}
          </button>
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-input lg:hidden"
            aria-label="关闭会话列表"
            onClick={() => setShowSessions(false)}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
      <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-contain">
        {sessions.map((s) => (
          <li key={s.id}>
            <div
              className={cn(
                'group flex min-h-11 items-center gap-1 rounded-md px-2 py-2 text-sm',
                sessionId === s.id ? 'bg-primary/15' : 'active:bg-accent hover:bg-accent'
              )}
            >
              <button
                type="button"
                className="min-w-0 flex-1 truncate py-1 text-left"
                onClick={() => selectSession(s.id)}
              >
                {s.title}
              </button>
              <PinToDashboardButton
                sourceType="chat_session"
                sourceId={s.id}
                pinned={isPinned('chat_session', s.id)}
                compact
              />
              <button
                type="button"
                className="inline-flex h-9 w-9 items-center justify-center"
                aria-label="删除会话"
                onClick={async () => {
                  try {
                    await deleteOsChatSession(s.id)
                    await queryClient.invalidateQueries({
                      queryKey: ['os-chat-sessions'],
                    })
                    if (sessionId === s.id) {
                      setSessionId(null)
                      navigate('/os/chat', { replace: true })
                    }
                  } catch (err) {
                    toast.error((err as Error).message || '删除失败')
                  }
                }}
              >
                <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </>
  )

  return (
    <div
      className="relative grid h-full min-h-0 gap-2 overflow-hidden sm:gap-3 lg:grid-cols-[15rem_minmax(0,1fr)]"
      data-testid="os-chat-page"
    >
      {/* 桌面侧栏 */}
      <section className={cn(panel, 'hidden min-h-0 p-3 lg:flex')}>{sessionList}</section>

      {/* 手机会话抽屉 */}
      {showSessions ? (
        <div className="absolute inset-0 z-20 flex lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="关闭会话列表遮罩"
            onClick={() => setShowSessions(false)}
          />
          <section
            className={cn(
              panel,
              'relative z-10 flex h-full w-[min(18rem,88vw)] flex-col p-3 shadow-xl'
            )}
          >
            {sessionList}
          </section>
        </div>
      ) : null}

      <section className={cn(panel, 'min-h-0 p-3 sm:p-4')}>
        {!sessionId ? (
          <div className="flex h-full flex-col items-start justify-center gap-3">
            <p className="text-sm text-muted-foreground">新建或选择一个会话开始</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className={btnPrimary}
                disabled={creating}
                onClick={() => void newSession()}
              >
                {creating ? '创建中…' : '新建对话'}
              </button>
              <button
                type="button"
                className="inline-flex h-9 items-center gap-1 rounded-md border border-input px-3 text-sm lg:hidden"
                onClick={() => setShowSessions(true)}
              >
                <List className="h-4 w-4" /> 会话列表
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="mb-2 flex shrink-0 items-center gap-2 sm:mb-3">
              <button
                type="button"
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-input lg:hidden"
                aria-label="打开会话列表"
                onClick={() => setShowSessions(true)}
              >
                <List className="h-4 w-4" />
              </button>
              <input
                className={cn(field, 'h-9 min-w-0 flex-1')}
                defaultValue={sessions.find((s) => s.id === sessionId)?.title}
                key={sessionId}
                onBlur={async (e) => {
                  const title = e.target.value.trim()
                  if (!title) return
                  try {
                    await updateOsChatSession(sessionId, { title })
                    await queryClient.invalidateQueries({
                      queryKey: ['os-chat-sessions'],
                    })
                  } catch (err) {
                    toast.error((err as Error).message || '重命名失败')
                  }
                }}
                aria-label="会话标题"
              />
            </div>

            <div className="min-h-0 flex-1 space-y-2.5 overflow-y-auto overscroll-contain sm:space-y-3">
              {loadingMessages ? (
                <p className="text-sm text-muted-foreground">加载消息…</p>
              ) : (
                localMessages.map((m) => (
                  <div
                    key={m.id}
                    className={cn(
                      'rounded-lg px-3 py-2 text-sm whitespace-pre-wrap break-words',
                      m.role === 'user'
                        ? 'ml-4 bg-primary/15 sm:ml-8'
                        : 'mr-4 bg-muted/50 sm:mr-8'
                    )}
                  >
                    <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                      {m.role === 'user' ? '你' : '助手'}
                    </p>
                    {m.content}
                  </div>
                ))
              )}
              {streamText ? (
                <div className="mr-4 rounded-lg bg-muted/50 px-3 py-2 text-sm whitespace-pre-wrap break-words sm:mr-8">
                  <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                    助手
                  </p>
                  {streamText}
                </div>
              ) : null}
              {sending && !streamText ? (
                <p className="text-sm text-muted-foreground">
                  {statusText || '正在等待模型回复…'}
                </p>
              ) : null}
              <div ref={bottomRef} />
            </div>

            <div className="mt-2 flex shrink-0 flex-col gap-2 sm:mt-3 sm:flex-row">
              <textarea
                className={cn(
                  field,
                  'min-h-[3.5rem] flex-1 resize-none py-2 text-base sm:min-h-[5rem] sm:text-sm'
                )}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="输入消息…"
                disabled={sending}
                enterKeyHint="send"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault()
                    void send()
                  }
                }}
              />
              <button
                type="button"
                className={cn(btnPrimary, 'h-11 w-full sm:h-9 sm:w-auto sm:self-end')}
                disabled={!draft.trim() || sending}
                onClick={() => void send()}
              >
                {sending ? '生成中' : '发送'}
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  )
}

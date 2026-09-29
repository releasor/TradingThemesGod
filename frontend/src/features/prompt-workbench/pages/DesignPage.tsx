import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

import { useToastContext } from '@/App'
import {
  designPromptStream,
  StreamAbortError,
  type StreamEvent,
} from '@/features/prompt-workbench/api/optimize'
import { createPromptItem } from '@/features/prompt-workbench/api/library'
import { PromptMarkdownPreview } from '@/features/prompt-workbench/components/PromptMarkdownPreview'
import { usePromptModelSelection } from '@/features/prompt-workbench/stores/modelSelection'
import { cn } from '@/lib/utils'

const panel = 'flex min-h-0 flex-col rounded-xl border border-border bg-card'
const field = 'w-full rounded-md border border-input bg-background px-3 text-sm'
const btn =
  'inline-flex h-9 shrink-0 items-center justify-center rounded-md px-3 text-sm transition-colors'
const btnPrimary = cn(btn, 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50')
const btnGhost = cn(btn, 'border border-input hover:bg-accent disabled:opacity-50')

export function DesignPage() {
  const toast = useToastContext()
  const navigate = useNavigate()
  const providerId = usePromptModelSelection((s) => s.providerId)
  const [goal, setGoal] = useState('')
  const [notes, setNotes] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamHint, setStreamHint] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit')
  const abortRef = useRef<AbortController | null>(null)
  const streamBufRef = useRef('')
  const streamRafRef = useRef<number | null>(null)
  const streamFirstDeltaRef = useRef(true)

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  function resetStreamUi() {
    if (streamRafRef.current != null) {
      cancelAnimationFrame(streamRafRef.current)
      streamRafRef.current = null
    }
    streamBufRef.current = ''
    streamFirstDeltaRef.current = true
    setStreamHint(null)
  }

  function handleStreamEvent(event: StreamEvent) {
    if (event.type === 'start') {
      setStreamHint('已连接，等待模型输出…')
      return
    }
    if (event.type === 'status') {
      setStreamHint(event.message)
      return
    }
    if (event.type === 'delta') {
      setStreamHint(null)
      if (streamFirstDeltaRef.current) {
        streamFirstDeltaRef.current = false
        flushSync(() => setResult((prev) => prev + event.text))
        return
      }
      streamBufRef.current += event.text
      if (streamRafRef.current == null) {
        streamRafRef.current = requestAnimationFrame(() => {
          const chunk = streamBufRef.current
          streamBufRef.current = ''
          streamRafRef.current = null
          if (chunk) setResult((prev) => prev + chunk)
        })
      }
      return
    }
    if (event.type === 'done') {
      if (streamRafRef.current != null) {
        cancelAnimationFrame(streamRafRef.current)
        streamRafRef.current = null
      }
      const pending = streamBufRef.current
      streamBufRef.current = ''
      setStreamHint(null)
      setResult(event.result || pending)
    }
  }

  function stopStreaming() {
    abortRef.current?.abort()
  }

  async function run() {
    if (!goal.trim()) {
      toast.warning('请填写设计目标')
      return
    }
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setLoading(true)
    setStreaming(true)
    setResult('')
    setViewMode('edit')
    resetStreamUi()
    setStreamHint('正在连接模型…')
    try {
      const res = await designPromptStream(
        {
          goal,
          notes: notes || undefined,
          provider_id: providerId,
        },
        handleStreamEvent,
        ac.signal
      )
      setResult(res.result)
      toast.success('设计完成')
    } catch (err) {
      if (err instanceof StreamAbortError) {
        if (err.reason === 'cancel') {
          toast.warning('已停止生成')
          return
        }
        toast.error(err.message)
        return
      }
      if ((err as Error).name === 'AbortError') return
      toast.error(err instanceof Error ? err.message : '设计失败')
    } finally {
      if (abortRef.current === ac) {
        resetStreamUi()
        setLoading(false)
        setStreaming(false)
      }
    }
  }

  return (
    <div
      className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3 overflow-y-auto lg:overflow-hidden"
      data-testid="prompt-design-page"
    >
      <div className="shrink-0">
        <h2 className="text-lg font-semibold tracking-tight">设计 Prompt</h2>
        <p className="text-sm text-muted-foreground">根据目标写出可复用 Prompt（流式生成）</p>
      </div>

      <div className="grid min-h-0 gap-3 lg:grid-cols-2 lg:overflow-hidden">
        <section className={cn(panel, 'min-h-[18rem] gap-3 p-4 lg:min-h-0')}>
          <label className="flex min-h-0 flex-[1.2] flex-col text-sm">
            <span className="mb-1.5 shrink-0 text-muted-foreground">设计目标</span>
            <textarea
              className={cn(field, 'min-h-[6rem] flex-1 resize-none py-2')}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              aria-label="设计目标"
            />
          </label>
          <label className="flex min-h-0 flex-1 flex-col text-sm">
            <span className="mb-1.5 shrink-0 text-muted-foreground">补充约束（可选）</span>
            <textarea
              className={cn(field, 'min-h-[4rem] flex-1 resize-none py-2')}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="受众、语气、输出格式…"
              aria-label="补充约束"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={cn(btnPrimary, 'min-w-[8rem]')}
              disabled={loading}
              onClick={() => void run()}
            >
              {streaming ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  生成中…
                </span>
              ) : loading ? (
                '处理中…'
              ) : (
                '生成 Prompt'
              )}
            </button>
            {streaming ? (
              <button type="button" className={btnGhost} onClick={stopStreaming}>
                停止
              </button>
            ) : null}
          </div>
        </section>

        <section className={cn(panel, 'min-h-[16rem] gap-3 p-4 lg:min-h-0')}>
          <div className="flex shrink-0 items-center justify-between gap-2">
            <h3 className="text-sm font-medium text-muted-foreground">
              生成结果
              {streaming ? (
                <span className="ml-2 text-xs font-normal">
                  {streamHint || '流式输出中'}
                </span>
              ) : null}
            </h3>
            <div className="flex gap-1 rounded-md border border-border p-0.5">
              <button
                type="button"
                className={cn(
                  'rounded px-2 py-1 text-xs',
                  viewMode === 'edit' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'
                )}
                onClick={() => setViewMode('edit')}
              >
                编辑
              </button>
              <button
                type="button"
                className={cn(
                  'rounded px-2 py-1 text-xs',
                  viewMode === 'preview'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground'
                )}
                onClick={() => setViewMode('preview')}
              >
                预览
              </button>
            </div>
          </div>

          <div className="relative flex min-h-[8rem] flex-1 flex-col lg:min-h-0">
            {streaming && !result ? (
              <div
                className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-muted/30"
                role="status"
              >
                <Loader2 className="h-7 w-7 animate-spin text-primary" />
                <p className="text-sm">{streamHint || '正在生成…'}</p>
                <button type="button" className={btnGhost} onClick={stopStreaming}>
                  停止
                </button>
              </div>
            ) : null}
            {viewMode === 'preview' ? (
              <PromptMarkdownPreview
                text={result}
                className="min-h-[8rem] flex-1 lg:min-h-0"
                empty="生成后可在此预览结构"
              />
            ) : (
              <textarea
                className={cn(field, 'min-h-[8rem] flex-1 resize-none py-2 lg:min-h-0')}
                value={result}
                onChange={(e) => setResult(e.target.value)}
                readOnly={streaming}
                placeholder="生成结果将流式显示在这里，可直接编辑"
                aria-label="生成结果"
              />
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={btnGhost}
              disabled={!result || streaming}
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(result)
                  toast.success('已复制')
                } catch {
                  toast.error('复制失败')
                }
              }}
            >
              复制
            </button>
            <button
              type="button"
              className={btnGhost}
              disabled={!result || streaming}
              onClick={async () => {
                try {
                  await createPromptItem({
                    title: `设计 ${new Date().toLocaleString()}`,
                    body: result,
                  })
                  toast.success('已存入库（仍可继续编辑）')
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : '存库失败')
                }
              }}
            >
              保存到库
            </button>
            <button
              type="button"
              className={btnGhost}
              disabled={!result || streaming}
              onClick={() =>
                navigate('/prompt/optimize', { state: { source: result } })
              }
            >
              送到优化
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

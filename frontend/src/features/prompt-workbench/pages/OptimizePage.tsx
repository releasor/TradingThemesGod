import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

import { fetchModelProviders } from '@/api/model-provider'
import { useToastContext } from '@/App'
import {
  iteratePromptStream,
  optimizePromptStream,
  type StreamEvent,
} from '@/features/prompt-workbench/api/optimize'
import { createPromptItem } from '@/features/prompt-workbench/api/library'
import {
  EXTRA_GOAL_CHIPS,
  OPTIMIZE_FRAMEWORKS,
  OPTIMIZE_SAMPLES,
  getFrameworkMeta,
  type FrameworkId,
} from '@/features/prompt-workbench/domain/frameworks'
import { lineDiff } from '@/features/prompt-workbench/domain/lineDiff'
import { usePromptModelSelection } from '@/features/prompt-workbench/stores/modelSelection'
import { cn } from '@/lib/utils'

const panel = 'flex min-h-0 flex-col rounded-xl border border-border bg-card'
const field = 'w-full rounded-md border border-input bg-background px-3 text-sm'
const btn =
  'inline-flex h-9 shrink-0 items-center justify-center rounded-md px-3 text-sm transition-colors'
const btnPrimary = cn(
  btn,
  'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50'
)
const btnGhost = cn(btn, 'border border-input hover:bg-accent disabled:opacity-50')

type LastAction =
  | { kind: 'optimize' }
  | { kind: 'iterate'; instruction: string }

function countChars(text: string) {
  return [...text].length
}

export function OptimizePage() {
  const toast = useToastContext()
  const navigate = useNavigate()
  const location = useLocation()
  const providerId = usePromptModelSelection((s) => s.providerId)

  const { data: providers = [] } = useQuery({
    queryKey: ['model-providers'],
    queryFn: fetchModelProviders,
  })
  const hasModel = providers.some((p) => p.enabled)

  const [source, setSource] = useState('')
  const [mode, setMode] = useState<'smart' | 'framework'>('smart')
  const [framework, setFramework] = useState<FrameworkId>('CRISPE')
  const [extraGoal, setExtraGoal] = useState('')
  const [result, setResult] = useState('')
  const [runId, setRunId] = useState<number | null>(null)
  const [versions, setVersions] = useState<string[]>([])
  const [versionIndex, setVersionIndex] = useState(0)
  const [instruction, setInstruction] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamHint, setStreamHint] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastAction, setLastAction] = useState<LastAction | null>(null)
  const [showCompare, setShowCompare] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const streamBufRef = useRef('')
  const streamRafRef = useRef<number | null>(null)
  const streamFirstDeltaRef = useRef(true)

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
        // 首包立刻上屏，避免 React 18 批量合并导致“干等”
        flushSync(() => {
          setResult((prev) => prev + event.text)
        })
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

  const frameworkMeta = getFrameworkMeta(framework)

  useEffect(() => {
    const fromState = (location.state as { source?: string } | null)?.source
    if (fromState) setSource(fromState)
  }, [location.state])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  function appendChip(value: string) {
    setExtraGoal((prev) => {
      if (!prev.trim()) return value
      if (prev.includes(value)) return prev
      return `${prev}；${value}`
    })
  }

  async function runOptimize() {
    if (!hasModel) {
      toast.warning('请先配置可用模型')
      return
    }
    if (!source.trim()) {
      toast.warning('请先填写原始 Prompt')
      return
    }
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setLoading(true)
    setStreaming(true)
    setError(null)
    setLastAction({ kind: 'optimize' })
    setResult('')
    setShowCompare(false)
    resetStreamUi()
    setStreamHint('正在连接模型…')
    try {
      const res = await optimizePromptStream(
        {
          source,
          mode,
          framework: mode === 'framework' ? framework : null,
          extra_goal: mode === 'smart' ? extraGoal || null : null,
          provider_id: providerId,
          persist: true,
        },
        handleStreamEvent,
        ac.signal
      )
      setResult(res.result)
      setRunId(res.run_id)
      setVersions([res.result])
      setVersionIndex(0)
      toast.success('优化完成')
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      const message = err instanceof Error ? err.message : '优化失败'
      setError(message)
      toast.error(message)
    } finally {
      if (abortRef.current === ac) {
        resetStreamUi()
        setLoading(false)
        setStreaming(false)
      }
    }
  }

  async function runIterate(forcedInstruction?: string) {
    const text = (forcedInstruction ?? instruction).trim()
    if (!hasModel) {
      toast.warning('请先配置可用模型')
      return
    }
    if (!result.trim() || !text) return
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setLoading(true)
    setStreaming(true)
    setError(null)
    setLastAction({ kind: 'iterate', instruction: text })
    const base = result
    setResult('')
    setShowCompare(false)
    resetStreamUi()
    setStreamHint('正在连接模型…')
    try {
      const res = await iteratePromptStream(
        {
          run_id: runId,
          current: base,
          instruction: text,
          provider_id: providerId,
        },
        handleStreamEvent,
        ac.signal
      )
      setResult(res.result)
      setRunId(res.run_id)
      setVersions((v) => {
        const next = [...v, res.result]
        setVersionIndex(next.length - 1)
        return next
      })
      setInstruction('')
      toast.success('已迭代')
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      setResult(base)
      const message = err instanceof Error ? err.message : '迭代失败'
      setError(message)
      toast.error(message)
    } finally {
      if (abortRef.current === ac) {
        resetStreamUi()
        setLoading(false)
        setStreaming(false)
      }
    }
  }

  function retryLast() {
    if (!lastAction) return
    if (lastAction.kind === 'optimize') void runOptimize()
    else void runIterate(lastAction.instruction)
  }

  function useResultAsSource() {
    if (!result.trim()) return
    setSource(result)
    toast.success('已将结果填入原文，可继续优化')
  }

  function selectVersion(index: number) {
    setVersionIndex(index)
    setResult(versions[index] ?? '')
  }

  const compareDiff =
    showCompare && versionIndex > 0
      ? lineDiff(versions[versionIndex - 1] ?? '', versions[versionIndex] ?? result)
      : null

  return (
    <div
      className="grid h-full min-h-0 grid-rows-[auto_minmax(12rem,1fr)] gap-3 overflow-y-auto lg:overflow-hidden"
      data-testid="prompt-optimize-page"
    >
      <div className="flex shrink-0 flex-wrap items-end justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold tracking-tight">优化 Prompt</h2>
          <p className="text-sm text-muted-foreground">
            Smart 或命名框架，流式生成结果并支持迭代
          </p>
        </div>
        {!hasModel ? (
          <p className="text-sm text-amber-600 dark:text-amber-400">
            尚未配置模型，请先前往{' '}
            <Link to="/settings/models?from=prompt" className="underline underline-offset-2">
              模型设置
            </Link>
          </p>
        ) : null}
      </div>

      <div className="grid min-h-0 gap-3 lg:grid-cols-2 lg:overflow-hidden">
        {/* 左侧：输入 */}
        <section className={cn(panel, 'min-h-[16rem] gap-3 p-4 lg:min-h-0')}>
          <div className="flex shrink-0 items-center justify-between gap-2">
            <span className="text-sm text-muted-foreground">原始 Prompt</span>
            <span className="text-xs text-muted-foreground tabular-nums">
              {countChars(source)} 字
            </span>
          </div>
          <textarea
            className={cn(field, 'min-h-[8rem] flex-1 resize-none py-2')}
            value={source}
            onChange={(e) => setSource(e.target.value)}
            aria-label="原始 Prompt"
            placeholder="粘贴或输入待优化的 Prompt…"
          />

          {!source.trim() ? (
            <div className="shrink-0 space-y-2 rounded-md border border-dashed border-border/80 p-3">
              <p className="text-xs text-muted-foreground">试试这些样例</p>
              <div className="flex flex-wrap gap-2">
                {OPTIMIZE_SAMPLES.map((sample) => (
                  <button
                    key={sample.title}
                    type="button"
                    className={btnGhost}
                    onClick={() => setSource(sample.body)}
                  >
                    {sample.title}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="flex shrink-0 flex-wrap gap-2">
            <button
              type="button"
              className={cn(
                btn,
                mode === 'smart'
                  ? 'bg-primary text-primary-foreground'
                  : 'border border-input hover:bg-accent'
              )}
              aria-pressed={mode === 'smart'}
              onClick={() => setMode('smart')}
            >
              Smart
            </button>
            <button
              type="button"
              className={cn(
                btn,
                mode === 'framework'
                  ? 'bg-primary text-primary-foreground'
                  : 'border border-input hover:bg-accent'
              )}
              aria-pressed={mode === 'framework'}
              onClick={() => setMode('framework')}
            >
              命名框架
            </button>
          </div>

          {mode === 'smart' ? (
            <div className="shrink-0 space-y-2" data-testid="extra-goal-field">
              <label className="block text-sm">
                <span className="mb-1.5 block text-muted-foreground">补充目标（可选）</span>
                <input
                  className={cn(field, 'h-9')}
                  value={extraGoal}
                  onChange={(e) => setExtraGoal(e.target.value)}
                  placeholder="例如：更短、更正式"
                />
              </label>
              <div className="flex flex-wrap gap-1.5">
                {EXTRA_GOAL_CHIPS.map((chip) => (
                  <button
                    key={chip.id}
                    type="button"
                    className="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                    onClick={() => appendChip(chip.value)}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="shrink-0 space-y-2">
              <label className="block text-sm">
                <span className="mb-1.5 block text-muted-foreground">框架</span>
                <select
                  className={cn(field, 'h-9')}
                  value={framework}
                  onChange={(e) => setFramework(e.target.value as FrameworkId)}
                >
                  {OPTIMIZE_FRAMEWORKS.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.label} — {f.hint}
                    </option>
                  ))}
                </select>
              </label>
              {frameworkMeta ? (
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {frameworkMeta.description}
                </p>
              ) : null}
            </div>
          )}

          <button
            type="button"
            className={cn(btnPrimary, 'w-full')}
            disabled={loading || !hasModel}
            onClick={() => void runOptimize()}
          >
            {streaming && lastAction?.kind === 'optimize' ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                生成中…
              </span>
            ) : loading ? (
              '处理中…'
            ) : (
              '运行优化'
            )}
          </button>
        </section>

        {/* 右侧：结果 + 操作 */}
        <section className={cn(panel, 'min-h-[16rem] gap-3 p-4 lg:min-h-0')}>
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-medium text-muted-foreground">优化结果</h3>
              <span
                className="text-xs text-muted-foreground tabular-nums"
                aria-live="polite"
              >
                {countChars(result)} 字
                {streaming ? (streamHint ? ` · ${streamHint}` : ' · 流式输出中') : ''}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className={btnGhost}
                disabled={!result || streaming}
                onClick={async () => {
                  await navigator.clipboard.writeText(result)
                  toast.success('已复制')
                }}
              >
                复制
              </button>
              <button
                type="button"
                className={btnGhost}
                disabled={!result || streaming}
                onClick={async () => {
                  await createPromptItem({
                    title: `优化 ${new Date().toLocaleString()}`,
                    body: result,
                  })
                  toast.success('已存入库')
                  navigate('/prompt/library')
                }}
              >
                存库
              </button>
              <button
                type="button"
                className={btnGhost}
                disabled={!result || streaming}
                onClick={useResultAsSource}
              >
                用作原文继续
              </button>
              {error ? (
                <button type="button" className={btnPrimary} disabled={loading} onClick={retryLast}>
                  重试
                </button>
              ) : null}
            </div>
          </div>

          {error ? (
            <p
              role="alert"
              className="shrink-0 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
            >
              {error}
            </p>
          ) : null}

          <div className="relative flex min-h-[8rem] flex-1 flex-col lg:min-h-0">
            {streaming && !result ? (
              <div
                data-testid="optimize-result-loading"
                className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-muted/30 px-4"
                role="status"
                aria-live="polite"
                aria-busy="true"
              >
                <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
                <div className="space-y-1 text-center">
                  <p className="text-sm font-medium text-foreground">
                    {streamHint || '正在生成优化结果…'}
                  </p>
                  <p className="text-xs text-muted-foreground">模型较慢时会在此等待，首字出现后开始流式显示</p>
                </div>
                <div className="flex w-40 items-center gap-1" aria-hidden="true">
                  <span className="h-1.5 flex-1 animate-pulse rounded-full bg-primary/70" />
                  <span className="h-1.5 flex-1 animate-pulse rounded-full bg-primary/50 [animation-delay:150ms]" />
                  <span className="h-1.5 flex-1 animate-pulse rounded-full bg-primary/30 [animation-delay:300ms]" />
                </div>
              </div>
            ) : null}
            <textarea
              className={cn(field, 'min-h-[8rem] flex-1 resize-none py-2 lg:min-h-0')}
              value={result}
              onChange={(e) => setResult(e.target.value)}
              placeholder={
                streaming
                  ? streamHint || '模型输出中…'
                  : '运行优化后，结果将在此流式显示并可编辑'
              }
              aria-label="优化结果"
            />
          </div>

          <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
            <input
              className={cn(field, 'h-9 min-w-0 flex-1')}
              placeholder="迭代指令，例如：语气更正式"
              aria-label="迭代指令"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              disabled={!result || streaming}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void runIterate()
                }
              }}
            />
            <button
              type="button"
              className={btnPrimary}
              disabled={loading || !instruction.trim() || !result.trim() || !hasModel}
              onClick={() => void runIterate()}
            >
              {streaming && lastAction?.kind === 'iterate' ? '迭代中…' : '迭代'}
            </button>
          </div>

          {versions.length > 0 ? (
            <div className="min-h-0 shrink-0 space-y-2 border-t border-border pt-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">版本历史</p>
                {versions.length > 1 ? (
                  <button
                    type="button"
                    className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                    onClick={() => setShowCompare((v) => !v)}
                    disabled={versionIndex === 0}
                  >
                    {showCompare ? '关闭对比' : '与上一版对比'}
                  </button>
                ) : null}
              </div>
              <ol className="flex max-h-24 list-none flex-wrap gap-2 overflow-y-auto">
                {versions.map((v, i) => (
                  <li key={i}>
                    <button
                      type="button"
                      className={cn(
                        'rounded-md border px-2 py-1 text-left text-xs',
                        i === versionIndex
                          ? 'border-primary bg-primary/10 text-foreground'
                          : 'border-border text-muted-foreground hover:bg-accent hover:text-foreground'
                      )}
                      onClick={() => selectVersion(i)}
                    >
                      v{i + 1}
                      {i === versions.length - 1 ? ' · 当前' : ''}
                    </button>
                  </li>
                ))}
              </ol>
              {compareDiff ? (
                <div
                  className="max-h-40 overflow-auto rounded-md border border-border bg-muted/20 p-2 font-mono text-xs leading-relaxed"
                  data-testid="version-diff"
                >
                  {compareDiff.map((line, idx) => (
                    <div
                      key={idx}
                      className={cn(
                        'whitespace-pre-wrap',
                        line.type === 'add' && 'bg-emerald-500/15 text-emerald-800 dark:text-emerald-300',
                        line.type === 'del' && 'bg-rose-500/15 text-rose-800 dark:text-rose-300 line-through'
                      )}
                    >
                      {line.type === 'add' ? '+ ' : line.type === 'del' ? '- ' : '  '}
                      {line.text || ' '}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  )
}

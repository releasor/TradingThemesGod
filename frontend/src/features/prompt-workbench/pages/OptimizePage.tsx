import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

import { fetchModelProviders } from '@/api/model-provider'
import { useToastContext } from '@/App'
import {
  dualTestPrompts,
  getOptimizeRun,
  iteratePromptStream,
  listOptimizeRuns,
  optimizePromptStream,
  StreamAbortError,
  type OptimizeRunSummary,
  type StreamEvent,
} from '@/features/prompt-workbench/api/optimize'
import { createPromptItem } from '@/features/prompt-workbench/api/library'
import { PromptMarkdownPreview } from '@/features/prompt-workbench/components/PromptMarkdownPreview'
import {
  EXTRA_GOAL_CHIPS,
  ITERATE_CHIPS,
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

type VersionEntry = { text: string; label: string }

type CompareMode = 'off' | 'prev' | 'source'

function countChars(text: string) {
  return [...text].length
}

export function OptimizePage() {
  const toast = useToastContext()
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
  const [versions, setVersions] = useState<VersionEntry[]>([])
  const [versionIndex, setVersionIndex] = useState(0)
  const [instruction, setInstruction] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamHint, setStreamHint] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastAction, setLastAction] = useState<LastAction | null>(null)
  const [compareMode, setCompareMode] = useState<CompareMode>('off')
  const [testMessage, setTestMessage] = useState('')
  const [testLoading, setTestLoading] = useState(false)
  const [testOutputs, setTestOutputs] = useState<{ a: string; b: string } | null>(null)
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit')
  const [showHistory, setShowHistory] = useState(false)
  const [historyRuns, setHistoryRuns] = useState<OptimizeRunSummary[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
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
      setStreamHint('已连接后端，等待模型首字（推理模型可能需 10–30 秒）…')
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
      if (event.run_id != null) setRunId(event.run_id)
      return
    }
    if (event.type === 'persisted') {
      setRunId(event.run_id)
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

  function stopStreaming() {
    abortRef.current?.abort()
  }

  function updateResult(text: string) {
    setResult(text)
    setVersions((prev) => {
      if (prev.length === 0) return prev
      const next = [...prev]
      const cur = next[versionIndex]
      if (!cur) return prev
      next[versionIndex] = { ...cur, text }
      return next
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
    setCompareMode('off')
    setTestOutputs(null)
    resetStreamUi()
    setStreamHint('正在连接后端并请求模型…')
    try {
      const res = await optimizePromptStream(
        {
          source,
          mode,
          framework: mode === 'framework' ? framework : null,
          extra_goal: extraGoal || null,
          provider_id: providerId,
          persist: true,
        },
        handleStreamEvent,
        ac.signal
      )
      if (!res.result.trim()) {
        const message = '模型未返回任何内容，请检查模型渠道或更换模型后重试'
        setError(message)
        toast.error(message)
        return
      }
      setResult(res.result)
      if (res.run_id != null) setRunId(res.run_id)
      setVersions([{ text: res.result, label: '初稿' }])
      setVersionIndex(0)
      toast.success('优化完成')
    } catch (err) {
      if (err instanceof StreamAbortError) {
        if (err.reason === 'cancel') {
          toast.warning('已停止生成')
          return
        }
        setError(err.message)
        toast.error(err.message)
        return
      }
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
    setCompareMode('off')
    resetStreamUi()
    setStreamHint('正在连接后端并请求模型…')
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
      if (res.run_id != null) setRunId(res.run_id)
      setVersions((v) => {
        const next = [...v, { text: res.result, label: text.slice(0, 24) }]
        setVersionIndex(next.length - 1)
        return next
      })
      setInstruction('')
      toast.success('已迭代')
    } catch (err) {
      if (err instanceof StreamAbortError) {
        setResult(base)
        if (err.reason === 'cancel') {
          toast.warning('已停止生成')
          return
        }
        setError(err.message)
        toast.error(err.message)
        return
      }
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
    setResult(versions[index]?.text ?? '')
    setCompareMode('off')
  }

  const compareDiff =
    compareMode === 'prev' && versionIndex > 0
      ? lineDiff(versions[versionIndex - 1]?.text ?? '', versions[versionIndex]?.text ?? result)
      : compareMode === 'source'
        ? lineDiff(source, result)
        : null

  async function saveToLibrary() {
    if (!result.trim()) return
    try {
      await createPromptItem({
        title: `优化 ${new Date().toLocaleString()}`,
        body: result,
      })
      toast.success('已存入库（仍可继续优化）')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '存库失败')
    }
  }

  async function copyResult() {
    try {
      await navigator.clipboard.writeText(result)
      toast.success('已复制')
    } catch {
      toast.error('复制失败')
    }
  }

  async function loadHistory() {
    setHistoryLoading(true)
    try {
      const rows = await listOptimizeRuns(20)
      setHistoryRuns(rows)
      setShowHistory(true)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载历史失败')
    } finally {
      setHistoryLoading(false)
    }
  }

  async function applyHistoryRun(id: number) {
    try {
      const detail = await getOptimizeRun(id)
      const versionEntries: VersionEntry[] = (detail.versions ?? []).map((v, i) => {
        if (typeof v === 'string') {
          return { text: v, label: i === 0 ? '初始优化' : `版本 ${i + 1}` }
        }
        return {
          text: v.result ?? detail.result,
          label: v.instruction?.trim() || (i === 0 ? '初始优化' : `版本 ${i + 1}`),
        }
      })
      if (versionEntries.length === 0) {
        versionEntries.push({ text: detail.result, label: '初始优化' })
      }
      setSource(detail.source)
      setResult(detail.result)
      setRunId(detail.id)
      setMode(detail.mode === 'framework' ? 'framework' : 'smart')
      if (detail.framework) {
        setFramework(detail.framework as FrameworkId)
      }
      setExtraGoal(detail.extra_goal ?? '')
      setVersions(versionEntries)
      setVersionIndex(versionEntries.length - 1)
      setCompareMode('off')
      setError(null)
      setTestOutputs(null)
      setViewMode('edit')
      toast.success('已载入历史运行')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '载入失败')
    }
  }

  async function runDualTest() {
    if (!hasModel) {
      toast.warning('请先配置可用模型')
      return
    }
    if (!source.trim() || !result.trim() || !testMessage.trim()) {
      toast.warning('需要原文、优化结果和测试用户消息')
      return
    }
    setTestLoading(true)
    setTestOutputs(null)
    try {
      const res = await dualTestPrompts({
        prompt_a: source,
        prompt_b: result,
        user_message: testMessage,
        provider_id: providerId,
      })
      setTestOutputs({ a: res.output_a, b: res.output_b })
      toast.success('双测完成')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '双测失败')
    } finally {
      setTestLoading(false)
    }
  }

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

          {mode === 'framework' ? (
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
          ) : null}

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

          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              className={cn(btnPrimary, 'flex-1')}
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
            {streaming ? (
              <button
                type="button"
                className={btnGhost}
                data-testid="optimize-stop"
                onClick={stopStreaming}
              >
                停止
              </button>
            ) : null}
          </div>
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
                        <div className="flex flex-wrap items-center gap-2">
              <div className="flex gap-1 rounded-md border border-border p-0.5">
                <button
                  type="button"
                  className={cn(
                    'rounded px-2 py-1 text-xs',
                    viewMode === 'edit'
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground'
                  )}
                  onClick={() => setViewMode('edit')}
                  data-testid="optimize-view-edit"
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
                  data-testid="optimize-view-preview"
                >
                  预览
                </button>
              </div>
              <button
                type="button"
                className={btnGhost}
                disabled={historyLoading || streaming}
                onClick={() => {
                  if (showHistory) {
                    setShowHistory(false)
                  } else {
                    void loadHistory()
                  }
                }}
                data-testid="optimize-history-toggle"
              >
                {historyLoading ? '加载中…' : showHistory ? '收起历史' : '运行历史'}
              </button>
              <button
                type="button"
                className={btnGhost}
                disabled={!result || streaming}
                onClick={() => void copyResult()}
              >
                复制
              </button>
              <button
                type="button"
                className={btnGhost}
                disabled={!result || streaming}
                onClick={() => void saveToLibrary()}
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
                <button type="button" className={btnGhost} onClick={stopStreaming}>
                  停止
                </button>
              </div>
            ) : null}
            {viewMode === 'preview' ? (
              <PromptMarkdownPreview
                text={result}
                className="min-h-[8rem] flex-1 lg:min-h-0"
                empty="优化后可在此预览结构"
              />
            ) : (
              <textarea
                className={cn(field, 'min-h-[8rem] flex-1 resize-none py-2 lg:min-h-0')}
                value={result}
                onChange={(e) => updateResult(e.target.value)}
                readOnly={streaming}
                placeholder={
                  streaming
                    ? streamHint || '模型输出中…'
                    : '运行优化后，结果将在此流式显示并可编辑'
                }
                aria-label="优化结果"
              />
            )}
          </div>

          {showHistory ? (
            <div
              className="shrink-0 space-y-2 rounded-md border border-border bg-muted/20 p-3"
              data-testid="optimize-history-panel"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">最近运行</p>
                <button
                  type="button"
                  className="text-xs text-muted-foreground underline-offset-2 hover:underline"
                  disabled={historyLoading}
                  onClick={() => void loadHistory()}
                >
                  刷新
                </button>
              </div>
              {historyRuns.length === 0 ? (
                <p className="text-xs text-muted-foreground">暂无历史记录</p>
              ) : (
                <ul className="max-h-40 space-y-1 overflow-y-auto">
                  {historyRuns.map((run) => (
                    <li key={run.id}>
                      <button
                        type="button"
                        className="flex w-full flex-col gap-0.5 rounded-md border border-transparent px-2 py-1.5 text-left text-xs hover:border-border hover:bg-accent"
                        onClick={() => void applyHistoryRun(run.id)}
                        disabled={streaming}
                      >
                        <span className="line-clamp-1 font-medium text-foreground">
                          {run.result.slice(0, 80) || run.source.slice(0, 80) || `运行 #${run.id}`}
                        </span>
                        <span className="text-muted-foreground">
                          {new Date(run.updated_at).toLocaleString()} · {run.mode}
                          {run.framework ? `/${run.framework}` : ''} · v{run.version_count}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}

          <div className="shrink-0 space-y-2">
            <div className="flex flex-wrap gap-1.5">
              {ITERATE_CHIPS.map((chip) => (
                <button
                  key={chip.id}
                  type="button"
                  className="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50"
                  disabled={!result || streaming}
                  onClick={() => void runIterate(chip.value)}
                >
                  {chip.label}
                </button>
              ))}
            </div>
          <div className="flex flex-col gap-2 sm:flex-row">
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
          </div>

          {versions.length > 0 ? (
            <div className="min-h-0 shrink-0 space-y-2 border-t border-border pt-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">版本历史</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                    disabled={!result}
                    onClick={() =>
                      setCompareMode((m) => (m === 'source' ? 'off' : 'source'))
                    }
                  >
                    {compareMode === 'source' ? '关闭原文对比' : '与原文对比'}
                  </button>
                  {versions.length > 1 ? (
                    <button
                      type="button"
                      className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline disabled:opacity-50"
                      onClick={() =>
                        setCompareMode((m) => (m === 'prev' ? 'off' : 'prev'))
                      }
                      disabled={versionIndex === 0}
                    >
                      {compareMode === 'prev' ? '关闭版本对比' : '与上一版对比'}
                    </button>
                  ) : null}
                </div>
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
                      title={v.label}
                    >
                      v{i + 1} · {v.label}
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

          {result.trim() && source.trim() ? (
            <div
              className="min-h-0 shrink-0 space-y-2 border-t border-border pt-3"
              data-testid="dual-test-panel"
            >
              <p className="text-xs font-medium text-muted-foreground">
                双测：同一用户消息对比优化前 / 后
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  className={cn(field, 'h-9 min-w-0 flex-1')}
                  placeholder="测试用户消息"
                  aria-label="双测用户消息"
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  disabled={testLoading || streaming}
                />
                <button
                  type="button"
                  className={btnGhost}
                  disabled={testLoading || streaming || !testMessage.trim() || !hasModel}
                  onClick={() => void runDualTest()}
                >
                  {testLoading ? '双测中…' : '运行双测'}
                </button>
              </div>
              {testOutputs ? (
                <div className="grid max-h-48 gap-2 overflow-auto sm:grid-cols-2">
                  <div className="rounded-md border border-border p-2">
                    <p className="mb-1 text-xs text-muted-foreground">优化前输出</p>
                    <pre className="whitespace-pre-wrap text-xs leading-relaxed">
                      {testOutputs.a}
                    </pre>
                  </div>
                  <div className="rounded-md border border-border p-2">
                    <p className="mb-1 text-xs text-muted-foreground">优化后输出</p>
                    <pre className="whitespace-pre-wrap text-xs leading-relaxed">
                      {testOutputs.b}
                    </pre>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

        </section>
      </div>
    </div>
  )
}

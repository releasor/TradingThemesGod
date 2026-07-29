import { useEffect, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import {
  Bot,
  Check,
  Copy,
  Cpu,
  KeyRound,
  Loader2,
  Plus,
  Save,
  Settings,
  Sparkles,
  Trash2,
  Wifi,
  Zap,
} from 'lucide-react'
import { AppCardNav } from '@/components/AppCardNav'
import { SettingsSubnav } from '@/components/SettingsSubnav'
import { GlowCard } from '@/components/GlowCard'
import { cn } from '@/lib/utils'
import {
  deleteModelProvider,
  fetchModelProviders,
  fetchProviderModels,
  saveModelProvider,
  testModelProvider,
  type ModelProtocol,
  type ModelProvider,
  type ModelProviderInput,
} from '@/api/model-provider'

const emptyForm: ModelProviderInput = {
  name: '',
  protocol: 'openai_compatible',
  base_url: '',
  api_key: '',
  model: '',
  custom_headers: {},
  timeout_seconds: 120,
  temperature: 0.1,
  max_tokens: 8192,
  enabled: true,
  is_default: true,
}

const PROTOCOL_META: Record<
  ModelProtocol,
  { label: string; hint: string; accent: string; icon: typeof Bot }
> = {
  openai_compatible: {
    label: 'OpenAI 兼容',
    hint: '中转端 / DeepSeek / 通义等',
    accent: 'from-emerald-500/20 to-teal-500/10 text-emerald-700 dark:text-emerald-300',
    icon: Zap,
  },
  anthropic: {
    label: 'Anthropic',
    hint: 'Claude 官方或兼容端',
    accent: 'from-amber-500/20 to-orange-500/10 text-amber-700 dark:text-amber-300',
    icon: Sparkles,
  },
  gemini: {
    label: 'Gemini',
    hint: 'Google AI Studio',
    accent: 'from-sky-500/20 to-blue-500/10 text-sky-700 dark:text-sky-300',
    icon: Bot,
  },
  ollama: {
    label: 'Ollama',
    hint: '本地推理服务',
    accent: 'from-violet-500/20 to-purple-500/10 text-violet-700 dark:text-violet-300',
    icon: Cpu,
  },
}

const pageMotion = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as const },
}

const listItemMotion = {
  initial: { opacity: 0, x: -16 },
  animate: { opacity: 1, x: 0 },
}

function errorMessage(error: unknown): string {
  const value = error as {
    response?: { data?: { detail?: string; message?: string } }
    message?: string
  }
  return (
    value.response?.data?.detail || value.response?.data?.message || value.message || '操作失败'
  )
}

function textToHeaders(text: string): Record<string, string> {
  return Object.fromEntries(
    text
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const index = line.indexOf(':')
        if (index < 1) throw new Error(`请求头格式错误：${line}`)
        return [line.slice(0, index).trim(), line.slice(index + 1).trim()]
      })
  )
}

function headersToText(headers: Record<string, string>): string {
  return Object.entries(headers)
    .map(([key, value]) => `${key}: ${value}`)
    .join('\n')
}

function providerToForm(provider: ModelProvider): ModelProviderInput {
  return {
    name: provider.name,
    protocol: provider.protocol,
    base_url: provider.base_url,
    api_key: provider.api_key,
    model: provider.model,
    custom_headers: provider.custom_headers,
    timeout_seconds: provider.timeout_seconds,
    temperature: provider.temperature,
    max_tokens: provider.max_tokens,
    enabled: provider.enabled,
    is_default: provider.is_default,
  }
}

function FieldLabel({
  children,
  hint,
}: {
  children: ReactNode
  hint?: string
}) {
  return (
    <span className="flex flex-col gap-0.5">
      <span className="font-medium text-foreground">{children}</span>
      {hint ? <span className="text-xs font-normal text-muted-foreground">{hint}</span> : null}
    </span>
  )
}

function inputClassName(extra?: string) {
  return cn(
    'w-full rounded-xl border border-input/80 bg-background/80 px-3 py-2.5 text-sm shadow-sm',
    'transition-all duration-200 placeholder:text-muted-foreground/70',
    'focus:border-primary/50 focus:bg-background focus:outline-none focus:ring-2 focus:ring-primary/20',
    extra
  )
}

export function ModelSettings() {
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | undefined>()
  const [form, setForm] = useState<ModelProviderInput>(emptyForm)
  const [headerText, setHeaderText] = useState('')
  const [notice, setNotice] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(
    null
  )
  const [copiedKey, setCopiedKey] = useState(false)

  const { data: providers = [], isLoading } = useQuery({
    queryKey: ['model-providers'],
    queryFn: fetchModelProviders,
  })

  useEffect(() => {
    if (editingId !== undefined || providers.length === 0) return
    selectProvider(providers[0])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingId, providers])

  const saveMutation = useMutation({
    mutationFn: () =>
      saveModelProvider({ ...form, custom_headers: textToHeaders(headerText) }, editingId),
    onSuccess: async (provider) => {
      applyProvider(provider)
      setNotice({ type: 'success', message: '配置已加密保存' })
      await queryClient.invalidateQueries({ queryKey: ['model-providers'] })
    },
    onError: (error) => setNotice({ type: 'error', message: errorMessage(error) }),
  })

  const testMutation = useMutation({
    mutationFn: () => testModelProvider(editingId!),
    onSuccess: (message) => setNotice({ type: 'success', message: `连接成功：${message}` }),
    onError: (error) => setNotice({ type: 'error', message: errorMessage(error) }),
  })

  const modelsMutation = useMutation({
    mutationFn: () => fetchProviderModels(editingId!),
    onSuccess: (models) =>
      setNotice({
        type: 'info',
        message: models.length ? `可用模型：${models.join('、')}` : '服务未返回模型列表',
      }),
    onError: (error) => setNotice({ type: 'error', message: errorMessage(error) }),
  })

  function applyProvider(provider: ModelProvider) {
    setEditingId(provider.id)
    setForm(providerToForm(provider))
    setHeaderText(headersToText(provider.custom_headers))
    setNotice(null)
  }

  function selectProvider(provider: ModelProvider) {
    applyProvider(provider)
  }

  function startNewProvider() {
    setEditingId(undefined)
    setForm(emptyForm)
    setHeaderText('')
    setNotice(null)
  }

  const set = <K extends keyof ModelProviderInput>(key: K, value: ModelProviderInput[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  const protocolMeta = PROTOCOL_META[form.protocol]
  const ProtocolIcon = protocolMeta.icon
  const isBusy = saveMutation.isPending || testMutation.isPending || modelsMutation.isPending

  async function copyApiKey() {
    if (!form.api_key) return
    await navigator.clipboard.writeText(form.api_key)
    setCopiedKey(true)
    window.setTimeout(() => setCopiedKey(false), 1600)
  }

  return (
    <div className="min-h-screen">
      <AppCardNav />

      <div className="mx-auto w-full max-w-none space-y-5 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Settings className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">模型设置</h1>
              <p className="text-sm text-muted-foreground">配置图谱分析使用的模型服务</p>
            </div>
          </div>
          <SettingsSubnav />
        </div>

        <motion.div
          {...pageMotion}
          transition={{ ...pageMotion.transition, delay: 0.06 }}
          className="grid w-full gap-6 lg:grid-cols-[280px_1fr]"
        >
        <aside className="space-y-4 lg:sticky lg:top-28 lg:self-start">
          <GlowCard animated className="overflow-hidden">
            <div className="p-4">
              <motion.button
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                onClick={startNewProvider}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-shadow hover:shadow-md"
              >
                <Plus className="h-4 w-4" />
                新增配置
              </motion.button>

              <div className="mt-4 space-y-2">
                {isLoading &&
                  Array.from({ length: 3 }).map((_, index) => (
                    <div
                      key={index}
                      className="h-[72px] animate-pulse rounded-xl border border-border/60 bg-muted/40"
                    />
                  ))}

                {!isLoading && providers.length === 0 && (
                  <p className="rounded-xl border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
                    暂无配置，点击上方按钮创建
                  </p>
                )}

                <AnimatePresence initial={false}>
                  {providers.map((provider, index) => {
                    const meta = PROTOCOL_META[provider.protocol]
                    const Icon = meta.icon
                    const selected = editingId === provider.id

                    return (
                      <motion.button
                        key={provider.id}
                        layout
                        {...listItemMotion}
                        transition={{ delay: index * 0.04, duration: 0.28 }}
                        onClick={() => selectProvider(provider)}
                        className={cn(
                          'group relative w-full overflow-hidden rounded-xl border px-3 py-3 text-left transition-all duration-300',
                          selected
                            ? 'border-primary/60 bg-primary/5 shadow-[0_0_0_1px_hsl(var(--primary)/0.25)]'
                            : 'border-border/70 bg-background/50 hover:border-primary/30 hover:bg-accent/40'
                        )}
                      >
                        <span
                          className={cn(
                            // 暗色主题 --primary 接近白，勿用 bg-primary，否则像一条白竖线
                            'absolute inset-y-0 left-0 w-1 rounded-r-full bg-sky-500 transition-opacity duration-300',
                            selected ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'
                          )}
                        />
                        <span className="flex items-start justify-between gap-2">
                          <span className="min-w-0">
                            <span className="flex items-center gap-2 text-sm font-medium">
                              <span
                                className={cn(
                                  'inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br',
                                  meta.accent
                                )}
                              >
                                <Icon className="h-3.5 w-3.5" />
                              </span>
                              <span className="truncate">{provider.name}</span>
                            </span>
                            <span className="mt-1.5 block truncate pl-9 text-xs text-muted-foreground">
                              {provider.model}
                            </span>
                          </span>
                          <span className="flex shrink-0 flex-col items-end gap-1">
                            {provider.is_default && (
                              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                                默认
                              </span>
                            )}
                            {provider.enabled ? (
                              <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                            ) : (
                              <span className="h-2 w-2 rounded-full bg-muted-foreground/40" />
                            )}
                          </span>
                        </span>
                      </motion.button>
                    )
                  })}
                </AnimatePresence>
              </div>
            </div>
          </GlowCard>
        </aside>

        <AnimatePresence mode="wait">
          <motion.form
            key={editingId ?? 'new'}
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
            onSubmit={(event) => {
              event.preventDefault()
              setNotice(null)
              saveMutation.mutate()
            }}
            className="min-w-0 space-y-5"
          >
            <GlowCard animated>
              <div className="border-b border-border/60 px-4 py-4 sm:px-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                      Provider
                    </p>
                    <h2 className="mt-1 text-lg font-semibold">
                      {editingId ? '编辑模型配置' : '新建模型配置'}
                    </h2>
                  </div>
                  <span
                    className={cn(
                      'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium bg-gradient-to-r',
                      protocolMeta.accent
                    )}
                  >
                    <ProtocolIcon className="h-3.5 w-3.5" />
                    {protocolMeta.label}
                  </span>
                </div>
              </div>

              <div className="space-y-5 p-4 sm:p-5">
                <section className="grid gap-4 sm:grid-cols-2">
                  <label className="space-y-2 text-sm">
                    <FieldLabel>配置名称</FieldLabel>
                    <input
                      required
                      value={form.name}
                      onChange={(e) => set('name', e.target.value)}
                      className={inputClassName()}
                      placeholder="例如：DeepSeek 生产"
                    />
                  </label>
                  <label className="space-y-2 text-sm">
                    <FieldLabel hint={protocolMeta.hint}>协议</FieldLabel>
                    <select
                      value={form.protocol}
                      onChange={(e) => set('protocol', e.target.value as ModelProtocol)}
                      className={inputClassName()}
                    >
                      <option value="openai_compatible">OpenAI 兼容 / 中转端</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="gemini">Gemini</option>
                      <option value="ollama">Ollama</option>
                    </select>
                  </label>
                </section>

                <section className="space-y-4 rounded-2xl border border-border/60 bg-muted/20 p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <KeyRound className="h-4 w-4 text-primary" />
                    连接凭证
                  </div>
                  <label className="block space-y-2 text-sm">
                    <FieldLabel hint="支持 http(s) 完整地址，末尾无需斜杠">API 地址</FieldLabel>
                    <input
                      required
                      type="url"
                      value={form.base_url}
                      onChange={(e) => set('base_url', e.target.value)}
                      placeholder="https://api.example.com/v1"
                      className={inputClassName('font-mono text-xs sm:text-sm')}
                    />
                  </label>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="space-y-2 text-sm">
                      <FieldLabel>模型</FieldLabel>
                      <input
                        required
                        value={form.model}
                        onChange={(e) => set('model', e.target.value)}
                        className={inputClassName('font-mono text-xs sm:text-sm')}
                        placeholder="deepseek-chat"
                      />
                    </label>
                    <label className="space-y-2 text-sm">
                      <FieldLabel hint="明文显示，保存时加密存储">API Key</FieldLabel>
                      <div className="relative">
                        <input
                          type="text"
                          value={form.api_key}
                          onChange={(e) => set('api_key', e.target.value)}
                          autoComplete="off"
                          spellCheck={false}
                          placeholder="sk-..."
                          className={inputClassName('pr-10 font-mono text-xs sm:text-sm')}
                        />
                        <button
                          type="button"
                          aria-label="复制 API Key"
                          disabled={!form.api_key}
                          onClick={() => void copyApiKey()}
                          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-40"
                        >
                          {copiedKey ? (
                            <Check className="h-4 w-4 text-primary" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </label>
                  </div>
                  <label className="block space-y-2 text-sm">
                    <FieldLabel hint="每行一个，格式 Name: Value">自定义请求头</FieldLabel>
                    <textarea
                      value={headerText}
                      onChange={(e) => setHeaderText(e.target.value)}
                      placeholder="X-API-Key: value&#10;HTTP-Referer: https://example.com"
                      rows={3}
                      className={inputClassName('resize-y font-mono text-xs')}
                    />
                  </label>
                </section>

                <section className="grid gap-4 sm:grid-cols-3">
                  <label className="space-y-2 text-sm">
                    <FieldLabel>超时（秒）</FieldLabel>
                    <input
                      type="number"
                      min={5}
                      max={300}
                      value={form.timeout_seconds}
                      onChange={(e) => set('timeout_seconds', Number(e.target.value))}
                      className={inputClassName()}
                    />
                  </label>
                  <label className="space-y-2 text-sm">
                    <FieldLabel>温度</FieldLabel>
                    <input
                      type="number"
                      min={0}
                      max={2}
                      step={0.1}
                      value={form.temperature}
                      onChange={(e) => set('temperature', Number(e.target.value))}
                      className={inputClassName()}
                    />
                  </label>
                  <label className="space-y-2 text-sm">
                    <FieldLabel>最大输出</FieldLabel>
                    <input
                      type="number"
                      min={256}
                      value={form.max_tokens}
                      onChange={(e) => set('max_tokens', Number(e.target.value))}
                      className={inputClassName()}
                    />
                  </label>
                </section>

                <div className="flex flex-wrap gap-3">
                  <label
                    className={cn(
                      'inline-flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-all duration-200',
                      form.enabled
                        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                        : 'border-border bg-background/60 text-muted-foreground'
                    )}
                  >
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={form.enabled}
                      onChange={(e) => set('enabled', e.target.checked)}
                    />
                    <span
                      className={cn(
                        'h-2 w-2 rounded-full transition-colors',
                        form.enabled ? 'bg-emerald-500' : 'bg-muted-foreground/40'
                      )}
                    />
                    启用
                  </label>
                  <label
                    className={cn(
                      'inline-flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-all duration-200',
                      form.is_default
                        ? 'border-primary/40 bg-primary/10 text-primary'
                        : 'border-border bg-background/60 text-muted-foreground'
                    )}
                  >
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={form.is_default}
                      onChange={(e) => set('is_default', e.target.checked)}
                    />
                    <Sparkles className="h-3.5 w-3.5" />
                    设为图谱默认模型
                  </label>
                </div>
              </div>
            </GlowCard>

            <AnimatePresence>
              {notice && (
                <motion.p
                  role="status"
                  initial={{ opacity: 0, y: 8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.22 }}
                  className={cn(
                    'rounded-xl border px-4 py-3 text-sm shadow-sm',
                    notice.type === 'error' &&
                      'border-destructive/30 bg-destructive/10 text-destructive',
                    notice.type === 'success' && 'border-primary/30 bg-primary/10 text-primary',
                    notice.type === 'info' && 'border-border bg-muted/60 text-foreground'
                  )}
                >
                  {notice.message}
                </motion.p>
              )}
            </AnimatePresence>

            <div className="flex flex-wrap gap-2 border-t border-border/60 pt-5">
              <motion.button
                whileHover={{ scale: isBusy ? 1 : 1.02 }}
                whileTap={{ scale: isBusy ? 1 : 0.98 }}
                type="submit"
                disabled={saveMutation.isPending}
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm disabled:opacity-50"
              >
                {saveMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                保存配置
              </motion.button>
              <motion.button
                whileHover={{ scale: !editingId || testMutation.isPending ? 1 : 1.02 }}
                whileTap={{ scale: !editingId || testMutation.isPending ? 1 : 0.98 }}
                type="button"
                disabled={!editingId || testMutation.isPending}
                onClick={() => testMutation.mutate()}
                className="inline-flex items-center gap-2 rounded-xl border border-border bg-background/80 px-4 py-2.5 text-sm transition-colors hover:bg-accent disabled:opacity-50"
              >
                {testMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Wifi className="h-4 w-4" />
                )}
                测试连接
              </motion.button>
              <motion.button
                whileHover={{ scale: !editingId || modelsMutation.isPending ? 1 : 1.02 }}
                whileTap={{ scale: !editingId || modelsMutation.isPending ? 1 : 0.98 }}
                type="button"
                disabled={!editingId || modelsMutation.isPending}
                onClick={() => modelsMutation.mutate()}
                className="rounded-xl border border-border bg-background/80 px-4 py-2.5 text-sm transition-colors hover:bg-accent disabled:opacity-50"
              >
                {modelsMutation.isPending ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    读取中...
                  </span>
                ) : (
                  '读取模型列表'
                )}
              </motion.button>
              {editingId && (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="button"
                  aria-label="删除配置"
                  onClick={async () => {
                    if (!confirm('确认删除此模型配置？')) return
                    await deleteModelProvider(editingId)
                    startNewProvider()
                    await queryClient.invalidateQueries({ queryKey: ['model-providers'] })
                  }}
                  className="ml-auto inline-flex items-center gap-2 rounded-xl border border-destructive/50 bg-destructive/5 px-3 py-2.5 text-sm text-destructive transition-colors hover:bg-destructive/10"
                >
                  <Trash2 className="h-4 w-4" />
                  删除
                </motion.button>
              )}
            </div>
          </motion.form>
        </AnimatePresence>
        </motion.div>
      </div>
    </div>
  )
}

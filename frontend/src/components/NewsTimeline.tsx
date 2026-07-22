import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import * as Popover from '@radix-ui/react-popover'
import dayjs from 'dayjs'
import {
  ExternalLink,
  LoaderCircle,
  Newspaper,
  RefreshCw,
  SlidersHorizontal,
  X,
} from 'lucide-react'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type UIEvent,
} from 'react'
import { fetchNews, fetchNewsSources, refreshNews } from '@/api/news'
import { useNewsChannelStore } from '@/stores/newsChannels'
import { GlowCard } from '@/components/GlowCard'
import AnimatedList from '@/components/AnimatedList'
import { getNewsChannelColor } from './newsChannelColors'

type FeedbackType = 'success' | 'error' | 'warning'

type RefreshResult = {
  type: 'progress' | FeedbackType
  message: string
} | null

interface NewsTimelineProps {
  onFeedback: (type: FeedbackType, message: string) => void
}

const AUTO_REFRESH_KEY = 'news-auto-refresh'
const REFRESH_INTERVAL = 60_000
const NEWS_PAGE_SIZE = 50
const LOAD_MORE_THRESHOLD = 160

export function NewsTimeline({ onFeedback }: NewsTimelineProps) {
  const [isAutoRefresh, setIsAutoRefresh] = useState(
    () => localStorage.getItem(AUTO_REFRESH_KEY) === 'true'
  )
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshResult, setRefreshResult] = useState<RefreshResult>(null)
  const refreshingRef = useRef(false)
  const disabledSources = useNewsChannelStore((state) => state.disabledSources)
  const toggleSource = useNewsChannelStore((state) => state.toggleSource)
  const { data: sourceNames, isLoading: isSourcesLoading } = useQuery({
    queryKey: ['news-sources'],
    queryFn: fetchNewsSources,
    staleTime: Infinity,
  })
  const enabledSources = useMemo(
    () => (sourceNames ?? []).filter((source) => !disabledSources.includes(source)),
    [disabledSources, sourceNames]
  )
  const {
    data,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['news', NEWS_PAGE_SIZE, enabledSources.join('|')],
    queryFn: ({ pageParam }) => fetchNews(NEWS_PAGE_SIZE, enabledSources, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      const loadedCount = pages.reduce((total, page) => total + page.items.length, 0)
      return loadedCount < lastPage.total ? loadedCount : undefined
    },
    enabled: Boolean(sourceNames && enabledSources.length > 0),
    staleTime: 30_000,
  })

  const handleRefresh = useCallback(async () => {
    if (refreshingRef.current) return
    refreshingRef.current = true
    setIsRefreshing(true)
    setRefreshResult({ type: 'progress', message: '正在刷新资讯...' })
    try {
      if (enabledSources.length === 0) {
        const message = '至少开启一个渠道后才能刷新新闻'
        setRefreshResult({ type: 'error', message })
        onFeedback('error', message)
        return
      }
      const result = await refreshNews(enabledSources)
      await refetch({ throwOnError: true })
      const failedSources = result.sources.filter((source) => !source.success)
      if (!result.success) {
        const detail = failedSources.map((source) => `${source.source}: ${source.error}`).join('、')
        const message = `新闻更新失败${detail ? `：${detail}` : ''}`
        setRefreshResult({ type: 'error', message })
        onFeedback('error', message)
      } else if (failedSources.length > 0) {
        const failedSourceNames = [...new Set(failedSources.map((source) => source.source))].join(
          '、'
        )
        const message = `新闻部分更新成功，抓取 ${result.fetched_count} 条，新增 ${result.inserted_count} 条；失败来源：${failedSourceNames}`
        setRefreshResult({ type: 'warning', message })
        onFeedback('warning', message)
      } else {
        const message = `新闻更新成功，抓取${result.fetched_count} 条，新增 ${result.inserted_count} 条`
        setRefreshResult({ type: 'success', message })
        onFeedback('success', message)
      }
    } catch (error) {
      const detail = error instanceof Error ? error.message : '未知错误'
      const message = `新闻更新失败：${detail}`
      setRefreshResult({ type: 'error', message })
      onFeedback('error', message)
    } finally {
      refreshingRef.current = false
      setIsRefreshing(false)
    }
  }, [enabledSources, onFeedback, refetch])

  useEffect(() => {
    if (!isAutoRefresh) return undefined
    const timer = window.setInterval(() => void handleRefresh(), REFRESH_INTERVAL)
    return () => window.clearInterval(timer)
  }, [handleRefresh, isAutoRefresh])

  const toggleAutoRefresh = () => {
    const next = !isAutoRefresh
    setIsAutoRefresh(next)
    localStorage.setItem(AUTO_REFRESH_KEY, String(next))
    onFeedback('success', next ? '新闻实时刷新已开启' : '新闻实时刷新已关闭')
  }

  const enabledSourceSet = useMemo(() => new Set(enabledSources), [enabledSources])
  const articles = useMemo(() => {
    const uniqueArticles = new Map<
      number,
      NonNullable<typeof data>['pages'][number]['items'][number]
    >()
    for (const page of data?.pages ?? []) {
      for (const article of page.items) {
        if (enabledSourceSet.has(article.source)) uniqueArticles.set(article.id, article)
      }
    }
    return [...uniqueArticles.values()]
  }, [data, enabledSourceSet])
  const hasEnabledSources = enabledSources.length > 0

  const handleNewsScroll = (event: UIEvent<HTMLDivElement>) => {
    const container = event.currentTarget
    const remainingScroll = container.scrollHeight - container.scrollTop - container.clientHeight
    if (remainingScroll <= LOAD_MORE_THRESHOLD && hasNextPage && !isFetchingNextPage) {
      void fetchNextPage()
    }
  }

  return (
    <section aria-labelledby="news-timeline-heading">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Newspaper className="h-5 w-5 shrink-0 text-primary" />
          <h2 id="news-timeline-heading" className="text-lg font-semibold text-foreground">
            实时资讯
          </h2>
          <span className="text-xs text-muted-foreground">
            {dataUpdatedAt ? `更新于 ${dayjs(dataUpdatedAt).format('HH:mm:ss')}` : '等待更新'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Popover.Root>
            <Popover.Trigger asChild>
              <button
                type="button"
                aria-label="配置新闻渠道"
                title="配置新闻渠道"
                className="inline-flex h-9 items-center gap-2 rounded-xl border border-border bg-background px-2.5 text-sm text-foreground transition-colors hover:bg-accent"
              >
                <SlidersHorizontal className="h-4 w-4" />
                <span className="hidden sm:inline">渠道</span>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {enabledSources.length}/{sourceNames?.length ?? 0}
                </span>
              </button>
            </Popover.Trigger>
            <Popover.Portal>
              <Popover.Content
                align="end"
                sideOffset={8}
                className="z-30 w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-border bg-popover p-3 text-popover-foreground shadow-lg"
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-semibold">新闻渠道</span>
                  <Popover.Close asChild>
                    <button
                      type="button"
                      aria-label="关闭渠道配置"
                      title="关闭"
                      className="inline-flex h-7 w-7 items-center justify-center rounded-xl text-muted-foreground hover:bg-accent hover:text-foreground"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </Popover.Close>
                </div>
                <div className="max-h-72 space-y-1 overflow-y-auto pr-1">
                  {isSourcesLoading && (
                    <div className="flex h-16 items-center justify-center text-sm text-muted-foreground">
                      <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> 加载渠道
                    </div>
                  )}
                  {(sourceNames ?? []).map((source) => {
                    const enabled = !disabledSources.includes(source)
                    const color = getNewsChannelColor(source)
                    return (
                      <button
                        key={source}
                        type="button"
                        role="switch"
                        aria-label={`${source}渠道`}
                        aria-checked={enabled}
                        onClick={() => toggleSource(source)}
                        className="flex h-9 w-full items-center gap-2 rounded-xl px-2 text-sm transition-colors hover:bg-accent"
                      >
                        <span
                          className="h-3 w-3 shrink-0 rounded-sm"
                          style={{ backgroundColor: color }}
                        />
                        <span className="min-w-0 flex-1 truncate text-left">{source}</span>
                        <span
                          className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${enabled ? '' : 'bg-muted-foreground/30'}`}
                          style={enabled ? { backgroundColor: color } : undefined}
                        >
                          <span
                            className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${enabled ? 'translate-x-4' : 'translate-x-0'}`}
                          />
                        </span>
                      </button>
                    )
                  })}
                </div>
                {!hasEnabledSources && (
                  <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                    至少开启一个渠道后才能刷新新闻
                  </p>
                )}
              </Popover.Content>
            </Popover.Portal>
          </Popover.Root>
          <span className="text-sm text-muted-foreground">实时刷新</span>
          <button
            type="button"
            role="switch"
            aria-label="实时刷新"
            aria-checked={isAutoRefresh}
            onClick={toggleAutoRefresh}
            className={`inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 transition-colors ${
              isAutoRefresh ? 'bg-green-600' : 'bg-muted-foreground/35'
            }`}
          >
            <span
              className={`h-5 w-5 shrink-0 rounded-full bg-white shadow transition-transform ${
                isAutoRefresh ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
          <button
            type="button"
            aria-label="立即刷新新闻"
            title="立即刷新新闻"
            disabled={isRefreshing || !hasEnabledSources}
            onClick={() => void handleRefresh()}
            className="inline-flex h-9 items-center justify-center gap-1.5 rounded-xl border border-border bg-background px-2.5 text-sm text-foreground transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{isRefreshing ? '刷新中' : '刷新'}</span>
          </button>
        </div>
      </div>
      {refreshResult && (
        <p
          data-testid="news-refresh-result"
          role="status"
          aria-live="polite"
          className={`mb-3 text-sm ${
            refreshResult.type === 'error'
              ? 'text-destructive'
              : refreshResult.type === 'success'
                ? 'text-primary'
                : refreshResult.type === 'warning'
                  ? 'text-amber-700 dark:text-amber-400'
                  : 'text-muted-foreground'
          }`}
        >
          {refreshResult.message}
        </p>
      )}

      <GlowCard>
        {isLoading && (
          <div className="flex h-36 items-center justify-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="h-4 w-4 animate-spin" /> 加载最新资讯
          </div>
        )}
        {isError && (
          <div className="flex h-36 flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
            <span>资讯加载失败</span>
            <button
              type="button"
              className="text-primary hover:underline"
              onClick={() => void refetch()}
            >
              重新加载
            </button>
          </div>
        )}
        {!isLoading && !isError && articles.length === 0 && (
          <div className="flex h-36 flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
            <span>{hasEnabledSources ? '暂无新闻数据' : '已关闭全部新闻渠道'}</span>
            {hasEnabledSources && (
              <button
                type="button"
                className="text-primary hover:underline"
                onClick={() => void handleRefresh()}
              >
                立即抓取
              </button>
            )}
          </div>
        )}
        {!isLoading && !isError && articles.length > 0 && (
          <AnimatedList
            items={articles}
            getItemKey={(article) => article.id}
            listTestId="news-scroll-container"
            listClassName="xl:h-[900px] xl:max-h-[900px]"
            showGradients
            enableArrowNavigation={false}
            displayScrollbar
            onScroll={handleNewsScroll}
            onItemSelect={(article) => {
              window.open(article.url, '_blank', 'noopener,noreferrer')
            }}
            renderItem={(article, _index, selected) => (
              <div
                data-testid={`news-item-${article.id}`}
                className={`item news-channel-item ${selected ? 'selected' : ''}`}
                style={
                  {
                    '--channel-color': getNewsChannelColor(article.source),
                  } as CSSProperties
                }
              >
                <div className="mb-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                  <time dateTime={article.published_at}>
                    {dayjs(article.published_at).format('MM-DD HH:mm')}
                  </time>
                  <span
                    className="rounded-xl px-1.5 py-0.5 font-medium text-white"
                    style={{ backgroundColor: getNewsChannelColor(article.source) }}
                  >
                    {article.source}
                  </span>
                  <span className="rounded-xl bg-secondary px-1.5 py-0.5 text-secondary-foreground">
                    {article.category}
                  </span>
                  <span
                    title="综合热度：根据新闻时效、来源指标、多渠道重复报道和市场关键词计算，并非阅读量"
                    className={`rounded-xl px-1.5 py-0.5 font-medium ${
                      article.heat_score >= 80
                        ? 'bg-red-500/15 text-red-600 dark:text-red-400'
                        : article.heat_score >= 60
                          ? 'bg-amber-500/15 text-amber-700 dark:text-amber-400'
                          : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    热度 {article.heat_score}
                  </span>
                </div>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group inline-flex max-w-full items-start gap-1.5 font-medium leading-6 text-foreground hover:text-primary"
                  onClick={(event) => event.stopPropagation()}
                >
                  <span>{article.title}</span>
                  <ExternalLink className="mt-1 h-3.5 w-3.5 shrink-0 opacity-60 group-hover:opacity-100" />
                </a>
                {article.summary && (
                  <p className="mt-1 line-clamp-2 text-sm leading-5 text-muted-foreground">
                    {article.summary}
                  </p>
                )}
              </div>
            )}
          />
        )}
        {!isLoading && !isError && articles.length > 0 && isFetchingNextPage && (
          <div className="flex h-12 items-center justify-center gap-2 text-xs text-muted-foreground">
            <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> 加载更早资讯
          </div>
        )}
      </GlowCard>
    </section>
  )
}

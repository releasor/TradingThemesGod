import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NewsTimeline } from './NewsTimeline'

vi.mock('@/api/news', () => ({
  fetchNews: vi.fn(),
  fetchNewsSources: vi.fn(),
  refreshNews: vi.fn(),
}))

import { fetchNews, fetchNewsSources, refreshNews } from '@/api/news'
import { useNewsChannelStore } from '@/stores/newsChannels'

const articles = [
  {
    id: 1,
    source: '新浪财经',
    category: '科技',
    title: '最新产业新闻',
    summary: '新闻摘要',
    url: 'https://finance.sina.com.cn/news/1.shtml',
    published_at: '2026-07-16T02:00:00Z',
    crawled_at: '2026-07-16T02:01:00Z',
    heat_score: 86,
  },
]

function renderTimeline(onFeedback = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <NewsTimeline onFeedback={onFeedback} />
    </QueryClientProvider>
  )
}

describe('NewsTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    useNewsChannelStore.setState({ disabledSources: [] })
    vi.mocked(fetchNewsSources).mockResolvedValue(['新浪财经', '财联社'])
    vi.mocked(fetchNews).mockResolvedValue({ items: articles, total: 1 })
  })

  it('renders a time stream with safe original links', async () => {
    renderTimeline()

    const link = await screen.findByRole('link', { name: /最新产业新闻/ })
    expect(link).toHaveAttribute('href', articles[0].url)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(screen.getByText('新浪财经')).toBeInTheDocument()
    expect(screen.getByText('热度 86')).toBeInTheDocument()
    expect(screen.getByTitle(/综合热度/)).toBeInTheDocument()
    expect(screen.getByTestId('news-item-1')).toHaveStyle({ '--channel-color': '#2563eb' })
    expect(screen.getByTestId('news-scroll-container')).toHaveClass(
      'xl:h-[900px]',
      'xl:max-h-[900px]'
    )
  })

  it('configures enabled channels and filters requests', async () => {
    renderTimeline()

    await userEvent.click(await screen.findByRole('button', { name: '配置新闻渠道' }))
    const sinaToggle = screen.getByRole('switch', { name: '新浪财经渠道' })
    expect(sinaToggle).toHaveAttribute('aria-checked', 'true')
    expect(sinaToggle.lastElementChild?.firstElementChild).toHaveClass('left-0.5', 'translate-x-4')

    await userEvent.click(sinaToggle)

    await waitFor(() => expect(fetchNews).toHaveBeenLastCalledWith(50, ['财联社'], 0))
    expect(screen.queryByText('最新产业新闻')).not.toBeInTheDocument()
  })

  it('loads the next page when the news list is scrolled near the bottom', async () => {
    const firstPage = Array.from({ length: 50 }, (_, index) => ({
      ...articles[0],
      id: index + 1,
      title: index === 0 ? '最新产业新闻' : `新闻 ${index + 1}`,
      url: `https://finance.sina.com.cn/news/${index + 1}.shtml`,
    }))
    const olderArticle = {
      ...articles[0],
      id: 51,
      source: '财联社',
      title: '更早的市场资讯',
      url: 'https://www.cls.cn/detail/2',
      published_at: '2026-07-16T01:00:00Z',
    }
    vi.mocked(fetchNews).mockImplementation(async (_limit, _sources, offset = 0) =>
      offset === 0 ? { items: firstPage, total: 51 } : { items: [olderArticle], total: 51 }
    )
    renderTimeline()

    await screen.findByText('最新产业新闻')
    const container = screen.getByTestId('news-scroll-container')
    Object.defineProperties(container, {
      scrollHeight: { configurable: true, value: 1000 },
      clientHeight: { configurable: true, value: 500 },
      scrollTop: { configurable: true, value: 420 },
    })

    fireEvent.scroll(container)

    await waitFor(() => expect(fetchNews).toHaveBeenCalledWith(50, ['新浪财经', '财联社'], 50))
    expect(await screen.findByText('更早的市场资讯')).toBeInTheDocument()
  })

  it('refreshes real news and reports the result', async () => {
    let resolveRefresh!: (value: {
      success: true
      fetched_count: number
      inserted_count: number
      refreshed_at: string
      sources: []
    }) => void
    vi.mocked(refreshNews).mockReturnValue(
      new Promise((resolve) => {
        resolveRefresh = resolve
      })
    )
    const feedback = vi.fn()
    renderTimeline(feedback)

    await userEvent.click(await screen.findByRole('button', { name: '立即刷新新闻' }))

    expect(screen.getByTestId('news-refresh-result')).toHaveTextContent('正在刷新资讯...')
    expect(screen.getByRole('button', { name: '立即刷新新闻' })).toBeDisabled()
    expect(screen.getByText('刷新中')).toBeInTheDocument()

    resolveRefresh({
      success: true,
      fetched_count: 12,
      inserted_count: 3,
      refreshed_at: '2026-07-16T02:02:00Z',
      sources: [],
    })

    await waitFor(() => expect(refreshNews).toHaveBeenCalledWith(['新浪财经', '财联社']))
    expect(feedback).toHaveBeenCalledWith('success', '新闻更新成功，抓取 12 条，新增 3 条')
    expect(screen.getByTestId('news-refresh-result')).toHaveTextContent(
      '新闻更新成功，抓取 12 条，新增 3 条'
    )
    expect(fetchNews).toHaveBeenCalledTimes(2)
  })

  it('reports failed source names when a refresh partially succeeds', async () => {
    vi.mocked(refreshNews).mockResolvedValue({
      success: true,
      fetched_count: 382,
      inserted_count: 225,
      refreshed_at: '2026-07-16T02:02:00Z',
      sources: [
        {
          source: '财联社',
          success: true,
          fetched_count: 20,
          error: null,
        },
        {
          source: '巨潮资讯',
          success: false,
          fetched_count: 0,
          error: '未抓取到有效新闻',
        },
        {
          source: '雪球',
          success: false,
          fetched_count: 0,
          error: '未配置 XUEQIU_COOKIE',
        },
      ],
    })
    const feedback = vi.fn()
    renderTimeline(feedback)

    await userEvent.click(await screen.findByRole('button', { name: '立即刷新新闻' }))

    await waitFor(() => expect(refreshNews).toHaveBeenCalledOnce())
    expect(feedback).toHaveBeenCalledWith(
      'warning',
      '新闻部分更新成功，抓取 382 条，新增 225 条；失败来源：巨潮资讯、雪球'
    )
    expect(screen.getByTestId('news-refresh-result')).toHaveTextContent(
      '新闻部分更新成功，抓取 382 条，新增 225 条；失败来源：巨潮资讯、雪球'
    )
  })

  it('shows inline error feedback when refresh fails', async () => {
    vi.mocked(refreshNews).mockRejectedValue(new Error('上游超时'))
    const feedback = vi.fn()
    renderTimeline(feedback)

    await userEvent.click(await screen.findByRole('button', { name: '立即刷新新闻' }))

    await waitFor(() =>
      expect(feedback).toHaveBeenCalledWith('error', '新闻更新失败：上游超时')
    )
    expect(screen.getByTestId('news-refresh-result')).toHaveTextContent('新闻更新失败：上游超时')
    expect(screen.getByRole('button', { name: '立即刷新新闻' })).not.toBeDisabled()
  })

  it('persists the real-time refresh switch', async () => {
    renderTimeline()

    const toggle = await screen.findByRole('switch', { name: '实时刷新' })
    const knob = toggle.firstElementChild
    expect(toggle).toHaveClass('shrink-0', 'items-center', 'p-0.5')
    expect(knob).toHaveClass('shrink-0')
    expect(toggle).toHaveAttribute('aria-checked', 'false')
    await userEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-checked', 'true')
    expect(localStorage.getItem('news-auto-refresh')).toBe('true')
  })

  it('runs a real refresh request every 60 seconds when enabled', async () => {
    vi.mocked(refreshNews).mockResolvedValue({
      success: true,
      fetched_count: 10,
      inserted_count: 1,
      refreshed_at: '2026-07-16T02:02:00Z',
      sources: [],
    })
    renderTimeline()

    const toggle = await screen.findByRole('switch', { name: '实时刷新' })
    vi.useFakeTimers()
    try {
      fireEvent.click(toggle)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(60_000)
      })

      expect(refreshNews).toHaveBeenCalledOnce()
      expect(fetchNews).toHaveBeenCalledTimes(2)
    } finally {
      vi.useRealTimers()
    }
  })
})

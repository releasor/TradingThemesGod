import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AppCardNav } from './AppCardNav'

vi.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => <button type="button" aria-label="切换主题" />,
}))

vi.mock('@/components/AuthNav', () => ({
  AuthNav: () => <div data-testid="auth-nav">auth</div>,
}))

vi.mock('@/components/MarketStatusNav', () => ({
  MarketStatusNav: () => <div data-testid="market-status-nav">market</div>,
}))

describe('AppCardNav', () => {
  it('renders card menu entries without top AI CTA', async () => {
    render(
      <MemoryRouter>
        <AppCardNav />
      </MemoryRouter>
    )

    expect(screen.getByTestId('app-card-nav')).toBeInTheDocument()
    expect(screen.getByTestId('market-status-nav')).toBeInTheDocument()
    expect(screen.getByTestId('auth-nav')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '切换主题' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'TradingThemesGod' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'AI 个股分析' })).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '打开菜单' }))
    expect(screen.getByText('题材看板')).toBeInTheDocument()
    expect(screen.getByText('题材分析')).toBeInTheDocument()
    expect(screen.getByText('复盘研究')).toBeInTheDocument()
    expect(screen.getByText('设置')).toBeInTheDocument()

    const dashboardCard = screen.getByText('题材看板').closest('.nav-card')
    const analysisCard = screen.getByText('题材分析').closest('.nav-card')
    const reviewCard = screen.getByText('复盘研究').closest('.nav-card')
    const settingsCard = screen.getByText('设置').closest('.nav-card')
    expect(dashboardCard).toHaveAttribute('data-tone', 'dashboard')
    expect(analysisCard).toHaveAttribute('data-tone', 'analysis')
    expect(reviewCard).toHaveAttribute('data-tone', 'review')
    expect(settingsCard).toHaveAttribute('data-tone', 'settings')
    expect(screen.getByRole('link', { name: '进入题材库' })).toHaveAttribute('href', '/themes')
    expect(screen.getByRole('link', { name: '打开 AI 个股分析' })).toHaveAttribute(
      'href',
      '/ai-analysis'
    )
    expect(screen.getByRole('link', { name: '进入复盘台' })).toHaveAttribute('href', '/review')
    expect(screen.getByRole('link', { name: '进入催化雷达' })).toHaveAttribute('href', '/catalysts')
    expect(screen.getByRole('link', { name: '进入题材挖掘' })).toHaveAttribute('href', '/mining')
    expect(screen.getByRole('link', { name: '进入主线图谱' })).toHaveAttribute(
      'href',
      '/mainline-graph'
    )
    expect(screen.getByRole('link', { name: '打开模型设置' })).toHaveAttribute(
      'href',
      '/settings/models'
    )
    expect(screen.getByRole('link', { name: '打开交易日历设置' })).toHaveAttribute(
      'href',
      '/settings/calendar'
    )
    expect(screen.getByRole('link', { name: '查看键盘快捷键' })).toHaveAttribute(
      'href',
      '/settings/shortcuts'
    )
    expect(screen.getByRole('link', { name: '打开账号设置' })).toHaveAttribute(
      'href',
      '/settings/account'
    )
  })
})

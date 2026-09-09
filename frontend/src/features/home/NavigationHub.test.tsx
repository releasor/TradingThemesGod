import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { NavigationHub } from './NavigationHub'
import { resolvePostAuthPath, DEFAULT_POST_AUTH_PATH } from './navHub'

vi.mock('@/components/AppCardNav', async () => {
  const actual = await vi.importActual<typeof import('@/components/AppCardNav')>(
    '@/components/AppCardNav'
  )
  return {
    ...actual,
    AppCardNav: () => <div data-testid="app-card-nav" />,
  }
})

vi.mock('@/components/RippleDistortion', () => ({
  default: () => <div data-testid="ripple-distortion" />,
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (s: { user: { username: string } | null }) => unknown) =>
    selector({ user: { username: 'releasor' } }),
}))

describe('resolvePostAuthPath', () => {
  it('defaults to project launch page', () => {
    expect(resolvePostAuthPath(null)).toBe(DEFAULT_POST_AUTH_PATH)
    expect(resolvePostAuthPath(undefined)).toBe('/')
    expect(resolvePostAuthPath('/login')).toBe('/')
  })
})

describe('NavigationHub', () => {
  it('renders TradingThemesGod module hub', () => {
    render(
      <MemoryRouter>
        <NavigationHub />
      </MemoryRouter>
    )

    expect(screen.getByTestId('navigation-hub')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'TradingThemesGod' })).toBeInTheDocument()
    expect(screen.getByText(/欢迎回来，releasor/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '题材看板' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '复盘研究' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '进入题材看板' })).toHaveAttribute(
      'href',
      '/dashboard'
    )
    expect(screen.getByRole('link', { name: /返回项目入口/ })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('link', { name: '进入 Studio Footer' })).not.toBeInTheDocument()
  })
})

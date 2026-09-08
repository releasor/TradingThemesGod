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
  it('defaults to home', () => {
    expect(resolvePostAuthPath(null)).toBe(DEFAULT_POST_AUTH_PATH)
    expect(resolvePostAuthPath(undefined)).toBe('/home')
    expect(resolvePostAuthPath('/login')).toBe('/home')
    expect(resolvePostAuthPath('/register')).toBe('/home')
  })

  it('keeps deep links', () => {
    expect(resolvePostAuthPath('/themes')).toBe('/themes')
    expect(resolvePostAuthPath('/settings/models')).toBe('/settings/models')
  })
})

describe('NavigationHub', () => {
  it('renders brand hero with ripple background and non-settings entries', () => {
    render(
      <MemoryRouter>
        <NavigationHub />
      </MemoryRouter>
    )

    expect(screen.getByTestId('navigation-hub')).toBeInTheDocument()
    expect(screen.getByTestId('ripple-distortion')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'TradingThemesGod' })).toBeInTheDocument()
    expect(screen.getByText(/releasor/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '题材看板' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '复盘研究' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '设置' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: '进入题材库' })).toHaveAttribute('href', '/themes')
    expect(screen.getByRole('link', { name: '进入复盘台' })).toHaveAttribute('href', '/review')
    expect(screen.queryByRole('link', { name: '打开模型设置' })).not.toBeInTheDocument()
  })
})

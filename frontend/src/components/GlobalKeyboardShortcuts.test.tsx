/** GlobalKeyboardShortcuts 全站快捷键 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import {
  DASHBOARD_REFRESH_EVENT,
  GlobalKeyboardShortcuts,
} from './GlobalKeyboardShortcuts'

function press(key: string, opts: KeyboardEventInit = {}) {
  act(() => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, ...opts }))
  })
}

function LocationProbe({ onPath }: { onPath: (path: string) => void }) {
  const location = useLocation()
  onPath(location.pathname)
  return null
}

function renderAt(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <GlobalKeyboardShortcuts />
    </MemoryRouter>
  )
}

describe('GlobalKeyboardShortcuts', () => {
  it('opens help panel on ?', () => {
    renderAt('/')
    press('?', { shiftKey: true })
    expect(screen.getByRole('dialog', { name: '键盘快捷键' })).toBeInTheDocument()
  })

  it('navigates to themes on t', () => {
    let path = '/'
    function Harness() {
      const navigate = useNavigate()
      return (
        <>
          <button type="button" onClick={() => navigate('/themes')}>
            go
          </button>
          <GlobalKeyboardShortcuts />
          <LocationProbe onPath={(p) => {
            path = p
          }}
          />
        </>
      )
    }
    render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>
    )
    press('t')
    expect(path).toBe('/themes')
  })

  it('dispatches dashboard refresh on r when already on home', () => {
    const onRefresh = vi.fn()
    window.addEventListener(DASHBOARD_REFRESH_EVENT, onRefresh)
    renderAt('/')
    press('r')
    expect(onRefresh).toHaveBeenCalledOnce()
    window.removeEventListener(DASHBOARD_REFRESH_EVENT, onRefresh)
  })

  it('navigates home on r when not on dashboard', () => {
    let path = '/themes'
    function Harness() {
      return (
        <>
          <GlobalKeyboardShortcuts />
          <LocationProbe onPath={(p) => {
            path = p
          }}
          />
        </>
      )
    }
    render(
      <MemoryRouter initialEntries={['/themes']}>
        <Harness />
      </MemoryRouter>
    )
    press('r')
    expect(path).toBe('/')
  })
})

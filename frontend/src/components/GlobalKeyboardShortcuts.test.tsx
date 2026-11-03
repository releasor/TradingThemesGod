/** GlobalKeyboardShortcuts 全站快捷键 */

import { describe, it, expect } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { GlobalKeyboardShortcuts } from './GlobalKeyboardShortcuts'

function press(key: string, opts: KeyboardEventInit = {}) {
  act(() => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, ...opts }))
  })
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
})

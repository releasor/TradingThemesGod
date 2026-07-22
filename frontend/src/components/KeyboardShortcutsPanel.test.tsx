import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { KeyboardShortcutsPanel, KeyboardShortcutsButton } from './KeyboardShortcutsPanel'

describe('KeyboardShortcutsPanel', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
  }

  it('renders when isOpen is true', () => {
    render(<KeyboardShortcutsPanel {...defaultProps} />)
    expect(screen.getByText('键盘快捷键')).toBeInTheDocument()
  })

  it('does not render when isOpen is false', () => {
    render(<KeyboardShortcutsPanel isOpen={false} onClose={vi.fn()} />)
    expect(screen.queryByText('键盘快捷键')).not.toBeInTheDocument()
  })

  it('has correct dialog role and ARIA attributes', () => {
    render(<KeyboardShortcutsPanel {...defaultProps} />)
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby', 'shortcuts-title')
  })

  it('displays all shortcut items', () => {
    render(<KeyboardShortcutsPanel {...defaultProps} />)
    expect(screen.getByText('刷新看板')).toBeInTheDocument()
    expect(screen.getByText('打开题材库')).toBeInTheDocument()
    expect(screen.getByText('聚焦搜索')).toBeInTheDocument()
    expect(screen.getByText('显示快捷键帮助')).toBeInTheDocument()
    expect(screen.getByText('关闭弹窗')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<KeyboardShortcutsPanel isOpen={true} onClose={onClose} />)
    fireEvent.click(screen.getByLabelText('关闭快捷键面板'))
    expect(onClose).toHaveBeenCalled()
  })

  it('closes on Escape key press', () => {
    const onClose = vi.fn()
    render(<KeyboardShortcutsPanel isOpen={true} onClose={onClose} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('does not call onClose on Escape when panel is closed', () => {
    const onClose = vi.fn()
    render(<KeyboardShortcutsPanel isOpen={false} onClose={onClose} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })

  it('has correct title id for accessibility', () => {
    render(<KeyboardShortcutsPanel {...defaultProps} />)
    const title = screen.getByText('键盘快捷键')
    expect(title).toHaveAttribute('id', 'shortcuts-title')
  })

  it('renders backdrop with click handler', () => {
    const onClose = vi.fn()
    render(<KeyboardShortcutsPanel isOpen={true} onClose={onClose} />)
    const dialog = screen.getByRole('dialog')
    const backdrop = dialog.querySelector('[class*="backdrop-blur"]')
    expect(backdrop).toBeInTheDocument()
  })
})

describe('KeyboardShortcutsButton', () => {
  it('renders the keyboard button', () => {
    render(<KeyboardShortcutsButton />)
    expect(screen.getByLabelText('键盘快捷键帮助')).toBeInTheDocument()
  })

  it('opens panel when button is clicked', () => {
    render(<KeyboardShortcutsButton />)
    fireEvent.click(screen.getByLabelText('键盘快捷键帮助'))
    expect(screen.getByText('键盘快捷键')).toBeInTheDocument()
  })

  it('closes panel when onClose is triggered', () => {
    render(<KeyboardShortcutsButton />)
    fireEvent.click(screen.getByLabelText('键盘快捷键帮助'))
    expect(screen.getByText('键盘快捷键')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('关闭快捷键面板'))
    expect(screen.queryByText('键盘快捷键')).not.toBeInTheDocument()
  })

  it('has correct title attribute', () => {
    render(<KeyboardShortcutsButton />)
    expect(screen.getByTitle('键盘快捷键 (?)')).toBeInTheDocument()
  })
})

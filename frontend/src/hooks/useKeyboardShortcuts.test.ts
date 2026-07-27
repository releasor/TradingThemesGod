import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useKeyboardShortcuts, useKeyboardShortcut } from './useKeyboardShortcuts'

describe('useKeyboardShortcuts', () => {
  let addSpy: ReturnType<typeof vi.spyOn>
  let removeSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    addSpy = vi.spyOn(window, 'addEventListener')
    removeSpy = vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function pressKey(key: string, opts: Partial<KeyboardEventInit> = {}) {
    const event = new KeyboardEvent('keydown', { key, ...opts })
    window.dispatchEvent(event)
    return event
  }

  it('calls matching key action', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 'r', action }]))

    pressKey('r')
    expect(action).toHaveBeenCalledOnce()
  })

  it('does not call action for non-matching key', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 'r', action }]))

    pressKey('x')
    expect(action).not.toHaveBeenCalled()
  })

  it('matches key case-insensitively', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 'r', action }]))

    pressKey('R')
    expect(action).toHaveBeenCalledOnce()
  })

  it('matches ctrl modifier', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 's', ctrl: true, action }]))

    pressKey('s', { ctrlKey: true })
    expect(action).toHaveBeenCalledOnce()
  })

  it('does not match when ctrl is required but missing', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 's', ctrl: true, action }]))

    pressKey('s')
    expect(action).not.toHaveBeenCalled()
  })

  it('matches shift modifier', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: '?', shift: true, action }]))

    pressKey('?', { shiftKey: true })
    expect(action).toHaveBeenCalledOnce()
  })

  it('matches alt modifier', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 'n', alt: true, action }]))

    pressKey('n', { altKey: true })
    expect(action).toHaveBeenCalledOnce()
  })

  it('matches combined modifiers', () => {
    const action = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'z', ctrl: true, shift: true, action }]),
    )

    pressKey('z', { ctrlKey: true, shiftKey: true })
    expect(action).toHaveBeenCalledOnce()
  })

  it('handles multiple shortcuts independently', () => {
    const action1 = vi.fn()
    const action2 = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([
        { key: 'a', action: action1 },
        { key: 'b', action: action2 },
      ]),
    )

    pressKey('a')
    expect(action1).toHaveBeenCalledOnce()
    expect(action2).not.toHaveBeenCalled()

    pressKey('b')
    expect(action2).toHaveBeenCalledOnce()
  })

  it('only calls first matching shortcut', () => {
    const action1 = vi.fn()
    const action2 = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([
        { key: 'a', action: action1 },
        { key: 'a', action: action2 },
      ]),
    )

    pressKey('a')
    expect(action1).toHaveBeenCalledOnce()
    expect(action2).not.toHaveBeenCalled()
  })

  it('cleans up event listener on unmount', () => {
    const { unmount } = renderHook(() =>
      useKeyboardShortcuts([{ key: 'r', action: vi.fn() }]),
    )

    expect(addSpy).toHaveBeenCalledWith('keydown', expect.any(Function))

    unmount()

    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
  })

  it('does not require ctrl when ctrl option is false', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 'r', ctrl: false, action }]))

    pressKey('r')
    expect(action).toHaveBeenCalledOnce()
  })

  it('allows shift when shift option is unspecified (e.g. ? / Shift+R)', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 'r', action }]))

    pressKey('r', { shiftKey: true })
    expect(action).toHaveBeenCalledOnce()
  })

  it('matches ? without requiring explicit shift option', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: '?', action }]))

    pressKey('?', { shiftKey: true })
    expect(action).toHaveBeenCalledOnce()
  })

  it('does not trigger when ctrl is held unless required', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcuts([{ key: 'r', action }]))

    pressKey('r', { ctrlKey: true })
    expect(action).not.toHaveBeenCalled()
  })
})

describe('useKeyboardShortcut (single)', () => {
  it('registers a single shortcut', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcut('r', action))

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'r' }))
    expect(action).toHaveBeenCalledOnce()
  })

  it('supports modifier keys', () => {
    const action = vi.fn()
    renderHook(() => useKeyboardShortcut('s', action, { ctrl: true }))

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
    expect(action).toHaveBeenCalledOnce()

    // 不带 ctrl 不应触发
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 's' }))
    expect(action).toHaveBeenCalledTimes(1)
  })
})

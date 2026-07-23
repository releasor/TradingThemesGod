import { describe, expect, it, vi } from 'vitest'
import { isCancelledError, refetchIgnoringCancel } from './react-query'

describe('react-query helpers', () => {
  it('detects cancelled errors by name', () => {
    const error = new Error('CancelledError')
    error.name = 'CancelledError'
    expect(isCancelledError(error)).toBe(true)
    expect(isCancelledError(new Error('network'))).toBe(false)
  })

  it('ignores cancelled refetch results', async () => {
    const cancelled = new Error('CancelledError')
    cancelled.name = 'CancelledError'
    const refetch = vi.fn().mockResolvedValue({ isError: true, error: cancelled })

    await expect(refetchIgnoringCancel(refetch)).resolves.toBeUndefined()
    expect(refetch).toHaveBeenCalledWith({ cancelRefetch: false })
  })

  it('rethrows real refetch errors', async () => {
    const refetch = vi.fn().mockResolvedValue({
      isError: true,
      error: new Error('server down'),
    })

    await expect(refetchIgnoringCancel(refetch)).rejects.toThrow('server down')
  })
})

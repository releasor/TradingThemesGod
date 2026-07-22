/** API client 测试 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { onApiError, apiClient, requestWithRetry } from './client'

// 使用 vi.hoisted 创建 mock axios 实例（在 vi.mock 之前可用）
const { mockAxiosInstance } = vi.hoisted(() => {
  const mockAxiosInstance = Object.assign(vi.fn(), {
    defaults: { baseURL: '/api/v1', timeout: 10000 },
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  })
  return { mockAxiosInstance }
})

// Mock axios 库，使 client.ts 中的 axios.create() 返回可控的 mock 实例
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}))

describe('onApiError', () => {
  it('registers and returns unsubscribe function', () => {
    const listener = vi.fn()
    const unsubscribe = onApiError(listener)
    expect(typeof unsubscribe).toBe('function')
    unsubscribe()
  })

  it('unsubscribes correctly', () => {
    const listener = vi.fn()
    const unsubscribe = onApiError(listener)
    unsubscribe()
    expect(listener).not.toHaveBeenCalled()
  })

  it('supports multiple listeners', () => {
    const listener1 = vi.fn()
    const listener2 = vi.fn()
    const unsub1 = onApiError(listener1)
    const unsub2 = onApiError(listener2)
    unsub1()
    unsub2()
  })
})

describe('apiClient', () => {
  it('exports a valid axios instance', () => {
    expect(apiClient).toBeDefined()
    expect(apiClient.defaults).toBeDefined()
  })
})

describe('requestWithRetry', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockAxiosInstance.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // 测试 1: 首次成功即返回数据
  it('returns data on first successful attempt', async () => {
    mockAxiosInstance.mockResolvedValue({ data: { ok: true } })

    const result = await requestWithRetry({ url: '/test' })

    expect(result).toEqual({ ok: true })
    expect(mockAxiosInstance).toHaveBeenCalledTimes(1)
  })

  // 测试 2: 可重试状态码会触发重试
  it.each([408, 429, 500, 502, 503, 504])(
    'retries on retryable status code %d',
    async (status) => {
      mockAxiosInstance
        .mockRejectedValueOnce({ response: { status } })
        .mockResolvedValueOnce({ data: { recovered: true } })

      const promise = requestWithRetry({ url: '/test' })
      await vi.advanceTimersByTimeAsync(1000)

      const result = await promise
      expect(result).toEqual({ recovered: true })
      expect(mockAxiosInstance).toHaveBeenCalledTimes(2)
    }
  )

  // 测试 3: 不可重试状态码不重试
  it.each([400, 404, 422])(
    'does NOT retry on non-retryable status code %d',
    async (status) => {
      mockAxiosInstance.mockRejectedValue({ response: { status } })

      await expect(requestWithRetry({ url: '/test' })).rejects.toBeDefined()
      expect(mockAxiosInstance).toHaveBeenCalledTimes(1)
    }
  )

  // 测试 4: 无 response 时（网络错误）不重试
  it('does NOT retry when there is no response (network error)', async () => {
    mockAxiosInstance.mockRejectedValue(new Error('Network Error'))

    await expect(requestWithRetry({ url: '/test' })).rejects.toThrow(
      'Network Error'
    )
    expect(mockAxiosInstance).toHaveBeenCalledTimes(1)
  })

  // 测试 5: 超过最大重试次数后抛出错误
  it('throws after max retries exceeded', async () => {
    mockAxiosInstance.mockRejectedValue({ response: { status: 500 } })

    const promise = requestWithRetry({ url: '/test' }, 2)
    // 先绑定 reject 处理，避免 advanceTimers 期间产生 unhandled rejection
    const assertion = expect(promise).rejects.toBeDefined()
    // attempt 0 → delay 1000, attempt 1 → delay 2000, attempt 2 → throw
    await vi.advanceTimersByTimeAsync(1000)
    await vi.advanceTimersByTimeAsync(2000)
    await assertion
    // 初始 1 次 + 2 次重试 = 3 次调用
    expect(mockAxiosInstance).toHaveBeenCalledTimes(3)
  })

  // 测试 6: 指数退避延迟正确应用
  it('applies exponential backoff delay', async () => {
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout')

    mockAxiosInstance
      .mockRejectedValueOnce({ response: { status: 500 } })
      .mockRejectedValueOnce({ response: { status: 500 } })
      .mockResolvedValueOnce({ data: { ok: true } })

    const promise = requestWithRetry({ url: '/test' }, 2)
    // attempt 0 重试延迟 = min(1000 * 2^0, 10000) = 1000
    await vi.advanceTimersByTimeAsync(1000)
    // attempt 1 重试延迟 = min(1000 * 2^1, 10000) = 2000
    await vi.advanceTimersByTimeAsync(2000)

    const result = await promise
    expect(result).toEqual({ ok: true })

    // 验证 setTimeout 被以正确的延迟调用
    expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 1000)
    expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 2000)

    setTimeoutSpy.mockRestore()
  })

  // 测试 7: 自定义 maxRetries 参数
  it('supports custom maxRetries=0 (no retries)', async () => {
    mockAxiosInstance.mockRejectedValue({ response: { status: 500 } })

    await expect(requestWithRetry({ url: '/test' }, 0)).rejects.toBeDefined()
    expect(mockAxiosInstance).toHaveBeenCalledTimes(1)
  })

  // 测试 8: 第一次失败后第二次成功
  it('returns data on second attempt after first fails with retryable error', async () => {
    mockAxiosInstance
      .mockRejectedValueOnce({ response: { status: 500 } })
      .mockResolvedValueOnce({ data: { success: true } })

    const promise = requestWithRetry({ url: '/test' })
    await vi.advanceTimersByTimeAsync(1000)

    const result = await promise
    expect(result).toEqual({ success: true })
    expect(mockAxiosInstance).toHaveBeenCalledTimes(2)
  })
})

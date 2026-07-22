/** error-messages 工具函数测试 */

import { describe, it, expect } from 'vitest'
import {
  getErrorTypeFromStatus,
  getErrorMessage,
  getErrorMessageByType,
  type ErrorType,
} from './error-messages'

describe('getErrorTypeFromStatus', () => {
  it('returns network for status 0', () => {
    expect(getErrorTypeFromStatus(0)).toBe('network')
  })

  it('returns unauthorized for 401', () => {
    expect(getErrorTypeFromStatus(401)).toBe('unauthorized')
  })

  it('returns forbidden for 403', () => {
    expect(getErrorTypeFromStatus(403)).toBe('forbidden')
  })

  it('returns not-found for 404', () => {
    expect(getErrorTypeFromStatus(404)).toBe('not-found')
  })

  it('returns timeout for 408', () => {
    expect(getErrorTypeFromStatus(408)).toBe('timeout')
  })

  it('returns timeout for 504', () => {
    expect(getErrorTypeFromStatus(504)).toBe('timeout')
  })

  it('returns conflict for 409', () => {
    expect(getErrorTypeFromStatus(409)).toBe('conflict')
  })

  it('returns validation for 422', () => {
    expect(getErrorTypeFromStatus(422)).toBe('validation')
  })

  it('returns rate-limit for 429', () => {
    expect(getErrorTypeFromStatus(429)).toBe('rate-limit')
  })

  it('returns cancelled for 499', () => {
    expect(getErrorTypeFromStatus(499)).toBe('cancelled')
  })

  it('returns server for 500', () => {
    expect(getErrorTypeFromStatus(500)).toBe('server')
  })

  it('returns server for 502', () => {
    expect(getErrorTypeFromStatus(502)).toBe('server')
  })

  it('returns server for 503', () => {
    expect(getErrorTypeFromStatus(503)).toBe('server')
  })

  it('returns unknown for unrecognized status', () => {
    expect(getErrorTypeFromStatus(418)).toBe('unknown')
  })

  it('returns unknown for 200', () => {
    expect(getErrorTypeFromStatus(200)).toBe('unknown')
  })
})

describe('getErrorMessage', () => {
  it('returns correct message for network error', () => {
    const error = new Error('Network Error')
    const result = getErrorMessage(error)
    expect(result.title).toBe('网络连接失败')
    expect(result.retryable).toBe(true)
  })

  it('returns correct message for Failed to fetch error', () => {
    const error = new Error('Failed to fetch')
    const result = getErrorMessage(error)
    expect(result.title).toBe('网络连接失败')
  })

  it('returns correct message for timeout error', () => {
    const error = new Error('timeout of 10000ms exceeded')
    const result = getErrorMessage(error)
    expect(result.title).toBe('请求超时')
    expect(result.retryable).toBe(true)
  })

  it('returns correct message for Timeout error', () => {
    const error = new Error('Timeout')
    const result = getErrorMessage(error)
    expect(result.title).toBe('请求超时')
  })

  it('returns unknown for unrecognized error', () => {
    const error = new Error('Something weird happened')
    const result = getErrorMessage(error)
    expect(result.title).toBe('未知错误')
  })

  it('returns correct message for status code 404', () => {
    const result = getErrorMessage(404)
    expect(result.title).toBe('资源不存在')
    expect(result.retryable).toBe(false)
  })

  it('returns correct message for status code 500', () => {
    const result = getErrorMessage(500)
    expect(result.title).toBe('服务器错误')
    expect(result.retryable).toBe(true)
  })
})

describe('getErrorMessageByType', () => {
  it('returns message for each error type', () => {
    const types: ErrorType[] = [
      'network', 'timeout', 'server', 'not-found',
      'unauthorized', 'forbidden', 'validation',
      'rate-limit', 'conflict', 'cancelled', 'unknown',
    ]

    types.forEach((type) => {
      const result = getErrorMessageByType(type)
      expect(result).toHaveProperty('title')
      expect(result).toHaveProperty('description')
      expect(result).toHaveProperty('suggestion')
      expect(result).toHaveProperty('retryable')
      expect(typeof result.title).toBe('string')
      expect(result.title.length).toBeGreaterThan(0)
    })
  })

  it('returns consistent data for same type', () => {
    const first = getErrorMessageByType('network')
    const second = getErrorMessageByType('network')
    expect(first).toEqual(second)
  })
})

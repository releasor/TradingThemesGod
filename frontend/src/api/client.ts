/** 共享 API 客户端
 *
 * 统一的 axios 实例，所有 API 模块共用。
 * 可在此处添加请求/响应拦截器（如全局错误处理、token 注入）。
 */

import axios, { type AxiosRequestConfig } from 'axios'

import { getAuthToken, useAuthStore } from '@/stores/auth'

const AUTH_EXEMPT_PATHS = ['/auth/login', '/auth/register']

/** API 错误事件 */
export interface ApiErrorEvent {
  status: number
  message: string
  url?: string
}

/** 错误监听器列表 */
const errorListeners: Array<(event: ApiErrorEvent) => void> = []

const NETWORK_ERROR_COOLDOWN_MS = 8_000
let lastNetworkErrorNoticeAt = 0

/** 注册 API 错误监听器，返回取消注册函数 */
export function onApiError(listener: (event: ApiErrorEvent) => void): () => void {
  errorListeners.push(listener)
  return () => {
    const index = errorListeners.indexOf(listener)
    if (index > -1) errorListeners.splice(index, 1)
  }
}

/** 通知所有错误监听器 */
function notifyError(event: ApiErrorEvent): void {
  if (event.status === 0) {
    const now = Date.now()
    if (now - lastNetworkErrorNoticeAt < NETWORK_ERROR_COOLDOWN_MS) {
      return
    }
    lastNetworkErrorNoticeAt = now
    event = {
      ...event,
      message: '无法连接后端服务，请确认 backend 已在 localhost:8000 启动',
    }
  }

  for (const listener of errorListeners) {
    try {
      listener(event)
    } catch {
      // 监听器异常不影响其他监听器
    }
  }
}

/** 状态码对应的中文消息 */
const STATUS_MESSAGES: Record<number, string> = {
  400: '请求参数错误',
  401: '未授权访问',
  403: '权限不足',
  404: '资源不存在',
  408: '请求超时',
  409: '数据冲突',
  422: '请求参数错误',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务不可用',
  504: '网关超时',
}

/** 是否可重试的状态码 */
const RETRYABLE_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504])

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10_000,
})

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url

    // 统一处理网络错误和服务器错误
    if (error.response) {
      const { status, data } = error.response
      const message = data?.message || data?.detail || '请求失败'
      const requestUrl = String(url || '')

      if (
        status === 401 &&
        !AUTH_EXEMPT_PATHS.some((path) => requestUrl.includes(path))
      ) {
        useAuthStore.getState().clearAuth()
        const currentPath = window.location.pathname
        if (!currentPath.startsWith('/login') && !currentPath.startsWith('/register')) {
          const redirect = encodeURIComponent(currentPath)
          window.location.assign(`/login?from=${redirect}`)
          return Promise.reject(error)
        }
      }

      notifyError({
        status,
        message: STATUS_MESSAGES[status] || `请求失败 (${status}): ${message}`,
        url,
      })
    } else if (error.request) {
      notifyError({ status: 0, message: '网络错误，请检查网络连接', url })
    }

    return Promise.reject(error)
  }
)

/**
 * 带重试的请求函数
 *
 * @param config - axios 请求配置
 * @param maxRetries - 最大重试次数
 * @returns 响应数据
 */
export async function requestWithRetry<T>(
  config: AxiosRequestConfig,
  maxRetries = 2
): Promise<T> {
  let lastError: Error | null = null

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await apiClient(config)
      return response.data
    } catch (error) {
      lastError = error as Error

      // 检查是否可重试
      const axiosError = error as { response?: { status: number } }
      const status = axiosError.response?.status

      if (!status || !RETRYABLE_STATUS_CODES.has(status) || attempt === maxRetries) {
        throw error
      }

      // 指数退避
      const delay = Math.min(1000 * Math.pow(2, attempt), 10000)
      await new Promise((resolve) => setTimeout(resolve, delay))
    }
  }

  throw lastError
}

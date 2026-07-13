/** 共享 API 客户端
 *
 * 统一的 axios 实例，所有 API 模块共用。
 * 可在此处添加请求/响应拦截器（如全局错误处理、token 注入）。
 */

import axios from 'axios'

/** API 错误事件 */
export interface ApiErrorEvent {
  status: number
  message: string
}

/** 错误监听器列表 */
const errorListeners: Array<(event: ApiErrorEvent) => void> = []

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
  for (const listener of errorListeners) {
    try {
      listener(event)
    } catch {
      // 监听器异常不影响其他监听器
    }
  }
}

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10_000,
})

// 响应拦截器：统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 统一处理网络错误和服务器错误
    if (error.response) {
      const { status, data } = error.response
      const message = data?.message || '请求失败'

      const statusMessages: Record<number, string> = {
        401: '未授权访问',
        403: '权限不足',
        404: '资源不存在',
        500: '服务器内部错误',
      }
      notifyError({
        status,
        message: statusMessages[status] || `请求失败 (${status}): ${message}`,
      })
    } else if (error.request) {
      notifyError({ status: 0, message: '网络错误，请检查网络连接' })
    }

    return Promise.reject(error)
  }
)

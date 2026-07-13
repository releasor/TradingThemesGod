/** 共享 API 客户端
 *
 * 统一的 axios 实例，所有 API 模块共用。
 * 可在此处添加请求/响应拦截器（如全局错误处理、token 注入）。
 */

import axios from 'axios'

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

      switch (status) {
        case 401:
          console.error('未授权访问')
          break
        case 403:
          console.error('权限不足')
          break
        case 404:
          console.error('资源不存在')
          break
        case 500:
          console.error('服务器内部错误')
          break
        default:
          console.error(`请求失败 (${status}): ${message}`)
      }
    } else if (error.request) {
      console.error('网络错误，请检查网络连接')
    }

    return Promise.reject(error)
  }
)

/** 错误消息映射

为不同类型的错误提供友好的中文提示。
*/

/** 错误类型 */
export type ErrorType =
  | 'network'
  | 'timeout'
  | 'server'
  | 'not-found'
  | 'unauthorized'
  | 'forbidden'
  | 'validation'
  | 'rate-limit'
  | 'conflict'
  | 'cancelled'
  | 'unknown'

/** 错误信息 */
export interface ErrorMessage {
  /** 错误标题 */
  title: string
  /** 错误描述 */
  description: string
  /** 恢复建议 */
  suggestion: string
  /** 是否可重试 */
  retryable: boolean
}

/** 错误消息映射 */
const errorMessages: Record<ErrorType, ErrorMessage> = {
  network: {
    title: '网络连接失败',
    description: '无法连接到服务器，请检查您的网络连接。',
    suggestion: '请检查网络连接后重试，或刷新页面。',
    retryable: true,
  },
  timeout: {
    title: '请求超时',
    description: '服务器响应时间过长，请稍后重试。',
    suggestion: '服务器可能正在处理大量请求，请稍后重试。',
    retryable: true,
  },
  server: {
    title: '服务器错误',
    description: '服务器遇到了问题，请稍后重试。',
    suggestion: '如果问题持续存在，请联系管理员。',
    retryable: true,
  },
  'not-found': {
    title: '资源不存在',
    description: '请求的资源不存在或已被移除。',
    suggestion: '请检查 URL 是否正确，或返回首页。',
    retryable: false,
  },
  unauthorized: {
    title: '未授权访问',
    description: '您需要登录才能访问此资源。',
    suggestion: '请登录后重试。',
    retryable: false,
  },
  forbidden: {
    title: '访问被拒绝',
    description: '您没有权限访问此资源。',
    suggestion: '请联系管理员获取权限。',
    retryable: false,
  },
  validation: {
    title: '请求参数错误',
    description: '请求的参数不正确。',
    suggestion: '请检查输入后重试。',
    retryable: false,
  },
  unknown: {
    title: '未知错误',
    description: '发生了未知错误。',
    suggestion: '请刷新页面或联系管理员。',
    retryable: true,
  },
  'rate-limit': {
    title: '请求过于频繁',
    description: '您发送了太多请求，请稍后重试。',
    suggestion: '请等待一段时间后重试。',
    retryable: true,
  },
  conflict: {
    title: '数据冲突',
    description: '数据已被其他操作修改。',
    suggestion: '请刷新页面获取最新数据。',
    retryable: true,
  },
  cancelled: {
    title: '请求已取消',
    description: '请求已被取消。',
    suggestion: '请重新发起请求。',
    retryable: false,
  },
}

/**
 * 根据 HTTP 状态码获取错误类型
 *
 * @param status - HTTP 状态码
 * @returns 错误类型
 */
export function getErrorTypeFromStatus(status: number): ErrorType {
  if (status === 0) return 'network'
  if (status === 401) return 'unauthorized'
  if (status === 403) return 'forbidden'
  if (status === 404) return 'not-found'
  if (status === 408 || status === 504) return 'timeout'
  if (status === 409) return 'conflict'
  if (status === 422) return 'validation'
  if (status === 429) return 'rate-limit'
  if (status === 499) return 'cancelled'
  if (status >= 500) return 'server'
  return 'unknown'
}

/**
 * 根据错误获取友好的错误消息
 *
 * @param error - 错误对象或 HTTP 状态码
 * @returns 错误消息
 */
export function getErrorMessage(error: Error | number): ErrorMessage {
  let errorType: ErrorType

  if (typeof error === 'number') {
    errorType = getErrorTypeFromStatus(error)
  } else if (error.message.includes('Network Error') || error.message.includes('Failed to fetch')) {
    errorType = 'network'
  } else if (error.message.includes('timeout') || error.message.includes('Timeout')) {
    errorType = 'timeout'
  } else {
    errorType = 'unknown'
  }

  return errorMessages[errorType]
}

/**
 * 根据错误类型获取错误消息
 *
 * @param errorType - 错误类型
 * @returns 错误消息
 */
export function getErrorMessageByType(errorType: ErrorType): ErrorMessage {
  return errorMessages[errorType]
}

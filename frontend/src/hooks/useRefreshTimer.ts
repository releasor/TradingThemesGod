/** 刷新过程计时 Hook */

import { useEffect, useState } from 'react'

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds} 秒`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return rest > 0 ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`
}

export function useRefreshTimer(active: boolean) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useEffect(() => {
    if (!active) {
      setElapsedSeconds(0)
      return
    }

    const startedAt = Date.now()
    setElapsedSeconds(0)
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)

    return () => window.clearInterval(timer)
  }, [active])

  return {
    elapsedSeconds,
    elapsedLabel: formatElapsed(elapsedSeconds),
  }
}

export function formatRefreshDurationMs(ms: number): string {
  return formatElapsed(Math.max(1, Math.round(ms / 1000)))
}

export function quoteSourceLabel(source: string): string {
  switch (source) {
    case 'eastmoney':
      return '东方财富'
    case 'akshare':
      return 'AKShare'
    default:
      return source
  }
}

/** React Query helpers shared across the app. */

/** Detect request abort/cancel from RQ, axios, or AbortController. */
export function isCancelledError(error: unknown): boolean {
  if (error == null || typeof error !== 'object') return false
  const e = error as { name?: string; code?: string }
  if (e.name === 'CancelledError' || e.name === 'CanceledError' || e.name === 'AbortError') {
    return true
  }
  if (e.code === 'ERR_CANCELED') return true
  return false
}

type RefetchResult = {
  error: unknown
  isError: boolean
}

type RefetchFn = (options?: {
  throwOnError?: boolean
  cancelRefetch?: boolean
}) => Promise<RefetchResult>

/** Refetch without surfacing cancellation from overlapping in-flight requests. */
export async function refetchIgnoringCancel(refetch: RefetchFn): Promise<void> {
  try {
    const result = await refetch({ cancelRefetch: false })
    if (result.isError && result.error && !isCancelledError(result.error)) {
      throw result.error
    }
  } catch (error) {
    if (!isCancelledError(error)) {
      throw error
    }
  }
}

/** React Query helpers shared across the app. */

export function isCancelledError(error: unknown): boolean {
  return error instanceof Error && error.name === 'CancelledError'
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

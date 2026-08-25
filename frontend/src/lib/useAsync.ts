/** Small data-fetching hook: one loading/error/data contract for every screen. */

import { useCallback, useEffect, useRef, useState } from 'react'

import { errorMessage } from './api'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
  /** Re-run the loader. Safe to call from event handlers. */
  reload: () => Promise<void>
  /** Replace the data locally, e.g. after a mutation returns the new record. */
  setData: (value: T | null) => void
}

export function useAsync<T>(
  loader: () => Promise<T>,
  deps: unknown[] = [],
  options: { enabled?: boolean } = {},
): AsyncState<T> {
  const enabled = options.enabled ?? true
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)
  const mounted = useRef(true)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const run = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    setError(null)
    try {
      const result = await loaderRef.current()
      if (mounted.current) setData(result)
    } catch (caught) {
      if (mounted.current) setError(errorMessage(caught))
    } finally {
      if (mounted.current) setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    void run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, ...deps])

  return { data, loading, error, reload: run, setData }
}

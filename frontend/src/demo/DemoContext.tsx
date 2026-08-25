/**
 * SIH demo mode.
 *
 * Holds the scripted scenario, tracks which of the ten steps the judge has
 * reached (derived from the real booking's status, never from a local
 * counter), and exposes a reset that restores the deterministic dataset.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { errorMessage } from '../lib/api'
import * as endpoints from '../lib/endpoints'
import type { BookingStatus, DemoState, DemoStep } from '../lib/types'

const STORAGE_KEY = 'nookr.demoMode'

/** Which scripted step a booking in a given status is waiting on. */
const STEP_FOR_STATUS: Record<BookingStatus, number> = {
  REQUESTED: 1,
  DECLINED: 1,
  ASSIGNED: 3,
  ACCEPTED: 4,
  IN_PROGRESS: 5,
  COMPLETED: 6,
  PAID: 7,
  RATED: 8,
  CANCELLED: 0,
}

export interface DemoContextValue {
  enabled: boolean
  setEnabled: (value: boolean) => void
  state: DemoState | null
  steps: DemoStep[]
  /** Index of the step the judge should do next. */
  currentStep: number
  scenarioBookingId: number | null
  loading: boolean
  resetting: boolean
  error: string | null
  message: string | null
  refresh: () => Promise<void>
  reset: () => Promise<void>
  startScenario: () => Promise<string | null>
  clearMessage: () => void
}

const DemoContext = createContext<DemoContextValue | null>(null)

function readStored(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

export function DemoProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabledState] = useState(readStored)
  const [state, setState] = useState<DemoState | null>(null)
  const [loading, setLoading] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const setEnabled = useCallback((value: boolean) => {
    setEnabledState(value)
    try {
      localStorage.setItem(STORAGE_KEY, String(value))
    } catch {
      /* storage unavailable */
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setState(await endpoints.getDemoState())
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const reset = useCallback(async () => {
    setResetting(true)
    setError(null)
    setMessage(null)
    try {
      const result = await endpoints.resetDemo()
      setMessage(result.message)
      await refresh()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setResetting(false)
    }
  }, [refresh])

  const startScenario = useCallback(async () => {
    setError(null)
    try {
      const result = await endpoints.startScenario()
      setMessage(result.message)
      await refresh()
      return result.scenario_request
    } catch (caught) {
      setError(errorMessage(caught))
      return null
    }
  }, [refresh])

  const booking = state?.active_scenario_booking ?? null
  const currentStep = booking ? (STEP_FOR_STATUS[booking.status] ?? 0) : 0

  const value = useMemo<DemoContextValue>(
    () => ({
      enabled,
      setEnabled,
      state,
      steps: state?.steps ?? [],
      currentStep,
      scenarioBookingId: booking?.id ?? null,
      loading,
      resetting,
      error,
      message,
      refresh,
      reset,
      startScenario,
      clearMessage: () => setMessage(null),
    }),
    [
      enabled,
      setEnabled,
      state,
      currentStep,
      booking,
      loading,
      resetting,
      error,
      message,
      refresh,
      reset,
      startScenario,
    ],
  )

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

export function useDemo(): DemoContextValue {
  const context = useContext(DemoContext)
  if (!context) throw new Error('useDemo must be used inside <DemoProvider>')
  return context
}

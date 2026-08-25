/**
 * Session state.
 *
 * Holds the signed-in user, restores a session from the stored token on boot,
 * and clears everything when the API reports the token is no longer valid.
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

import { getToken, setToken, setUnauthorizedHandler } from '../lib/api'
import * as endpoints from '../lib/endpoints'
import type { Role, User } from '../lib/types'

export interface AuthContextValue {
  user: User | null
  /** True until the stored token has been checked, so routes do not flash. */
  initialising: boolean
  signIn: (email: string, password: string) => Promise<User>
  signInAsDemo: (role: Role) => Promise<User>
  registerAccount: (payload: endpoints.RegisterPayload) => Promise<User>
  signOut: () => void
  refresh: () => Promise<void>
  /** Adopt a token issued elsewhere, e.g. by a demo reset. */
  adoptToken: (token: string) => Promise<User>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [initialising, setInitialising] = useState(true)

  const signOut = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null)
      setUser(null)
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  useEffect(() => {
    let cancelled = false
    const restore = async () => {
      // No stored token means no session to restore: skip the round trip
      // rather than provoking a 401 on every cold load.
      if (!getToken()) {
        setInitialising(false)
        return
      }
      try {
        const me = await endpoints.getMe()
        if (!cancelled) setUser(me)
      } catch {
        // No valid session; the app shows the public routes.
        if (!cancelled) setUser(null)
      } finally {
        if (!cancelled) setInitialising(false)
      }
    }
    void restore()
    return () => {
      cancelled = true
    }
  }, [])

  const adopt = useCallback((token: string, nextUser: User) => {
    setToken(token)
    setUser(nextUser)
    return nextUser
  }, [])

  const signIn = useCallback(
    async (email: string, password: string) => {
      const response = await endpoints.login(email, password)
      return adopt(response.access_token, response.user)
    },
    [adopt],
  )

  const signInAsDemo = useCallback(
    async (role: Role) => {
      const response = await endpoints.demoLogin(role)
      return adopt(response.access_token, response.user)
    },
    [adopt],
  )

  const registerAccount = useCallback(
    async (payload: endpoints.RegisterPayload) => {
      const response = await endpoints.register(payload)
      return adopt(response.access_token, response.user)
    },
    [adopt],
  )

  const refresh = useCallback(async () => {
    try {
      setUser(await endpoints.getMe())
    } catch {
      setUser(null)
    }
  }, [])

  const adoptToken = useCallback(async (token: string) => {
    setToken(token)
    const me = await endpoints.getMe()
    setUser(me)
    return me
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      initialising,
      signIn,
      signInAsDemo,
      registerAccount,
      signOut,
      refresh,
      adoptToken,
    }),
    [user, initialising, signIn, signInAsDemo, registerAccount, signOut, refresh, adoptToken],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}

/** Where each role lands after signing in. */
export function homeRouteFor(role: Role | undefined): string {
  switch (role) {
    case 'ADMIN':
      return '/dashboard'
    case 'WORKER':
      return '/worker'
    case 'CUSTOMER':
      return '/customer'
    default:
      return '/login'
  }
}

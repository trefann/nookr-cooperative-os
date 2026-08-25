/**
 * Routing.
 *
 * Public screens for signing in, everything else behind a role check that
 * redirects rather than rendering an empty page.
 */

import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { homeRouteFor, useAuth } from './auth/AuthContext'
import { AppShell } from './components/layout/AppShell'
import { Spinner } from './components/ui'
import type { Role } from './lib/types'

import AnalyticsPage from './pages/AnalyticsPage'
import BookingDetailPage from './pages/BookingDetailPage'
import BookingsPage from './pages/BookingsPage'
import CustomerPage from './pages/CustomerPage'
import DashboardPage from './pages/DashboardPage'
import ForecastPage from './pages/ForecastPage'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import MatchingPage from './pages/MatchingPage'
import NotFoundPage from './pages/NotFoundPage'
import RegisterPage from './pages/RegisterPage'
import ServicesPage from './pages/ServicesPage'
import WelfarePage from './pages/WelfarePage'
import WorkerPage from './pages/WorkerPage'
import WorkforcePage from './pages/WorkforcePage'

function FullPageSpinner() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <Spinner label="Loading Nookr" />
    </div>
  )
}

function Protected({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { user, initialising } = useAuth()
  const location = useLocation()

  if (initialising) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (roles && !roles.includes(user.role)) return <Navigate to={homeRouteFor(user.role)} replace />

  return <AppShell>{children}</AppShell>
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { user, initialising } = useAuth()
  if (initialising) return <FullPageSpinner />
  if (user) return <Navigate to={homeRouteFor(user.role)} replace />
  return <>{children}</>
}

export default function App() {
  const { user, initialising } = useAuth()

  return (
    <Routes>
      <Route
        path="/"
        element={
          initialising ? (
            <FullPageSpinner />
          ) : user ? (
            <Navigate to={homeRouteFor(user.role)} replace />
          ) : (
            <LandingPage />
          )
        }
      />

      <Route
        path="/login"
        element={
          <PublicOnly>
            <LoginPage />
          </PublicOnly>
        }
      />
      <Route
        path="/register"
        element={
          <PublicOnly>
            <RegisterPage />
          </PublicOnly>
        }
      />

      <Route
        path="/customer"
        element={
          <Protected roles={['CUSTOMER', 'ADMIN']}>
            <CustomerPage />
          </Protected>
        }
      />
      <Route
        path="/worker"
        element={
          <Protected roles={['WORKER']}>
            <WorkerPage />
          </Protected>
        }
      />
      <Route
        path="/dashboard"
        element={
          <Protected roles={['ADMIN']}>
            <DashboardPage />
          </Protected>
        }
      />
      <Route
        path="/services"
        element={
          <Protected>
            <ServicesPage />
          </Protected>
        }
      />
      <Route
        path="/bookings"
        element={
          <Protected>
            <BookingsPage />
          </Protected>
        }
      />
      <Route
        path="/bookings/:bookingId"
        element={
          <Protected>
            <BookingDetailPage />
          </Protected>
        }
      />
      <Route
        path="/matching"
        element={
          <Protected roles={['CUSTOMER', 'ADMIN']}>
            <MatchingPage />
          </Protected>
        }
      />
      <Route
        path="/forecast"
        element={
          <Protected roles={['WORKER', 'ADMIN']}>
            <ForecastPage />
          </Protected>
        }
      />
      <Route
        path="/workforce"
        element={
          <Protected roles={['WORKER', 'ADMIN']}>
            <WorkforcePage />
          </Protected>
        }
      />
      <Route
        path="/welfare"
        element={
          <Protected roles={['WORKER', 'ADMIN']}>
            <WelfarePage />
          </Protected>
        }
      />
      <Route
        path="/analytics"
        element={
          <Protected roles={['ADMIN']}>
            <AnalyticsPage />
          </Protected>
        }
      />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

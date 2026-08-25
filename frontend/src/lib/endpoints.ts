/**
 * Typed API surface.
 *
 * Components call these functions; nothing in the UI constructs a URL.
 */

import { api } from './api'
import type {
  AnalyticsResponse,
  AuthResponse,
  Booking,
  BookingDetail,
  BookingStatus,
  CustomerSummary,
  DashboardResponse,
  DemoAccount,
  DemoResetResponse,
  DemoState,
  ForecastResponse,
  HealthResponse,
  Invoice,
  MatchResponse,
  Notification,
  PaymentResponse,
  RatingResponse,
  Role,
  Service,
  UnderstandResponse,
  User,
  WelfareResponse,
  Worker,
  WorkerDetail,
  WorkerSummary,
  WorkforceResponse,
  Zone,
} from './types'

/* -- meta ---------------------------------------------------------------- */

export const getHealth = () => api.get<HealthResponse>('/api/health')

/* -- auth ---------------------------------------------------------------- */

export const login = (email: string, password: string) =>
  api.post<AuthResponse>('/api/auth/login', { email, password }, { anonymous: true })

export interface RegisterPayload {
  email: string
  password: string
  full_name: string
  role: Role
  phone?: string
  address?: string
  zone_id?: number | null
  language?: string
}

export const register = (payload: RegisterPayload) =>
  api.post<AuthResponse>('/api/auth/register', payload, { anonymous: true })

export const demoLogin = (role: Role) =>
  api.post<AuthResponse>('/api/auth/demo-login', { role }, { anonymous: true })

export const getDemoAccounts = () =>
  api.get<DemoAccount[]>('/api/auth/demo-accounts')

export const getMe = () => api.get<User>('/api/auth/me')

/* -- catalogue ----------------------------------------------------------- */

export const getServices = () => api.get<Service[]>('/api/services')
export const getZones = () => api.get<Zone[]>('/api/zones')

/* -- workers ------------------------------------------------------------- */

export interface WorkerFilters {
  service_id?: number
  zone_id?: number
  skill_id?: number
  availability?: string
  search?: string
  lat?: number
  lng?: number
  limit?: number
}

export const getWorkers = (filters: WorkerFilters = {}) =>
  api.get<Worker[]>('/api/workers', filters as Record<string, string | number>)

export const getWorker = (id: number) => api.get<WorkerDetail>(`/api/workers/${id}`)

export const getMyWorkerSummary = () => api.get<WorkerSummary>('/api/workers/me/summary')

export const setAvailability = (availability_status: string) =>
  api.patch<WorkerDetail>('/api/workers/me/availability', { availability_status })

/* -- bookings ------------------------------------------------------------ */

export interface CreateBookingPayload {
  raw_request?: string
  service_id?: number | null
  problem_summary?: string
  skill_ids?: number[]
  zone_id?: number | null
  address?: string
  lat?: number | null
  lng?: number | null
  urgency?: string | null
  workers_required?: number
  scheduled_for?: string | null
  preferred_time_label?: string
  is_emergency?: boolean
}

export const createBooking = (payload: CreateBookingPayload) =>
  api.post<BookingDetail>('/api/bookings', payload)

export interface BookingFilters {
  status?: BookingStatus
  active_only?: boolean
  service_id?: number
  zone_id?: number
  worker_id?: number
  unassigned?: boolean
  limit?: number
}

export const getBookings = (filters: BookingFilters = {}) =>
  api.get<Booking[]>('/api/bookings', filters as Record<string, string | number | boolean>)

export const getBooking = (id: number) => api.get<BookingDetail>(`/api/bookings/${id}`)

export const setBookingStatus = (id: number, status: BookingStatus) =>
  api.patch<BookingDetail>(`/api/bookings/${id}/status`, { status })

/* -- customer ------------------------------------------------------------ */

export const getCustomerSummary = () => api.get<CustomerSummary>('/api/customer/summary')

/* -- AI ------------------------------------------------------------------ */

export const understandRequest = (text: string, zone_id?: number | null) =>
  api.post<UnderstandResponse>('/api/ai/understand-request', { text, zone_id })

export interface MatchPayload {
  booking_id?: number
  service_id?: number
  skill_ids?: number[]
  zone_id?: number | null
  lat?: number | null
  lng?: number | null
  scheduled_for?: string | null
  urgency?: string | null
  workers_required?: number
  limit?: number
}

export const findMatches = (payload: MatchPayload) =>
  api.post<MatchResponse>('/api/matching', payload)

export const assignWorker = (booking_id: number, worker_id: number) =>
  api.post<{ booking: BookingDetail; allocation: unknown }>('/api/matching/assign', {
    booking_id,
    worker_id,
  })

/* -- intelligence -------------------------------------------------------- */

export const getForecast = (zone_id?: number) =>
  api.get<ForecastResponse>('/api/forecast', zone_id ? { zone_id } : undefined)

export const getWorkforce = () => api.get<WorkforceResponse>('/api/workforce')
export const getWelfare = () => api.get<WelfareResponse>('/api/welfare')
export const getDashboard = () => api.get<DashboardResponse>('/api/dashboard')
export const getAnalytics = (days = 30) =>
  api.get<AnalyticsResponse>('/api/analytics', { days })

/* -- transactions -------------------------------------------------------- */

export const payForBooking = (booking_id: number, method = 'UPI_SIMULATED') =>
  api.post<PaymentResponse>('/api/payments', { booking_id, method })

export const getInvoice = (booking_id: number) =>
  api.get<Invoice>(`/api/payments/${booking_id}/invoice`)

export const submitRating = (booking_id: number, stars: number, comment: string) =>
  api.post<RatingResponse>('/api/ratings', { booking_id, stars, comment })

export const getNotifications = (unread_only = false) =>
  api.get<Notification[]>('/api/notifications', { unread_only })

export const markNotificationRead = (id: number) =>
  api.patch<{ id: number; is_read: boolean }>(`/api/notifications/${id}/read`)

/* -- demo ---------------------------------------------------------------- */

export const getDemoState = () => api.get<DemoState>('/api/demo/state')
export const resetDemo = () => api.post<DemoResetResponse>('/api/demo/reset')
export const startScenario = () =>
  api.post<{ ready: boolean; message: string; scenario_request: string }>(
    '/api/demo/scenario/start',
  )

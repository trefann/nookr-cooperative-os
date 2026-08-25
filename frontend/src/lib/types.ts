/** Shapes returned by the Nookr API. */

export type Role = 'CUSTOMER' | 'WORKER' | 'ADMIN'

export type BookingStatus =
  | 'REQUESTED'
  | 'ASSIGNED'
  | 'ACCEPTED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'PAID'
  | 'RATED'
  | 'DECLINED'
  | 'CANCELLED'

export type Urgency = 'LOW' | 'NORMAL' | 'HIGH' | 'EMERGENCY'
export type AvailabilityStatus = 'AVAILABLE' | 'BUSY' | 'OFF_DUTY'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  phone: string
  address: string
  language: string
  is_demo: boolean
  cooperative_id: number | null
  zone_id: number | null
  lat: number
  lng: number
  worker_id: number | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface DemoAccount {
  role: Role
  label: string
  email: string
  password: string
  description: string
}

export interface SkillRef {
  id: number
  name: string
  slug: string
  is_emerging: boolean
  requires_certification: boolean
  is_primary: boolean
}

export interface Service {
  id: number
  name: string
  slug: string
  description: string
  icon: string
  base_price: number
  avg_duration_minutes: number
  emergency_supported: boolean
  skills: SkillRef[]
}

export interface Zone {
  id: number
  name: string
  code: string
  city: string
  lat: number
  lng: number
  description: string
}

export interface WorkerSkill {
  skill_id: number
  name: string
  slug: string
  proficiency: number
  years_experience: number
  is_emerging: boolean
}

export interface Certification {
  id: number
  name: string
  issuing_body: string
  credential_id: string
  issued_on: string | null
  expires_on: string | null
  verified: boolean
}

export interface AvailabilitySlot {
  day_of_week: number
  start_time: string
  end_time: string
  is_available: boolean
}

export interface Worker {
  id: number
  user_id: number
  name: string
  headline: string
  service_id: number
  service_name: string
  zone_id: number
  zone_name: string
  rating_avg: number
  rating_count: number
  jobs_completed: number
  experience_years: number
  availability_status: AvailabilityStatus
  verification_status: string
  insurance_active: boolean
  training_credits: number
  weekly_capacity: number
  workload_pct: number
  active_jobs: number
  skills: WorkerSkill[]
  certification_count: number
  lat: number
  lng: number
  distance_km: number | null
}

export interface WorkerDetail extends Worker {
  bio: string
  phone: string
  email: string
  total_earnings: number
  joined_on: string | null
  certifications: Certification[]
  availability: AvailabilitySlot[]
  committed_jobs: number
}

export interface Payment {
  id: number
  booking_id: number
  invoice_number: string
  amount: number
  worker_amount: number
  cooperative_amount: number
  welfare_amount: number
  technology_amount: number
  status: string
  method: string
  paid_at: string | null
}

export interface Rating {
  id: number
  booking_id: number
  stars: number
  comment: string
  created_at: string | null
}

export interface TimelineStep {
  status: BookingStatus
  label: string
  state: 'done' | 'current' | 'pending'
  at: string | null
}

export interface BookingWorker {
  id: number
  name: string
  headline: string
  rating_avg: number
  rating_count: number
  jobs_completed: number
  phone: string
  availability_status: AvailabilityStatus
  verification_status: string
  zone: string
  lat: number
  lng: number
}

export interface Booking {
  id: number
  reference: string
  status: BookingStatus
  urgency: Urgency
  is_emergency: boolean
  service_id: number
  service_name: string
  service_slug: string
  zone_id: number
  zone_name: string
  problem_summary: string
  raw_request: string
  address: string
  lat: number
  lng: number
  workers_required: number
  scheduled_for: string | null
  preferred_time_label: string
  estimated_price: number
  final_price: number | null
  distance_km: number | null
  customer_id: number
  customer_name: string
  worker: BookingWorker | null
  required_skills: string[]
  created_at: string | null
  assigned_at: string | null
  accepted_at: string | null
  started_at: string | null
  completed_at: string | null
  payment: Payment | null
  rating: Rating | null
  timeline: TimelineStep[]
}

export interface PaymentSplit {
  amount: number
  worker_amount: number
  cooperative_amount: number
  welfare_amount: number
  technology_amount: number
}

export interface BookingDetail extends Booking {
  ai_interpretation: Understanding | null
  match_breakdown: MatchCandidate | null
  declined_worker_ids: number[]
  payment_split_preview: PaymentSplit | null
  eta_minutes: number | null
}

/* -------------------------------------------------------------------------- */
/* AI #1 - service understanding                                              */
/* -------------------------------------------------------------------------- */

export interface Understanding {
  service_slug: string
  service_name: string
  problem: string
  skill_slugs: string[]
  skill_names: string[]
  workers_required: number
  urgency: Urgency
  preferred_time_label: string
  scheduled_for: string | null
  confidence: number
  method: string
  matched_terms: string[]
  notes: string
}

export interface UnderstandResponse {
  understanding: Understanding
  engine: {
    method: string
    llm_configured: boolean
    is_fallback: boolean
    confidence: number
    explanation: string
  }
  service: { id: number; name: string; slug: string; base_price: number; emergency_supported: boolean } | null
  skills: { id: number; name: string; slug: string }[]
  zone: { id: number; name: string } | null
  estimated_price: number | null
}

/* -------------------------------------------------------------------------- */
/* AI #2 - matching                                                           */
/* -------------------------------------------------------------------------- */

export interface ScoreComponent {
  key: 'skill' | 'availability' | 'location' | 'rating' | 'fairness'
  label: string
  score: number
  percent: number
  weight: number
  weight_percent: number
  contribution: number
  reason: string
}

export interface MatchCandidate {
  worker_id: number
  worker_name: string
  headline: string
  zone_name: string
  rating_avg: number
  rating_count: number
  jobs_completed: number
  distance_km: number
  eta_minutes: number
  availability_status: AvailabilityStatus
  verification_status: string
  workload_pct: number
  matched_skills: string[]
  missing_skills: string[]
  certifications: string[]
  components: ScoreComponent[]
  final_score: number
  score_percent: number
  explanation: string
  warnings: string[]
  recommended: boolean
}

export interface MatchResponse {
  method: string
  workers_required: number
  considered: number
  weights: Record<string, { label: string; percent: number }>
  excluded: { worker: string; reason: string }[]
  candidates: MatchCandidate[]
  recommended: MatchCandidate | null
  booking_id: number | null
  emergency: boolean
  message?: string
}

/* -------------------------------------------------------------------------- */
/* AI #3/#4/#5 - forecast, workforce, skill gaps                              */
/* -------------------------------------------------------------------------- */

export interface ServiceForecast {
  service_id: number
  service_name: string
  service_slug: string
  predicted_demand: number
  last_week_demand: number
  baseline_demand: number
  change_pct: number
  change_basis: string
  change_vs_last_week_pct: number
  confidence: number
  weeks_of_history: number
  history: { label: string; jobs: number }[]
  top_zone: string | null
  top_zone_id: number | null
  method: string
}

export interface WorkforceInsight {
  kind: 'shortage' | 'balanced'
  service?: string
  service_slug?: string
  change_pct?: number
  predicted_demand?: number
  required_workers?: number
  available_workers?: number
  shortage?: number
  priority_zone?: string | null
  confidence?: number
  headline: string
  recommendation: string
  supporting?: string
  reallocation?: string
}

export interface ServicePlan {
  service_id: number
  service_name: string
  service_slug: string
  predicted_demand: number
  required_workers: number
  available_workers: number
  gap: number
  status: 'shortage' | 'surplus' | 'balanced'
  utilisation_pct: number
  priority_zone: string | null
  priority_zone_id: number | null
  confidence: number
  recommendation: string
}

export interface SkillGap {
  skill_id: number
  skill_name: string
  skill_slug: string
  service_name: string
  is_emerging: boolean
  requires_certification: boolean
  is_specialist: boolean
  capacity_basis: string
  recent_jobs: number
  projected_jobs: number
  required_workers: number
  available_workers: number
  certified_workers: number
  gap: number
  status: 'shortage' | 'covered'
  recommendation: string
}

export interface ZonePressure {
  zone_id: number
  zone: string
  jobs_last_14_days: number
  workers: number
  jobs_per_worker: number | null
}

export interface ForecastResponse {
  horizon_days: number
  method: string
  method_label: string
  method_note: string
  services: ServiceForecast[]
  insight: WorkforceInsight
  plans: ServicePlan[]
  zone_pressure: ZonePressure[]
}

export interface UtilisationRow {
  worker_id: number
  worker: string
  service: string
  zone: string
  workload_pct: number
  committed_jobs: number
  active_jobs: number
  weekly_capacity: number
  availability_status: AvailabilityStatus
}

export interface WorkforceResponse {
  plans: ServicePlan[]
  insight: WorkforceInsight
  skill_gaps: SkillGap[]
  skill_gaps_top: SkillGap[]
  most_demanded_skills: { skill: string; jobs: number }[]
  zone_pressure: ZonePressure[]
  utilisation: UtilisationRow[]
  fair_distribution_projection: {
    is_simulation: boolean
    label: string
    note: string
    rows: { worker: string; before: number; after: number }[]
  }
  weights: Record<string, number>
}

/* -------------------------------------------------------------------------- */
/* Dashboard, analytics, welfare                                              */
/* -------------------------------------------------------------------------- */

export interface DashboardSummary {
  workers: number
  available_workers: number
  off_duty_workers: number
  active_jobs: number
  unassigned_jobs: number
  completed_today: number
  worker_utilisation_pct: number
  fairness_score: number
  average_rating: number
  rating_count: number
  total_bookings: number
  completed_bookings: number
  cancelled_bookings: number
  completion_rate_pct: number
  customers: number
  revenue: {
    total: number
    worker_earnings: number
    welfare_fund: number
    cooperative_fund: number
    technology_fund: number
  }
  generated_at: string
}

export interface DashboardResponse {
  cooperative: {
    id: number
    name: string
    code: string
    city: string
    state: string
    founded_year: number
  } | null
  summary: DashboardSummary
  insight: WorkforceInsight
  plans: ServicePlan[]
  utilisation: UtilisationRow[]
  least_loaded: UtilisationRow[]
  live_jobs: {
    id: number
    reference: string
    status: BookingStatus
    service: string
    zone: string
    problem: string
    worker: string | null
    scheduled_for: string | null
    urgency: Urgency
  }[]
}

export interface AnalyticsResponse {
  range_days: number
  summary: DashboardSummary
  jobs_by_service: { service: string; jobs: number }[]
  jobs_by_zone: { zone: string; jobs: number }[]
  worker_utilisation: UtilisationRow[]
  earnings: { date: string; total: number; worker: number; welfare: number }[]
  rating_distribution: { stars: number; count: number }[]
  rating_trend: { label: string; average_rating: number | null; ratings: number }[]
  demand_trend: { date: string; jobs: number }[]
  completion_funnel: { status: string; label: string; count: number }[]
}

export interface WelfareWorkerRow {
  worker_id: number
  worker: string
  service: string
  zone: string
  jobs_completed: number
  earnings: number
  welfare_contribution: number
  insurance_active: boolean
  training_credits: number
  training_credits_earned: number
  certifications: { name: string; verified: boolean }[]
  certification_count: number
  rating_avg: number
}

export interface WelfareResponse {
  fund_total: number
  workers_covered: number
  workers_total: number
  coverage_pct: number
  training_credits_outstanding: number
  certified_workers: number
  workers: WelfareWorkerRow[]
}

export interface WelfareLedger {
  worker_id: number
  total_contribution: number
  insurance_active: boolean
  training_credits: number
  entries: {
    id: number
    kind: string
    amount: number
    credits: number
    note: string
    booking_id: number | null
    created_at: string | null
  }[]
}

/* -------------------------------------------------------------------------- */
/* Portals                                                                    */
/* -------------------------------------------------------------------------- */

export interface CustomerSummary {
  customer: {
    id: number
    name: string
    email: string
    address: string
    zone_id: number | null
    lat: number
    lng: number
  }
  counts: {
    total: number
    active: number
    unmatched: number
    awaiting_payment: number
    awaiting_rating: number
    completed: number
  }
  needs_attention: Booking[]
  active_service: Booking | null
  upcoming: Booking[]
  previous: Booking[]
  payments: {
    id: number
    invoice_number: string
    booking_id: number
    amount: number
    welfare_amount: number
    method: string
    status: string
    paid_at: string | null
  }[]
  spend: { total: number; welfare_contributed: number; payments: number }
  ratings: { given: number; average: number | null }
}

export interface WorkerSummary {
  profile: WorkerDetail
  workload: {
    workload_pct: number
    committed_jobs: number
    active_jobs: number
    weekly_capacity: number
    has_headroom: boolean
  }
  earnings: { total: number; last_7_days: number; jobs_paid: number }
  active_jobs: Booking[]
  recent_jobs: Booking[]
  welfare: WelfareLedger
}

export interface Notification {
  id: number
  kind: string
  title: string
  body: string
  booking_id: number | null
  is_read: boolean
  created_at: string | null
}

/* -------------------------------------------------------------------------- */
/* Payments, invoices, demo                                                   */
/* -------------------------------------------------------------------------- */

export interface PaymentResponse {
  simulated: boolean
  notice: string
  payment: Payment
  split: { label: string; amount: number; key: string }[]
  shares: Record<string, number | null>
  booking: BookingDetail
}

export interface Invoice {
  invoice_number: string
  issued_at: string | null
  simulated: boolean
  cooperative: { name: string; code: string; city: string; state: string }
  customer: { name: string; address: string; phone: string }
  worker: { name: string | null; headline: string | null }
  booking: { reference: string; service: string; problem: string; completed_at: string | null }
  lines: { description: string; amount: number }[]
  distribution: { label: string; amount: number }[]
  total: number
  method: string
  status: string
}

export interface RatingResponse {
  recorded: boolean
  effects: string[]
  rating: { id: number; stars: number; comment: string }
  worker: { id: number; name: string; rating_avg: number; rating_count: number } | null
  booking: BookingDetail
}

export interface DemoStep {
  key: string
  title: string
  detail: string
  route: string
  actor: string
}

export interface DemoState {
  seeded: boolean
  bookings: number
  workers: number
  scenario_request: string
  steps: DemoStep[]
  active_scenario_booking: {
    id: number
    reference: string
    status: BookingStatus
    problem: string
  } | null
  demo_password: string
  llm_configured: boolean
}

export interface DemoResetResponse {
  reset: boolean
  message: string
  counts: Record<string, number>
  tokens: Record<string, { user_id: number; email: string; name: string; access_token: string }>
  scenario_request: string
}

export interface HealthResponse {
  status: string
  app: string
  version: string
  environment: string
  database: { connected: boolean; engine: string; error: string | null }
  ai: Record<string, string | boolean>
  warnings: string[]
}

/**
 * One job, end to end.
 *
 * The same screen serves all three roles: customers track, pay and rate here;
 * workers accept, start and complete here; admins can see everything and step
 * in. What each role is offered comes from the booking's own status.
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, CreditCard, PlayCircle, Receipt, XCircle } from 'lucide-react'

import { useAuth } from '../auth/AuthContext'
import { InvoiceModal } from '../components/domain/InvoiceView'
import { PaymentSplitPanel } from '../components/domain/PaymentSplit'
import { RatingConfirmation, RatingForm } from '../components/domain/RatingForm'
import { ScoreBreakdown } from '../components/domain/ScoreBreakdown'
import { ServiceMap } from '../components/domain/ServiceMap'
import { StatusBadge, StatusTimeline, UrgencyBadge } from '../components/domain/status'
import {
  Avatar,
  Badge,
  Button,
  Card,
  ErrorState,
  InlineNotice,
  LoadingBlock,
  SectionHeader,
  StarRating,
  cx,
} from '../components/ui'
import { useDemo } from '../demo/DemoContext'
import { useI18n } from '../i18n'
import { errorMessage } from '../lib/api'
import * as endpoints from '../lib/endpoints'
import { currency, distanceLabel, formatDateTime } from '../lib/format'
import type { BookingDetail, BookingStatus, Invoice, RatingResponse } from '../lib/types'

export default function BookingDetailPage() {
  const { bookingId } = useParams<{ bookingId: string }>()
  const id = Number(bookingId)
  const { user } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  const demo = useDemo()

  const [booking, setBooking] = useState<BookingDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [ratingResult, setRatingResult] = useState<RatingResponse | null>(null)
  const [paid, setPaid] = useState(false)

  const load = useCallback(async () => {
    if (!Number.isFinite(id)) {
      setError('That booking reference is not valid.')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      setBooking(await endpoints.getBooking(id))
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  const isCustomer = user?.role === 'CUSTOMER' || (user?.role === 'ADMIN' && booking?.customer_id === user.id)
  const isAssignedWorker =
    user?.role === 'WORKER' && booking?.worker?.id === user.worker_id
  const isAdmin = user?.role === 'ADMIN'

  const transition = async (status: BookingStatus, label: string) => {
    setBusy(label)
    setActionError(null)
    try {
      setBooking(await endpoints.setBookingStatus(id, status))
      void demo.refresh()
    } catch (caught) {
      setActionError(errorMessage(caught))
    } finally {
      setBusy(null)
    }
  }

  const pay = async () => {
    setBusy('pay')
    setActionError(null)
    try {
      const result = await endpoints.payForBooking(id)
      setBooking(result.booking)
      setPaid(true)
      void demo.refresh()
    } catch (caught) {
      setActionError(errorMessage(caught))
    } finally {
      setBusy(null)
    }
  }

  const rate = async (stars: number, comment: string) => {
    setBusy('rate')
    setActionError(null)
    try {
      const result = await endpoints.submitRating(id, stars, comment)
      setRatingResult(result)
      setBooking(result.booking)
      void demo.refresh()
    } catch (caught) {
      setActionError(errorMessage(caught))
    } finally {
      setBusy(null)
    }
  }

  const openInvoice = async () => {
    setBusy('invoice')
    setActionError(null)
    try {
      setInvoice(await endpoints.getInvoice(id))
    } catch (caught) {
      setActionError(errorMessage(caught))
    } finally {
      setBusy(null)
    }
  }

  if (loading) {
    return (
      <Card>
        <LoadingBlock rows={6} />
      </Card>
    )
  }
  if (error || !booking) {
    return <ErrorState message={error ?? 'Booking not found.'} onRetry={load} />
  }

  const price = booking.final_price ?? booking.estimated_price

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(-1)}
          icon={<ArrowLeft className="size-4" aria-hidden />}
        >
          {t('common.back')}
        </Button>
        <span className="text-ink-400 font-mono text-xs">{booking.reference}</span>
      </div>

      {/* Header */}
      <Card className={cx(booking.is_emergency && 'border-danger-200')}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="outline">{booking.service_name}</Badge>
              <UrgencyBadge urgency={booking.urgency} />
              <StatusBadge status={booking.status} />
            </div>
            <h1 className="mt-2 text-xl font-semibold">{booking.problem_summary}</h1>
            {booking.raw_request ? (
              <p className="text-ink-500 mt-1 text-sm italic">“{booking.raw_request}”</p>
            ) : null}
          </div>
          <div className="text-right">
            <p className="text-ink-500 text-xs">
              {booking.final_price === null ? t('ai.estimatedPrice') : t('payment.total')}
            </p>
            <p className="text-ink-900 text-2xl font-semibold tabular-nums">{currency(price)}</p>
          </div>
        </div>

        <div className="border-ink-100 mt-5 border-t pt-5">
          <StatusTimeline steps={booking.timeline} className="hidden sm:flex" />
          <StatusTimeline steps={booking.timeline} orientation="vertical" className="sm:hidden" />
        </div>
      </Card>

      {actionError ? <InlineNotice tone="danger">{actionError}</InlineNotice> : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {/* Worker actions */}
          {(isAssignedWorker || (isAdmin && booking.worker)) && (
            <WorkerActions
              booking={booking}
              busy={busy}
              onTransition={transition}
            />
          )}

          {/* Customer payment */}
          {isCustomer && booking.status === 'COMPLETED' ? (
            <Card className="border-accent-200 bg-accent-50/40 space-y-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="text-accent-600 mt-0.5 size-6 shrink-0" aria-hidden />
                <div>
                  <h2 className="text-ink-900 text-lg font-semibold">
                    {t('payment.serviceCompleted')}
                  </h2>
                  <p className="text-ink-600 mt-0.5 text-sm">
                    {booking.service_name} — {booking.problem_summary}
                  </p>
                </div>
                <span className="text-ink-900 ml-auto text-2xl font-semibold tabular-nums">
                  {currency(price)}
                </span>
              </div>
              <Button
                size="lg"
                block
                onClick={pay}
                loading={busy === 'pay'}
                icon={<CreditCard className="size-4" aria-hidden />}
              >
                {busy === 'pay' ? t('payment.paying') : t('payment.payNow')}
              </Button>
              <p className="text-ink-500 text-xs">{t('payment.distributionNote')}</p>
            </Card>
          ) : null}

          {/* Payment success */}
          {booking.payment && (paid || booking.status !== 'COMPLETED') ? (
            <Card className="border-accent-200 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="text-accent-600 size-5" aria-hidden />
                  <h2 className="text-ink-900 text-base font-semibold">
                    {t('payment.successful')}
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-ink-500 font-mono text-sm">
                    {booking.payment.invoice_number}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={openInvoice}
                    loading={busy === 'invoice'}
                    icon={<Receipt className="size-4" aria-hidden />}
                  >
                    {t('payment.viewInvoice')}
                  </Button>
                </div>
              </div>
            </Card>
          ) : null}

          {/* Rating */}
          {isCustomer && booking.status === 'PAID' && !ratingResult ? (
            <RatingForm onSubmit={rate} submitting={busy === 'rate'} error={actionError} />
          ) : null}
          {ratingResult ? <RatingConfirmation result={ratingResult} /> : null}
          {booking.rating && !ratingResult ? (
            <Card className="space-y-2">
              <SectionHeader title={t('customer.ratings')} />
              <StarRating value={booking.rating.stars} size="md" />
              {booking.rating.comment ? (
                <p className="text-ink-600 text-sm">“{booking.rating.comment}”</p>
              ) : null}
            </Card>
          ) : null}

          {/* AI interpretation */}
          {booking.ai_interpretation ? (
            <Card className="space-y-3">
              <SectionHeader
                title={t('ai.understood')}
                description={
                  booking.ai_interpretation.method === 'llm'
                    ? 'Interpreted by the configured language model, validated against the service catalogue.'
                    : 'Interpreted by the built-in rule engine.'
                }
              />
              <dl className="divide-ink-100 grid divide-y">
                {[
                  [t('ai.service'), booking.ai_interpretation.service_name],
                  [t('ai.problem'), booking.ai_interpretation.problem],
                  [t('ai.skills'), booking.ai_interpretation.skill_names.join(', ')],
                  [t('ai.workers'), String(booking.ai_interpretation.workers_required)],
                  [t('ai.urgency'), booking.ai_interpretation.urgency],
                  [t('ai.preferredTime'), booking.ai_interpretation.preferred_time_label],
                  [t('ai.location'), booking.zone_name],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-4 py-2 text-sm">
                    <dt className="text-ink-500">{label}</dt>
                    <dd className="text-ink-900 text-right font-medium">{value || '-'}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          ) : null}

          {/* Allocation reasoning */}
          {booking.match_breakdown ? (
            <Card>
              <SectionHeader
                title={t('matching.whyThisWorker')}
                description="The score that justified this allocation, exactly as it was calculated."
                className="mb-4"
              />
              <ScoreBreakdown candidate={booking.match_breakdown} />
            </Card>
          ) : null}
        </div>

        {/* Sidebar */}
        <aside className="space-y-4">
          {booking.worker ? (
            <Card className="space-y-3">
              <SectionHeader title={t('booking.workerAssigned')} />
              <div className="flex items-center gap-3">
                <Avatar name={booking.worker.name} size="lg" />
                <div className="min-w-0">
                  <p className="text-ink-900 truncate font-semibold">{booking.worker.name}</p>
                  <p className="text-ink-500 text-sm">{booking.worker.headline}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <StarRating
                      value={booking.worker.rating_avg}
                      count={booking.worker.rating_count}
                    />
                    {booking.worker.verification_status === 'VERIFIED' ? (
                      <Badge tone="brand">{t('matching.verified')}</Badge>
                    ) : null}
                  </div>
                </div>
              </div>
              <dl className="text-ink-600 border-ink-100 grid grid-cols-2 gap-2 border-t pt-3 text-sm">
                <div>
                  <dt className="text-ink-400 text-xs">{t('matching.distance')}</dt>
                  <dd className="font-medium">{distanceLabel(booking.distance_km)}</dd>
                </div>
                <div>
                  <dt className="text-ink-400 text-xs">{t('worker.completedJobs')}</dt>
                  <dd className="font-medium tabular-nums">{booking.worker.jobs_completed}</dd>
                </div>
              </dl>
            </Card>
          ) : booking.status === 'REQUESTED' ? (
            <Card className="space-y-3">
              <p className="text-ink-600 text-sm">
                No worker has been allocated to this job yet.
              </p>
              <Button block onClick={() => navigate(`/matching?booking=${booking.id}`)}>
                {t('ai.findWorker')}
              </Button>
            </Card>
          ) : null}

          {booking.worker && booking.status !== 'RATED' ? <ServiceMap booking={booking} /> : null}

          {booking.payment ? (
            <PaymentSplitPanel
              split={{
                amount: booking.payment.amount,
                worker_amount: booking.payment.worker_amount,
                cooperative_amount: booking.payment.cooperative_amount,
                welfare_amount: booking.payment.welfare_amount,
                technology_amount: booking.payment.technology_amount,
              }}
            />
          ) : booking.payment_split_preview ? (
            <PaymentSplitPanel
              split={booking.payment_split_preview}
              title="How this payment will be shared"
            />
          ) : null}

          <Card className="space-y-2">
            <SectionHeader title="Job details" />
            <dl className="text-ink-600 divide-ink-100 divide-y text-sm">
              {[
                [t('ai.preferredTime'), booking.preferred_time_label || formatDateTime(booking.scheduled_for)],
                [t('ai.location'), booking.zone_name],
                ['Address', booking.address],
                [t('ai.skills'), booking.required_skills.join(', ')],
                [t('ai.workers'), String(booking.workers_required)],
                ['Requested', formatDateTime(booking.created_at)],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between gap-4 py-2">
                  <dt className="text-ink-400 shrink-0 text-xs">{label}</dt>
                  <dd className="text-right">{value || '-'}</dd>
                </div>
              ))}
            </dl>
          </Card>

          {isCustomer &&
          ['REQUESTED', 'ASSIGNED', 'ACCEPTED'].includes(booking.status) ? (
            <Button
              variant="secondary"
              block
              onClick={() => transition('CANCELLED', 'cancel')}
              loading={busy === 'cancel'}
              icon={<XCircle className="size-4" aria-hidden />}
            >
              {t('booking.cancelBooking')}
            </Button>
          ) : null}
        </aside>
      </div>

      {invoice ? <InvoiceModal invoice={invoice} onClose={() => setInvoice(null)} /> : null}
    </div>
  )
}

function WorkerActions({
  booking,
  busy,
  onTransition,
}: {
  booking: BookingDetail
  busy: string | null
  onTransition: (status: BookingStatus, label: string) => void
}) {
  const { t } = useI18n()

  if (booking.status === 'ASSIGNED') {
    return (
      <Card className="border-brand-200 bg-brand-50/40 space-y-4">
        <SectionHeader
          eyebrow={t('worker.newRequest')}
          title={booking.problem_summary}
          description={`${booking.service_name} · ${booking.zone_name}`}
        />
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-ink-500 text-xs">{t('matching.distance')}</dt>
            <dd className="text-ink-900 font-semibold">{distanceLabel(booking.distance_km)}</dd>
          </div>
          <div>
            <dt className="text-ink-500 text-xs">{t('worker.scheduled')}</dt>
            <dd className="text-ink-900 font-semibold">
              {booking.preferred_time_label || formatDateTime(booking.scheduled_for)}
            </dd>
          </div>
          <div>
            <dt className="text-ink-500 text-xs">{t('worker.estimatedEarnings')}</dt>
            <dd className="text-accent-700 font-semibold tabular-nums">
              {currency(booking.payment_split_preview?.worker_amount ?? 0)}
            </dd>
          </div>
        </dl>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            size="lg"
            className="sm:flex-1"
            onClick={() => onTransition('ACCEPTED', 'accept')}
            loading={busy === 'accept'}
          >
            {t('worker.accept')}
          </Button>
          <Button
            variant="secondary"
            size="lg"
            onClick={() => onTransition('DECLINED', 'decline')}
            loading={busy === 'decline'}
          >
            {t('worker.decline')}
          </Button>
        </div>
      </Card>
    )
  }

  if (booking.status === 'ACCEPTED') {
    return (
      <Card className="space-y-3">
        <SectionHeader
          title="Ready to start"
          description="Mark the job as started when you reach the address."
        />
        <Button
          size="lg"
          block
          onClick={() => onTransition('IN_PROGRESS', 'start')}
          loading={busy === 'start'}
          icon={<PlayCircle className="size-4" aria-hidden />}
        >
          {t('worker.startJob')}
        </Button>
      </Card>
    )
  }

  if (booking.status === 'IN_PROGRESS') {
    return (
      <Card className="border-brand-200 space-y-3">
        <SectionHeader
          title="Work in progress"
          description="Complete the job when the work is finished; the customer is then asked to pay."
        />
        <Button
          size="lg"
          block
          variant="success"
          onClick={() => onTransition('COMPLETED', 'complete')}
          loading={busy === 'complete'}
          icon={<CheckCircle2 className="size-4" aria-hidden />}
        >
          {t('worker.completeJob')}
        </Button>
      </Card>
    )
  }

  return null
}

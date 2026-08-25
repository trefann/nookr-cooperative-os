/**
 * Fair allocation.
 *
 * Pick a job awaiting allocation, see every eligible member ranked by the
 * server-side score, and read exactly why the top choice won before assigning.
 */

import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Scale, ShieldOff, Siren, Users } from 'lucide-react'

import { CandidateCard } from '../components/domain/CandidateCard'
import {
  AllocationExplanation,
  ScoreBreakdown,
  WeightLegend,
} from '../components/domain/ScoreBreakdown'
import { StatusBadge, UrgencyBadge } from '../components/domain/status'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  InlineNotice,
  LoadingBlock,
  SectionHeader,
  cx,
} from '../components/ui'
import { useDemo } from '../demo/DemoContext'
import { useI18n } from '../i18n'
import { errorMessage } from '../lib/api'
import * as endpoints from '../lib/endpoints'
import { currency, formatDateTime } from '../lib/format'
import type { BookingDetail, MatchResponse } from '../lib/types'
import { useAsync } from '../lib/useAsync'

export default function MatchingPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const demo = useDemo()
  const [params, setParams] = useSearchParams()
  const bookingId = params.get('booking') ? Number(params.get('booking')) : null

  const openJobs = useAsync(
    () => endpoints.getBookings({ status: 'REQUESTED', limit: 50 }),
    [],
  )

  const [booking, setBooking] = useState<BookingDetail | null>(null)
  const [matches, setMatches] = useState<MatchResponse | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [assigning, setAssigning] = useState(false)

  useEffect(() => {
    if (bookingId === null) {
      setBooking(null)
      setMatches(null)
      return
    }
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const detail = await endpoints.getBooking(bookingId)
        if (cancelled) return
        setBooking(detail)
        const result = await endpoints.findMatches({ booking_id: bookingId, limit: 10 })
        if (cancelled) return
        setMatches(result)
        setSelectedId(result.recommended?.worker_id ?? result.candidates[0]?.worker_id ?? null)
      } catch (caught) {
        if (!cancelled) setError(errorMessage(caught))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [bookingId])

  const selected = useMemo(
    () => matches?.candidates.find((candidate) => candidate.worker_id === selectedId) ?? null,
    [matches, selectedId],
  )

  const assign = async () => {
    if (!booking || !selected) return
    setAssigning(true)
    setError(null)
    try {
      await endpoints.assignWorker(booking.id, selected.worker_id)
      void demo.refresh()
      navigate(`/bookings/${booking.id}`)
    } catch (caught) {
      setError(errorMessage(caught))
      setAssigning(false)
    }
  }

  /* ---------------------------------------------------------------- picker */

  if (bookingId === null) {
    return (
      <div className="space-y-6">
        <SectionHeader
          eyebrow={t('nav.matching')}
          title={t('matching.title')}
          description={t('matching.subtitle')}
        />

        {openJobs.loading ? (
          <Card>
            <LoadingBlock rows={4} />
          </Card>
        ) : openJobs.error ? (
          <ErrorState message={openJobs.error} onRetry={openJobs.reload} />
        ) : openJobs.data?.length ? (
          <Card padded={false}>
            <ul className="divide-ink-100 divide-y">
              {openJobs.data.map((job) => (
                <li key={job.id}>
                  <button
                    type="button"
                    onClick={() => setParams({ booking: String(job.id) })}
                    className="hover:bg-ink-50 flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3.5 text-left transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-ink-900 text-sm font-medium">{job.problem_summary}</p>
                      <p className="text-ink-500 mt-0.5 text-xs">
                        {job.service_name} · {job.zone_name} ·{' '}
                        {job.preferred_time_label || formatDateTime(job.scheduled_for)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <UrgencyBadge urgency={job.urgency} />
                      <span className="text-ink-400 font-mono text-xs">{job.reference}</span>
                      <Badge tone="warn">{t('booking.requested')}</Badge>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        ) : (
          <EmptyState
            title="No jobs are waiting for allocation"
            description="Every request currently has a worker assigned."
            icon={<Users className="size-8" aria-hidden />}
          />
        )}
      </div>
    )
  }

  /* -------------------------------------------------------------- matching */

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <SectionHeader
          eyebrow={t('nav.matching')}
          title={t('matching.title')}
          description={t('matching.subtitle')}
        />
        <Button variant="ghost" size="sm" onClick={() => setParams({})}>
          {t('common.back')}
        </Button>
      </div>

      {loading ? (
        <Card>
          <LoadingBlock rows={5} />
        </Card>
      ) : error && !matches ? (
        <ErrorState message={error} onRetry={() => setParams({ booking: String(bookingId) })} />
      ) : booking && matches ? (
        <>
          {/* The job */}
          <Card className={cx(booking.is_emergency && 'border-danger-200 bg-danger-50/40')}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  {booking.is_emergency ? (
                    <Badge tone="danger" icon={<Siren className="size-3" aria-hidden />}>
                      Emergency request
                    </Badge>
                  ) : null}
                  <Badge tone="outline">{booking.service_name}</Badge>
                  <UrgencyBadge urgency={booking.urgency} />
                  <StatusBadge status={booking.status} />
                </div>
                <h2 className="text-ink-900 mt-2 text-lg font-semibold">
                  {booking.problem_summary}
                </h2>
                {booking.raw_request ? (
                  <p className="text-ink-500 mt-1 max-w-2xl text-sm italic">
                    “{booking.raw_request}”
                  </p>
                ) : null}
                <dl className="text-ink-600 mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
                  <div>
                    <dt className="text-ink-400 text-xs">{t('ai.preferredTime')}</dt>
                    <dd>{booking.preferred_time_label || formatDateTime(booking.scheduled_for)}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-400 text-xs">{t('ai.location')}</dt>
                    <dd>{booking.zone_name}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-400 text-xs">{t('ai.skills')}</dt>
                    <dd>{booking.required_skills.join(', ') || '-'}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-400 text-xs">{t('ai.estimatedPrice')}</dt>
                    <dd className="font-medium tabular-nums">
                      {currency(booking.estimated_price)}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          </Card>

          <WeightLegend weights={matches.weights} />

          {error ? <InlineNotice tone="danger">{error}</InlineNotice> : null}

          {matches.candidates.length === 0 ? (
            <EmptyState
              title={t('matching.noCandidates')}
              description={matches.message}
              icon={<ShieldOff className="size-8" aria-hidden />}
            />
          ) : (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
              {/* Candidates */}
              <section className="space-y-3">
                <SectionHeader
                  title={t('matching.eligible')}
                  description={`${matches.considered} ${t('matching.considered')} · ${matches.candidates.length} eligible`}
                />
                <div className="space-y-3">
                  {matches.candidates.map((candidate) => (
                    <CandidateCard
                      key={candidate.worker_id}
                      candidate={candidate}
                      selected={candidate.worker_id === selectedId}
                      onSelect={() => setSelectedId(candidate.worker_id)}
                    />
                  ))}
                </div>

                {matches.excluded.length ? (
                  <details className="border-ink-200 rounded-[var(--radius-card)] border bg-white">
                    <summary className="text-ink-600 hover:text-ink-900 cursor-pointer px-4 py-3 text-sm font-medium">
                      {t('matching.excluded')} ({matches.excluded.length})
                    </summary>
                    <ul className="divide-ink-100 divide-y border-ink-100 border-t">
                      {matches.excluded.map((entry, index) => (
                        <li
                          key={`${entry.worker}-${index}`}
                          className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
                        >
                          <span className="text-ink-700">{entry.worker}</span>
                          <span className="text-ink-500 text-xs">{entry.reason}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : null}
              </section>

              {/* Why this worker */}
              <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
                {selected ? (
                  <>
                    <Card>
                      <div className="mb-4 flex items-center gap-2">
                        <Scale className="text-brand-700 size-4" aria-hidden />
                        <h3 className="text-ink-900 text-sm font-semibold">
                          {t('matching.whyThisWorker')}
                        </h3>
                      </div>
                      <p className="text-ink-900 mb-4 text-base font-semibold">
                        {selected.worker_name}
                      </p>
                      <ScoreBreakdown candidate={selected} />
                    </Card>

                    <AllocationExplanation candidate={selected} />

                    <Button
                      size="lg"
                      block
                      onClick={assign}
                      loading={assigning}
                      variant={booking.is_emergency ? 'danger' : 'primary'}
                    >
                      {assigning
                        ? t('matching.assigning')
                        : booking.is_emergency
                          ? t('matching.dispatch')
                          : t('matching.assign')}
                    </Button>
                  </>
                ) : (
                  <Card>
                    <p className="text-ink-500 text-sm">
                      Select a worker to see the score breakdown.
                    </p>
                  </Card>
                )}
              </aside>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}

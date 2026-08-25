/**
 * Worker portal.
 *
 * Profile, verification, skills, availability, live jobs, earnings and
 * welfare — the member's own view of what the cooperative holds about them.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BadgeCheck,
  Briefcase,
  GraduationCap,
  HeartHandshake,
  ShieldCheck,
  Star,
  Wallet,
} from 'lucide-react'

import { BookingCard } from '../components/domain/BookingCard'
import { AvailabilityDot } from '../components/domain/status'
import {
  Avatar,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  InlineNotice,
  LoadingBlock,
  ProgressBar,
  SectionHeader,
  Stat,
  StarRating,
  cx,
} from '../components/ui'
import { useI18n } from '../i18n'
import { errorMessage } from '../lib/api'
import * as endpoints from '../lib/endpoints'
import { currency, formatDate } from '../lib/format'
import type { AvailabilityStatus } from '../lib/types'
import { useAsync } from '../lib/useAsync'

const AVAILABILITY_OPTIONS: { value: AvailabilityStatus; labelKey: 'worker.available' | 'worker.busy' | 'worker.offDuty' }[] = [
  { value: 'AVAILABLE', labelKey: 'worker.available' },
  { value: 'BUSY', labelKey: 'worker.busy' },
  { value: 'OFF_DUTY', labelKey: 'worker.offDuty' },
]

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function WorkerPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const summary = useAsync(() => endpoints.getMyWorkerSummary(), [])
  const [saving, setSaving] = useState(false)
  const [availabilityError, setAvailabilityError] = useState<string | null>(null)

  const data = summary.data

  const changeAvailability = async (status: AvailabilityStatus) => {
    setSaving(true)
    setAvailabilityError(null)
    try {
      await endpoints.setAvailability(status)
      await summary.reload()
    } catch (caught) {
      setAvailabilityError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  if (summary.loading && !data) {
    return (
      <Card>
        <LoadingBlock rows={6} />
      </Card>
    )
  }
  if (summary.error || !data) {
    return <ErrorState message={summary.error ?? 'Worker profile unavailable.'} onRetry={summary.reload} />
  }

  const profile = data.profile
  const offers = data.active_jobs.filter((job) => job.status === 'ASSIGNED')
  const inFlight = data.active_jobs.filter((job) => job.status !== 'ASSIGNED')

  return (
    <div className="space-y-8">
      {/* Profile header */}
      <Card>
        <div className="flex flex-wrap items-start gap-4">
          <Avatar name={profile.name} size="lg" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold">{profile.name}</h1>
              {profile.verification_status === 'VERIFIED' ? (
                <Badge tone="brand" icon={<BadgeCheck className="size-3" aria-hidden />}>
                  {t('matching.verified')}
                </Badge>
              ) : (
                <Badge tone="warn">{profile.verification_status}</Badge>
              )}
            </div>
            <p className="text-ink-500 mt-0.5 text-sm">
              {profile.headline} · {profile.zone_name} · {profile.experience_years} years
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-4">
              <StarRating value={profile.rating_avg} count={profile.rating_count} size="md" />
              <AvailabilityDot status={profile.availability_status} />
            </div>
            {profile.bio ? <p className="text-ink-600 mt-2 max-w-2xl text-sm">{profile.bio}</p> : null}
          </div>

          <div className="w-full sm:w-auto">
            <p className="label mb-1.5">{t('worker.setAvailability')}</p>
            <div className="border-ink-300 inline-flex rounded-lg border bg-white p-0.5">
              {AVAILABILITY_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  disabled={saving}
                  onClick={() => changeAvailability(option.value)}
                  className={cx(
                    'rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-60',
                    profile.availability_status === option.value
                      ? 'bg-brand-700 text-white'
                      : 'text-ink-600 hover:bg-ink-100',
                  )}
                >
                  {t(option.labelKey)}
                </button>
              ))}
            </div>
            {availabilityError ? (
              <p className="text-danger-600 mt-1.5 text-xs">{availabilityError}</p>
            ) : null}
          </div>
        </div>
      </Card>

      {/* KPIs */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label={t('worker.earnings')}
          value={currency(data.earnings.total)}
          hint={`${currency(data.earnings.last_7_days)} in the last 7 days`}
          icon={<Wallet className="size-4" aria-hidden />}
          tone="success"
        />
        <Stat
          label={t('worker.completedJobs')}
          value={profile.jobs_completed}
          hint={`${data.earnings.jobs_paid} paid`}
          icon={<Briefcase className="size-4" aria-hidden />}
        />
        <Stat
          label={t('worker.rating')}
          value={profile.rating_avg ? `${profile.rating_avg.toFixed(1)} ★` : '-'}
          hint={`${profile.rating_count} ratings`}
          icon={<Star className="size-4" aria-hidden />}
        />
        <Stat
          label={t('worker.thisWeek')}
          value={`${data.workload.workload_pct}%`}
          hint={`${data.workload.committed_jobs} of ${data.workload.weekly_capacity} ${t('common.jobs')}`}
          icon={<GraduationCap className="size-4" aria-hidden />}
          tone={data.workload.workload_pct >= 85 ? 'warn' : 'brand'}
        />
      </section>

      {/* New offers */}
      {offers.length ? (
        <section className="space-y-3">
          <SectionHeader
            title={t('worker.newRequest')}
            description="Jobs the cooperative has allocated to you. Accept or decline."
          />
          <div className="grid gap-3 lg:grid-cols-2">
            {offers.map((job) => (
              <BookingCard
                key={job.id}
                booking={job}
                highlight
                showCustomer
                onOpen={() => navigate(`/bookings/${job.id}`)}
                actions={
                  <Button size="sm" onClick={(event) => {
                    event.stopPropagation()
                    navigate(`/bookings/${job.id}`)
                  }}>
                    {t('common.viewDetails')}
                  </Button>
                }
              />
            ))}
          </div>
        </section>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {/* Current jobs */}
          <section className="space-y-3">
            <SectionHeader
              title={t('worker.currentJobs')}
              action={
                <Button variant="ghost" size="sm" onClick={() => navigate('/bookings')}>
                  {t('common.viewAll')}
                </Button>
              }
            />
            {inFlight.length ? (
              <div className="grid gap-3">
                {inFlight.map((job) => (
                  <BookingCard
                    key={job.id}
                    booking={job}
                    showCustomer
                    onOpen={() => navigate(`/bookings/${job.id}`)}
                    actions={
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={(event) => {
                          event.stopPropagation()
                          navigate(`/bookings/${job.id}`)
                        }}
                      >
                        {t('common.viewDetails')}
                      </Button>
                    }
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title={t('worker.noActiveJobs')}
                description="New allocations will appear here."
                icon={<Briefcase className="size-8" aria-hidden />}
              />
            )}
          </section>

          {/* Recent work */}
          <section className="space-y-3">
            <SectionHeader title={t('worker.completedJobs')} />
            {data.recent_jobs.length ? (
              <Card padded={false}>
                <ul className="divide-ink-100 divide-y">
                  {data.recent_jobs.map((job) => (
                    <li
                      key={job.id}
                      className="hover:bg-ink-50 flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                    >
                      <button
                        type="button"
                        onClick={() => navigate(`/bookings/${job.id}`)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <p className="text-ink-900 truncate text-sm font-medium">
                          {job.problem_summary}
                        </p>
                        <p className="text-ink-500 text-xs">
                          {job.service_name} · {job.zone_name} · {formatDate(job.completed_at)}
                        </p>
                      </button>
                      <div className="flex items-center gap-3">
                        {job.rating ? <StarRating value={job.rating.stars} /> : null}
                        <span className="text-ink-900 text-sm font-semibold tabular-nums">
                          {currency(job.payment?.worker_amount ?? 0)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </Card>
            ) : (
              <EmptyState title={t('common.noResults')} />
            )}
          </section>
        </div>

        {/* Sidebar */}
        <aside className="space-y-4">
          <Card className="space-y-3">
            <SectionHeader title={t('worker.skills')} />
            <ul className="space-y-2.5">
              {profile.skills.map((skill) => (
                <li key={skill.skill_id}>
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="text-ink-800 text-sm">
                      {skill.name}
                      {skill.is_emerging ? (
                        <Badge tone="success" className="ml-1.5">
                          {t('workforce.emerging')}
                        </Badge>
                      ) : null}
                    </span>
                    <span className="text-ink-400 text-xs">{skill.proficiency}/5</span>
                  </div>
                  <ProgressBar value={(skill.proficiency / 5) * 100} height="sm" />
                </li>
              ))}
            </ul>
          </Card>

          <Card className="space-y-3">
            <SectionHeader title={t('worker.certifications')} />
            {profile.certifications.length ? (
              <ul className="space-y-2.5">
                {profile.certifications.map((cert) => (
                  <li key={cert.id} className="flex items-start gap-2.5">
                    <ShieldCheck
                      className={cx(
                        'mt-0.5 size-4 shrink-0',
                        cert.verified ? 'text-accent-600' : 'text-ink-300',
                      )}
                      aria-hidden
                    />
                    <div className="min-w-0">
                      <p className="text-ink-900 text-sm font-medium">{cert.name}</p>
                      <p className="text-ink-500 text-xs">{cert.issuing_body}</p>
                      {cert.expires_on ? (
                        <p className="text-ink-400 text-xs">
                          Valid until {formatDate(cert.expires_on)}
                        </p>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-ink-500 text-sm">{t('common.noResults')}</p>
            )}
          </Card>

          <Card className="space-y-3">
            <SectionHeader title={t('worker.availability')} />
            <ul className="grid grid-cols-7 gap-1">
              {DAY_LABELS.map((day, index) => {
                const slot = profile.availability.find((entry) => entry.day_of_week === index)
                const available = slot?.is_available ?? false
                return (
                  <li key={day} className="text-center">
                    <div
                      className={cx(
                        'rounded-md py-1.5 text-[11px] font-medium',
                        available ? 'bg-accent-100 text-accent-800' : 'bg-ink-100 text-ink-400',
                      )}
                    >
                      {day}
                    </div>
                  </li>
                )
              })}
            </ul>
            <p className="text-ink-500 text-xs">
              Working hours {profile.availability[0]?.start_time ?? '08:00'} –{' '}
              {profile.availability[0]?.end_time ?? '19:00'}
            </p>
          </Card>

          <Card className="space-y-3">
            <SectionHeader title={t('worker.welfare')} />
            <dl className="divide-ink-100 divide-y text-sm">
              <div className="flex items-center justify-between py-2">
                <dt className="text-ink-600 flex items-center gap-1.5">
                  <HeartHandshake className="text-accent-600 size-4" aria-hidden />
                  {t('welfare.contribution')}
                </dt>
                <dd className="text-ink-900 font-semibold tabular-nums">
                  {currency(data.welfare.total_contribution)}
                </dd>
              </div>
              <div className="flex items-center justify-between py-2">
                <dt className="text-ink-600">{t('welfare.insurance')}</dt>
                <dd>
                  {data.welfare.insurance_active ? (
                    <Badge tone="success">{t('welfare.active')}</Badge>
                  ) : (
                    <Badge tone="warn">{t('welfare.inactive')}</Badge>
                  )}
                </dd>
              </div>
              <div className="flex items-center justify-between py-2">
                <dt className="text-ink-600">{t('welfare.trainingCredits')}</dt>
                <dd className="text-ink-900 font-semibold tabular-nums">
                  {data.welfare.training_credits}
                </dd>
              </div>
            </dl>
            {data.welfare.entries.length ? (
              <details>
                <summary className="text-brand-700 cursor-pointer text-xs font-medium">
                  {t('welfare.ledger')}
                </summary>
                <ul className="divide-ink-100 mt-2 max-h-48 divide-y overflow-y-auto">
                  {data.welfare.entries.slice(0, 12).map((entry) => (
                    <li key={entry.id} className="flex justify-between gap-2 py-1.5 text-xs">
                      <span className="text-ink-600 truncate">{entry.note}</span>
                      <span className="text-ink-900 shrink-0 font-medium tabular-nums">
                        {entry.amount > 0 ? currency(entry.amount) : `+${entry.credits} credit`}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}
            {!data.workload.has_headroom ? (
              <InlineNotice tone="warn">
                You are at your weekly capacity. New allocations will go to members with more room.
              </InlineNotice>
            ) : null}
          </Card>
        </aside>
      </div>
    </div>
  )
}

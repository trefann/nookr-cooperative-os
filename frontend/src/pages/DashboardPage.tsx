/**
 * Cooperative Intelligence Dashboard.
 *
 * The primary judging screen: the state of the workforce right now, what the
 * AI recommends doing about it, and where the work is actually sitting.
 */

import { useNavigate } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Gauge,
  Lightbulb,
  Scale,
  Star,
  UserCheck,
  Users,
} from 'lucide-react'

import { BarSeriesChart } from '../components/charts'
import { StatusBadge, UrgencyBadge } from '../components/domain/status'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingBlock,
  ProgressBar,
  SectionHeader,
  Stat,
  TableWrap,
  Td,
  Th,
} from '../components/ui'
import { useI18n } from '../i18n'
import * as endpoints from '../lib/endpoints'
import { compactCurrency, formatDateTime } from '../lib/format'
import { useAsync } from '../lib/useAsync'

export default function DashboardPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const dashboard = useAsync(() => endpoints.getDashboard(), [])

  if (dashboard.loading && !dashboard.data) {
    return (
      <div className="space-y-4">
        <LoadingBlock rows={2} />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <Card key={index}>
              <LoadingBlock rows={2} />
            </Card>
          ))}
        </div>
      </div>
    )
  }
  if (dashboard.error || !dashboard.data) {
    return (
      <ErrorState
        message={dashboard.error ?? 'Dashboard unavailable.'}
        onRetry={dashboard.reload}
      />
    )
  }

  const { summary, insight, plans, utilisation, least_loaded, live_jobs, cooperative } =
    dashboard.data

  const planChart = plans.map((plan) => ({
    service: plan.service_name,
    required: plan.required_workers,
    available: plan.available_workers,
  }))

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="label">{cooperative?.name ?? 'Cooperative'}</p>
          <h1 className="mt-1 text-2xl font-semibold">{t('admin.title')}</h1>
          <p className="text-ink-500 mt-1 text-sm">
            {cooperative ? `${cooperative.city}, ${cooperative.state} · ` : ''}
            Updated {formatDateTime(summary.generated_at)}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={dashboard.reload}>
          Refresh
        </Button>
      </header>

      {/* KPI band */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label={t('admin.workers')}
          value={summary.workers}
          hint={`${summary.customers} customers served`}
          icon={<Users className="size-4" aria-hidden />}
        />
        <Stat
          label={t('admin.activeJobs')}
          value={summary.active_jobs}
          hint={`${summary.unassigned_jobs} awaiting allocation`}
          icon={<Activity className="size-4" aria-hidden />}
          tone="brand"
        />
        <Stat
          label={t('admin.availableWorkers')}
          value={summary.available_workers}
          hint={`${summary.off_duty_workers} off duty`}
          icon={<UserCheck className="size-4" aria-hidden />}
          tone="success"
        />
        <Stat
          label={t('admin.completedToday')}
          value={summary.completed_today}
          hint={`${summary.completion_rate_pct}% completion rate`}
          icon={<CheckCircle2 className="size-4" aria-hidden />}
        />
        <Stat
          label={t('admin.utilisation')}
          value={`${summary.worker_utilisation_pct}%`}
          hint="Average share of weekly capacity committed"
          icon={<Gauge className="size-4" aria-hidden />}
          tone={summary.worker_utilisation_pct >= 85 ? 'warn' : 'brand'}
        />
        <Stat
          label={t('admin.fairness')}
          value={`${summary.fairness_score}/100`}
          hint="Evenness of workload across members"
          icon={<Scale className="size-4" aria-hidden />}
          tone={summary.fairness_score >= 80 ? 'success' : 'warn'}
        />
        <Stat
          label={t('admin.averageRating')}
          value={`${summary.average_rating.toFixed(1)}/5`}
          hint={`${summary.rating_count.toLocaleString('en-IN')} ratings`}
          icon={<Star className="size-4" aria-hidden />}
        />
        <Stat
          label={t('welfare.fund')}
          value={compactCurrency(summary.revenue.welfare_fund)}
          hint={`of ${compactCurrency(summary.revenue.total)} collected`}
          icon={<Scale className="size-4" aria-hidden />}
          tone="success"
        />
      </section>

      {/* AI insight */}
      <Card className="border-brand-200 bg-brand-50/50">
        <div className="flex flex-wrap items-start gap-4">
          <span className="bg-brand-700 flex size-10 shrink-0 items-center justify-center rounded-xl text-white">
            <Lightbulb className="size-5" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="label">{t('forecast.insight')}</p>
              {insight.kind === 'shortage' ? (
                <Badge tone="warn">{t('workforce.shortage')}</Badge>
              ) : (
                <Badge tone="success">{t('workforce.balanced')}</Badge>
              )}
              {insight.confidence !== undefined ? (
                <Badge tone="outline">
                  {t('forecast.confidence')} {Math.round(insight.confidence * 100)}%
                </Badge>
              ) : null}
            </div>
            <p className="text-ink-900 mt-1.5 text-base font-semibold">{insight.headline}</p>
            {insight.supporting ? (
              <p className="text-ink-600 mt-1 text-sm">{insight.supporting}</p>
            ) : null}
            <p className="text-brand-800 mt-2 text-sm font-medium">{insight.recommendation}</p>
            {insight.reallocation ? (
              <p className="text-ink-600 mt-1 text-sm">{insight.reallocation}</p>
            ) : null}
          </div>
          <Button
            variant="secondary"
            onClick={() => navigate('/forecast')}
            iconRight={<ArrowRight className="size-4" aria-hidden />}
          >
            {t('nav.forecast')}
          </Button>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Capacity */}
        <Card className="space-y-4">
          <SectionHeader
            title={t('workforce.title')}
            description="Workers required by forecast demand against workers available."
            action={
              <Button variant="ghost" size="sm" onClick={() => navigate('/workforce')}>
                {t('common.viewAll')}
              </Button>
            }
          />
          <BarSeriesChart
            data={planChart}
            xKey="service"
            horizontal
            height={280}
            series={[
              { key: 'required', label: t('workforce.required'), color: '#1e4d8c' },
              { key: 'available', label: t('workforce.available'), color: '#2a9469' },
            ]}
          />
        </Card>

        {/* Workload */}
        <Card className="space-y-4">
          <SectionHeader
            title={t('admin.mostLoaded')}
            description="Members carrying the most work this week."
          />
          <ul className="space-y-3">
            {utilisation.slice(0, 6).map((row) => (
              <li key={row.worker_id}>
                <div className="mb-1 flex items-baseline justify-between gap-2">
                  <span className="text-ink-800 truncate text-sm">
                    {row.worker}
                    <span className="text-ink-400"> · {row.service}</span>
                  </span>
                  <span className="text-ink-700 text-xs font-semibold tabular-nums">
                    {row.workload_pct}%
                  </span>
                </div>
                <ProgressBar value={row.workload_pct} tone="auto" height="sm" />
              </li>
            ))}
          </ul>

          <div className="border-ink-100 border-t pt-4">
            <p className="label mb-2">{t('admin.leastLoaded')}</p>
            <ul className="space-y-2">
              {least_loaded.map((row) => (
                <li key={row.worker_id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-ink-700 truncate">
                    {row.worker}
                    <span className="text-ink-400"> · {row.service}</span>
                  </span>
                  <Badge tone="success">{row.workload_pct}%</Badge>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </div>

      {/* Live jobs */}
      <Card className="space-y-4">
        <SectionHeader
          title={t('admin.liveJobs')}
          description="Requests in flight right now."
          action={
            <Button variant="ghost" size="sm" onClick={() => navigate('/bookings')}>
              {t('common.viewAll')}
            </Button>
          }
        />
        {live_jobs.length ? (
          <TableWrap>
            <table>
              <thead>
                <tr>
                  <Th>Job</Th>
                  <Th>Service</Th>
                  <Th>Zone</Th>
                  <Th>Worker</Th>
                  <Th>Scheduled</Th>
                  <Th align="right">Status</Th>
                </tr>
              </thead>
              <tbody>
                {live_jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="hover:bg-ink-50 cursor-pointer"
                    onClick={() => navigate(`/bookings/${job.id}`)}
                  >
                    <Td>
                      <span className="text-ink-900 font-medium">{job.problem}</span>
                      <span className="text-ink-400 block font-mono text-xs">{job.reference}</span>
                    </Td>
                    <Td>{job.service}</Td>
                    <Td className="whitespace-nowrap">{job.zone}</Td>
                    <Td>{job.worker ?? <span className="text-warn-600">Unassigned</span>}</Td>
                    <Td className="whitespace-nowrap">{formatDateTime(job.scheduled_for)}</Td>
                    <Td align="right">
                      <span className="inline-flex items-center gap-1.5">
                        <UrgencyBadge urgency={job.urgency} />
                        <StatusBadge status={job.status} />
                      </span>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        ) : (
          <EmptyState title="No jobs are in flight." />
        )}
      </Card>

      {/* Plans table */}
      <Card className="space-y-4">
        <SectionHeader
          title={t('forecast.title')}
          description={t('forecast.subtitle')}
          action={
            <Button variant="ghost" size="sm" onClick={() => navigate('/analytics')}>
              {t('nav.analytics')}
            </Button>
          }
        />
        <TableWrap>
          <table>
            <thead>
              <tr>
                <Th>{t('workforce.service')}</Th>
                <Th align="right">{t('forecast.predicted')}</Th>
                <Th align="right">{t('workforce.required')}</Th>
                <Th align="right">{t('workforce.available')}</Th>
                <Th align="right">{t('workforce.gap')}</Th>
                <Th>{t('forecast.priorityZone')}</Th>
              </tr>
            </thead>
            <tbody>
              {plans.map((plan) => (
                <tr key={plan.service_id}>
                  <Td className="font-medium">{plan.service_name}</Td>
                  <Td align="right">{plan.predicted_demand}</Td>
                  <Td align="right">{plan.required_workers}</Td>
                  <Td align="right">{plan.available_workers}</Td>
                  <Td align="right">
                    <Badge
                      tone={
                        plan.status === 'shortage'
                          ? 'danger'
                          : plan.status === 'surplus'
                            ? 'success'
                            : 'neutral'
                      }
                    >
                      {plan.gap > 0 ? '+' : ''}
                      {plan.gap}
                    </Badge>
                  </Td>
                  <Td className="text-ink-500">{plan.priority_zone ?? '-'}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Card>
    </div>
  )
}

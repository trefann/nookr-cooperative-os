/** Cooperative analytics: the operating picture across every dimension. */

import { useState } from 'react'

import {
  BarSeriesChart,
  CategoricalBarChart,
  DonutChart,
  TrendAreaChart,
  TrendLineChart,
} from '../components/charts'
import {
  Badge,
  Card,
  ErrorState,
  LoadingBlock,
  ProgressBar,
  SectionHeader,
  Stat,
  cx,
} from '../components/ui'
import { useI18n } from '../i18n'
import * as endpoints from '../lib/endpoints'
import { compactCurrency, currency, formatDayLabel } from '../lib/format'
import { useAsync } from '../lib/useAsync'

const RANGES = [7, 30, 60, 90]

export default function AnalyticsPage() {
  const { t } = useI18n()
  const [days, setDays] = useState(30)
  const analytics = useAsync(() => endpoints.getAnalytics(days), [days])

  if (analytics.loading && !analytics.data) {
    return (
      <Card>
        <LoadingBlock rows={6} />
      </Card>
    )
  }
  if (analytics.error || !analytics.data) {
    return <ErrorState message={analytics.error ?? 'Analytics unavailable.'} onRetry={analytics.reload} />
  }

  const data = analytics.data
  const summary = data.summary

  const earnings = data.earnings.map((row) => ({
    date: formatDayLabel(row.date),
    total: row.total,
    worker: row.worker,
    welfare: row.welfare,
  }))

  const demand = data.demand_trend.map((row) => ({
    date: formatDayLabel(row.date),
    jobs: row.jobs,
  }))

  const ratings = data.rating_trend.map((row) => ({
    label: row.label,
    rating: row.average_rating,
  }))

  const funnel = data.completion_funnel.filter((row) => row.count > 0)

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <SectionHeader
          eyebrow={t('nav.analytics')}
          title={t('analytics.title')}
          description={t('analytics.lastDays', { days })}
        />
        <div className="border-ink-300 inline-flex rounded-lg border bg-white p-0.5">
          {RANGES.map((range) => (
            <button
              key={range}
              type="button"
              onClick={() => setDays(range)}
              className={cx(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                days === range ? 'bg-brand-700 text-white' : 'text-ink-600 hover:bg-ink-100',
              )}
            >
              {range}d
            </button>
          ))}
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total jobs" value={summary.total_bookings} hint={`${summary.completed_bookings} completed`} />
        <Stat
          label={t('analytics.completionRate')}
          value={`${summary.completion_rate_pct}%`}
          hint={`${summary.cancelled_bookings} cancelled`}
          tone={summary.completion_rate_pct >= 85 ? 'success' : 'warn'}
        />
        <Stat
          label="Revenue collected"
          value={compactCurrency(summary.revenue.total)}
          hint={`${compactCurrency(summary.revenue.worker_earnings)} to workers`}
          tone="brand"
        />
        <Stat
          label={t('admin.averageRating')}
          value={`${summary.average_rating.toFixed(2)}/5`}
          hint={`${summary.rating_count.toLocaleString('en-IN')} ratings`}
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-4">
          <SectionHeader title={t('analytics.jobsByService')} />
          <CategoricalBarChart
            data={data.jobs_by_service}
            xKey="service"
            valueKey="jobs"
            height={280}
            valueFormatter={(value) => `${value} jobs`}
          />
        </Card>

        <Card className="space-y-4">
          <SectionHeader title={t('analytics.jobsByZone')} />
          <CategoricalBarChart
            data={data.jobs_by_zone}
            xKey="zone"
            valueKey="jobs"
            height={280}
            valueFormatter={(value) => `${value} jobs`}
          />
        </Card>

        <Card className="space-y-4">
          <SectionHeader
            title={t('analytics.demandTrend')}
            description="Requests received each day."
          />
          <TrendAreaChart
            data={demand}
            xKey="date"
            height={260}
            series={[{ key: 'jobs', label: t('common.jobs') }]}
            valueFormatter={(value) => `${value} jobs`}
          />
        </Card>

        <Card className="space-y-4">
          <SectionHeader
            title={t('analytics.earnings')}
            description="Daily payments, and the share going to worker welfare."
          />
          <TrendAreaChart
            data={earnings}
            xKey="date"
            height={260}
            series={[
              { key: 'worker', label: t('payment.workerEarnings'), color: '#1e4d8c' },
              { key: 'welfare', label: t('payment.welfareContribution'), color: '#2a9469' },
            ]}
            valueFormatter={(value) => currency(value)}
          />
        </Card>

        <Card className="space-y-4">
          <SectionHeader
            title={t('analytics.workerUtilisation')}
            description="Share of weekly capacity committed, per member."
          />
          <ul className="space-y-2.5">
            {data.worker_utilisation.map((row) => (
              <li key={row.worker_id}>
                <div className="mb-1 flex items-baseline justify-between gap-2">
                  <span className="text-ink-700 truncate text-sm">
                    {row.worker}
                    <span className="text-ink-400"> · {row.service}</span>
                  </span>
                  <span className="text-ink-900 text-xs font-semibold tabular-nums">
                    {row.workload_pct}%
                  </span>
                </div>
                <ProgressBar value={row.workload_pct} tone="auto" height="sm" />
              </li>
            ))}
          </ul>
        </Card>

        <Card className="space-y-4">
          <SectionHeader title={t('analytics.averageRating')} description="Weekly average." />
          <TrendLineChart
            data={ratings}
            xKey="label"
            height={230}
            domain={[3, 5]}
            series={[{ key: 'rating', label: t('worker.rating'), color: '#c2790d' }]}
            valueFormatter={(value) => `${value.toFixed(2)} ★`}
          />
          <div className="border-ink-100 border-t pt-4">
            <p className="label mb-2">{t('analytics.ratingDistribution')}</p>
            <BarSeriesChart
              data={data.rating_distribution.map((row) => ({
                stars: `${row.stars} ★`,
                count: row.count,
              }))}
              xKey="stars"
              height={160}
              series={[{ key: 'count', label: 'Ratings', color: '#4a7fc4' }]}
            />
          </div>
        </Card>

        <Card className="space-y-4 lg:col-span-2">
          <SectionHeader
            title="Booking outcomes"
            description="Where every request in the system currently stands."
          />
          <div className="grid gap-6 sm:grid-cols-[18rem_minmax(0,1fr)] sm:items-center">
            <DonutChart
              data={funnel.map((row) => ({ name: row.label, value: row.count }))}
              height={240}
              centerValue={summary.total_bookings.toLocaleString('en-IN')}
              centerLabel="total jobs"
              valueFormatter={(value) => `${value} jobs`}
            />
            <ul className="grid gap-2 sm:grid-cols-2">
              {funnel.map((row) => (
                <li
                  key={row.status}
                  className="border-ink-100 flex items-center justify-between gap-2 rounded-lg border px-3 py-2"
                >
                  <span className="text-ink-700 text-sm">{row.label}</span>
                  <Badge tone="neutral">{row.count.toLocaleString('en-IN')}</Badge>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </div>
    </div>
  )
}

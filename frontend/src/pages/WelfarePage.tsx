/**
 * Worker welfare.
 *
 * What the cooperative gives back: the welfare fund, insurance coverage,
 * training credits and certifications, per member.
 */

import { useState } from 'react'
import { GraduationCap, HeartHandshake, Search, ShieldCheck, Users } from 'lucide-react'

import { DonutChart } from '../components/charts'
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingBlock,
  ProgressBar,
  SectionHeader,
  Stat,
  StarRating,
  TableWrap,
  Td,
  Th,
} from '../components/ui'
import { useI18n } from '../i18n'
import * as endpoints from '../lib/endpoints'
import { compactCurrency, currency } from '../lib/format'
import { useAsync } from '../lib/useAsync'

export default function WelfarePage() {
  const { t } = useI18n()
  const welfare = useAsync(() => endpoints.getWelfare(), [])
  const [search, setSearch] = useState('')

  if (welfare.loading && !welfare.data) {
    return (
      <Card>
        <LoadingBlock rows={6} />
      </Card>
    )
  }
  if (welfare.error || !welfare.data) {
    return <ErrorState message={welfare.error ?? 'Welfare data unavailable.'} onRetry={welfare.reload} />
  }

  const data = welfare.data
  const term = search.trim().toLowerCase()
  const rows = term
    ? data.workers.filter(
        (row) =>
          row.worker.toLowerCase().includes(term) ||
          row.service.toLowerCase().includes(term) ||
          row.zone.toLowerCase().includes(term),
      )
    : data.workers

  const coverage = [
    { name: t('welfare.active'), value: data.workers_covered, color: '#2a9469' },
    {
      name: t('welfare.inactive'),
      value: Math.max(0, data.workers_total - data.workers_covered),
      color: '#c8ced9',
    },
  ]

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow={t('nav.welfare')}
        title={t('welfare.title')}
        description={t('welfare.subtitle')}
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label={t('welfare.fund')}
          value={compactCurrency(data.fund_total)}
          hint="Accumulated from completed jobs"
          icon={<HeartHandshake className="size-4" aria-hidden />}
          tone="success"
        />
        <Stat
          label={t('welfare.coverage')}
          value={`${data.coverage_pct}%`}
          hint={`${data.workers_covered} of ${data.workers_total} members insured`}
          icon={<ShieldCheck className="size-4" aria-hidden />}
          tone={data.coverage_pct >= 80 ? 'success' : 'warn'}
        />
        <Stat
          label={t('welfare.trainingCredits')}
          value={data.training_credits_outstanding}
          hint="Available to spend on certification"
          icon={<GraduationCap className="size-4" aria-hidden />}
        />
        <Stat
          label={t('welfare.certifications')}
          value={data.certified_workers}
          hint="Members holding a verified credential"
          icon={<Users className="size-4" aria-hidden />}
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-[20rem_minmax(0,1fr)]">
        <Card className="space-y-3 lg:self-start">
          <SectionHeader title={t('welfare.coverage')} />
          <DonutChart
            data={coverage}
            height={220}
            centerValue={`${data.coverage_pct}%`}
            centerLabel="insured"
            valueFormatter={(value) => `${value} workers`}
          />
          {data.coverage_pct < 100 ? (
            <p className="text-ink-500 text-xs">
              {data.workers_total - data.workers_covered} member
              {data.workers_total - data.workers_covered === 1 ? '' : 's'} not yet covered.
              Insurance is funded from the welfare share of every job.
            </p>
          ) : null}
        </Card>

        <Card className="space-y-4">
          <SectionHeader
            title="Member welfare"
            description="Each member's contribution, cover and credits."
            action={
              <div className="relative">
                <Search className="text-ink-400 pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" aria-hidden />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder={t('common.search')}
                  className="w-48 pl-8"
                  aria-label={t('common.search')}
                />
              </div>
            }
          />

          {rows.length ? (
            <TableWrap>
              <table>
                <thead>
                  <tr>
                    <Th>{t('welfare.worker')}</Th>
                    <Th align="right">{t('welfare.jobsCompleted')}</Th>
                    <Th align="right">{t('welfare.earnings')}</Th>
                    <Th align="right">{t('welfare.contribution')}</Th>
                    <Th>{t('welfare.insurance')}</Th>
                    <Th align="right">{t('welfare.trainingCredits')}</Th>
                    <Th align="right">{t('welfare.certifications')}</Th>
                    <Th align="right">{t('worker.rating')}</Th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.worker_id}>
                      <Td>
                        <span className="text-ink-900 font-medium">{row.worker}</span>
                        <span className="text-ink-400 block text-xs">
                          {row.service} · {row.zone}
                        </span>
                      </Td>
                      <Td align="right">{row.jobs_completed}</Td>
                      <Td align="right">{currency(row.earnings)}</Td>
                      <Td align="right" className="font-semibold">
                        {currency(row.welfare_contribution)}
                      </Td>
                      <Td>
                        {row.insurance_active ? (
                          <Badge tone="success">{t('welfare.active')}</Badge>
                        ) : (
                          <Badge tone="warn">{t('welfare.inactive')}</Badge>
                        )}
                      </Td>
                      <Td align="right">{row.training_credits}</Td>
                      <Td align="right">{row.certification_count}</Td>
                      <Td align="right">
                        <StarRating value={row.rating_avg} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          ) : (
            <EmptyState title={t('common.noResults')} description={`No member matches “${search}”.`} />
          )}

          {rows.length ? (
            <div>
              <p className="label mb-2">Contribution distribution</p>
              <ul className="space-y-2">
                {rows.slice(0, 6).map((row) => {
                  const max = rows[0]?.welfare_contribution || 1
                  return (
                    <li key={row.worker_id}>
                      <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
                        <span className="text-ink-600 truncate">{row.worker}</span>
                        <span className="text-ink-900 font-semibold tabular-nums">
                          {currency(row.welfare_contribution)}
                        </span>
                      </div>
                      <ProgressBar
                        value={(row.welfare_contribution / max) * 100}
                        tone="success"
                        height="sm"
                      />
                    </li>
                  )
                })}
              </ul>
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  )
}

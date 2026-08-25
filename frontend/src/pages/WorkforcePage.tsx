/**
 * Workforce planning and skill gaps.
 *
 * Where demand is about to outrun capacity, who has room, and which skills the
 * cooperative should train for next.
 */

import { AlertTriangle, GraduationCap, Info, Scale, Users } from 'lucide-react'

import { BarSeriesChart } from '../components/charts'
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  InlineNotice,
  LoadingBlock,
  ProgressBar,
  SectionHeader,
  Stat,
  TableWrap,
  Td,
  Th,
  cx,
} from '../components/ui'
import { useI18n } from '../i18n'
import * as endpoints from '../lib/endpoints'
import { useAsync } from '../lib/useAsync'

export default function WorkforcePage() {
  const { t } = useI18n()
  const workforce = useAsync(() => endpoints.getWorkforce(), [])

  if (workforce.loading && !workforce.data) {
    return (
      <Card>
        <LoadingBlock rows={6} />
      </Card>
    )
  }
  if (workforce.error || !workforce.data) {
    return (
      <ErrorState message={workforce.error ?? 'Workforce data unavailable.'} onRetry={workforce.reload} />
    )
  }

  const {
    plans,
    insight,
    skill_gaps,
    skill_gaps_top,
    most_demanded_skills,
    utilisation,
    fair_distribution_projection,
  } = workforce.data

  const shortages = plans.filter((plan) => plan.gap < 0)
  const surpluses = plans.filter((plan) => plan.gap > 0)
  const projection = fair_distribution_projection.rows.map((row) => ({
    worker: row.worker,
    before: row.before,
    after: row.after,
  }))

  const averageWorkload = utilisation.length
    ? Math.round(utilisation.reduce((sum, row) => sum + row.workload_pct, 0) / utilisation.length)
    : 0

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow={t('nav.workforce')}
        title={t('workforce.title')}
        description={t('workforce.subtitle')}
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label={t('common.workers')}
          value={utilisation.length}
          hint={`${averageWorkload}% average workload`}
          icon={<Users className="size-4" aria-hidden />}
        />
        <Stat
          label={t('workforce.shortage')}
          value={shortages.length}
          hint={
            shortages.length
              ? shortages.map((plan) => plan.service_name).join(', ')
              : 'No service is short-staffed'
          }
          icon={<AlertTriangle className="size-4" aria-hidden />}
          tone={shortages.length ? 'danger' : 'success'}
        />
        <Stat
          label={t('workforce.surplus')}
          value={surpluses.length}
          hint={
            surpluses.length
              ? surpluses.map((plan) => plan.service_name).join(', ')
              : 'No spare capacity'
          }
          icon={<Scale className="size-4" aria-hidden />}
          tone="success"
        />
        <Stat
          label={t('workforce.skillGaps')}
          value={skill_gaps_top.length}
          hint="Skills where demand exceeds capacity"
          icon={<GraduationCap className="size-4" aria-hidden />}
          tone={skill_gaps_top.length ? 'warn' : 'success'}
        />
      </section>

      {/* Headline recommendation */}
      <Card className="border-brand-200 bg-brand-50/50 space-y-1.5">
        <p className="label">{t('workforce.trainRecommendation')}</p>
        <p className="text-ink-900 text-lg font-semibold">{insight.headline}</p>
        {insight.supporting ? <p className="text-ink-600 text-sm">{insight.supporting}</p> : null}
        <p className="text-brand-800 text-sm font-medium">{insight.recommendation}</p>
        {insight.reallocation ? (
          <p className="text-ink-600 text-sm">{insight.reallocation}</p>
        ) : null}
      </Card>

      {/* Service plan */}
      <Card className="space-y-4">
        <SectionHeader
          title="Service capacity plan"
          description="Workers required by forecast demand against workers available now."
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
                <Th>{t('workforce.trainRecommendation')}</Th>
              </tr>
            </thead>
            <tbody>
              {plans.map((plan) => (
                <tr
                  key={plan.service_id}
                  className={cx(plan.status === 'shortage' && 'bg-danger-50/40')}
                >
                  <Td className="font-medium whitespace-nowrap">{plan.service_name}</Td>
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
                      {plan.gap > 0 ? `+${plan.gap}` : plan.gap}
                    </Badge>
                  </Td>
                  <Td className="text-ink-600 text-xs">{plan.recommendation}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Card>

      {/* Fair workload distribution */}
      <Card className="space-y-4">
        <SectionHeader
          title={t('workforce.utilisationTitle')}
          description={fair_distribution_projection.label}
          action={<Badge tone="warn">{t('workforce.projectionNote')}</Badge>}
        />
        <InlineNotice tone="neutral" icon={<Info className="size-4" aria-hidden />}>
          {fair_distribution_projection.note}
        </InlineNotice>
        {projection.length ? (
          <BarSeriesChart
            data={projection}
            xKey="worker"
            horizontal
            height={240}
            series={[
              { key: 'before', label: 'Current workload', color: '#c2790d' },
              { key: 'after', label: 'Projected in 7 days', color: '#2a9469' },
            ]}
            valueFormatter={(value) => `${value}%`}
          />
        ) : (
          <EmptyState title={t('common.noResults')} />
        )}
      </Card>

      {/* Utilisation list */}
      <Card className="space-y-4">
        <SectionHeader
          title={t('admin.utilisation')}
          description="Share of each member's weekly capacity that is already committed."
        />
        <ul className="grid gap-3 sm:grid-cols-2">
          {utilisation.map((row) => (
            <li key={row.worker_id}>
              <div className="mb-1 flex items-baseline justify-between gap-2">
                <span className="text-ink-800 truncate text-sm">
                  {row.worker}
                  <span className="text-ink-400"> · {row.service}</span>
                </span>
                <span className="text-ink-700 text-xs font-semibold tabular-nums">
                  {row.committed_jobs}/{row.weekly_capacity} · {row.workload_pct}%
                </span>
              </div>
              <ProgressBar value={row.workload_pct} tone="auto" height="sm" />
            </li>
          ))}
        </ul>
      </Card>

      {/* Skill gaps */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card className="space-y-4">
          <SectionHeader
            title={t('workforce.skillGaps')}
            description="Projected demand for each skill against the members who can serve it."
          />
          {skill_gaps_top.length ? (
            <div className="space-y-3">
              {skill_gaps_top.map((gap) => (
                <div
                  key={gap.skill_id}
                  className="border-ink-200 rounded-xl border p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-ink-900 font-semibold">{gap.skill_name}</h3>
                        {gap.is_emerging ? (
                          <Badge tone="success">{t('workforce.emerging')}</Badge>
                        ) : null}
                        {gap.requires_certification ? (
                          <Badge tone="brand">{t('matching.certification')}</Badge>
                        ) : null}
                      </div>
                      <p className="text-ink-500 mt-0.5 text-xs">{gap.service_name}</p>
                    </div>
                    <Badge tone="danger">
                      {t('workforce.gap')} {gap.gap}
                    </Badge>
                  </div>

                  <dl className="mt-3 grid grid-cols-3 gap-3 text-sm">
                    <div>
                      <dt className="text-ink-400 text-xs">{t('workforce.required')}</dt>
                      <dd className="text-ink-900 font-semibold tabular-nums">
                        {gap.required_workers}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-ink-400 text-xs">{t('workforce.available')}</dt>
                      <dd className="text-ink-900 font-semibold tabular-nums">
                        {gap.requires_certification ? gap.certified_workers : gap.available_workers}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-ink-400 text-xs">Projected jobs</dt>
                      <dd className="text-ink-900 font-semibold tabular-nums">
                        {gap.projected_jobs}
                      </dd>
                    </div>
                  </dl>

                  <p className="text-brand-800 border-ink-100 mt-3 border-t pt-3 text-sm font-medium">
                    {gap.recommendation}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No skill gaps detected"
              description="Every skill currently has enough qualified members."
            />
          )}

          <details className="border-ink-200 rounded-xl border">
            <summary className="text-ink-600 hover:text-ink-900 cursor-pointer px-4 py-3 text-sm font-medium">
              All skills ({skill_gaps.length})
            </summary>
            <TableWrap className="border-ink-100 border-t px-4 pb-3">
              <table>
                <thead>
                  <tr>
                    <Th>Skill</Th>
                    <Th align="right">Recent</Th>
                    <Th align="right">Projected</Th>
                    <Th align="right">Required</Th>
                    <Th align="right">Available</Th>
                    <Th align="right">Gap</Th>
                  </tr>
                </thead>
                <tbody>
                  {skill_gaps.map((gap) => (
                    <tr key={gap.skill_id}>
                      <Td className="whitespace-nowrap">
                        {gap.skill_name}
                        {gap.is_specialist ? (
                          <span className="text-ink-400 ml-1 text-xs">specialist</span>
                        ) : null}
                      </Td>
                      <Td align="right">{gap.recent_jobs}</Td>
                      <Td align="right">{gap.projected_jobs}</Td>
                      <Td align="right">{gap.required_workers}</Td>
                      <Td align="right">
                        {gap.requires_certification ? gap.certified_workers : gap.available_workers}
                      </Td>
                      <Td align="right">
                        {gap.gap > 0 ? (
                          <Badge tone="danger">{gap.gap}</Badge>
                        ) : (
                          <span className="text-ink-400">-</span>
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          </details>
        </Card>

        <Card className="space-y-3 lg:self-start">
          <SectionHeader
            title={t('workforce.mostDemanded')}
            description="Skills real jobs asked for in the last four weeks."
          />
          <ul className="space-y-2.5">
            {most_demanded_skills.map((skill, index) => {
              const max = most_demanded_skills[0]?.jobs || 1
              return (
                <li key={skill.skill}>
                  <div className="mb-1 flex items-baseline justify-between gap-2">
                    <span className="text-ink-700 truncate text-sm">
                      <span className="text-ink-400 mr-1.5 tabular-nums">{index + 1}.</span>
                      {skill.skill}
                    </span>
                    <span className="text-ink-900 text-xs font-semibold tabular-nums">
                      {skill.jobs}
                    </span>
                  </div>
                  <ProgressBar value={(skill.jobs / max) * 100} height="sm" />
                </li>
              )
            })}
          </ul>
        </Card>
      </div>
    </div>
  )
}

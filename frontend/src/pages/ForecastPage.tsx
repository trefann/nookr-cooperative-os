/**
 * AI demand forecast.
 *
 * Expected job volume per service for the next seven days, with the method
 * stated plainly and the confidence reported for each service.
 */

import { Info, Lightbulb, TrendingUp } from 'lucide-react'

import { CategoricalBarChart, TrendLineChart } from '../components/charts'
import {
  Badge,
  Card,
  ErrorState,
  InlineNotice,
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
import { signedPercent } from '../lib/format'
import { useAsync } from '../lib/useAsync'

export default function ForecastPage() {
  const { t } = useI18n()
  const forecast = useAsync(() => endpoints.getForecast(), [])

  if (forecast.loading && !forecast.data) {
    return (
      <Card>
        <LoadingBlock rows={6} />
      </Card>
    )
  }
  if (forecast.error || !forecast.data) {
    return <ErrorState message={forecast.error ?? 'Forecast unavailable.'} onRetry={forecast.reload} />
  }

  const { services, insight, zone_pressure, method_label, method_note, horizon_days } =
    forecast.data

  const chartData = services.map((service) => ({
    service: service.service_name,
    predicted: service.predicted_demand,
  }))

  // Weekly history for the top four services, aligned on the same week labels.
  const topServices = services.slice(0, 4)
  const historyLabels = topServices[0]?.history.map((point) => point.label) ?? []
  const historyData = historyLabels.map((label, index) => {
    const row: Record<string, string | number> = { label }
    for (const service of topServices) {
      row[service.service_slug] = service.history[index]?.jobs ?? 0
    }
    return row
  })

  const totalPredicted = services.reduce((sum, item) => sum + item.predicted_demand, 0)
  const averageConfidence =
    services.length
      ? services.reduce((sum, item) => sum + item.confidence, 0) / services.length
      : 0

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow={t('nav.forecast')}
        title={t('forecast.title')}
        description={t('forecast.subtitle')}
      />

      <section className="grid gap-4 sm:grid-cols-3">
        <Stat
          label="Forecast horizon"
          value={`${horizon_days} days`}
          hint={method_label}
          icon={<TrendingUp className="size-4" aria-hidden />}
        />
        <Stat
          label="Total jobs expected"
          value={totalPredicted}
          hint="Across all services"
          tone="brand"
        />
        <Stat
          label={t('forecast.confidence')}
          value={`${Math.round(averageConfidence * 100)}%`}
          hint="Average across services"
          tone={averageConfidence >= 0.7 ? 'success' : 'warn'}
        />
      </section>

      <InlineNotice tone="neutral" icon={<Info className="size-4" aria-hidden />} title={method_label}>
        {method_note}
      </InlineNotice>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="space-y-4">
          <SectionHeader
            title={t('forecast.title')}
            description={`Predicted jobs for the next ${horizon_days} days`}
          />
          <CategoricalBarChart
            data={chartData}
            xKey="service"
            valueKey="predicted"
            height={300}
            valueFormatter={(value) => `${value} jobs`}
          />
        </Card>

        <Card className="space-y-4">
          <SectionHeader
            title="Weekly history"
            description="What the forecast is built from: the last four weeks per service."
          />
          <TrendLineChart
            data={historyData}
            xKey="label"
            height={300}
            series={topServices.map((service) => ({
              key: service.service_slug,
              label: service.service_name,
            }))}
            valueFormatter={(value) => `${value} jobs`}
          />
        </Card>
      </div>

      {/* AI insight */}
      <Card className="border-brand-200 bg-brand-50/50">
        <div className="flex flex-wrap items-start gap-4">
          <span className="bg-brand-700 flex size-10 shrink-0 items-center justify-center rounded-xl text-white">
            <Lightbulb className="size-5" aria-hidden />
          </span>
          <div className="min-w-0 flex-1 space-y-1.5">
            <p className="label">{t('forecast.insight')}</p>
            <p className="text-ink-900 text-lg font-semibold">{insight.headline}</p>
            {insight.supporting ? (
              <p className="text-ink-600 text-sm">{insight.supporting}</p>
            ) : null}
            <div className="border-brand-200 mt-2 border-t pt-2.5">
              <p className="label mb-0.5">{t('forecast.recommendation')}</p>
              <p className="text-brand-800 text-sm font-medium">{insight.recommendation}</p>
              {insight.reallocation ? (
                <p className="text-ink-600 mt-1 text-sm">{insight.reallocation}</p>
              ) : null}
            </div>
          </div>
          {insight.priority_zone ? (
            <div className="text-right">
              <p className="label">{t('forecast.priorityZone')}</p>
              <p className="text-ink-900 font-semibold">{insight.priority_zone}</p>
            </div>
          ) : null}
        </div>
      </Card>

      {/* Detail table */}
      <Card className="space-y-4">
        <SectionHeader title="Per service" description="Prediction, baseline and confidence." />
        <TableWrap>
          <table>
            <thead>
              <tr>
                <Th>{t('workforce.service')}</Th>
                <Th align="right">{t('forecast.predicted')}</Th>
                <Th align="right">{t('forecast.lastWeek')}</Th>
                <Th align="right">{t('forecast.baseline')}</Th>
                <Th align="right">Change</Th>
                <Th>{t('forecast.confidence')}</Th>
                <Th>{t('forecast.priorityZone')}</Th>
              </tr>
            </thead>
            <tbody>
              {services.map((service) => (
                <tr key={service.service_id}>
                  <Td className="font-medium whitespace-nowrap">{service.service_name}</Td>
                  <Td align="right" className="font-semibold">
                    {service.predicted_demand}
                  </Td>
                  <Td align="right">{service.last_week_demand}</Td>
                  <Td align="right">{service.baseline_demand.toFixed(1)}</Td>
                  <Td align="right">
                    <Badge
                      tone={
                        service.change_pct > 8
                          ? 'warn'
                          : service.change_pct < -8
                            ? 'info'
                            : 'neutral'
                      }
                    >
                      {signedPercent(service.change_pct)}
                    </Badge>
                  </Td>
                  <Td>
                    <div className="w-24">
                      <ProgressBar
                        value={service.confidence * 100}
                        tone={service.confidence >= 0.7 ? 'success' : 'warn'}
                        height="sm"
                        showLabel
                      />
                    </div>
                  </Td>
                  <Td className="text-ink-500 whitespace-nowrap">{service.top_zone ?? '-'}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
        <p className="text-ink-400 text-xs">
          Change is measured against each service's four-week weighted average, which is the
          baseline the model reasons about.
        </p>
      </Card>

      {/* Zone pressure */}
      <Card className="space-y-4">
        <SectionHeader
          title={t('forecast.zonePressure')}
          description="Jobs in the last fortnight per worker based in each zone."
        />
        <TableWrap>
          <table>
            <thead>
              <tr>
                <Th>Zone</Th>
                <Th align="right">Jobs (14 days)</Th>
                <Th align="right">{t('common.workers')}</Th>
                <Th align="right">Jobs per worker</Th>
              </tr>
            </thead>
            <tbody>
              {zone_pressure.map((zone) => (
                <tr key={zone.zone_id}>
                  <Td className="font-medium">{zone.zone}</Td>
                  <Td align="right">{zone.jobs_last_14_days}</Td>
                  <Td align="right">{zone.workers}</Td>
                  <Td align="right">
                    <Badge tone={(zone.jobs_per_worker ?? 0) > 20 ? 'warn' : 'neutral'}>
                      {zone.jobs_per_worker?.toFixed(1) ?? '-'}
                    </Badge>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Card>
    </div>
  )
}

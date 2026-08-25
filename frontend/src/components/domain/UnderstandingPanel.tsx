/**
 * "AI understood your request" - the structured interpretation, shown back to
 * the customer before anything is booked, with the engine that produced it
 * named honestly and every field editable.
 */

import { ArrowRight, Cpu, Pencil, Sparkles } from 'lucide-react'

import { useI18n } from '../../i18n'
import { currency } from '../../lib/format'
import type { Service, UnderstandResponse, Zone } from '../../lib/types'
import { Badge, Button, Card, Field, InlineNotice, ProgressBar, Select, cx } from '../ui'

interface Row {
  label: string
  value: string
}

export function UnderstandingPanel({
  result,
  services,
  zones,
  serviceId,
  zoneId,
  onServiceChange,
  onZoneChange,
  onConfirm,
  onEdit,
  confirming,
  className,
}: {
  result: UnderstandResponse
  services: Service[]
  zones: Zone[]
  serviceId: number | null
  zoneId: number | null
  onServiceChange: (id: number) => void
  onZoneChange: (id: number) => void
  onConfirm: () => void
  onEdit: () => void
  confirming?: boolean
  className?: string
}) {
  const { t } = useI18n()
  const u = result.understanding
  const lowConfidence = u.confidence < 0.5

  const rows: Row[] = [
    { label: t('ai.service'), value: u.service_name },
    { label: t('ai.problem'), value: u.problem },
    { label: t('ai.skills'), value: u.skill_names.join(', ') || '-' },
    { label: t('ai.workers'), value: String(u.workers_required) },
    { label: t('ai.urgency'), value: t(`urgency.${u.urgency}` as 'urgency.NORMAL') },
    { label: t('ai.preferredTime'), value: u.preferred_time_label },
  ]

  const price = result.estimated_price

  return (
    <Card className={cx('animate-fade-up border-brand-200 space-y-5', className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="bg-brand-100 text-brand-700 flex size-10 shrink-0 items-center justify-center rounded-xl">
            <Sparkles className="size-5" aria-hidden />
          </span>
          <div>
            <h2 className="text-ink-900 text-base font-semibold">{t('ai.understood')}</h2>
            <p className="text-ink-500 mt-0.5 text-sm">{result.engine.explanation}</p>
          </div>
        </div>
        <Badge tone={result.engine.is_fallback ? 'neutral' : 'brand'} icon={<Cpu className="size-3" aria-hidden />}>
          {result.engine.is_fallback ? t('ai.engineRules') : t('ai.engineLlm')}
        </Badge>
      </div>

      {lowConfidence ? (
        <InlineNotice tone="warn" title="Low confidence">
          {u.notes || 'Please confirm the service below before continuing.'}
        </InlineNotice>
      ) : null}

      <dl className="divide-ink-100 divide-y">
        {rows.map((row) => (
          <div key={row.label} className="flex items-baseline justify-between gap-4 py-2.5">
            <dt className="text-ink-500 text-sm">{row.label}</dt>
            <dd className="text-ink-900 text-right text-sm font-medium">{row.value}</dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={t('ai.changeService')} htmlFor="understanding-service">
          <Select
            id="understanding-service"
            value={serviceId ?? ''}
            onChange={(event) => onServiceChange(Number(event.target.value))}
          >
            {services.map((service) => (
              <option key={service.id} value={service.id}>
                {service.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t('ai.location')} htmlFor="understanding-zone">
          <Select
            id="understanding-zone"
            value={zoneId ?? ''}
            onChange={(event) => onZoneChange(Number(event.target.value))}
          >
            {zones.map((zone) => (
              <option key={zone.id} value={zone.id}>
                {zone.name}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <div className="border-ink-100 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
        <div className="min-w-[9rem]">
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="text-ink-500 text-xs">{t('ai.confidence')}</span>
            <span className="text-ink-700 text-xs font-semibold tabular-nums">
              {Math.round(u.confidence * 100)}%
            </span>
          </div>
          <ProgressBar value={u.confidence * 100} tone={lowConfidence ? 'warn' : 'success'} height="sm" />
        </div>

        {price !== null ? (
          <div className="text-right">
            <p className="text-ink-500 text-xs">{t('ai.estimatedPrice')}</p>
            <p className="text-ink-900 text-lg font-semibold tabular-nums">{currency(price)}</p>
          </div>
        ) : null}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row-reverse">
        <Button
          size="lg"
          onClick={onConfirm}
          loading={confirming}
          iconRight={<ArrowRight className="size-4" aria-hidden />}
          className="sm:flex-1"
        >
          {t('ai.findWorker')}
        </Button>
        <Button variant="secondary" size="lg" onClick={onEdit} icon={<Pencil className="size-4" aria-hidden />}>
          {t('ai.editRequest')}
        </Button>
      </div>
    </Card>
  )
}

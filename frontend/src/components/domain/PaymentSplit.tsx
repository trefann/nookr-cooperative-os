/**
 * The cooperative payment model, made visible.
 *
 * This is the screen that shows where a customer's money actually goes: most
 * to the worker, the rest into the cooperative's own funds. Labelled as a
 * demo distribution because no real transaction takes place.
 */

import { Info } from 'lucide-react'

import { useI18n } from '../../i18n'
import { currency } from '../../lib/format'
import type { PaymentSplit as Split } from '../../lib/types'
import { Card, InlineNotice, cx } from '../ui'

const SEGMENT_COLORS = ['#1e4d8c', '#2a9469', '#4a7fc4', '#c2790d'] as const

export function PaymentSplitPanel({
  split,
  title,
  className,
  compact = false,
}: {
  split: Split
  title?: string
  className?: string
  compact?: boolean
}) {
  const { t } = useI18n()

  const rows = [
    { label: t('payment.workerEarnings'), amount: split.worker_amount, color: SEGMENT_COLORS[0] },
    { label: t('payment.cooperativeFund'), amount: split.cooperative_amount, color: SEGMENT_COLORS[1] },
    { label: t('payment.welfareContribution'), amount: split.welfare_amount, color: SEGMENT_COLORS[2] },
    { label: t('payment.technologyFund'), amount: split.technology_amount, color: SEGMENT_COLORS[3] },
  ]
  const total = split.amount || 1

  return (
    <Card className={cx('space-y-4', className)}>
      <div>
        <h3 className="text-ink-900 text-sm font-semibold">{title ?? t('payment.distribution')}</h3>
        <p className="text-ink-500 mt-0.5 text-xs">
          {t('payment.customerPayment')}: {currency(split.amount)}
        </p>
      </div>

      <div className="bg-ink-100 flex h-2.5 w-full overflow-hidden rounded-full" aria-hidden>
        {rows.map((row) => (
          <div
            key={row.label}
            style={{ width: `${(row.amount / total) * 100}%`, backgroundColor: row.color }}
          />
        ))}
      </div>

      <dl className="divide-ink-100 divide-y">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-3 py-2">
            <dt className="text-ink-600 flex items-center gap-2 text-sm">
              <span
                className="size-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: row.color }}
                aria-hidden
              />
              {row.label}
            </dt>
            <dd className="text-ink-900 text-sm font-medium tabular-nums">
              {currency(row.amount)}
              <span className="text-ink-400 ml-1.5 text-xs font-normal">
                {Math.round((row.amount / total) * 100)}%
              </span>
            </dd>
          </div>
        ))}
        <div className="flex items-center justify-between gap-3 pt-2.5">
          <dt className="text-ink-900 text-sm font-semibold">{t('payment.total')}</dt>
          <dd className="text-ink-900 text-base font-semibold tabular-nums">
            {currency(split.amount)}
          </dd>
        </div>
      </dl>

      {!compact ? (
        <InlineNotice tone="neutral" icon={<Info className="size-4" aria-hidden />}>
          {t('payment.distributionNote')}
        </InlineNotice>
      ) : null}
    </Card>
  )
}

/** A job, summarised. Used in every list across the three portals. */

import { CalendarClock, MapPin, User2 } from 'lucide-react'
import type { ReactNode } from 'react'

import { currency, formatDateTime } from '../../lib/format'
import type { Booking } from '../../lib/types'
import { Badge, Card, cx } from '../ui'
import { StatusBadge, UrgencyBadge } from './status'

export function BookingCard({
  booking,
  onOpen,
  actions,
  showCustomer = false,
  highlight = false,
  className,
}: {
  booking: Booking
  onOpen?: () => void
  actions?: ReactNode
  showCustomer?: boolean
  highlight?: boolean
  className?: string
}) {
  const interactive = Boolean(onOpen)
  const price = booking.final_price ?? booking.estimated_price

  return (
    <Card
      padded={false}
      className={cx(
        'overflow-hidden',
        highlight && 'ring-brand-200 border-brand-200 ring-2',
        interactive && 'card-hover',
        className,
      )}
    >
      <div
        role={interactive ? 'button' : undefined}
        tabIndex={interactive ? 0 : undefined}
        onClick={onOpen}
        onKeyDown={
          interactive
            ? (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  onOpen?.()
                }
              }
            : undefined
        }
        className={cx('p-4 sm:p-5', interactive && 'cursor-pointer')}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="outline">{booking.service_name}</Badge>
              <UrgencyBadge urgency={booking.urgency} />
            </div>
            <h3 className="text-ink-900 mt-2 text-base leading-snug font-semibold">
              {booking.problem_summary}
            </h3>
          </div>
          <div className="text-right">
            <StatusBadge status={booking.status} />
            <p className="text-ink-400 mt-1.5 font-mono text-xs">{booking.reference}</p>
          </div>
        </div>

        <dl className="text-ink-600 mt-3 grid gap-x-4 gap-y-1.5 text-sm sm:grid-cols-2">
          <div className="flex items-center gap-1.5">
            <CalendarClock className="text-ink-400 size-3.5 shrink-0" aria-hidden />
            <dt className="sr-only">Scheduled</dt>
            <dd className="truncate">
              {booking.preferred_time_label || formatDateTime(booking.scheduled_for)}
            </dd>
          </div>
          <div className="flex items-center gap-1.5">
            <MapPin className="text-ink-400 size-3.5 shrink-0" aria-hidden />
            <dt className="sr-only">Zone</dt>
            <dd className="truncate">{booking.zone_name}</dd>
          </div>
          {booking.worker ? (
            <div className="flex items-center gap-1.5">
              <User2 className="text-ink-400 size-3.5 shrink-0" aria-hidden />
              <dt className="sr-only">Worker</dt>
              <dd className="truncate">
                {booking.worker.name}
                <span className="text-ink-400"> · ★ {booking.worker.rating_avg.toFixed(1)}</span>
              </dd>
            </div>
          ) : null}
          {showCustomer && booking.customer_name ? (
            <div className="flex items-center gap-1.5">
              <User2 className="text-ink-400 size-3.5 shrink-0" aria-hidden />
              <dt className="sr-only">Customer</dt>
              <dd className="truncate">{booking.customer_name}</dd>
            </div>
          ) : null}
        </dl>

        {booking.required_skills.length ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {booking.required_skills.map((skill) => (
              <Badge key={skill} tone="neutral">
                {skill}
              </Badge>
            ))}
          </div>
        ) : null}
      </div>

      <div className="border-ink-100 bg-ink-50/60 flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 sm:px-5">
        <span className="text-ink-900 text-sm font-semibold tabular-nums">
          {currency(price)}
          {booking.final_price === null ? (
            <span className="text-ink-400 ml-1 text-xs font-normal">estimated</span>
          ) : null}
        </span>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </Card>
  )
}

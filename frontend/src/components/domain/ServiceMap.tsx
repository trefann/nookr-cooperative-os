/**
 * Simulated location view.
 *
 * A schematic of the worker's position relative to the job, drawn from the
 * real coordinates the API returns. It is deliberately not a mapping service:
 * the product must run with no paid API and no network dependency, and the
 * panel says so rather than implying live GPS.
 */

import { Home, Navigation, Wrench } from 'lucide-react'

import { distanceLabel } from '../../lib/format'
import type { BookingDetail } from '../../lib/types'
import { Badge, Card, cx } from '../ui'

export function ServiceMap({
  booking,
  className,
}: {
  booking: BookingDetail
  className?: string
}) {
  const worker = booking.worker
  if (!worker) return null

  // Place both points inside a padded box, preserving their real bearing.
  const dLat = worker.lat - booking.lat
  const dLng = worker.lng - booking.lng
  const magnitude = Math.max(Math.abs(dLat), Math.abs(dLng), 0.0001)
  const offsetX = (dLng / magnitude) * 30
  const offsetY = (-dLat / magnitude) * 26

  const workerX = 50 + offsetX
  const workerY = 50 + offsetY

  const inTransit = booking.status === 'ACCEPTED' || booking.status === 'ASSIGNED'
  const onSite = booking.status === 'IN_PROGRESS'

  return (
    <Card className={cx('space-y-3', className)} padded={false}>
      <div className="flex items-center justify-between gap-2 px-5 pt-5">
        <h3 className="text-ink-900 text-sm font-semibold">Worker location</h3>
        <Badge tone="neutral">Simulated view</Badge>
      </div>

      <div className="relative mx-5 overflow-hidden rounded-xl border border-ink-200 bg-[linear-gradient(0deg,#f7f8fa_1px,transparent_1px),linear-gradient(90deg,#f7f8fa_1px,transparent_1px)] bg-ink-50 [background-size:22px_22px]">
        <svg viewBox="0 0 100 68" className="h-44 w-full" role="img" aria-label="Schematic of worker distance from the job address">
          <line
            x1={workerX}
            y1={workerY * 0.68}
            x2={50}
            y2={50 * 0.68}
            stroke="#4a7fc4"
            strokeWidth="0.7"
            strokeDasharray="2 1.6"
          />
          <circle cx={50} cy={50 * 0.68} r="9" fill="#1e4d8c" fillOpacity="0.08" />
          <circle cx={50} cy={50 * 0.68} r="2.6" fill="#1e4d8c" />
          <circle
            cx={workerX}
            cy={workerY * 0.68}
            r={onSite ? 2.6 : 2.9}
            fill={onSite ? '#1e4d8c' : '#2a9469'}
          />
        </svg>

        <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 px-3 pb-2.5">
          <span className="text-ink-700 inline-flex items-center gap-1.5 rounded-md bg-white/90 px-2 py-1 text-xs shadow-sm">
            <Home className="text-brand-700 size-3.5" aria-hidden />
            Your address
          </span>
          <span className="text-ink-700 inline-flex items-center gap-1.5 rounded-md bg-white/90 px-2 py-1 text-xs shadow-sm">
            <Wrench className="text-accent-600 size-3.5" aria-hidden />
            {worker.name}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 px-5 pb-5">
        <div>
          <p className="text-ink-500 text-xs">Distance</p>
          <p className="text-ink-900 text-sm font-semibold tabular-nums">
            {distanceLabel(booking.distance_km)}
          </p>
        </div>
        <div>
          <p className="text-ink-500 text-xs">Travel time</p>
          <p className="text-ink-900 text-sm font-semibold tabular-nums">
            {booking.eta_minutes !== null ? `${booking.eta_minutes} min` : '-'}
          </p>
        </div>
        <div>
          <p className="text-ink-500 text-xs">Status</p>
          <p className="text-ink-900 inline-flex items-center gap-1 text-sm font-semibold">
            {onSite ? (
              'On site'
            ) : inTransit ? (
              <>
                <Navigation className="text-accent-600 size-3.5" aria-hidden />
                En route
              </>
            ) : (
              'Scheduled'
            )}
          </p>
        </div>
      </div>
    </Card>
  )
}

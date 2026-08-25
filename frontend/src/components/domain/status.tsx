/** Status vocabulary: one badge and one timeline used everywhere. */

import { Check, Circle, Loader2 } from 'lucide-react'

import type { BookingStatus, TimelineStep, Urgency } from '../../lib/types'
import { Badge, cx, type BadgeTone } from '../ui'

const STATUS_TONES: Record<BookingStatus, BadgeTone> = {
  REQUESTED: 'warn',
  ASSIGNED: 'info',
  ACCEPTED: 'brand',
  IN_PROGRESS: 'brand',
  COMPLETED: 'success',
  PAID: 'success',
  RATED: 'neutral',
  DECLINED: 'danger',
  CANCELLED: 'neutral',
}

const STATUS_LABELS: Record<BookingStatus, string> = {
  REQUESTED: 'Awaiting allocation',
  ASSIGNED: 'Assigned',
  ACCEPTED: 'Accepted',
  IN_PROGRESS: 'In progress',
  COMPLETED: 'Completed',
  PAID: 'Paid',
  RATED: 'Rated',
  DECLINED: 'Declined',
  CANCELLED: 'Cancelled',
}

export function statusLabel(status: BookingStatus): string {
  return STATUS_LABELS[status] ?? status
}

export function StatusBadge({ status, className }: { status: BookingStatus; className?: string }) {
  return (
    <Badge tone={STATUS_TONES[status] ?? 'neutral'} className={className}>
      {status === 'IN_PROGRESS' ? (
        <span className="bg-brand-500 animate-live inline-block size-1.5 rounded-full" aria-hidden />
      ) : null}
      {STATUS_LABELS[status] ?? status}
    </Badge>
  )
}

const URGENCY_TONES: Record<Urgency, BadgeTone> = {
  LOW: 'neutral',
  NORMAL: 'outline',
  HIGH: 'warn',
  EMERGENCY: 'danger',
}

export function UrgencyBadge({ urgency, className }: { urgency: Urgency; className?: string }) {
  if (urgency === 'NORMAL') return null
  return (
    <Badge tone={URGENCY_TONES[urgency]} className={className}>
      {urgency === 'EMERGENCY' ? '🚨 ' : ''}
      {urgency.charAt(0) + urgency.slice(1).toLowerCase()}
    </Badge>
  )
}

export function AvailabilityDot({ status }: { status: string }) {
  const map: Record<string, { colour: string; label: string }> = {
    AVAILABLE: { colour: 'bg-accent-500', label: 'Available' },
    BUSY: { colour: 'bg-warn-500', label: 'On a job' },
    OFF_DUTY: { colour: 'bg-ink-400', label: 'Off duty' },
  }
  const entry = map[status] ?? map.OFF_DUTY
  return (
    <span className="text-ink-600 inline-flex items-center gap-1.5 text-sm">
      <span className={cx('size-2 rounded-full', entry.colour)} aria-hidden />
      {entry.label}
    </span>
  )
}

/* -------------------------------------------------------------------------- */

/**
 * Progress through the job lifecycle.
 *
 * The API decides which steps are done, current and pending; this renders that
 * verdict rather than inferring it from a status string.
 */
export function StatusTimeline({
  steps,
  orientation = 'horizontal',
  className,
}: {
  steps: TimelineStep[]
  orientation?: 'horizontal' | 'vertical'
  className?: string
}) {
  if (!steps.length) return null

  if (orientation === 'vertical') {
    return (
      <ol className={cx('space-y-0', className)}>
        {steps.map((step, index) => (
          <li key={step.status} className="flex gap-3">
            <div className="flex flex-col items-center">
              <StepMarker state={step.state} />
              {index < steps.length - 1 ? (
                <span
                  className={cx(
                    'w-px flex-1',
                    step.state === 'done' ? 'bg-accent-400' : 'bg-ink-200',
                  )}
                  aria-hidden
                />
              ) : null}
            </div>
            <div className={cx('pb-4', index === steps.length - 1 && 'pb-0')}>
              <p
                className={cx(
                  'text-sm font-medium',
                  step.state === 'pending' ? 'text-ink-400' : 'text-ink-900',
                )}
              >
                {step.label}
              </p>
              {step.at ? (
                <p className="text-ink-500 text-xs">
                  {new Date(
                    /[zZ]|[+-]\d{2}:?\d{2}$/.test(step.at) ? step.at : `${step.at}Z`,
                  ).toLocaleString('en-IN', {
                    day: 'numeric',
                    month: 'short',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </p>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    )
  }

  return (
    <ol className={cx('flex items-start gap-1', className)}>
      {steps.map((step, index) => (
        <li key={step.status} className="flex min-w-0 flex-1 flex-col items-center gap-1.5">
          <div className="flex w-full items-center">
            <span
              className={cx(
                'h-px flex-1',
                index === 0 ? 'bg-transparent' : step.state === 'pending' ? 'bg-ink-200' : 'bg-accent-400',
              )}
              aria-hidden
            />
            <StepMarker state={step.state} />
            <span
              className={cx(
                'h-px flex-1',
                index === steps.length - 1
                  ? 'bg-transparent'
                  : steps[index + 1]?.state === 'pending'
                    ? 'bg-ink-200'
                    : 'bg-accent-400',
              )}
              aria-hidden
            />
          </div>
          <span
            className={cx(
              'text-center text-[11px] leading-tight',
              step.state === 'pending' ? 'text-ink-400' : 'text-ink-700 font-medium',
            )}
          >
            {step.label}
          </span>
        </li>
      ))}
    </ol>
  )
}

function StepMarker({ state }: { state: TimelineStep['state'] }) {
  if (state === 'done') {
    return (
      <span className="bg-accent-500 inline-flex size-5 shrink-0 items-center justify-center rounded-full text-white">
        <Check className="size-3" strokeWidth={3} aria-hidden />
        <span className="sr-only">Done</span>
      </span>
    )
  }
  if (state === 'current') {
    return (
      <span className="bg-brand-600 animate-live inline-flex size-5 shrink-0 items-center justify-center rounded-full text-white">
        <Loader2 className="size-3 animate-spin" aria-hidden />
        <span className="sr-only">In progress</span>
      </span>
    )
  }
  return (
    <span className="text-ink-300 inline-flex size-5 shrink-0 items-center justify-center">
      <Circle className="size-3.5" strokeWidth={2.5} aria-hidden />
      <span className="sr-only">Pending</span>
    </span>
  )
}

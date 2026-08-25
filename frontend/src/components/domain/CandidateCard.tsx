/** One ranked worker in the allocation list. */

import { BadgeCheck, MapPin, Timer } from 'lucide-react'

import { distanceLabel } from '../../lib/format'
import type { MatchCandidate } from '../../lib/types'
import { Avatar, Badge, Button, Card, ProgressBar, StarRating, cx } from '../ui'
import { AvailabilityDot } from './status'

export function CandidateCard({
  candidate,
  selected,
  onSelect,
  onAssign,
  assigning,
  actionLabel = 'Assign Worker',
  className,
}: {
  candidate: MatchCandidate
  selected?: boolean
  onSelect?: () => void
  onAssign?: () => void
  assigning?: boolean
  actionLabel?: string
  className?: string
}) {
  const interactive = Boolean(onSelect)

  return (
    <Card
      padded={false}
      className={cx(
        'overflow-hidden transition-all duration-200',
        selected ? 'ring-brand-500 border-brand-300 ring-2' : 'card-hover',
        className,
      )}
    >
      <div
        role={interactive ? 'button' : undefined}
        tabIndex={interactive ? 0 : undefined}
        onClick={onSelect}
        onKeyDown={
          interactive
            ? (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  onSelect?.()
                }
              }
            : undefined
        }
        className={cx('p-4 sm:p-5', interactive && 'cursor-pointer')}
      >
        <div className="flex items-start gap-3">
          <Avatar name={candidate.worker_name} size="lg" />

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <h3 className="text-ink-900 truncate text-base font-semibold">
                {candidate.worker_name}
              </h3>
              {candidate.recommended ? <Badge tone="success">Recommended</Badge> : null}
              {candidate.verification_status === 'VERIFIED' ? (
                <BadgeCheck className="text-brand-600 size-4 shrink-0" aria-label="Verified" />
              ) : null}
            </div>

            <p className="text-ink-500 mt-0.5 truncate text-sm">
              {candidate.headline}
              {candidate.zone_name ? ` · ${candidate.zone_name}` : ''}
            </p>

            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5">
              <StarRating value={candidate.rating_avg} count={candidate.rating_count} />
              <span className="text-ink-600 inline-flex items-center gap-1 text-sm">
                <MapPin className="text-ink-400 size-3.5" aria-hidden />
                {distanceLabel(candidate.distance_km)}
              </span>
              <span className="text-ink-600 inline-flex items-center gap-1 text-sm">
                <Timer className="text-ink-400 size-3.5" aria-hidden />
                {candidate.eta_minutes} min
              </span>
              <AvailabilityDot status={candidate.availability_status} />
            </div>
          </div>

          <div className="shrink-0 text-right">
            <div
              className={cx(
                'text-2xl leading-none font-semibold tabular-nums',
                candidate.score_percent >= 80
                  ? 'text-accent-700'
                  : candidate.score_percent >= 60
                    ? 'text-brand-700'
                    : 'text-ink-600',
              )}
            >
              {candidate.score_percent}%
            </div>
            <div className="text-ink-400 mt-0.5 text-[11px] tracking-wide uppercase">
              match score
            </div>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-ink-500 text-xs">Current workload</span>
              <span className="text-ink-700 text-xs font-semibold tabular-nums">
                {candidate.workload_pct}%
              </span>
            </div>
            <ProgressBar value={candidate.workload_pct} tone="auto" height="sm" />
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {candidate.matched_skills.slice(0, 3).map((skill) => (
              <Badge key={skill} tone="brand">
                {skill}
              </Badge>
            ))}
            {candidate.certifications.length ? (
              <Badge tone="outline" icon={<BadgeCheck className="size-3" aria-hidden />}>
                {candidate.certifications.length} certified
              </Badge>
            ) : null}
          </div>
        </div>
      </div>

      {onAssign ? (
        <div className="border-ink-100 bg-ink-50/60 flex items-center justify-between gap-3 border-t px-4 py-3 sm:px-5">
          <p className="text-ink-500 line-clamp-1 text-xs">{candidate.explanation}</p>
          <Button size="sm" onClick={onAssign} loading={assigning}>
            {actionLabel}
          </Button>
        </div>
      ) : null}
    </Card>
  )
}

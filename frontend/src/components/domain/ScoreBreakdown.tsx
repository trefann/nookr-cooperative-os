/**
 * "Why this worker?" - the allocation score, unpacked.
 *
 * Renders exactly what the server returned: each weighted component, the
 * reason behind it, and the final total. Nothing is computed here, so the
 * screen can never disagree with the decision the backend actually made.
 */

import { Info } from 'lucide-react'

import type { MatchCandidate, ScoreComponent } from '../../lib/types'
import { Badge, Card, ProgressBar, cx } from '../ui'

const COMPONENT_TONE: Record<ScoreComponent['key'], 'brand' | 'success' | 'warn'> = {
  skill: 'brand',
  availability: 'brand',
  location: 'brand',
  rating: 'brand',
  fairness: 'success',
}

export function ScoreBreakdown({
  candidate,
  compact = false,
  className,
}: {
  candidate: MatchCandidate
  compact?: boolean
  className?: string
}) {
  return (
    <div className={cx('space-y-3', className)}>
      {candidate.components.map((component) => (
        <div key={component.key}>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="text-ink-700 text-sm font-medium">
              {component.label}
              <span className="text-ink-400 ml-1.5 text-xs font-normal">
                weight {component.weight_percent}%
              </span>
            </span>
            <span className="text-ink-900 text-sm font-semibold tabular-nums">
              {component.percent}%
            </span>
          </div>
          <ProgressBar value={component.percent} tone={COMPONENT_TONE[component.key]} height="sm" />
          {!compact ? (
            <p className="text-ink-500 mt-1 text-xs leading-relaxed">{component.reason}</p>
          ) : null}
        </div>
      ))}

      <div className="border-ink-200 flex items-baseline justify-between border-t pt-3">
        <span className="text-ink-900 text-sm font-semibold">Final score</span>
        <span className="text-brand-700 text-2xl font-semibold tabular-nums">
          {candidate.score_percent}%
        </span>
      </div>
    </div>
  )
}

export function AllocationExplanation({
  candidate,
  className,
}: {
  candidate: MatchCandidate
  className?: string
}) {
  return (
    <Card className={cx('bg-brand-50/60 border-brand-100', className)}>
      <div className="flex items-start gap-2.5">
        <Info className="text-brand-600 mt-0.5 size-4 shrink-0" aria-hidden />
        <div className="min-w-0 space-y-2">
          <p className="text-brand-900 text-sm leading-relaxed">{candidate.explanation}</p>
          {candidate.warnings.length ? (
            <ul className="space-y-1">
              {candidate.warnings.map((warning) => (
                <li key={warning} className="text-warn-700 text-xs">
                  • {warning}
                </li>
              ))}
            </ul>
          ) : null}
          {candidate.matched_skills.length ? (
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              {candidate.matched_skills.map((skill) => (
                <Badge key={skill} tone="brand">
                  {skill}
                </Badge>
              ))}
              {candidate.missing_skills.map((skill) => (
                <Badge key={skill} tone="warn">
                  {skill} (missing)
                </Badge>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  )
}

export function WeightLegend({
  weights,
  className,
}: {
  weights: Record<string, { label: string; percent: number }>
  className?: string
}) {
  const entries = Object.entries(weights)
  return (
    <div className={cx('flex flex-wrap items-center gap-x-4 gap-y-1.5', className)}>
      <span className="text-ink-500 text-xs">Scoring weights:</span>
      {entries.map(([key, value]) => (
        <span key={key} className="text-ink-600 text-xs">
          {value.label}{' '}
          <span className="text-ink-900 font-semibold tabular-nums">{value.percent}%</span>
        </span>
      ))}
    </div>
  )
}

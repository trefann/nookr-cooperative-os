/** Star rating plus written feedback, and what the feedback changed. */

import { useState } from 'react'
import { Star } from 'lucide-react'

import { useI18n } from '../../i18n'
import type { RatingResponse } from '../../lib/types'
import { Button, Card, CheckList, InlineNotice, Textarea, cx } from '../ui'

export function RatingForm({
  onSubmit,
  submitting,
  error,
  className,
}: {
  onSubmit: (stars: number, comment: string) => void
  submitting?: boolean
  error?: string | null
  className?: string
}) {
  const { t } = useI18n()
  const [stars, setStars] = useState(0)
  const [hovered, setHovered] = useState(0)
  const [comment, setComment] = useState('')

  const shown = hovered || stars

  return (
    <Card className={cx('space-y-4', className)}>
      <div>
        <h3 className="text-ink-900 text-base font-semibold">{t('rating.title')}</h3>
        <p className="text-ink-500 mt-0.5 text-sm">{t('rating.prompt')}</p>
      </div>

      <div className="flex items-center gap-1" onMouseLeave={() => setHovered(0)}>
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            aria-label={`${value} ${t('rating.stars')}`}
            aria-pressed={stars === value}
            onMouseEnter={() => setHovered(value)}
            onFocus={() => setHovered(value)}
            onBlur={() => setHovered(0)}
            onClick={() => setStars(value)}
            className="rounded p-0.5 transition-transform hover:scale-110"
          >
            <Star
              className={cx(
                'size-8 transition-colors',
                value <= shown ? 'fill-warn-500 text-warn-500' : 'text-ink-300',
              )}
              aria-hidden
            />
          </button>
        ))}
        {stars > 0 ? (
          <span className="text-ink-600 ml-2 text-sm">
            {stars} {t('rating.stars')}
          </span>
        ) : null}
      </div>

      <Textarea
        rows={3}
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder={t('rating.placeholder')}
        maxLength={2000}
      />

      {error ? <InlineNotice tone="danger">{error}</InlineNotice> : null}

      <Button
        size="lg"
        block
        disabled={stars === 0}
        loading={submitting}
        onClick={() => onSubmit(stars, comment)}
      >
        {submitting ? t('rating.submitting') : t('rating.submit')}
      </Button>
    </Card>
  )
}

export function RatingConfirmation({
  result,
  className,
}: {
  result: RatingResponse
  className?: string
}) {
  const { t } = useI18n()
  return (
    <Card className={cx('border-accent-200 bg-accent-50/50 space-y-3', className)}>
      <div className="flex items-center gap-2">
        <span className="bg-accent-600 flex size-8 items-center justify-center rounded-full text-white">
          <Star className="size-4 fill-current" aria-hidden />
        </span>
        <h3 className="text-accent-900 text-base font-semibold">{t('rating.recorded')}</h3>
      </div>
      <p className="text-ink-600 text-sm">{t('rating.effects')}</p>
      <CheckList items={result.effects} />
      {result.worker ? (
        <p className="text-ink-600 border-accent-200 border-t pt-3 text-sm">
          {result.worker.name} now averages{' '}
          <span className="text-ink-900 font-semibold">
            {result.worker.rating_avg.toFixed(2)} ★
          </span>{' '}
          across {result.worker.rating_count} ratings.
        </p>
      ) : null}
    </Card>
  )
}

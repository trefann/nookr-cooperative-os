import { Link } from 'react-router-dom'

import { useI18n } from '../../i18n'
import { cx } from '../ui'

/** The product logotype. One mark, used in every header. */
export function BrandMark({
  compact = false,
  to = '/',
  className,
}: {
  compact?: boolean
  to?: string
  className?: string
}) {
  const { t } = useI18n()
  return (
    <Link to={to} className={cx('group flex items-center gap-2.5', className)}>
      <span
        aria-hidden
        className="bg-brand-800 flex size-8 shrink-0 items-center justify-center rounded-lg"
      >
        <svg viewBox="0 0 32 32" className="size-5" fill="none">
          <path
            d="M9 20.5c0-2.2 1.8-4 4-4h6c2.2 0 4-1.8 4-4s-1.8-4-4-4h-7"
            stroke="#ffffff"
            strokeWidth="2.6"
            strokeLinecap="round"
          />
          <circle cx="11" cy="8.5" r="2.2" fill="#43b083" />
          <circle cx="21" cy="23.5" r="2.2" fill="#43b083" />
        </svg>
      </span>
      <span className="min-w-0">
        <span className="text-ink-900 block text-[15px] leading-tight font-semibold tracking-tight">
          Nookr
        </span>
        {!compact ? (
          <span className="text-ink-400 block truncate text-[10px] leading-tight">
            {t('auth.signInSubtitle')}
          </span>
        ) : null}
      </span>
    </Link>
  )
}

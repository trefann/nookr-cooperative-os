/**
 * The shared UI kit.
 *
 * Every screen is assembled from these primitives so spacing, radius, colour
 * and states stay identical across the product.
 */

import {
  forwardRef,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react'
import { AlertCircle, Check, ChevronRight, Loader2, Inbox } from 'lucide-react'

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}

/* -------------------------------------------------------------------------- */
/* Button                                                                     */
/* -------------------------------------------------------------------------- */

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'
type ButtonSize = 'sm' | 'md' | 'lg'

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-brand-700 text-white hover:bg-brand-800 active:bg-brand-900 disabled:bg-brand-300 shadow-[var(--shadow-card)]',
  secondary:
    'bg-white text-ink-700 border border-ink-300 hover:bg-ink-50 hover:border-ink-400 active:bg-ink-100 disabled:text-ink-400',
  ghost: 'text-ink-600 hover:bg-ink-100 hover:text-ink-900 active:bg-ink-200',
  danger:
    'bg-danger-500 text-white hover:bg-danger-600 active:bg-danger-700 disabled:bg-danger-100',
  success:
    'bg-accent-600 text-white hover:bg-accent-700 active:bg-accent-800 disabled:bg-accent-200',
}

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-[13px] gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-lg',
  lg: 'h-12 px-6 text-[15px] gap-2.5 rounded-xl',
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
  iconRight?: ReactNode
  block?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    icon,
    iconRight,
    block,
    className,
    children,
    disabled,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cx(
        'inline-flex items-center justify-center font-medium whitespace-nowrap transition-colors duration-150',
        'disabled:cursor-not-allowed',
        BUTTON_VARIANTS[variant],
        BUTTON_SIZES[size],
        block && 'w-full',
        className,
      )}
      {...rest}
    >
      {loading ? <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden /> : icon}
      {children}
      {!loading && iconRight}
    </button>
  )
})

/* -------------------------------------------------------------------------- */
/* Card                                                                       */
/* -------------------------------------------------------------------------- */

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padded?: boolean
  hoverable?: boolean
}

export function Card({ padded = true, hoverable, className, children, ...rest }: CardProps) {
  return (
    <div
      className={cx('card', padded && 'p-5', hoverable && 'card-hover', className)}
      {...rest}
    >
      {children}
    </div>
  )
}

export interface SectionHeaderProps {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  eyebrow?: ReactNode
  className?: string
}

export function SectionHeader({
  title,
  description,
  action,
  eyebrow,
  className,
}: SectionHeaderProps) {
  return (
    <div className={cx('flex flex-wrap items-start justify-between gap-3', className)}>
      <div className="min-w-0">
        {eyebrow ? <div className="label mb-1">{eyebrow}</div> : null}
        <h2 className="text-lg leading-tight font-semibold">{title}</h2>
        {description ? (
          <p className="text-ink-500 mt-1 max-w-2xl text-sm">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Badge                                                                      */
/* -------------------------------------------------------------------------- */

export type BadgeTone =
  | 'neutral'
  | 'brand'
  | 'success'
  | 'warn'
  | 'danger'
  | 'info'
  | 'outline'

const BADGE_TONES: Record<BadgeTone, string> = {
  neutral: 'bg-ink-100 text-ink-700 ring-ink-200',
  brand: 'bg-brand-50 text-brand-700 ring-brand-200',
  success: 'bg-accent-50 text-accent-700 ring-accent-200',
  warn: 'bg-warn-50 text-warn-700 ring-warn-100',
  danger: 'bg-danger-50 text-danger-700 ring-danger-100',
  info: 'bg-brand-50 text-brand-600 ring-brand-100',
  outline: 'bg-white text-ink-600 ring-ink-300',
}

export function Badge({
  tone = 'neutral',
  icon,
  children,
  className,
}: {
  tone?: BadgeTone
  icon?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        BADGE_TONES[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  )
}

/* -------------------------------------------------------------------------- */
/* Stat                                                                       */
/* -------------------------------------------------------------------------- */

export interface StatProps {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  tone?: 'default' | 'brand' | 'success' | 'warn' | 'danger'
  trend?: { value: number; label?: string }
  className?: string
}

const STAT_TONES: Record<NonNullable<StatProps['tone']>, string> = {
  default: 'text-ink-900',
  brand: 'text-brand-700',
  success: 'text-accent-700',
  warn: 'text-warn-600',
  danger: 'text-danger-600',
}

export function Stat({ label, value, hint, icon, tone = 'default', trend, className }: StatProps) {
  return (
    <Card className={cx('flex flex-col gap-2', className)}>
      <div className="flex items-start justify-between gap-2">
        <span className="label">{label}</span>
        {icon ? <span className="text-ink-400 shrink-0">{icon}</span> : null}
      </div>
      <div className={cx('metric', STAT_TONES[tone])}>{value}</div>
      {trend || hint ? (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {trend ? (
            <span
              className={cx(
                'font-medium tabular-nums',
                trend.value > 0
                  ? 'text-accent-700'
                  : trend.value < 0
                    ? 'text-danger-600'
                    : 'text-ink-500',
              )}
            >
              {trend.value > 0 ? '+' : ''}
              {trend.value.toFixed(0)}% {trend.label}
            </span>
          ) : null}
          {hint ? <span className="text-ink-500">{hint}</span> : null}
        </div>
      ) : null}
    </Card>
  )
}

/* -------------------------------------------------------------------------- */
/* Progress                                                                   */
/* -------------------------------------------------------------------------- */

export function ProgressBar({
  value,
  tone = 'brand',
  showLabel = false,
  className,
  height = 'md',
}: {
  value: number
  tone?: 'brand' | 'success' | 'warn' | 'danger' | 'auto'
  showLabel?: boolean
  className?: string
  height?: 'sm' | 'md' | 'lg'
}) {
  const clamped = Math.max(0, Math.min(100, value))
  const resolved =
    tone === 'auto' ? (clamped >= 85 ? 'danger' : clamped >= 65 ? 'warn' : 'success') : tone
  const fills: Record<string, string> = {
    brand: 'bg-brand-600',
    success: 'bg-accent-500',
    warn: 'bg-warn-500',
    danger: 'bg-danger-500',
  }
  const heights = { sm: 'h-1.5', md: 'h-2', lg: 'h-3' }

  return (
    <div className={cx('flex items-center gap-2', className)}>
      <div
        className={cx('bg-ink-200 w-full overflow-hidden rounded-full', heights[height])}
        role="progressbar"
        aria-valuenow={Math.round(clamped)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={cx('h-full rounded-full transition-[width] duration-500', fills[resolved])}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showLabel ? (
        <span className="text-ink-600 w-10 shrink-0 text-right text-xs font-medium tabular-nums">
          {Math.round(clamped)}%
        </span>
      ) : null}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Form fields                                                                */
/* -------------------------------------------------------------------------- */

export interface FieldProps {
  label: string
  htmlFor?: string
  hint?: ReactNode
  error?: string | null
  required?: boolean
  children: ReactNode
  className?: string
}

export function Field({ label, htmlFor, hint, error, required, children, className }: FieldProps) {
  return (
    <div className={cx('flex flex-col gap-1.5', className)}>
      <label htmlFor={htmlFor} className="text-ink-700 text-sm font-medium">
        {label}
        {required ? <span className="text-danger-500 ml-0.5">*</span> : null}
      </label>
      {children}
      {error ? (
        <p className="text-danger-600 flex items-start gap-1 text-xs">
          <AlertCircle className="mt-px size-3.5 shrink-0" aria-hidden />
          {error}
        </p>
      ) : hint ? (
        <p className="text-ink-500 text-xs">{hint}</p>
      ) : null}
    </div>
  )
}

const CONTROL_CLASSES =
  'w-full rounded-lg border border-ink-300 bg-white px-3 text-sm text-ink-900 placeholder:text-ink-400 transition-colors hover:border-ink-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none disabled:bg-ink-50 disabled:text-ink-400'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return <input ref={ref} className={cx(CONTROL_CLASSES, 'h-10', className)} {...rest} />
  },
)

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...rest }, ref) {
    return <textarea ref={ref} className={cx(CONTROL_CLASSES, 'py-2.5 leading-relaxed', className)} {...rest} />
  },
)

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...rest }, ref) {
    return (
      <select ref={ref} className={cx(CONTROL_CLASSES, 'h-10 pr-8', className)} {...rest}>
        {children}
      </select>
    )
  },
)

/* -------------------------------------------------------------------------- */
/* Feedback states                                                            */
/* -------------------------------------------------------------------------- */

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return (
    <span className={cx('text-ink-400 inline-flex items-center gap-2', className)} role="status">
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label ? <span className="text-sm">{label}</span> : <span className="sr-only">Loading</span>}
    </span>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('bg-ink-200/70 animate-pulse rounded-md', className)} />
}

export function LoadingBlock({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cx('space-y-3', className)} aria-hidden>
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className={cx('h-4', index === 0 ? 'w-2/5' : 'w-full')} />
      ))}
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
  retryLabel = 'Try again',
  className,
}: {
  message: string
  onRetry?: () => void
  retryLabel?: string
  className?: string
}) {
  return (
    <div
      role="alert"
      className={cx(
        'border-danger-100 bg-danger-50 flex flex-col items-start gap-3 rounded-[var(--radius-card)] border p-5 sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="text-danger-500 mt-0.5 size-5 shrink-0" aria-hidden />
        <p className="text-danger-700 text-sm">{message}</p>
      </div>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  )
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cx(
        'border-ink-200 flex flex-col items-center justify-center gap-3 rounded-[var(--radius-card)] border border-dashed px-6 py-10 text-center',
        className,
      )}
    >
      <span className="text-ink-300">{icon ?? <Inbox className="size-8" aria-hidden />}</span>
      <div>
        <p className="text-ink-800 text-sm font-medium">{title}</p>
        {description ? <p className="text-ink-500 mt-1 text-sm">{description}</p> : null}
      </div>
      {action}
    </div>
  )
}

export function InlineNotice({
  tone = 'info',
  title,
  children,
  icon,
  className,
}: {
  tone?: 'info' | 'success' | 'warn' | 'danger' | 'neutral'
  title?: ReactNode
  children?: ReactNode
  icon?: ReactNode
  className?: string
}) {
  const tones = {
    info: 'bg-brand-50 border-brand-100 text-brand-800',
    success: 'bg-accent-50 border-accent-100 text-accent-800',
    warn: 'bg-warn-50 border-warn-100 text-warn-700',
    danger: 'bg-danger-50 border-danger-100 text-danger-700',
    neutral: 'bg-ink-50 border-ink-200 text-ink-700',
  }
  return (
    <div className={cx('rounded-xl border p-3.5 text-sm', tones[tone], className)}>
      <div className="flex items-start gap-2.5">
        {icon ? <span className="mt-0.5 shrink-0">{icon}</span> : null}
        <div className="min-w-0 flex-1">
          {title ? <p className="font-semibold">{title}</p> : null}
          {children ? <div className={cx(Boolean(title) && 'mt-1', 'leading-relaxed')}>{children}</div> : null}
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/* Table                                                                      */
/* -------------------------------------------------------------------------- */

export function TableWrap({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx('scroll-x', className)}>
      <div className="min-w-full align-middle">{children}</div>
    </div>
  )
}

export function Th({
  children,
  align = 'left',
  className,
}: {
  children?: ReactNode
  align?: 'left' | 'right' | 'center'
  className?: string
}) {
  return (
    <th
      scope="col"
      className={cx(
        'text-ink-500 border-ink-200 border-b px-3 py-2.5 text-xs font-semibold tracking-wide whitespace-nowrap uppercase',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        align === 'left' && 'text-left',
        className,
      )}
    >
      {children}
    </th>
  )
}

export function Td({
  children,
  align = 'left',
  className,
}: {
  children?: ReactNode
  align?: 'left' | 'right' | 'center'
  className?: string
}) {
  return (
    <td
      className={cx(
        'border-ink-100 border-b px-3 py-2.5 text-sm',
        align === 'right' && 'text-right tabular-nums',
        align === 'center' && 'text-center',
        className,
      )}
    >
      {children}
    </td>
  )
}

/* -------------------------------------------------------------------------- */
/* Misc                                                                       */
/* -------------------------------------------------------------------------- */

export function Avatar({
  name,
  size = 'md',
  tone = 'brand',
  className,
}: {
  name: string
  size?: 'sm' | 'md' | 'lg'
  tone?: 'brand' | 'accent' | 'ink'
  className?: string
}) {
  const letters = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
  const sizes = {
    sm: 'size-7 text-[11px]',
    md: 'size-9 text-xs',
    lg: 'size-12 text-sm',
  }
  const tones = {
    brand: 'bg-brand-100 text-brand-800',
    accent: 'bg-accent-100 text-accent-800',
    ink: 'bg-ink-200 text-ink-700',
  }
  return (
    <span
      aria-hidden
      className={cx(
        'inline-flex shrink-0 items-center justify-center rounded-full font-semibold',
        sizes[size],
        tones[tone],
        className,
      )}
    >
      {letters || '?'}
    </span>
  )
}

export function StarRating({
  value,
  count,
  size = 'sm',
  className,
}: {
  value: number
  count?: number
  size?: 'sm' | 'md'
  className?: string
}) {
  return (
    <span className={cx('text-ink-700 inline-flex items-center gap-1', className)}>
      <span className={cx('text-warn-500', size === 'md' ? 'text-base' : 'text-sm')} aria-hidden>
        ★
      </span>
      <span className={cx('font-medium tabular-nums', size === 'md' ? 'text-base' : 'text-sm')}>
        {value.toFixed(1)}
      </span>
      {count !== undefined ? (
        <span className="text-ink-400 text-xs">({count})</span>
      ) : null}
      <span className="sr-only">out of 5</span>
    </span>
  )
}

export function CheckList({ items, className }: { items: string[]; className?: string }) {
  return (
    <ul className={cx('space-y-1.5', className)}>
      {items.map((item) => (
        <li key={item} className="text-ink-700 flex items-start gap-2 text-sm">
          <Check className="text-accent-600 mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

export function LinkRow({
  children,
  onClick,
  className,
}: {
  children: ReactNode
  onClick?: () => void
  className?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'hover:bg-ink-50 flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition-colors',
        className,
      )}
    >
      <span className="min-w-0 flex-1">{children}</span>
      <ChevronRight className="text-ink-400 size-4 shrink-0" aria-hidden />
    </button>
  )
}

/** Shared formatting so numbers, money and dates look the same everywhere. */

const RUPEE = '₹'

export function currency(value: number | null | undefined, withDecimals = false): string {
  if (value === null || value === undefined || Number.isNaN(value)) return `${RUPEE}0`
  return `${RUPEE}${value.toLocaleString('en-IN', {
    minimumFractionDigits: withDecimals ? 2 : 0,
    maximumFractionDigits: withDecimals ? 2 : 0,
  })}`
}

export function compactCurrency(value: number | null | undefined): string {
  if (!value) return `${RUPEE}0`
  if (value >= 10_000_000) return `${RUPEE}${(value / 10_000_000).toFixed(1)}Cr`
  if (value >= 100_000) return `${RUPEE}${(value / 100_000).toFixed(1)}L`
  if (value >= 1_000) return `${RUPEE}${(value / 1_000).toFixed(1)}k`
  return `${RUPEE}${Math.round(value)}`
}

export function percent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${value.toFixed(digits)}%`
}

export function signedPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(digits)}%`
}

function parse(value: string | null | undefined): Date | null {
  if (!value) return null
  // SQLite hands back naive timestamps; everything the API writes is UTC.
  const normalised = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`
  const date = new Date(normalised)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value: string | null | undefined): string {
  const date = parse(value)
  if (!date) return '-'
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatTime(value: string | null | undefined): string {
  const date = parse(value)
  if (!date) return '-'
  return date.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })
}

export function formatDateTime(value: string | null | undefined): string {
  const date = parse(value)
  if (!date) return '-'
  return `${formatDate(value)}, ${formatTime(value)}`
}

export function formatDayLabel(value: string | null | undefined): string {
  const date = parse(value)
  if (!date) return '-'
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export function relativeTime(value: string | null | undefined): string {
  const date = parse(value)
  if (!date) return '-'
  const diffMs = date.getTime() - Date.now()
  const minutes = Math.round(diffMs / 60000)
  const abs = Math.abs(minutes)
  if (abs < 1) return 'just now'
  if (abs < 60) return minutes < 0 ? `${abs}m ago` : `in ${abs}m`
  const hours = Math.round(abs / 60)
  if (hours < 24) return minutes < 0 ? `${hours}h ago` : `in ${hours}h`
  const days = Math.round(hours / 24)
  if (days < 7) return minutes < 0 ? `${days}d ago` : `in ${days}d`
  return formatDate(value)
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function distanceLabel(km: number | null | undefined): string {
  if (km === null || km === undefined) return '-'
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`
}

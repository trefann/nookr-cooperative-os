/** All bookings visible to the signed-in role, with filters. */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarDays } from 'lucide-react'

import { useAuth } from '../auth/AuthContext'
import { BookingCard } from '../components/domain/BookingCard'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingBlock,
  SectionHeader,
  Select,
  cx,
} from '../components/ui'
import { useI18n } from '../i18n'
import * as endpoints from '../lib/endpoints'
import type { BookingStatus } from '../lib/types'
import { useAsync } from '../lib/useAsync'

const STATUS_FILTERS: { value: BookingStatus | 'ALL' | 'ACTIVE'; label: string }[] = [
  { value: 'ACTIVE', label: 'Active' },
  { value: 'ALL', label: 'All' },
  { value: 'REQUESTED', label: 'Awaiting allocation' },
  { value: 'ASSIGNED', label: 'Assigned' },
  { value: 'IN_PROGRESS', label: 'In progress' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'PAID', label: 'Paid' },
  { value: 'RATED', label: 'Rated' },
  { value: 'CANCELLED', label: 'Cancelled' },
]

export default function BookingsPage() {
  const { t } = useI18n()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [filter, setFilter] = useState<BookingStatus | 'ALL' | 'ACTIVE'>('ACTIVE')
  const [serviceId, setServiceId] = useState('')

  const services = useAsync(() => endpoints.getServices(), [])
  const bookings = useAsync(
    () =>
      endpoints.getBookings({
        status: filter !== 'ALL' && filter !== 'ACTIVE' ? filter : undefined,
        active_only: filter === 'ACTIVE' || undefined,
        service_id: serviceId ? Number(serviceId) : undefined,
        limit: 100,
      }),
    [filter, serviceId],
  )

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow={t('nav.bookings')}
        title={user?.role === 'CUSTOMER' ? 'Your service requests' : 'Cooperative bookings'}
        description={
          user?.role === 'WORKER'
            ? 'Your allocated jobs, plus open work the cooperative has not yet assigned.'
            : undefined
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="border-ink-300 flex flex-wrap gap-0.5 rounded-lg border bg-white p-0.5">
          {STATUS_FILTERS.slice(0, 4).map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setFilter(option.value)}
              className={cx(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                filter === option.value ? 'bg-brand-700 text-white' : 'text-ink-600 hover:bg-ink-100',
              )}
            >
              {option.label}
            </button>
          ))}
        </div>

        <Select
          value={filter}
          onChange={(event) => setFilter(event.target.value as BookingStatus | 'ALL' | 'ACTIVE')}
          aria-label={t('booking.status')}
          className="w-48"
        >
          {STATUS_FILTERS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>

        <Select
          value={serviceId}
          onChange={(event) => setServiceId(event.target.value)}
          aria-label={t('workforce.service')}
          className="w-48"
        >
          <option value="">{t('common.all')} services</option>
          {(services.data ?? []).map((service) => (
            <option key={service.id} value={service.id}>
              {service.name}
            </option>
          ))}
        </Select>

        <span className="text-ink-500 ml-auto text-sm">
          {bookings.data?.length ?? 0} {t('common.jobs')}
        </span>
      </div>

      {bookings.loading && !bookings.data ? (
        <Card>
          <LoadingBlock rows={5} />
        </Card>
      ) : bookings.error ? (
        <ErrorState message={bookings.error} onRetry={bookings.reload} />
      ) : bookings.data?.length ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {bookings.data.map((booking) => (
            <BookingCard
              key={booking.id}
              booking={booking}
              showCustomer={user?.role !== 'CUSTOMER'}
              onOpen={() => navigate(`/bookings/${booking.id}`)}
              actions={
                booking.status === 'REQUESTED' && user?.role !== 'WORKER' ? (
                  <Button
                    size="sm"
                    onClick={(event) => {
                      event.stopPropagation()
                      navigate(`/matching?booking=${booking.id}`)
                    }}
                  >
                    {t('ai.findWorker')}
                  </Button>
                ) : undefined
              }
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title={t('common.noResults')}
          description="Nothing matches these filters."
          icon={<CalendarDays className="size-8" aria-hidden />}
          action={
            <Button variant="secondary" size="sm" onClick={() => setFilter('ALL')}>
              Show all
            </Button>
          }
        />
      )}
    </div>
  )
}

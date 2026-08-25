/** The cooperative's service catalogue and the members who cover each service. */

import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Brush,
  Droplet,
  Hammer,
  Leaf,
  Search,
  Settings,
  Sparkles,
  Wrench,
  Zap,
} from 'lucide-react'
import type { ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'
import { AvailabilityDot } from '../components/domain/status'
import {
  Avatar,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingBlock,
  ProgressBar,
  SectionHeader,
  Select,
  StarRating,
  cx,
} from '../components/ui'
import { useI18n } from '../i18n'
import * as endpoints from '../lib/endpoints'
import { currency, distanceLabel } from '../lib/format'
import { useAsync } from '../lib/useAsync'

const ICONS: Record<string, ReactNode> = {
  droplet: <Droplet className="size-5" aria-hidden />,
  zap: <Zap className="size-5" aria-hidden />,
  hammer: <Hammer className="size-5" aria-hidden />,
  brush: <Brush className="size-5" aria-hidden />,
  sparkles: <Sparkles className="size-5" aria-hidden />,
  leaf: <Leaf className="size-5" aria-hidden />,
  settings: <Settings className="size-5" aria-hidden />,
}

export default function ServicesPage() {
  const { t } = useI18n()
  const { user } = useAuth()
  const navigate = useNavigate()

  const services = useAsync(() => endpoints.getServices(), [])
  const zones = useAsync(() => endpoints.getZones(), [])

  const [selectedService, setSelectedService] = useState<number | null>(null)
  const [zoneId, setZoneId] = useState<string>('')
  const [search, setSearch] = useState('')

  const workers = useAsync(
    () =>
      endpoints.getWorkers({
        service_id: selectedService ?? undefined,
        zone_id: zoneId ? Number(zoneId) : undefined,
        search: search.trim() || undefined,
        lat: user?.lat,
        lng: user?.lng,
        limit: 60,
      }),
    [selectedService, zoneId, search],
  )

  const activeService = useMemo(
    () => services.data?.find((service) => service.id === selectedService) ?? null,
    [services.data, selectedService],
  )

  return (
    <div className="space-y-8">
      <SectionHeader
        eyebrow={t('nav.services')}
        title="Services the cooperative offers"
        description="Each service, what it typically costs, the skills it needs, and the members who cover it."
      />

      {services.loading && !services.data ? (
        <Card>
          <LoadingBlock rows={4} />
        </Card>
      ) : services.error ? (
        <ErrorState message={services.error} onRetry={services.reload} />
      ) : (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {(services.data ?? []).map((service) => {
            const active = service.id === selectedService
            return (
              <Card
                key={service.id}
                hoverable
                className={cx('flex flex-col gap-3', active && 'ring-brand-500 ring-2')}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="bg-brand-50 text-brand-700 flex size-10 shrink-0 items-center justify-center rounded-xl">
                    {ICONS[service.icon] ?? <Wrench className="size-5" aria-hidden />}
                  </span>
                  {service.emergency_supported ? <Badge tone="warn">Emergency</Badge> : null}
                </div>
                <div>
                  <h3 className="text-ink-900 font-semibold">{service.name}</h3>
                  <p className="text-ink-500 mt-1 text-sm leading-relaxed">
                    {service.description}
                  </p>
                </div>
                <dl className="text-ink-600 flex gap-4 text-xs">
                  <div>
                    <dt className="text-ink-400">From</dt>
                    <dd className="text-ink-900 font-semibold tabular-nums">
                      {currency(service.base_price)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-ink-400">Typical</dt>
                    <dd className="text-ink-900 font-semibold">
                      {service.avg_duration_minutes} min
                    </dd>
                  </div>
                </dl>
                <div className="flex flex-wrap gap-1.5">
                  {service.skills.slice(0, 3).map((skill) => (
                    <Badge key={skill.id} tone={skill.is_emerging ? 'success' : 'neutral'}>
                      {skill.name}
                    </Badge>
                  ))}
                  {service.skills.length > 3 ? (
                    <Badge tone="outline">+{service.skills.length - 3}</Badge>
                  ) : null}
                </div>
                <div className="mt-auto flex gap-2 pt-1">
                  <Button
                    size="sm"
                    variant={active ? 'primary' : 'secondary'}
                    onClick={() => setSelectedService(active ? null : service.id)}
                    className="flex-1"
                  >
                    {active ? 'Showing members' : 'See members'}
                  </Button>
                  {user?.role === 'CUSTOMER' ? (
                    <Button size="sm" variant="ghost" onClick={() => navigate('/customer')}>
                      Request
                    </Button>
                  ) : null}
                </div>
              </Card>
            )
          })}
        </section>
      )}

      {/* Members */}
      <section className="space-y-4">
        <SectionHeader
          title={activeService ? `${activeService.name} members` : 'All members'}
          description="Ranked by rating, with current workload shown so allocation stays transparent."
          action={
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search
                  className="text-ink-400 pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2"
                  aria-hidden
                />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder={t('common.search')}
                  className="w-44 pl-8"
                  aria-label={t('common.search')}
                />
              </div>
              <Select
                value={zoneId}
                onChange={(event) => setZoneId(event.target.value)}
                aria-label={t('auth.zone')}
                className="w-44"
              >
                <option value="">{t('common.all')} zones</option>
                {(zones.data ?? []).map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </Select>
            </div>
          }
        />

        {workers.loading && !workers.data ? (
          <Card>
            <LoadingBlock rows={5} />
          </Card>
        ) : workers.error ? (
          <ErrorState message={workers.error} onRetry={workers.reload} />
        ) : workers.data?.length ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {workers.data.map((worker) => (
              <Card key={worker.id} hoverable className="space-y-3">
                <div className="flex items-start gap-3">
                  <Avatar name={worker.name} />
                  <div className="min-w-0 flex-1">
                    <p className="text-ink-900 truncate font-semibold">{worker.name}</p>
                    <p className="text-ink-500 truncate text-sm">
                      {worker.headline} · {worker.zone_name}
                    </p>
                  </div>
                  {worker.verification_status === 'VERIFIED' ? (
                    <Badge tone="brand">{t('matching.verified')}</Badge>
                  ) : null}
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <StarRating value={worker.rating_avg} count={worker.rating_count} />
                  <AvailabilityDot status={worker.availability_status} />
                  {worker.distance_km !== null ? (
                    <span className="text-ink-500 text-sm">
                      {distanceLabel(worker.distance_km)}
                    </span>
                  ) : null}
                </div>

                <div>
                  <div className="mb-1 flex items-baseline justify-between text-xs">
                    <span className="text-ink-500">{t('matching.workload')}</span>
                    <span className="text-ink-700 font-semibold tabular-nums">
                      {worker.workload_pct}%
                    </span>
                  </div>
                  <ProgressBar value={worker.workload_pct} tone="auto" height="sm" />
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {worker.skills.slice(0, 3).map((skill) => (
                    <Badge key={skill.skill_id} tone={skill.is_emerging ? 'success' : 'neutral'}>
                      {skill.name}
                    </Badge>
                  ))}
                </div>

                <dl className="text-ink-500 border-ink-100 flex justify-between border-t pt-2 text-xs">
                  <div>
                    <dt>{t('worker.completedJobs')}</dt>
                    <dd className="text-ink-900 font-semibold tabular-nums">
                      {worker.jobs_completed}
                    </dd>
                  </div>
                  <div className="text-right">
                    <dt>{t('worker.certifications')}</dt>
                    <dd className="text-ink-900 font-semibold tabular-nums">
                      {worker.certification_count}
                    </dd>
                  </div>
                </dl>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            title={t('common.noResults')}
            description="Try a different zone or clear the search."
          />
        )}
      </section>
    </div>
  )
}

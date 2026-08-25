/**
 * Customer home.
 *
 * The primary action is describing a need in plain language; everything else
 * on the page is the state of work already in flight.
 */

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  CalendarClock,
  History,
  Mic,
  MicOff,
  Receipt,
  Sparkles,
  Star,
} from 'lucide-react'

import { useAuth } from '../auth/AuthContext'
import { BookingCard } from '../components/domain/BookingCard'
import { UnderstandingPanel } from '../components/domain/UnderstandingPanel'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  InlineNotice,
  LoadingBlock,
  SectionHeader,
  Stat,
  Textarea,
  cx,
} from '../components/ui'
import { useDemo } from '../demo/DemoContext'
import { useI18n } from '../i18n'
import { errorMessage } from '../lib/api'
import * as endpoints from '../lib/endpoints'
import { currency } from '../lib/format'
import { isSpeechSupported, startDictation, type DictationSession } from '../lib/speech'
import type { UnderstandResponse } from '../lib/types'
import { useAsync } from '../lib/useAsync'

export default function CustomerPage() {
  const { user } = useAuth()
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const demo = useDemo()

  const summary = useAsync(() => endpoints.getCustomerSummary(), [])
  const services = useAsync(() => endpoints.getServices(), [])
  const zones = useAsync(() => endpoints.getZones(), [])

  const [text, setText] = useState('')
  const [isEmergency, setIsEmergency] = useState(false)
  const [understanding, setUnderstanding] = useState<UnderstandResponse | null>(null)
  const [serviceId, setServiceId] = useState<number | null>(null)
  const [zoneId, setZoneId] = useState<number | null>(null)
  const [analysing, setAnalysing] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [listening, setListening] = useState(false)
  const [speechError, setSpeechError] = useState<string | null>(null)
  const sessionRef = useRef<DictationSession | null>(null)
  const baseTextRef = useRef('')
  const speechSupported = isSpeechSupported()

  useEffect(() => {
    if (user?.zone_id && zoneId === null) setZoneId(user.zone_id)
  }, [user?.zone_id, zoneId])

  useEffect(() => () => sessionRef.current?.stop(), [])

  const toggleDictation = () => {
    if (listening) {
      sessionRef.current?.stop()
      sessionRef.current = null
      setListening(false)
      return
    }
    setSpeechError(null)
    baseTextRef.current = text ? `${text.trim()} ` : ''
    const session = startDictation(locale, {
      onTranscript: (transcript, isFinal) => {
        setText(`${baseTextRef.current}${transcript}`)
        if (isFinal) baseTextRef.current = `${baseTextRef.current}${transcript} `
      },
      onError: (message) => {
        setSpeechError(message)
        setListening(false)
      },
      onEnd: () => {
        sessionRef.current = null
        setListening(false)
      },
    })
    if (session) {
      sessionRef.current = session
      setListening(true)
    } else {
      setSpeechError(t('customer.voiceUnsupported'))
    }
  }

  const analyse = async () => {
    const value = text.trim()
    if (value.length < 3) {
      setError('Please describe the problem in a few more words.')
      return
    }
    sessionRef.current?.stop()
    setAnalysing(true)
    setError(null)
    try {
      const result = await endpoints.understandRequest(value, zoneId)
      setUnderstanding(result)
      setServiceId(result.service?.id ?? null)
      if (result.zone?.id) setZoneId(result.zone.id)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setAnalysing(false)
    }
  }

  const confirm = async () => {
    if (!understanding) return
    setCreating(true)
    setError(null)
    try {
      const skillIds = understanding.skills.map((skill) => skill.id)
      const booking = await endpoints.createBooking({
        raw_request: text.trim(),
        service_id: serviceId,
        zone_id: zoneId,
        skill_ids: serviceId === understanding.service?.id ? skillIds : [],
        is_emergency: isEmergency,
        workers_required: understanding.understanding.workers_required,
      })
      setUnderstanding(null)
      setText('')
      setIsEmergency(false)
      void demo.refresh()
      navigate(`/matching?booking=${booking.id}`)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setCreating(false)
    }
  }

  const useScenarioText = async () => {
    const scenario = await demo.startScenario()
    if (scenario) {
      setText(scenario)
      setUnderstanding(null)
    }
  }

  const data = summary.data

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">
            {t('customer.welcome')}
            {user ? `, ${user.full_name.split(' ')[0]}` : ''}
          </h1>
          <p className="text-ink-500 mt-1 text-sm">{t('brand.tagline')}</p>
        </div>
        {demo.enabled ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={useScenarioText}
            icon={<Sparkles className="size-4" aria-hidden />}
          >
            {t('demo.start')}
          </Button>
        ) : null}
      </header>

      {/* Primary action */}
      {understanding ? (
        <UnderstandingPanel
          result={understanding}
          services={services.data ?? []}
          zones={zones.data ?? []}
          serviceId={serviceId}
          zoneId={zoneId}
          onServiceChange={setServiceId}
          onZoneChange={setZoneId}
          onConfirm={confirm}
          onEdit={() => setUnderstanding(null)}
          confirming={creating}
        />
      ) : (
        <Card className={cx('space-y-4', isEmergency && 'border-danger-200 bg-danger-50/30')}>
          <SectionHeader
            eyebrow={t('nav.customer')}
            title={t('customer.describeCta')}
            description={t('customer.describeHelp')}
          />

          <div className="relative">
            <Textarea
              rows={3}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder={t('customer.placeholder')}
              maxLength={2000}
              className="pr-12"
              aria-label={t('customer.describeCta')}
            />
            {speechSupported ? (
              <button
                type="button"
                onClick={toggleDictation}
                aria-label={listening ? t('customer.stopVoice') : t('customer.useVoice')}
                aria-pressed={listening}
                className={cx(
                  'absolute top-2.5 right-2.5 rounded-lg p-2 transition-colors',
                  listening
                    ? 'bg-danger-500 animate-live text-white'
                    : 'text-ink-500 hover:bg-ink-100 hover:text-ink-800',
                )}
              >
                {listening ? <MicOff className="size-4" aria-hidden /> : <Mic className="size-4" aria-hidden />}
              </button>
            ) : null}
          </div>

          {listening ? (
            <p className="text-danger-600 flex items-center gap-2 text-sm">
              <span className="bg-danger-500 size-2 animate-pulse rounded-full" aria-hidden />
              {t('customer.listening')}…
            </p>
          ) : null}
          {speechError ? <InlineNotice tone="warn">{speechError}</InlineNotice> : null}
          {!speechSupported ? (
            <p className="text-ink-400 text-xs">{t('customer.voiceUnsupported')}</p>
          ) : null}

          <label className="flex cursor-pointer items-start gap-2.5">
            <input
              type="checkbox"
              checked={isEmergency}
              onChange={(event) => setIsEmergency(event.target.checked)}
              className="text-danger-600 focus:ring-danger-200 border-ink-300 mt-0.5 size-4 rounded"
            />
            <span>
              <span className="text-ink-900 flex items-center gap-1.5 text-sm font-medium">
                <AlertTriangle className="text-danger-500 size-4" aria-hidden />
                {t('customer.emergency')}
              </span>
              <span className="text-ink-500 block text-xs">{t('customer.emergencyHelp')}</span>
            </span>
          </label>

          {error ? <InlineNotice tone="danger">{error}</InlineNotice> : null}

          <Button
            size="lg"
            block
            onClick={analyse}
            loading={analysing}
            disabled={text.trim().length < 3}
            iconRight={<ArrowRight className="size-4" aria-hidden />}
          >
            {analysing ? t('customer.analysing') : t('customer.analyse')}
          </Button>
        </Card>
      )}

      {summary.loading && !data ? (
        <Card>
          <LoadingBlock rows={4} />
        </Card>
      ) : summary.error ? (
        <ErrorState message={summary.error} onRetry={summary.reload} />
      ) : data ? (
        <>
          {/* Needs attention */}
          {data.needs_attention.length ? (
            <section className="space-y-3">
              <SectionHeader
                title={t('customer.needsAttention')}
                description="These jobs are waiting on you."
              />
              <div className="grid gap-3 sm:grid-cols-2">
                {data.needs_attention.map((booking) => (
                  <BookingCard
                    key={booking.id}
                    booking={booking}
                    highlight
                    onOpen={() => navigate(`/bookings/${booking.id}`)}
                    actions={
                      <Button
                        size="sm"
                        onClick={(event) => {
                          event.stopPropagation()
                          navigate(
                            booking.status === 'REQUESTED'
                              ? `/matching?booking=${booking.id}`
                              : `/bookings/${booking.id}`,
                          )
                        }}
                      >
                        {booking.status === 'REQUESTED'
                          ? t('ai.findWorker')
                          : booking.status === 'COMPLETED'
                            ? t('payment.payNow')
                            : t('rating.submit')}
                      </Button>
                    }
                  />
                ))}
              </div>
            </section>
          ) : null}

          {/* KPIs */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label={t('customer.activeService')}
              value={data.counts.active}
              hint={`${data.counts.total} requests in total`}
              icon={<CalendarClock className="size-4" aria-hidden />}
              tone="brand"
            />
            <Stat
              label={t('customer.totalSpent')}
              value={currency(data.spend.total)}
              hint={`${data.spend.payments} payments`}
              icon={<Receipt className="size-4" aria-hidden />}
            />
            <Stat
              label={t('customer.welfareContributed')}
              value={currency(data.spend.welfare_contributed)}
              hint="To the cooperative welfare fund"
              icon={<Sparkles className="size-4" aria-hidden />}
              tone="success"
            />
            <Stat
              label={t('customer.ratings')}
              value={data.ratings.average ? `${data.ratings.average.toFixed(1)} ★` : '-'}
              hint={`${data.ratings.given} ratings given`}
              icon={<Star className="size-4" aria-hidden />}
            />
          </section>

          {/* Active service */}
          {data.active_service ? (
            <section className="space-y-3">
              <SectionHeader title={t('customer.activeService')} />
              <BookingCard
                booking={data.active_service}
                onOpen={() => navigate(`/bookings/${data.active_service!.id}`)}
                actions={
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={(event) => {
                      event.stopPropagation()
                      navigate(`/bookings/${data.active_service!.id}`)
                    }}
                  >
                    {t('customer.trackService')}
                  </Button>
                }
              />
            </section>
          ) : null}

          {/* Upcoming */}
          <section className="space-y-3">
            <SectionHeader
              title={t('customer.upcoming')}
              action={
                <Button variant="ghost" size="sm" onClick={() => navigate('/bookings')}>
                  {t('common.viewAll')}
                </Button>
              }
            />
            {data.upcoming.length ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {data.upcoming.map((booking) => (
                  <BookingCard
                    key={booking.id}
                    booking={booking}
                    onOpen={() => navigate(`/bookings/${booking.id}`)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title={t('customer.noBookings')}
                description={t('customer.describeHelp')}
                icon={<CalendarClock className="size-8" aria-hidden />}
              />
            )}
          </section>

          {/* History and payments */}
          <section className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-3">
              <SectionHeader title={t('customer.previous')} />
              {data.previous.length ? (
                <div className="space-y-3">
                  {data.previous.slice(0, 4).map((booking) => (
                    <BookingCard
                      key={booking.id}
                      booking={booking}
                      onOpen={() => navigate(`/bookings/${booking.id}`)}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState
                  title={t('common.noResults')}
                  icon={<History className="size-8" aria-hidden />}
                />
              )}
            </div>

            <div className="space-y-3">
              <SectionHeader title={t('customer.payments')} />
              <Card padded={false}>
                {data.payments.length ? (
                  <ul className="divide-ink-100 divide-y">
                    {data.payments.map((payment) => (
                      <li key={payment.id} className="flex items-center justify-between gap-3 px-4 py-3">
                        <div className="min-w-0">
                          <p className="text-ink-900 font-mono text-sm">{payment.invoice_number}</p>
                          <p className="text-ink-500 text-xs">
                            {payment.method.replace('_', ' ').toLowerCase()} ·{' '}
                            {t('payment.welfareContribution')} {currency(payment.welfare_amount)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-ink-900 text-sm font-semibold tabular-nums">
                            {currency(payment.amount)}
                          </span>
                          <Badge tone="success">{payment.status}</Badge>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-4">
                    <EmptyState
                      title={t('common.noResults')}
                      icon={<Receipt className="size-8" aria-hidden />}
                    />
                  </div>
                )}
              </Card>
            </div>
          </section>
        </>
      ) : null}
    </div>
  )
}

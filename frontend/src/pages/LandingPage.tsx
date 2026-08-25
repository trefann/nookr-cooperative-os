/** Public entry point: what the product is, and one click into the demo. */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BrainCircuit,
  GraduationCap,
  HeartHandshake,
  Scale,
  ShieldCheck,
  Target,
  TrendingUp,
} from 'lucide-react'

import { homeRouteFor, useAuth } from '../auth/AuthContext'
import { BrandMark } from '../components/layout/BrandMark'
import { LanguageSelect } from '../components/layout/LanguageSelect'
import { Badge, Button, Card, InlineNotice, cx } from '../components/ui'
import { useDemo } from '../demo/DemoContext'
import { useI18n } from '../i18n'
import { errorMessage } from '../lib/api'
import type { Role } from '../lib/types'

const PIPELINE = [
  'Customer need',
  'AI service understanding',
  'Skill identification',
  'Demand & workforce analysis',
  'Fair worker allocation',
  'Service execution',
  'Cooperative intelligence',
]

const CAPABILITIES = [
  {
    icon: <BrainCircuit className="size-5" aria-hidden />,
    title: 'Understands the request',
    body: 'Plain language becomes a service, a problem, the skills it needs and when it has to happen.',
  },
  {
    icon: <Scale className="size-5" aria-hidden />,
    title: 'Allocates work fairly',
    body: 'Skill, availability, distance, rating and current workload, each weighted and explained.',
  },
  {
    icon: <TrendingUp className="size-5" aria-hidden />,
    title: 'Forecasts demand',
    body: 'Weeks of cooperative history projected forward, so staffing decisions are made early.',
  },
  {
    icon: <GraduationCap className="size-5" aria-hidden />,
    title: 'Finds skill gaps',
    body: 'Where demand is outrunning certified capacity, and who should be trained next.',
  },
  {
    icon: <HeartHandshake className="size-5" aria-hidden />,
    title: 'Tracks welfare',
    body: 'Every job contributes to a welfare fund, insurance cover and training credits.',
  },
  {
    icon: <ShieldCheck className="size-5" aria-hidden />,
    title: 'Keeps the cooperative in control',
    body: 'The workforce data, the allocation policy and the intelligence belong to the cooperative.',
  },
]

const PERSONAS: { role: Role; label: string; description: string }[] = [
  {
    role: 'CUSTOMER',
    label: 'Customer Demo',
    description: 'Describe a problem and follow it through to payment and feedback.',
  },
  {
    role: 'WORKER',
    label: 'Worker Demo',
    description: 'Kumar Selvan, plumber. Accept work, run it, see earnings and welfare.',
  },
  {
    role: 'ADMIN',
    label: 'Cooperative Admin Demo',
    description: 'The intelligence dashboard, forecasting, planning and skill gaps.',
  },
]

export default function LandingPage() {
  const { signInAsDemo } = useAuth()
  const { setEnabled } = useDemo()
  const { t } = useI18n()
  const navigate = useNavigate()
  const [pending, setPending] = useState<Role | null>(null)
  const [error, setError] = useState<string | null>(null)

  const enterDemo = async (role: Role) => {
    setPending(role)
    setError(null)
    try {
      setEnabled(true)
      const user = await signInAsDemo(role)
      navigate(homeRouteFor(user.role))
    } catch (caught) {
      setError(errorMessage(caught))
      setPending(null)
    }
  }

  return (
    <div className="bg-white">
      <header className="border-ink-200 border-b">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-4 py-3.5 sm:px-6">
          <BrandMark />
          <div className="flex items-center gap-2">
            <LanguageSelect />
            <Link to="/login">
              <Button variant="ghost" size="sm">
                {t('auth.signIn')}
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="border-ink-200 border-b bg-gradient-to-b from-white to-brand-50/40">
          <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6 sm:py-20">
            <div className="grid gap-10 lg:grid-cols-[1.15fr_1fr] lg:items-center">
              <div>
                <Badge tone="brand">Smart India Hackathon 2026 · SIH26089</Badge>
                <h1 className="mt-4 text-3xl leading-[1.1] font-semibold sm:text-4xl lg:text-[2.75rem]">
                  An operating system for labour cooperatives
                </h1>
                <p className="text-ink-600 mt-4 max-w-xl text-base leading-relaxed sm:text-lg">
                  {t('brand.tagline')}. Nookr turns household service demand into skills,
                  fair allocation, workforce planning and worker welfare — with the cooperative
                  owning the intelligence.
                </p>

                <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                  <Button
                    size="lg"
                    onClick={() => enterDemo('CUSTOMER')}
                    loading={pending === 'CUSTOMER'}
                    icon={<Target className="size-4" aria-hidden />}
                  >
                    {t('auth.tryDemo')}
                  </Button>
                  <Link to="/register" className="sm:w-auto">
                    <Button
                      variant="secondary"
                      size="lg"
                      block
                      iconRight={<ArrowRight className="size-4" aria-hidden />}
                    >
                      {t('auth.register')}
                    </Button>
                  </Link>
                </div>

                {error ? (
                  <InlineNotice tone="danger" className="mt-4">
                    {error}
                  </InlineNotice>
                ) : null}
              </div>

              <Card className="border-brand-200 bg-white">
                <p className="label mb-3">How a request flows</p>
                <ol className="space-y-0">
                  {PIPELINE.map((stage, index) => (
                    <li key={stage} className="flex items-start gap-3">
                      <div className="flex flex-col items-center">
                        <span
                          className={cx(
                            'flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold',
                            index === PIPELINE.length - 1
                              ? 'bg-accent-600 text-white'
                              : 'bg-brand-100 text-brand-800',
                          )}
                        >
                          {index + 1}
                        </span>
                        {index < PIPELINE.length - 1 ? (
                          <span className="bg-ink-200 h-6 w-px" aria-hidden />
                        ) : null}
                      </div>
                      <span
                        className={cx(
                          'pt-0.5 text-sm',
                          index === PIPELINE.length - 1
                            ? 'text-accent-800 font-semibold'
                            : 'text-ink-700',
                        )}
                      >
                        {stage}
                      </span>
                    </li>
                  ))}
                </ol>
              </Card>
            </div>
          </div>
        </section>

        {/* Capabilities */}
        <section className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
          <h2 className="text-2xl font-semibold">What the cooperative gets</h2>
          <p className="text-ink-600 mt-2 max-w-2xl">
            Five distinct decision-support systems, each one explainable and each one grounded in
            the cooperative's own operating history.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {CAPABILITIES.map((item) => (
              <Card key={item.title} hoverable className="flex gap-3">
                <span className="bg-brand-50 text-brand-700 flex size-10 shrink-0 items-center justify-center rounded-xl">
                  {item.icon}
                </span>
                <div>
                  <h3 className="text-ink-900 text-sm font-semibold">{item.title}</h3>
                  <p className="text-ink-600 mt-1 text-sm leading-relaxed">{item.body}</p>
                </div>
              </Card>
            ))}
          </div>
        </section>

        {/* Demo access */}
        <section className="border-ink-200 border-y bg-ink-50">
          <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold">{t('auth.demoAccess')}</h2>
                <p className="text-ink-600 mt-1.5">{t('auth.demoNote')}</p>
              </div>
              <Badge tone="warn">{t('common.demoData')}</Badge>
            </div>

            <div className="mt-7 grid gap-4 sm:grid-cols-3">
              {PERSONAS.map((persona) => (
                <Card key={persona.role} className="flex flex-col gap-3" hoverable>
                  <div>
                    <h3 className="text-ink-900 font-semibold">{persona.label}</h3>
                    <p className="text-ink-600 mt-1 text-sm">{persona.description}</p>
                  </div>
                  <p className="text-ink-400 mt-auto font-mono text-xs">
                    {persona.role.toLowerCase()}@demo.com · demo1234
                  </p>
                  <Button
                    block
                    variant={persona.role === 'ADMIN' ? 'primary' : 'secondary'}
                    onClick={() => enterDemo(persona.role)}
                    loading={pending === persona.role}
                    iconRight={<ArrowRight className="size-4" aria-hidden />}
                  >
                    Open
                  </Button>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Principle */}
        <section className="mx-auto w-full max-w-4xl px-4 py-16 text-center sm:px-6">
          <Scale className="text-brand-600 mx-auto size-8" aria-hidden />
          <p className="text-ink-800 mt-4 text-xl leading-relaxed font-medium text-balance">
            {t('brand.principle')}
          </p>
        </section>
      </main>

      <footer className="border-ink-200 border-t">
        <div className="text-ink-500 mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-xs sm:px-6">
          <span>Nookr · Cooperative Gig Services Platform · SIH26089</span>
          <span>All data shown in this build is generated demo data.</span>
        </div>
      </footer>
    </div>
  )
}

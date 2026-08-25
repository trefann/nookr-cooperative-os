/**
 * The demo control strip.
 *
 * Always visible when demo mode is on: the scripted request, where the judge
 * is in the ten-step flow, one-click persona switching, and Reset Demo.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, ChevronDown, RotateCcw, Target, X } from 'lucide-react'

import { useAuth } from '../../auth/AuthContext'
import { useDemo } from '../../demo/DemoContext'
import { useI18n } from '../../i18n'
import { homeRouteFor } from '../../auth/AuthContext'
import type { Role } from '../../lib/types'
import { Badge, Button, cx } from '../ui'

const PERSONAS: { role: Role; label: string }[] = [
  { role: 'CUSTOMER', label: 'Customer' },
  { role: 'WORKER', label: 'Worker' },
  { role: 'ADMIN', label: 'Cooperative admin' },
]

export function DemoBar() {
  const { enabled, setEnabled, steps, currentStep, state, reset, resetting, message, clearMessage } =
    useDemo()
  const { user, signInAsDemo } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)
  const [switching, setSwitching] = useState<Role | null>(null)

  if (!enabled) return null

  const switchPersona = async (role: Role) => {
    setSwitching(role)
    try {
      const next = await signInAsDemo(role)
      navigate(homeRouteFor(next.role))
    } finally {
      setSwitching(null)
    }
  }

  const progress = steps.length ? Math.round((currentStep / steps.length) * 100) : 0

  return (
    <div className="bg-brand-900 text-white">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2 sm:px-6">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <Target className="size-4" aria-hidden />
          {t('demo.banner')}
        </span>

        <span className="text-brand-200 hidden text-xs sm:inline">
          {steps.length ? (
            <>
              Step {Math.min(currentStep + 1, steps.length)} of {steps.length}
              {steps[currentStep] ? ` · ${steps[currentStep].title}` : ''}
            </>
          ) : (
            'Loading scenario'
          )}
        </span>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="hidden items-center gap-1 md:flex">
            {PERSONAS.map((persona) => (
              <button
                key={persona.role}
                type="button"
                onClick={() => switchPersona(persona.role)}
                disabled={switching !== null}
                className={cx(
                  'rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-60',
                  user?.role === persona.role
                    ? 'bg-white text-brand-900'
                    : 'text-brand-100 hover:bg-brand-800',
                )}
              >
                {switching === persona.role ? '…' : persona.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            className="text-brand-100 hover:bg-brand-800 inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium"
          >
            {t('demo.steps')}
            <ChevronDown className={cx('size-3.5 transition-transform', expanded && 'rotate-180')} aria-hidden />
          </button>

          <Button
            size="sm"
            variant="secondary"
            onClick={reset}
            loading={resetting}
            icon={<RotateCcw className="size-3.5" aria-hidden />}
          >
            {resetting ? t('demo.resetting') : t('demo.reset')}
          </Button>

          <button
            type="button"
            onClick={() => setEnabled(false)}
            aria-label="Turn off demo mode"
            className="text-brand-200 hover:bg-brand-800 rounded-md p-1"
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>

        <div className="h-1 w-full overflow-hidden rounded-full bg-brand-800">
          <div
            className="bg-accent-400 h-full rounded-full transition-[width] duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {message ? (
        <div className="bg-accent-600 px-4 py-1.5 text-center text-xs sm:px-6">
          {message}
          <button
            type="button"
            onClick={clearMessage}
            className="ml-2 underline underline-offset-2"
          >
            {t('common.close')}
          </button>
        </div>
      ) : null}

      {expanded ? (
        <div className="bg-brand-800 border-brand-700 border-t">
          <div className="mx-auto w-full max-w-7xl px-4 py-4 sm:px-6">
            {state?.scenario_request ? (
              <p className="text-brand-100 mb-3 text-xs">
                <span className="font-semibold">{t('demo.scenario')}:</span> “
                {state.scenario_request}”
              </p>
            ) : null}
            <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
              {steps.map((step, index) => {
                const done = index < currentStep
                const active = index === currentStep
                return (
                  <li key={step.key}>
                    <button
                      type="button"
                      onClick={() => navigate(step.route)}
                      className={cx(
                        'flex w-full items-start gap-2 rounded-lg p-2.5 text-left transition-colors',
                        active ? 'bg-white/15' : 'hover:bg-white/10',
                      )}
                    >
                      <span
                        className={cx(
                          'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold',
                          done
                            ? 'bg-accent-500 text-white'
                            : active
                              ? 'bg-white text-brand-900'
                              : 'bg-brand-700 text-brand-200',
                        )}
                      >
                        {done ? <Check className="size-3" strokeWidth={3} aria-hidden /> : index + 1}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-xs font-medium text-white">{step.title}</span>
                        <span className="text-brand-200 block text-[11px] leading-snug">
                          {step.detail}
                        </span>
                        <Badge tone="outline" className="mt-1 bg-transparent text-brand-100 ring-brand-600">
                          {step.actor}
                        </Badge>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ol>
          </div>
        </div>
      ) : null}
    </div>
  )
}

/** The button that turns demo mode on, shown on the public screens. */
export function DemoModeToggle({ className }: { className?: string }) {
  const { enabled, setEnabled } = useDemo()
  const { t } = useI18n()
  if (enabled) return null
  return (
    <Button
      variant="secondary"
      onClick={() => setEnabled(true)}
      icon={<Target className="size-4" aria-hidden />}
      className={className}
    >
      {t('demo.banner')}
    </Button>
  )
}

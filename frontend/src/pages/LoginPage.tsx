/** Sign in, with clearly labelled one-click demo access beside it. */

import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, LogIn, Target } from 'lucide-react'

import { homeRouteFor, useAuth } from '../auth/AuthContext'
import { BrandMark } from '../components/layout/BrandMark'
import { LanguageSelect } from '../components/layout/LanguageSelect'
import { Badge, Button, Card, Field, InlineNotice, Input } from '../components/ui'
import { useDemo } from '../demo/DemoContext'
import { useI18n } from '../i18n'
import { ApiError, errorMessage } from '../lib/api'
import * as endpoints from '../lib/endpoints'
import { useAsync } from '../lib/useAsync'
import type { Role } from '../lib/types'

export default function LoginPage() {
  const { signIn, signInAsDemo } = useAuth()
  const { setEnabled } = useDemo()
  const { t } = useI18n()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [demoPending, setDemoPending] = useState<Role | null>(null)

  const { data: demoAccounts } = useAsync(() => endpoints.getDemoAccounts(), [])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    setFieldErrors({})
    try {
      const user = await signIn(email.trim(), password)
      navigate(from ?? homeRouteFor(user.role), { replace: true })
    } catch (caught) {
      if (caught instanceof ApiError) setFieldErrors(caught.fieldErrors)
      setError(errorMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  const enterDemo = async (role: Role) => {
    setDemoPending(role)
    setError(null)
    try {
      setEnabled(true)
      const user = await signInAsDemo(role)
      navigate(homeRouteFor(user.role), { replace: true })
    } catch (caught) {
      setError(errorMessage(caught))
      setDemoPending(null)
    }
  }

  return (
    <div className="bg-ink-50 min-h-dvh">
      <header className="border-ink-200 border-b bg-white">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 px-4 py-3.5 sm:px-6">
          <BrandMark />
          <LanguageSelect />
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6 sm:py-14">
        <div className="grid gap-6 lg:grid-cols-2 lg:gap-8">
          <Card className="order-2 lg:order-1">
            <h1 className="text-xl font-semibold">{t('auth.signInTitle')}</h1>
            <p className="text-ink-500 mt-1 text-sm">{t('auth.signInSubtitle')}</p>

            <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
              <Field label={t('auth.email')} htmlFor="email" error={fieldErrors.email} required>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                />
              </Field>

              <Field
                label={t('auth.password')}
                htmlFor="password"
                error={fieldErrors.password}
                required
              >
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Field>

              {error ? <InlineNotice tone="danger">{error}</InlineNotice> : null}

              <Button
                type="submit"
                size="lg"
                block
                loading={submitting}
                icon={<LogIn className="size-4" aria-hidden />}
              >
                {submitting ? t('auth.signingIn') : t('auth.signIn')}
              </Button>
            </form>

            <p className="text-ink-500 mt-5 text-sm">
              {t('auth.noAccount')}{' '}
              <Link to="/register" className="text-brand-700 font-medium hover:underline">
                {t('auth.register')}
              </Link>
            </p>
          </Card>

          <Card className="order-1 border-brand-200 lg:order-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-lg font-semibold">
                  <Target className="text-brand-700 size-5" aria-hidden />
                  {t('auth.demoAccess')}
                </h2>
                <p className="text-ink-500 mt-1 text-sm">{t('auth.demoNote')}</p>
              </div>
              <Badge tone="warn">{t('common.demoData')}</Badge>
            </div>

            <ul className="mt-5 space-y-3">
              {(demoAccounts ?? []).map((account) => (
                <li key={account.role}>
                  <button
                    type="button"
                    onClick={() => enterDemo(account.role)}
                    disabled={demoPending !== null}
                    className="border-ink-200 hover:border-brand-300 hover:bg-brand-50/50 flex w-full items-center gap-3 rounded-xl border p-3.5 text-left transition-colors disabled:opacity-60"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-ink-900 text-sm font-semibold">{account.label}</p>
                      <p className="text-ink-500 mt-0.5 text-xs">{account.description}</p>
                      <p className="text-ink-400 mt-1.5 font-mono text-[11px]">
                        {account.email} · {account.password}
                      </p>
                    </div>
                    <ArrowRight className="text-ink-400 size-4 shrink-0" aria-hidden />
                  </button>
                </li>
              ))}
              {!demoAccounts?.length ? (
                <li className="text-ink-500 text-sm">
                  Demo accounts are unavailable. Make sure the API is running and the database has
                  been seeded.
                </li>
              ) : null}
            </ul>
          </Card>
        </div>
      </main>
    </div>
  )
}

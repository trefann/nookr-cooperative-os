/** Account creation. Only customers self-register; workers are enrolled by the cooperative. */

import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { UserPlus } from 'lucide-react'

import { homeRouteFor, useAuth } from '../auth/AuthContext'
import { BrandMark } from '../components/layout/BrandMark'
import { LanguageSelect } from '../components/layout/LanguageSelect'
import { Button, Card, Field, InlineNotice, Input, Select, Textarea } from '../components/ui'
import { useI18n } from '../i18n'
import { ApiError, errorMessage } from '../lib/api'
import * as endpoints from '../lib/endpoints'
import { useAsync } from '../lib/useAsync'

export default function RegisterPage() {
  const { registerAccount } = useAuth()
  const { t, locale } = useI18n()
  const navigate = useNavigate()

  const { data: zones } = useAsync(() => endpoints.getZones(), [])

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    phone: '',
    address: '',
    zone_id: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const update = (key: keyof typeof form) => (value: string) =>
    setForm((current) => ({ ...current, [key]: value }))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    setFieldErrors({})
    try {
      const user = await registerAccount({
        email: form.email.trim(),
        password: form.password,
        full_name: form.full_name.trim(),
        role: 'CUSTOMER',
        phone: form.phone.trim(),
        address: form.address.trim(),
        zone_id: form.zone_id ? Number(form.zone_id) : null,
        language: locale,
      })
      navigate(homeRouteFor(user.role), { replace: true })
    } catch (caught) {
      if (caught instanceof ApiError) setFieldErrors(caught.fieldErrors)
      setError(errorMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-ink-50 min-h-dvh">
      <header className="border-ink-200 border-b bg-white">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 py-3.5 sm:px-6">
          <BrandMark />
          <LanguageSelect />
        </div>
      </header>

      <main className="mx-auto w-full max-w-2xl px-4 py-10 sm:px-6 sm:py-14">
        <Card>
          <h1 className="text-xl font-semibold">{t('auth.registerTitle')}</h1>
          <p className="text-ink-500 mt-1 text-sm">{t('auth.registerSubtitle')}</p>

          <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
            <Field
              label={t('auth.fullName')}
              htmlFor="full_name"
              error={fieldErrors.full_name}
              required
            >
              <Input
                id="full_name"
                required
                autoComplete="name"
                value={form.full_name}
                onChange={(event) => update('full_name')(event.target.value)}
              />
            </Field>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t('auth.email')} htmlFor="email" error={fieldErrors.email} required>
                <Input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={form.email}
                  onChange={(event) => update('email')(event.target.value)}
                />
              </Field>
              <Field label={t('auth.phone')} htmlFor="phone" error={fieldErrors.phone}>
                <Input
                  id="phone"
                  type="tel"
                  autoComplete="tel"
                  placeholder="+91 98430 00000"
                  value={form.phone}
                  onChange={(event) => update('phone')(event.target.value)}
                />
              </Field>
            </div>

            <Field
              label={t('auth.password')}
              htmlFor="password"
              error={fieldErrors.password}
              hint="At least 8 characters."
              required
            >
              <Input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={form.password}
                onChange={(event) => update('password')(event.target.value)}
              />
            </Field>

            <Field label={t('auth.zone')} htmlFor="zone_id" error={fieldErrors.zone_id}>
              <Select
                id="zone_id"
                value={form.zone_id}
                onChange={(event) => update('zone_id')(event.target.value)}
              >
                <option value="">Select your zone</option>
                {(zones ?? []).map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label={t('auth.address')} htmlFor="address" error={fieldErrors.address}>
              <Textarea
                id="address"
                rows={2}
                autoComplete="street-address"
                value={form.address}
                onChange={(event) => update('address')(event.target.value)}
              />
            </Field>

            {error ? <InlineNotice tone="danger">{error}</InlineNotice> : null}

            <Button
              type="submit"
              size="lg"
              block
              loading={submitting}
              icon={<UserPlus className="size-4" aria-hidden />}
            >
              {t('auth.register')}
            </Button>
          </form>

          <p className="text-ink-500 mt-5 text-sm">
            {t('auth.haveAccount')}{' '}
            <Link to="/login" className="text-brand-700 font-medium hover:underline">
              {t('auth.signIn')}
            </Link>
          </p>

          <p className="text-ink-400 border-ink-100 mt-5 border-t pt-4 text-xs">
            Cooperative worker accounts are created by the cooperative office, not through this
            form.
          </p>
        </Card>
      </main>
    </div>
  )
}

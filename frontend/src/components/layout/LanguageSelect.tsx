import { Globe } from 'lucide-react'

import { useI18n, type LocaleCode } from '../../i18n'

/** Language switcher. Present in every header, on every screen size. */
export function LanguageSelect({ className }: { className?: string }) {
  const { locale, setLocale, locales, t } = useI18n()

  return (
    <label className={className}>
      <span className="sr-only">{t('common.language')}</span>
      <span className="border-ink-300 hover:border-ink-400 focus-within:border-brand-500 focus-within:ring-brand-100 relative inline-flex items-center rounded-lg border bg-white transition-colors focus-within:ring-2">
        <Globe className="text-ink-400 pointer-events-none absolute left-2.5 size-4" aria-hidden />
        <select
          value={locale}
          onChange={(event) => setLocale(event.target.value as LocaleCode)}
          className="text-ink-700 h-9 cursor-pointer appearance-none rounded-lg bg-transparent py-0 pr-7 pl-8 text-sm focus:outline-none"
        >
          {locales.map((item) => (
            <option key={item.code} value={item.code}>
              {item.nativeLabel}
            </option>
          ))}
        </select>
        <svg
          className="text-ink-400 pointer-events-none absolute right-2 size-3"
          viewBox="0 0 12 12"
          fill="none"
          aria-hidden
        >
          <path d="M3 4.5 6 8l3-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </span>
    </label>
  )
}

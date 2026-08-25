/**
 * Translation provider.
 *
 * Strings live in locale files keyed by dotted path, never inline in
 * components. Lookups fall back to English so a partially translated locale
 * degrades to readable text rather than to a missing-key placeholder.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { en } from './en'
import { DEFAULT_LOCALE, DICTIONARIES, LOCALES, type LocaleCode } from './locales'
import type { TranslationKey } from './types'

const STORAGE_KEY = 'nookr.locale'

function lookup(source: unknown, path: string): string | undefined {
  const value = path
    .split('.')
    .reduce<unknown>(
      (acc, part) =>
        acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[part] : undefined,
      source,
    )
  return typeof value === 'string' ? value : undefined
}

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in vars ? String(vars[key]) : match,
  )
}

export interface I18nContextValue {
  locale: LocaleCode
  setLocale: (locale: LocaleCode) => void
  /** Translate a dotted key, with optional {placeholder} values. */
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string
  locales: typeof LOCALES
}

const I18nContext = createContext<I18nContextValue | null>(null)

function readStoredLocale(): LocaleCode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) as LocaleCode | null
    if (stored && stored in DICTIONARIES) return stored
  } catch {
    /* storage unavailable */
  }
  const browser = navigator.language?.slice(0, 2) as LocaleCode | undefined
  return browser && browser in DICTIONARIES ? browser : DEFAULT_LOCALE
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<LocaleCode>(readStoredLocale)

  useEffect(() => {
    document.documentElement.lang = locale
    try {
      localStorage.setItem(STORAGE_KEY, locale)
    } catch {
      /* storage unavailable */
    }
  }, [locale])

  const setLocale = useCallback((next: LocaleCode) => setLocaleState(next), [])

  const t = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>) => {
      const translated = lookup(DICTIONARIES[locale], key) ?? lookup(en, key)
      // A missing key is a bug, not a runtime failure: show the key so it is
      // obvious in review, rather than rendering an empty space.
      return interpolate(translated ?? key, vars)
    },
    [locale],
  )

  const value = useMemo<I18nContextValue>(
    () => ({ locale, setLocale, t, locales: LOCALES }),
    [locale, setLocale, t],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext)
  if (!context) throw new Error('useI18n must be used inside <I18nProvider>')
  return context
}

export { LOCALES, type LocaleCode }

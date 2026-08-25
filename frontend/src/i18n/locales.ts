import { en } from './en'
import { hi } from './hi'
import { ta } from './ta'
import { te } from './te'
import type { PartialDictionary } from './types'

export const LOCALES = [
  { code: 'en', label: 'English', nativeLabel: 'English' },
  { code: 'hi', label: 'Hindi', nativeLabel: 'हिन्दी' },
  { code: 'ta', label: 'Tamil', nativeLabel: 'தமிழ்' },
  { code: 'te', label: 'Telugu', nativeLabel: 'తెలుగు' },
] as const

export type LocaleCode = (typeof LOCALES)[number]['code']

export const DICTIONARIES: Record<LocaleCode, PartialDictionary> = { en, hi, ta, te }

export const DEFAULT_LOCALE: LocaleCode = 'en'

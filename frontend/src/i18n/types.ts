import type { Dictionary } from './en'

/** Locales may translate any subset; the rest falls back to English. */
export type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends string ? string : DeepPartial<T[K]>
}

export type PartialDictionary = DeepPartial<Dictionary>

/** Dotted key path into the dictionary, e.g. "customer.describeCta". */
type Join<K, P> = K extends string
  ? P extends string
    ? `${K}${'' extends P ? '' : '.'}${P}`
    : never
  : never

export type Paths<T> = T extends object
  ? { [K in keyof T]-?: K extends string ? T[K] extends string ? K : Join<K, Paths<T[K]>> : never }[keyof T]
  : never

export type TranslationKey = Paths<Dictionary>

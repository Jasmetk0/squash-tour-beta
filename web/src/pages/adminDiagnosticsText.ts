import type { Language } from '../i18n/LanguageContext'

import czechCopy from './adminDiagnostics.cs.json'

const cs: Record<string, string> = czechCopy

export function adminDiagnosticsText(english: string, language: Language): string {
  return language === 'cs' ? cs[english] ?? english : english
}

export function adminDiagnosticsCountLabel(visible: number, language: Language): string {
  return language === 'cs'
    ? `Zobrazeno ${visible} z 6 diagnostických oblastí`
    : `Showing ${visible} of 6 diagnostic areas`
}

import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export type Language = 'cs' | 'en'
const STORAGE_KEY = 'squash-engine-language-v1'
const words: Record<string, { cs: string; en: string }> = {
  'Home': { cs: 'Domů', en: 'Home' },
  'Runs': { cs: 'Runy', en: 'Runs' },
  'Packages': { cs: 'Balíčky', en: 'Packages' },
  'Test Lab': { cs: 'Testovací laboratoř', en: 'Test Lab' },
  'Settings': { cs: 'Nastavení aplikace', en: 'Application settings' },
  'World': { cs: 'Svět', en: 'World' },
  'Players': { cs: 'Hráči', en: 'Players' },
  'Tour': { cs: 'Tour', en: 'Tour' },
  'Rankings & Analytics': { cs: 'Žebříčky a analytika', en: 'Rankings & Analytics' },
  'Simulation': { cs: 'Simulace', en: 'Simulation' },
  'History & Branches': { cs: 'Historie a větve', en: 'History & Branches' },
  'Run Management': { cs: 'Správa Runu', en: 'Run Management' },
  'Expand sidebar': { cs: 'Rozbalit navigaci', en: 'Expand sidebar' },
  'Collapse sidebar': { cs: 'Sbalit navigaci', en: 'Collapse sidebar' },
  'Pin sidebar': { cs: 'Připnout navigaci', en: 'Pin sidebar' },
  'Unpin sidebar': { cs: 'Odepnout navigaci', en: 'Unpin sidebar' },
  'Open navigation': { cs: 'Otevřít navigaci', en: 'Open navigation' },
  'Squash Engine Home': { cs: 'Squash Engine – Domů', en: 'Squash Engine Home' },
  'A world-building and simulation workspace. Choose what to work with.': {
    cs: 'Pracovní prostředí pro tvorbu a simulaci squashového světa. Vyber oblast, se kterou chceš pracovat.',
    en: 'A world-building and simulation workspace. Choose what to work with.'
  },
  'Create, open and manage independent saved worlds.': { cs: 'Vytvářej, otevírej a spravuj nezávislé uložené světy.', en: 'Create, open and manage independent saved worlds.' },
  'Browse source packages; applying a package creates a Run-owned copy.': { cs: 'Procházej zdrojové balíčky; použitím vznikne nezávislá kopie v Runu.', en: 'Browse source packages; applying a package creates a Run-owned copy.' },
  'Run isolated Match, Tournament and Player experiments.': { cs: 'Spouštěj nezávislé testy zápasů, turnajů a hráčů.', en: 'Run isolated Match, Tournament and Player experiments.' },
  'Saved Product Runs': { cs: 'Uložené Product Runy', en: 'Saved Product Runs' },
  'Recently opened': { cs: 'Nedávno otevřené', en: 'Recently opened' },
  'Other saved Runs': { cs: 'Další uložené Runy', en: 'Other saved Runs' },
  'Open Run': { cs: 'Otevřít Run', en: 'Open Run' },
  'Create Run': { cs: 'Vytvořit Run', en: 'Create Run' },
  'Loading': { cs: 'Načítání…', en: 'Loading…' },
  'Unavailable': { cs: 'Data nejsou dostupná', en: 'Data unavailable' },
  'No Runs yet': { cs: 'Zatím neexistují žádné uložené Runy.', en: 'No saved Runs yet.' },
  'World packages': { cs: 'World balíčky', en: 'World packages' },
  'Saved Runs': { cs: 'Uložené Runy', en: 'Saved Runs' },
  'Not implemented': { cs: 'Zatím neimplementováno', en: 'Not implemented' }
}

type LanguageContextValue = {
  language: Language
  setLanguage: (value: Language) => void
  t: (key: string) => string
}
const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }): JSX.Element {
  const [language, setLanguage] = useState<Language>(() => {
    try { return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'cs' } catch { return 'cs' }
  })
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, language) } catch { /* private browsing */ }
  }, [language])
  const value = useMemo<LanguageContextValue>(() => ({
    language, setLanguage,
    t: key => words[key]?.[language] ?? key
  }), [language])
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('useLanguage requires LanguageProvider')
  return context
}

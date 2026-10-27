import type { Language } from '../i18n/LanguageContext'

const cs: Record<string, string> = {
  'Diagnostics': 'Diagnostika',
  'Control center for world balance, calendar validation, run health, invalidated data, narrative locks, and audit warnings.':
    'Řídicí centrum pro vyváženost světa, validaci kalendáře, zdraví runu, invalidovaná data, narativní zámky a auditní upozornění.',
  'This is a navigation and triage page, not a consolidated diagnostic scan. Existing tools are linked below; planned coverage is explicitly separate. Run-specific diagnostics remain under Run Diagnostics.':
    'Toto je navigační a třídicí stránka, ne souhrnný diagnostický scan. Existující nástroje jsou odkazované níže; plánované pokrytí je uvedené zvlášť. Diagnostika konkrétního runu zůstává pod Run Diagnostics.',
  'Overview': 'Přehled',
  'Open a run first to inspect current operational diagnostics.': 'Nejdřív otevřete run, abyste mohli zkontrolovat aktuální provozní diagnostiku.',
  'Open Runs': 'Otevřít runy',
  'Open last run diagnostics': 'Otevřít diagnostiku posledního runu',
  'Show diagnostics sections': 'Zobrazit sekce diagnostiky',
  'All areas': 'Všechny oblasti',
  'Linked tools': 'Propojené nástroje',
  'Planned areas': 'Plánované oblasti',
  'diagnostic areas': 'diagnostických oblastí',
  'World Balance': 'Vyváženost světa',
  'Use linked World tools to inspect country inputs and Talent Preview. Broader balance diagnostics, population dominance and small-country risk checks are planned; links here do not imply that all such checks are implemented.':
    'Použijte propojené nástroje World pro kontrolu vstupů zemí a Talent Preview. Širší diagnostika vyváženosti, dominance populace a kontrola rizik malých zemí jsou plánované; odkazy zde neznamenají, že jsou všechny tyto kontroly implementované.',
  'Current action:': 'Aktuální akce:',
  'Talent Preview': 'Talent Preview',
  'Official FAX World countries': 'Země Official FAX World',
  'Calendar Validation': 'Validace kalendáře',
  "Calendar checks should use each Run's configured season-week range rather than assuming W01–W61. Existing validation tools also cover event timing, qualifiers, categories, hosts and schedule conflicts within their supported scope.":
    'Kontroly kalendáře mají používat nakonfigurovaný sezonní rozsah každého runu místo předpokladu W01–W61. Existující validační nástroje navíc v podporovaném rozsahu pokrývají načasování událostí, kvalifikace, kategorie, hostitele a konflikty rozvrhu.',
  'Seasons': 'Sezony',
  'Run Health': 'Zdraví runu',
  'Open the Run Diagnostics page for currently supported operational checks. Broader health, snapshot and stale-artifact coverage is not implied by this navigation card.':
    'Otevřete stránku Run Diagnostics pro aktuálně podporované provozní kontroly. Tato navigační karta neznamená širší pokrytí zdraví, snapshotů ani zastaralých artefaktů.',
  'Runs': 'Runy',
  'Last run diagnostics': 'Diagnostika posledního runu',
  'Invalidated Data': 'Invalidovaná data',
  'Planned downstream invalidation tracking after calendar, entry, draw, result, points, or ranking edits.':
    'Plánované navazující sledování invalidací po úpravách kalendáře, přihlášek, losu, výsledků, bodů nebo žebříčku.',
  'Current action: Planned / run-scoped diagnostics later.': 'Aktuální akce: Plánováno / run-scoped diagnostika později.',
  'Narrative Locks': 'Narativní zámky',
  'Planned conflict/plausibility checks for Soft/Hard/Winner/Round/Exact Match/Path locks.':
    'Plánované kontroly konfliktů a plausibility pro zámky Soft/Hard/Winner/Round/Exact Match/Path.',
  'Current action: Planned.': 'Aktuální akce: Plánováno.',
  'Audit / Warnings': 'Audit / upozornění',
  'Future consolidated feed for manual edits, lock changes, regeneration skips, invalidation events, and warning history.':
    'Budoucí souhrnný přehled ručních úprav, změn zámků, přeskočených regenerací, invalidačních událostí a historie upozornění.',
  'Current action: Audit remains embedded in specific operational pages.':
    'Aktuální akce: Audit zůstává vložený v konkrétních provozních stránkách.',
  'What Diagnostics should explain': 'Co by měla Diagnostika vysvětlit',
  'what happened': 'co se stalo',
  'why it matters': 'proč je to důležité',
  'what is affected': 'čeho se to týká',
  'what to do next': 'co dělat dál',
  'where to click': 'kam kliknout',
  'Current vs planned': 'Aktuální vs plánované',
  'Current:': 'Aktuální:',
  'real diagnostics are mostly run-scoped; this top-level page is a launcher/triage shell; existing Run Diagnostics is the operational source today.':
    'reálná diagnostika je převážně run-scoped; tato top-level stránka je launcher/triage shell; provozním zdrojem je dnes existující Run Diagnostics.',
  'Planned:': 'Plánované:',
  'top-level aggregation across World, Calendar, Runs, Invalidated Data, Narrative Locks, and Audit.':
    'top-level agregace napříč World, Calendar, Runs, Invalidated Data, Narrative Locks a Audit.',
}

export function adminDiagnosticsText(english: string, language: Language): string {
  return language === 'cs' ? cs[english] ?? english : english
}

export function adminDiagnosticsCountLabel(visible: number, language: Language): string {
  return language === 'cs'
    ? `Zobrazeno ${visible} z 6 diagnostických oblastí`
    : `Showing ${visible} of 6 diagnostic areas`
}

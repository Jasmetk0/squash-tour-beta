import { Link } from 'react-router-dom'
import type { RunHomeReadiness, RunReadinessCode, RunReadinessItem } from '../api/runHomeReadiness'

const content = {
  cs: {
    heading: 'Připravenost této Branch',
    explanation: 'Ověřené uložené podklady vybrané větve. Připravenost se vždy posuzuje pro konkrétní operaci.',
    refresh: 'Obnovit kontrolu',
    loading: 'Načítání aktuálního uloženého stavu…',
    noSupport: 'Tento kalendář nepodporuje starší FAX simulační postup. Nativní operace mají vlastní nezávislé kontroly; tento údaj je nezakazuje.',
    supported: 'Kalendář odpovídá referenčnímu FAX postupu staršího simulátoru. Před každou operací je stále nutná vlastní kontrola.',
    drafted: 'Neuložené změny nejsou do tohoto přehledu započítané.',
    phase: { preparation: 'Příprava', sporting_history: 'Již existuje uložená sportovní historie', completed: 'Dokončený Run' },
    item: {
      world: 'World – uložené entity',
      calendar_package: 'Kalendář turnajů – uložené entity',
      population: 'Hráči – uložená populace',
      health: 'Zdraví hráčů – uložené stavy',
      official_ranking: 'Oficiálně publikovaný ranking',
      working_draft: 'Working Draft',
    },
    status: { saved: 'Uloženo', missing: 'Chybí', candidate_only: 'Pouze návrh', unsaved: 'Neuloženo', optional: 'Zde není vyžadováno' },
    task: 'Rozpracované úlohy',
    history: 'Uložené přechody',
    help: 'Co dál?',
    labHint: 'Samostatné experimenty nevyžadují připravený Run.',
    lab: 'Otevřít globální Test Lab',
    action: {
      world: 'Doplnit World Package',
      calendar_package: 'Doplnit Calendar Package',
      population: 'Vygenerovat a uložit hráče',
      health: 'Otevřít hráče a jejich Health',
      official_ranking: 'Otevřít přípravu rankingu',
      working_draft: 'Zkontrolovat a uložit změny',
    },
    allSaved: 'Kontrola uložených podkladů zde nevyžaduje další krok. Neznamená to připravenost všech operací; každá má vlastní kontrolu.',
    checklist: 'Zobrazit kontrolu uložených podkladů',
    attentionCount: 'položky k prověření',
    details: 'Technický původ a hranice',
    branch: 'Vybraná Branch',
    calendar: 'Kalendář Runu',
    weeks: 'týdnů za sezónu',
    seasons: 'sezón',
    revision: 'Uložená revize HEAD',
    draftVersion: 'Verze pracovního návrhu',
  },
  en: {
    heading: 'This Branch readiness',
    explanation: 'Verified saved foundations for the selected Branch. Readiness is always specific to the requested operation.',
    refresh: 'Refresh inspection',
    loading: 'Loading current saved state…',
    noSupport: 'This calendar is not supported by the legacy FAX simulation path. Native operations have their own independent preflights; this indicator does not disable them.',
    supported: 'The calendar matches the reference FAX configuration for the legacy simulator. Every operation still requires its own preflight.',
    drafted: 'Unsaved changes are not counted in this overview.',
    phase: { preparation: 'Preparation', sporting_history: 'Saved sporting history exists', completed: 'Completed Run' },
    item: {
      world: 'World – saved entities',
      calendar_package: 'Tournament calendar – saved entities',
      population: 'Players – saved population',
      health: 'Player Health – saved states',
      official_ranking: 'Officially published ranking',
      working_draft: 'Working Draft',
    },
    status: { saved: 'Saved', missing: 'Missing', candidate_only: 'Candidate only', unsaved: 'Unsaved', optional: 'Not required here' },
    task: 'Nonterminal tasks',
    history: 'Saved transitions',
    help: 'Next action',
    labHint: 'Standalone experiments do not require a prepared Run.',
    lab: 'Open global Test Lab',
    action: {
      world: 'Add a World Package',
      calendar_package: 'Add a Calendar Package',
      population: 'Generate and Save players',
      health: 'Open players and their Health',
      official_ranking: 'Open ranking preparation',
      working_draft: 'Inspect and Save changes',
    },
    allSaved: 'This saved-foundation inspection has no further action. It does not certify all operations; each requires its own preflight.',
    checklist: 'Show saved-foundation checks',
    attentionCount: 'items needing attention',
    details: 'Technical provenance and limits',
    branch: 'Selected Branch',
    calendar: 'Run calendar',
    weeks: 'weeks per season',
    seasons: 'seasons',
    revision: 'Saved Revision HEAD',
    draftVersion: 'Working Draft version',
  }
} as const

const href: Record<RunReadinessCode, string> = {
  world: '/manage',
  calendar_package: '/manage',
  population: '/players/generate',
  health: '/players',
  official_ranking: '/simulate',
  working_draft: '/branches'
}
const ordered: RunReadinessCode[] = [
  'world', 'calendar_package', 'population', 'health', 'official_ranking', 'working_draft'
]

const needsAttention = (item: RunReadinessItem): boolean =>
  item.status === 'missing' || item.status === 'candidate_only' || item.status === 'unsaved'

export function RunHomeReadinessPanel({
  data, runId, language, refreshing, refresh,
}: {
  data: RunHomeReadiness
  runId: string
  language: 'cs' | 'en'
  refreshing: boolean
  refresh: () => void
}): JSX.Element {
  const l = content[language]
  const base = '/admin/runs/' + encodeURIComponent(runId)
  const draftDirty = data.items.some(
    item => item.code === 'working_draft' && item.status === 'unsaved'
  )
  // The inventory describes only Saved foundations. Prioritize reviewing a
  // dirty Working Draft before recommending another import/generation: its
  // pending changes are not yet part of the verified Saved evidence.
  const next = draftDirty ? 'working_draft' : ordered.find(code => data.items.some(
    item => item.code === code && needsAttention(item)
  ))
  const attentionCount = data.items.filter(needsAttention).length
  return <section aria-label={language === 'cs' ? 'Připravenost Runu' : 'Run saved readiness'} className="run-home-status-block">
    <div className="actions">
      <h3>{l.heading}</h3>
      <button type="button" disabled={refreshing} onClick={refresh}>{refreshing ? l.loading : l.refresh}</button>
    </div>
    <p className="status">{l.explanation} · {l.phase[data.phase]}</p>
    <details className="run-home-readiness-checklist">
      <summary>{l.checklist} ({data.items.length}){attentionCount > 0 ? ` · ${attentionCount} ${l.attentionCount}` : ''}</summary>
      <ul className="run-home-feed" aria-label={language === 'cs' ? 'Kontrola uložených podkladů' : 'Saved preparation checks'}>
        {data.items.map(item => <li key={item.code}>
          <span><strong>{l.item[item.code]}</strong>
            <small>{l.status[item.status]} · {item.evidence_count}</small>
          </span>
          {needsAttention(item) &&
            <Link to={base + href[item.code]}>{l.action[item.code]} →</Link>}
        </li>)}
      </ul>
    </details>
    {draftDirty && <p className="error">{l.drafted}</p>}
    <p className="status">
      {data.sporting_calendar_supported_by_legacy_writers ? l.supported : l.noSupport}
    </p>
    {next
      ? <p><strong>{l.help}: </strong>
          <Link to={base + href[next]}>{l.action[next]} →</Link>
        </p>
      : <p className="status">{l.allSaved}</p>}
    {data.phase === 'preparation' &&
      <p className="status">{l.labHint} <Link to="/admin/labs">{l.lab}</Link></p>}
    <details>
      <summary>{l.details}</summary>
      <p>{l.branch}: <code>{data.branch_id}</code></p>
      <p>{l.calendar}: {data.current_calendar.weeks_per_year} {l.weeks} · {data.current_calendar.season_count} {l.seasons}</p>
      <p>{l.revision}: <code>{data.saved_revision_id}</code></p>
      <p>SHA256: <code>{data.saved_revision_content_hash}</code></p>
      <p>{l.draftVersion}: {data.draft_version}</p>
      <p>{l.history}: {data.saved_transition_count}
        {' · '}{l.task}: {data.active_full_simulation_task_count}
        / {data.historical_full_simulation_task_count}</p>
    </details>
  </section>
}

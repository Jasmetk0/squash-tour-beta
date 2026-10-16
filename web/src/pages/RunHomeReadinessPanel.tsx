import { Link } from 'react-router-dom'
import type { RunHomeReadiness, RunReadinessCode, RunReadinessStatus } from '../api/runHomeReadiness'

const content = {
  cs: {
    heading: 'Připravenost této Branch',
    explanation: 'Ověřené uložené podklady, nikoli souhlas se spuštěním simulace.',
    refresh: 'Obnovit kontrolu',
    loading: 'Načítání aktuálního uloženého stavu…',
    noSupport: 'Tento Run používá kalendář, pro který sportovní engine zatím neumí bezpečně simulovat.',
    supported: 'Kalendář odpovídá podporované referenční FAX konfiguraci. Před každou operací je stále nutná vlastní kontrola.',
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
    action: {
      world: 'Doplnit World Package',
      calendar_package: 'Doplnit Calendar Package',
      population: 'Vygenerovat a uložit hráče',
      health: 'Otevřít hráče a jejich Health',
      official_ranking: 'Otevřít přípravu rankingu',
      working_draft: 'Zkontrolovat a uložit změny',
    },
    allSaved: 'Vybrané podklady jsou uloženy. Sportovní operace stále vyžadují samostatné ověření.',
    details: 'Technický původ a hranice',
  },
  en: {
    heading: 'This Branch readiness',
    explanation: 'Verified saved foundations, not authorization to run simulation.',
    refresh: 'Refresh inspection',
    loading: 'Loading current saved state…',
    noSupport: 'This Run calendar is not yet safely executable by the sporting engine.',
    supported: 'The calendar matches the supported reference FAX configuration. Every operation still requires its own preflight.',
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
    action: {
      world: 'Add a World Package',
      calendar_package: 'Add a Calendar Package',
      population: 'Generate and Save players',
      health: 'Open players and their Health',
      official_ranking: 'Open ranking preparation',
      working_draft: 'Inspect and Save changes',
    },
    allSaved: 'The selected foundations are saved. Sporting operations still require a separate preflight.',
    details: 'Technical provenance and limits',
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
  const byCode = Object.fromEntries(data.items.map(item => [item.code, item])) as
    Record<RunReadinessCode, { status: RunReadinessStatus; evidence_count: number }>
  const next = ordered.find(code => {
    const status = byCode[code].status
    return status === 'missing' || status === 'candidate_only' || status === 'unsaved'
  })
  const draftDirty = byCode.working_draft.status === 'unsaved'
  return <section aria-label="Run saved readiness" className="run-home-status-block">
    <div className="actions">
      <h3>{l.heading}</h3>
      <button type="button" disabled={refreshing} onClick={refresh}>{refreshing ? l.loading : l.refresh}</button>
    </div>
    <p className="status">{l.explanation} · {l.phase[data.phase]}</p>
    <ul className="run-home-feed" aria-label="Saved preparation checks">
      {data.items.map(item => <li key={item.code}>
        <span><strong>{l.item[item.code]}</strong>
          <small>{l.status[item.status]} · {item.evidence_count}</small>
        </span>
        {(item.status === 'missing' || item.status === 'candidate_only' || item.status === 'unsaved') &&
          <Link to={base + href[item.code]}>{l.action[item.code]} →</Link>}
      </li>)}
    </ul>
    {draftDirty && <p className="error">{l.drafted}</p>}
    <p className={data.sporting_calendar_supported_by_legacy_writers ? 'status' : 'error'}>
      {data.sporting_calendar_supported_by_legacy_writers ? l.supported : l.noSupport}
    </p>
    {next
      ? <p><strong>{l.help}: </strong>
          <Link to={base + href[next]}>{l.action[next]} →</Link>
        </p>
      : <p className="status">{l.allSaved}</p>}
    <details>
      <summary>{l.details}</summary>
      <p>Saved HEAD: <code>{data.saved_revision_id}</code></p>
      <p>SHA256: <code>{data.saved_revision_content_hash}</code></p>
      <p>Draft version: {data.draft_version}</p>
      <p>{l.history}: {data.saved_transition_count}
        {' · '}{l.task}: {data.active_full_simulation_task_count}
        / {data.historical_full_simulation_task_count}</p>
    </details>
  </section>
}

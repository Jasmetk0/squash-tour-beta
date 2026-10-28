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
    candidateLink: 'Prohlédnout kandidáty rankingu',
    rankingLimit: 'U tohoto kalendáře není dostupný starší postup publikace prvního rankingu. Kandidáty lze prohlížet samostatně; publikaci musí povolit příslušný postup.',
    draftSave: 'Historie větví sama neukládá Working Draft. Změny ulož výslovně v editoru, ve kterém vznikly.',
    action: {
      world: 'Doplnit World Package',
      calendar_package: 'Doplnit Calendar Package',
      population: 'Vygenerovat a uložit hráče',
      health: 'Otevřít hráče a jejich Health',
      official_ranking: 'Otevřít přípravu a publikaci rankingu',
      working_draft: 'Prověřit Branch a historii revizí',
    },
    allSaved: 'Kontrola uložených podkladů zde nevyžaduje další krok. Neznamená to připravenost všech operací; každá má vlastní kontrolu.',
    checklist: 'Zobrazit kontrolu uložených podkladů',
    attentionCount: (count: number) => count === 1 ? 'položka k prověření'
      : count >= 2 && count <= 4 ? 'položky k prověření' : 'položek k prověření',
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
    candidateLink: 'Inspect ranking candidates',
    rankingLimit: 'The legacy initial-ranking publication workflow is not available for this calendar. You can inspect candidates separately; publication needs its own supported operation.',
    draftSave: 'Branch history does not Save a Working Draft. Explicitly Save changes in the editor that produced them.',
    action: {
      world: 'Add a World Package',
      calendar_package: 'Add a Calendar Package',
      population: 'Generate and Save players',
      health: 'Open players and their Health',
      official_ranking: 'Open ranking preparation and publication',
      working_draft: 'Inspect Branch and revision history',
    },
    allSaved: 'This saved-foundation inspection has no further action. It does not certify all operations; each requires its own preflight.',
    checklist: 'Show saved-foundation checks',
    attentionCount: (count: number) => count === 1 ? 'item needing attention' : 'items needing attention',
    details: 'Technical provenance and limits',
    branch: 'Selected Branch',
    calendar: 'Run calendar',
    weeks: 'weeks per season',
    seasons: 'seasons',
    revision: 'Saved Revision HEAD',
    draftVersion: 'Working Draft version',
  }
} as const

// Store evidence labels by foundation/status, pairing languages at the leaf.
// This avoids two duplicated blocks whose drift could misstate Saved authority.
const detailText = {
  cleanDraft: {
    cs: 'Čistý Working Draft',
    en: 'Clean Working Draft',
  },
  cleanDraftMeaning: {
    cs: 'Tento Working Draft nemá čekající změny; ostatní editory se posuzují samostatně.',
    en: 'This Working Draft has no pending changes; other editors remain separate.',
  },
  unit: {
    world: { cs: 'Entity World Package', en: 'World entities' },
    calendar_package: { cs: 'Entity Calendar Package', en: 'Calendar entities' },
    population: { cs: 'Hráči počáteční populace', en: 'Initial-population players' },
    health: { cs: 'Health záznamy', en: 'Health records' },
    official_ranking: { cs: 'Publikace rankingu', en: 'Ranking publications' },
    working_draft: { cs: 'Nevyřízené změny', en: 'Pending changes' },
  },
  evidence: {
    world: {
      cs: 'Jde o entity World Package vlastněné Runem v uložené revizi.',
      en: 'Counts Run-owned World Package entities in this Saved Revision.',
    },
    calendar_package: {
      cs: 'Jde o entity Calendar Package v uložené revizi, nikoliv nastavení počtu týdnů Runu.',
      en: 'Counts Calendar Package entities in this Saved Revision, not the Run week-count configuration.',
    },
    population: {
      cs: 'Jde jen o uloženou počáteční populaci, nikoliv všechny hráče z pozdější historie.',
      en: 'Counts only saved initial-population players, not every player from later history.',
    },
    health: {
      cs: 'Jde o uložené Health záznamy, nikoliv o kontrolu zdravotní způsobilosti k zápasu.',
      en: 'Counts Saved Health records, not match-specific medical clearance.',
    },
    official_ranking: {
      cs: 'Počítají se skutečné uložené publikace; kandidátní pořadí není publikované.',
      en: 'Counts actually saved ranking publications; candidate rankings are not publications.',
    },
    working_draft: {
      cs: 'Počítají se změny tohoto Working Draftu; jiné rozpracované editory nejsou zahrnuté.',
      en: 'Counts this Branch Working Draft changes; other unfinished editors are outside this check.',
    },
  },
  explanationByStatus: {
    saved: {
      cs: 'Tato evidence existuje, ale neznamená připravenost všech operací.',
      en: 'This evidence exists, but it does not certify readiness for every operation.',
    },
    missing: {
      cs: 'V této uložené revizi se podklad nenašel. Potřebu určí kontrola konkrétní operace.',
      en: 'No matching evidence in this Saved Revision. Each operation checks its own prerequisites.',
    },
    candidate_only: {
      cs: 'Kandidátní data nejsou publikovanou autoritou; případné použití vyžaduje zvláštní potvrzení.',
      en: 'Candidate data is not published authority; any adoption needs separate confirmation.',
    },
    unsaved: {
      cs: 'Tyto změny dosud nejsou součástí Saved Revision; uložení vyžaduje výslovný krok.',
      en: 'These changes are not in the Saved Revision yet; an explicit Save is required.',
    },
    optional: {
      cs: 'Tato kontrola podklad zde nevyžaduje; jiná operace jej vyžadovat může.',
      en: 'This check does not require this foundation here; another operation may.',
    },
  },
} as const

const href: Record<Exclude<RunReadinessCode, 'official_ranking'>, string> = {
  world: '/manage',
  calendar_package: '/manage',
  population: '/players/generate',
  health: '/players',
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
  const target = (code: RunReadinessCode): string => code === 'official_ranking'
    ? data.sporting_calendar_supported_by_legacy_writers
      ? base + '#run-initial-ranking'
      : base + '/branches/' + encodeURIComponent(data.branch_id) + '/ranking-candidates'
    : base + href[code]
  const action = (code: RunReadinessCode): string => code === 'official_ranking'
    && !data.sporting_calendar_supported_by_legacy_writers ? l.candidateLink : l.action[code]
  return <section aria-label={language === 'cs' ? 'Připravenost Runu' : 'Run saved readiness'} className="run-home-status-block">
    <div className="actions">
      <h3>{l.heading}</h3>
      <button type="button" disabled={refreshing} onClick={refresh}>{refreshing ? l.loading : l.refresh}</button>
    </div>
    <p className="status">{l.explanation} · {l.phase[data.phase]}</p>
    <details className="run-home-readiness-checklist">
      <summary>{l.checklist} ({data.items.length}){attentionCount > 0 ? ` · ${attentionCount} ${l.attentionCount(attentionCount)}` : ''}</summary>
      <ul className="run-home-feed" aria-label={language === 'cs' ? 'Kontrola uložených podkladů' : 'Saved preparation checks'}>
        {data.items.map(item => <li key={item.code}>
          <span><strong>{l.item[item.code]}</strong>
            <small>{item.code === 'working_draft' && item.status === 'saved'
              ? detailText.cleanDraft[language] : l.status[item.status]} · {detailText.unit[item.code][language]}: {item.evidence_count}</small>
            <small className="status">{detailText.evidence[item.code][language]} {item.code === 'working_draft' && item.status === 'saved'
              ? detailText.cleanDraftMeaning[language] : detailText.explanationByStatus[item.status][language]}</small>
          </span>
          {needsAttention(item) &&
            <Link to={target(item.code)}>{action(item.code)} →</Link>}
        </li>)}
      </ul>
    </details>
    {draftDirty && <p className="error">{l.drafted} {l.draftSave}</p>}
    {!data.sporting_calendar_supported_by_legacy_writers && data.items.some(item =>
      item.code === 'official_ranking' && needsAttention(item)) &&
      <p className="status">{l.rankingLimit}</p>}
    <p className="status">
      {data.sporting_calendar_supported_by_legacy_writers ? l.supported : l.noSupport}
    </p>
    {next
      ? <p><strong>{l.help}: </strong>
          <Link to={target(next)}>{action(next)} →</Link>
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

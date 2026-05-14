import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TournamentTemplatesPage } from './TournamentTemplatesPage'

import { ViewerRunSelector } from '../components/ViewerRunSelector'
import { VIEWER_ACTIVE_RUN_CHANGED_EVENT, readViewerActiveRunId } from '../viewer/activeRun'

type LinkCard = {
  title: string
  description: string
  to: string
}

function useViewerActiveRunId(): string | null {
  const [activeRunId, setActiveRunId] = useState(() => readViewerActiveRunId())

  useEffect(() => {
    function handleActiveRunChange(): void {
      setActiveRunId(readViewerActiveRunId())
    }

    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, handleActiveRunChange)
    window.addEventListener('storage', handleActiveRunChange)
    return () => {
      window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, handleActiveRunChange)
      window.removeEventListener('storage', handleActiveRunChange)
    }
  }, [])

  return activeRunId
}

function LinkCardGrid({ cards }: { cards: LinkCard[] }): JSX.Element {
  return (
    <div className="mode-card-grid">
      {cards.map((card) => (
        <Link className="mode-card" to={card.to} key={card.to}>
          <strong>{card.title}</strong>
          <span>{card.description}</span>
        </Link>
      ))}
    </div>
  )
}

function ViewerRunScopedSuggestion({ page }: { page: string }): JSX.Element {
  const activeRunId = useViewerActiveRunId()
  if (!activeRunId) {
    return (
      <div className="empty-state">
        <p className="status">Select a Viewer run first.</p>
        <p>Viewer pages need an explicit generated world/run before they can show run-scoped data.</p>
        <ViewerRunSelector />
      </div>
    )
  }

  return (
    <p className="status">
      Viewing run: <strong>{activeRunId}</strong>. Open{' '}
      <Link to={`/viewer/runs/${activeRunId}/${page}`}>{page}</Link>.
    </p>
  )
}

function AdminRunScopedSuggestion({ page }: { page: string }): JSX.Element {
  const lastRunId = typeof window === 'undefined' ? null : window.localStorage.getItem('beta_engine:last_run_id')
  if (!lastRunId) {
    return (
      <p className="status">
        Open a run from <Link to="/admin/runs">Runs</Link> to view run-scoped data.
      </p>
    )
  }

  return (
    <p className="status">
      Last opened run: <Link to={`/admin/runs/${lastRunId}/${page}`}>{lastRunId}</Link>
    </p>
  )
}

export function LandingPage(): JSX.Element {
  return (
    <section className="panel landing-panel">
      <div className="page-intro">
        <h2>Squash Tour Beta Engine</h2>
        <p className="subtitle">Choose how you want to use the deterministic FAX squash world.</p>
      </div>
      <div className="mode-choice-grid">
        <Link className="mode-choice mode-choice--viewer" to="/viewer">
          <span className="eyebrow">Viewer / MSA Website Mode</span>
          <strong>Browse the generated squash world</strong>
          <span>Rankings, tournaments, players, countries, history, and records in a public sports-site view.</span>
        </Link>
        <Link className="mode-choice mode-choice--admin" to="/admin">
          <span className="eyebrow">Admin / Engine Mode</span>
          <strong>Build, validate, and simulate the world</strong>
          <span>World setup, generation, run control, simulation commands, diagnostics, and engine tools.</span>
        </Link>
      </div>
    </section>
  )
}

export function AdminHomePage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Admin Engine Dashboard</h2>
        <p className="subtitle">Operational workspace for building, editing, validating, regenerating, and simulating worlds.</p>
      </div>
      <LinkCardGrid
        cards={[
          { title: 'World', description: 'Country configuration, talent setup, overrides, and world package tools.', to: '/admin/world' },
          { title: 'Tournament Templates', description: 'Future reusable category/template definitions.', to: '/admin/tournament-templates' },
          { title: 'Seasons', description: 'Season and calendar planning workspace.', to: '/admin/seasons' },
          { title: 'Players', description: 'Generation, override, and future lock/regeneration controls.', to: '/admin/players' },
          { title: 'Simulate', description: 'Open run controls for next match, round, tournament, week, or full season.', to: '/admin/simulate' },
          { title: 'Runs', description: 'Create, resume, inspect, and operate simulation runs.', to: '/admin/runs' },
          { title: 'Diagnostics', description: 'Run/world status, validation, and replay inspection tools.', to: '/admin/diagnostics' }
        ]}
      />
    </section>
  )
}

export function ViewerHomePage(): JSX.Element {
  const activeRunId = useViewerActiveRunId()
  const cards = activeRunId
    ? [
        { title: 'Rankings', description: 'Official ranking snapshot browsing.', to: `/viewer/runs/${activeRunId}/rankings` },
        { title: 'Race', description: 'Seasonal race standings for Finals qualification.', to: `/viewer/runs/${activeRunId}/race` },
        { title: 'Tournaments', description: 'Tournament and finals result browsing.', to: `/viewer/runs/${activeRunId}/tournaments` },
        { title: 'Calendar', description: 'Season calendar and planned-event browsing.', to: `/viewer/runs/${activeRunId}/calendar` },
        { title: 'Players', description: 'Player index and career pages.', to: `/viewer/runs/${activeRunId}/players` },
        { title: 'Countries', description: 'Read-only nation profiles and player pipelines.', to: `/viewer/runs/${activeRunId}/countries` },
        { title: 'History', description: 'Activity, archives, weeks, and historical snapshots.', to: `/viewer/runs/${activeRunId}/history` },
        { title: 'Finals', description: 'World Tour Finals qualification and result views.', to: `/viewer/runs/${activeRunId}/finals` }
      ]
    : []

  return (
    <section className="panel viewer-home">
      <div className="page-intro">
        <h2>MSA Website Home</h2>
        <p className="subtitle">Public-style generated FAX squash world view for browsing and analysis.</p>
      </div>
      <p>
        Viewer / MSA Website Mode is the read-only public site for a generated squash world. Select the run/world first, then browse
        rankings, tournaments, players, countries, history, and Finals pages as run-scoped website sections.
      </p>
      <ViewerRunSelector />
      {activeRunId ? (
        <section className="panel nested-panel">
          <h3>Browse selected world</h3>
          <p className="status">Viewing run: {activeRunId}</p>
          <LinkCardGrid cards={cards} />
        </section>
      ) : (
        <p className="status">Select a Viewer run first to enable run-scoped MSA website links.</p>
      )}
    </section>
  )
}

export function AdminWorldPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>World</h2>
        <p className="subtitle">Admin World is the authored input workspace for country parameters, talent setup, manual overrides, package import/export, and world generation diagnostics.</p>
      </div>
      <LinkCardGrid
        cards={[
          { title: 'Countries Editor', description: 'Edit country configuration: population, culture, system quality, competition density, federation quality, courts, and style DNA.', to: '/admin/world/countries' },
          { title: 'Talent Preview', description: 'Preview deterministic talent distribution from current world inputs before creating or rebuilding runs.', to: '/admin/world/talent-preview' },
          { title: 'Manual Player Overrides', description: 'Explicit player override tools for commissioner workflows.', to: '/admin/world/manual-player-overrides' },
          { title: 'World Package', description: 'Import and export authored world configuration packages.', to: '/admin/world/package' },
          { title: 'Future: Country Momentum / Era Modifiers', description: 'Placeholder only: time-based country strength changes are planned but not implemented in Phase 2.', to: '/admin/world/countries' },
          { title: 'Future: Style DNA / Court Count Balancing', description: 'Style DNA and court count can be authored now; deeper balancing remains future deterministic tuning.', to: '/admin/world/countries' },
          { title: 'Run World Generation', description: 'Inspect generated world provenance inside a selected run.', to: '/admin/runs' }
        ]}
      />
    </section>
  )
}

export function AdminTournamentTemplatesPage(): JSX.Element {
  return <TournamentTemplatesPage />
}


export function AdminSeasonsPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Seasons</h2>
        <p className="subtitle">Season editor will manage 61 Season Weeks plus Year Week/calendar positioning.</p>
      </div>
      <p className="status">Placeholder only for Phase 1 navigation. Season Week / Year Week logic is intentionally not implemented.</p>
      <p>
        Existing run calendars remain available from <Link to="/admin/runs">Runs</Link> after opening a run.
      </p>
    </section>
  )
}

export function AdminPlayersPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Admin Players</h2>
        <p className="subtitle">Future workspace for player generation, edit, lock, and regeneration workflows.</p>
      </div>
      <LinkCardGrid
        cards={[
          { title: 'Talent Preview', description: 'Preview generated player pools before simulation.', to: '/admin/world/talent-preview' },
          { title: 'Manual Player Overrides', description: 'Manage explicit player override records.', to: '/admin/world/manual-player-overrides' },
          { title: 'Run World Generation', description: 'Inspect generated player provenance inside a selected run.', to: '/admin/runs' }
        ]}
      />
    </section>
  )
}

export function AdminSimulatePage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Simulate</h2>
        <p className="subtitle">Simulation commands remain on each run detail page so they operate against an explicit run context.</p>
      </div>
      <ul className="dashboard-help-list">
        <li>Next match</li>
        <li>Next round</li>
        <li>Next tournament</li>
        <li>Next week</li>
        <li>Full season</li>
      </ul>
      <p>
        Open a run from <Link to="/admin/runs">Runs</Link>, then use Run Detail to execute deterministic simulation commands.
      </p>
    </section>
  )
}

export function AdminDiagnosticsPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Diagnostics</h2>
        <p className="subtitle">Diagnostics are run-scoped today; open a run to inspect status, history counts, lineage, and replay artifacts.</p>
      </div>
      <AdminRunScopedSuggestion page="diagnostics" />
    </section>
  )
}

export function AdminSettingsPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Settings</h2>
        <p className="subtitle">Engine settings placeholder for future config-version and environment controls.</p>
      </div>
      <p className="status">No settings editor is implemented in Phase 1.</p>
    </section>
  )
}

export function ViewerRankingsPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Rankings</h2>
        <p className="subtitle">Read-oriented official ranking and race snapshot browsing.</p>
      </div>
      <ViewerRunScopedSuggestion page="rankings" />
    </section>
  )
}

export function ViewerTournamentsPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Tournaments</h2>
        <p className="subtitle">Read-oriented tournament, calendar, and finals browsing.</p>
      </div>
      <ViewerRunScopedSuggestion page="tournaments" />
    </section>
  )
}

export function ViewerPlayersPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Players</h2>
        <p className="subtitle">Read-oriented player index and career browsing.</p>
      </div>
      <ViewerRunScopedSuggestion page="players" />
    </section>
  )
}

export function ViewerCountriesPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Countries</h2>
        <p className="subtitle">Read-oriented nation profiles and country-level player views.</p>
      </div>
      <ViewerRunScopedSuggestion page="countries" />
    </section>
  )
}

export function ViewerHistoryPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>History</h2>
        <p className="subtitle">Read-oriented activity, archives, event history, and snapshots.</p>
      </div>
      <ViewerRunScopedSuggestion page="history" />
    </section>
  )
}

export function ViewerRecordsPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Records</h2>
        <p className="subtitle">Records and GOAT-style statistics will appear here later.</p>
      </div>
      <p className="status">Placeholder only for Phase 1 navigation. No records logic is implemented in this task.</p>
    </section>
  )
}

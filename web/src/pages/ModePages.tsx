import { Link } from 'react-router-dom'

const LAST_RUN_ID_STORAGE_KEY = 'beta_engine:last_run_id'

type LinkCard = {
  title: string
  description: string
  to: string
}

function useRememberedRunId(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(LAST_RUN_ID_STORAGE_KEY)
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

function RunScopedSuggestion({ mode, page }: { mode: 'admin' | 'viewer'; page: string }): JSX.Element {
  const lastRunId = useRememberedRunId()
  if (!lastRunId) {
    return (
      <p className="status">
        Open a run from <Link to={mode === 'admin' ? '/admin/runs' : '/admin/runs'}>Runs</Link> to view run-scoped data.
      </p>
    )
  }

  return (
    <p className="status">
      Last opened run:{' '}
      <Link to={`/${mode}/runs/${lastRunId}/${page}`}>{lastRunId}</Link>
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
  const lastRunId = useRememberedRunId()
  return (
    <section className="panel viewer-home">
      <div className="page-intro">
        <h2>MSA Website Home</h2>
        <p className="subtitle">Public-style generated FAX squash world view for browsing and analysis.</p>
      </div>
      {lastRunId ? (
        <section className="panel nested-panel">
          <h3>Latest run shortcut</h3>
          <p className="status">Continue browsing run {lastRunId} through read-only viewer sections.</p>
          <div className="actions">
            <Link to={`/viewer/runs/${lastRunId}/rankings`}>Rankings</Link>
            <Link to={`/viewer/runs/${lastRunId}/tournaments`}>Tournaments</Link>
            <Link to={`/viewer/runs/${lastRunId}/players`}>Players</Link>
            <Link to={`/viewer/runs/${lastRunId}/history`}>History</Link>
          </div>
        </section>
      ) : (
        <p className="status">No recently opened run found. Open or create a run from Admin Mode to browse generated results.</p>
      )}
      <LinkCardGrid
        cards={[
          { title: 'Rankings', description: 'Official ranking and race snapshot browsing.', to: '/viewer/rankings' },
          { title: 'Tournaments', description: 'Tournament and finals result browsing.', to: '/viewer/tournaments' },
          { title: 'Players', description: 'Player index and career pages.', to: '/viewer/players' },
          { title: 'Countries', description: 'Read-only nation profiles and player pipelines.', to: '/viewer/countries' },
          { title: 'History', description: 'Activity, archives, weeks, and historical snapshots.', to: '/viewer/history' },
          { title: 'Records', description: 'Future records and GOAT-style statistics.', to: '/viewer/records' }
        ]}
      />
    </section>
  )
}

export function AdminWorldPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>World</h2>
        <p className="subtitle">Admin tools for country config, talent setup, manual overrides, package import/export, and world generation.</p>
      </div>
      <LinkCardGrid
        cards={[
          { title: 'Countries Editor', description: 'Edit country configuration used by the engine.', to: '/admin/world/countries' },
          { title: 'Talent Preview', description: 'Preview generated talent distribution from world inputs.', to: '/admin/world/talent-preview' },
          { title: 'Manual Player Overrides', description: 'Explicit player override tools for commissioner workflows.', to: '/admin/world/manual-player-overrides' },
          { title: 'World Package', description: 'Import and export world configuration packages.', to: '/admin/world/package' },
          { title: 'Run World Generation', description: 'Inspect generated world provenance inside a selected run.', to: '/admin/runs' }
        ]}
      />
    </section>
  )
}

export function AdminTournamentTemplatesPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Tournament Templates</h2>
        <p className="subtitle">
          Tournament Template editor will define reusable categories such as World Championship, Diamond, Emerald, Platinum, Gold,
          Silver, Bronze, Elite, Challenger, Future.
        </p>
      </div>
      <p className="status">Placeholder only for Phase 1 navigation. No template editor logic is implemented in this task.</p>
    </section>
  )
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
      <RunScopedSuggestion mode="admin" page="diagnostics" />
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
      <RunScopedSuggestion mode="viewer" page="rankings" />
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
      <RunScopedSuggestion mode="viewer" page="tournaments" />
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
      <RunScopedSuggestion mode="viewer" page="players" />
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
      <RunScopedSuggestion mode="viewer" page="countries" />
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
      <RunScopedSuggestion mode="viewer" page="history" />
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

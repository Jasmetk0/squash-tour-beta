import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AdminPlayersPage as InitialPoolAdminPlayersPage } from './AdminPlayersPage'
import { AdminPlayersHubPage } from './AdminPlayersHubPage'
import { AdminSeasonsPage as SeasonBootstrapAdminSeasonsPage } from './AdminSeasonsPage'
import { TournamentTemplatesPage } from './TournamentTemplatesPage'
import { getCountriesMetadata, getTournamentTemplatesMetadata, listRuns } from '../api/client'

import { LinkCardGrid } from '../components/LinkCardGrid'
import { ViewerRunSelector } from '../components/ViewerRunSelector'
import { SectionCard } from '../components/RunScopedUi'
import { ViewerRankingsReadOnlyPage } from './RankingTables'
import { VIEWER_ACTIVE_RUN_CHANGED_EVENT, readViewerActiveRunId } from '../viewer/activeRun'

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
  const countriesQuery = useQuery({ queryKey: ['admin-dashboard-countries-metadata'], queryFn: getCountriesMetadata, retry: false })
  const templatesQuery = useQuery({ queryKey: ['admin-dashboard-tournament-templates-metadata'], queryFn: getTournamentTemplatesMetadata, retry: false })
  const runsQuery = useQuery({ queryKey: ['admin-dashboard-runs'], queryFn: listRuns, retry: false })
  const latestRun = useMemo(() => runsQuery.data?.runs[runsQuery.data.runs.length - 1] ?? null, [runsQuery.data?.runs])

  const statusCards = [
    { label: 'Active world', value: latestRun ? latestRun.run_id : 'Not available yet' },
    { label: 'Active season', value: latestRun ? String(latestRun.season) : 'Not available yet' },
    { label: 'Current season week', value: 'Pending backend integration' },
    { label: 'Current calendar year/week', value: 'Pending backend integration' },
    { label: 'Countries', value: countriesQuery.data ? String(countriesQuery.data.country_count) : countriesQuery.isLoading ? 'Loading…' : 'Not available yet' },
    { label: 'Players', value: 'Run-scoped; open a run' },
    { label: 'Tournament templates', value: templatesQuery.data ? String(templatesQuery.data.template_count) : templatesQuery.isLoading ? 'Loading…' : 'Not available yet' },
    { label: 'Scheduled events', value: latestRun ? String(latestRun.progress.total_events) : 'Not available yet' },
    { label: 'Simulation status', value: latestRun ? `${latestRun.progress.completed_event_count}/${latestRun.progress.total_events} events complete` : 'Not running' },
    { label: 'Validation issues', value: countriesQuery.isError || templatesQuery.isError ? 'Metadata unavailable' : 'No dashboard validation feed yet' },
    { label: 'Stale/invalid history warnings', value: 'Pending backend integration' }
  ]

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Admin Engine Dashboard</h2>
        <p className="subtitle">Operational workspace for building, editing, validating, regenerating, and simulating worlds.</p>
      </div>
      <div className="dashboard-grid">
        {statusCards.map((card) => (
          <article className="metric-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </article>
        ))}
      </div>
      <p className="status">Dashboard cards use available backend metadata where present and explicit placeholders where backend status is not exposed yet.</p>
      <LinkCardGrid
        cards={[
          { title: 'World', description: 'Countries, Talent Preview, and world model inputs.', to: '/admin/world' },
          { title: 'Players', description: 'Player database, future Talent Intake, custom players, locks, and audits.', to: '/admin/players' },
          { title: 'Tour & Seasons', description: 'Categories, tournaments, season templates, concrete calendars, and validation. Includes existing Tournament Templates and Seasons pages.', to: '/admin/tour-seasons' },
          { title: 'Runs', description: 'Master Run and sandbox run management.', to: '/admin/runs' },
          { title: 'Simulate', description: 'Simulation launcher for match, round, tournament, week, season, and full timeline.', to: '/admin/simulate' },
          { title: 'Diagnostics', description: 'World balance, calendar validation, run health, invalidated data, and future narrative locks.', to: '/admin/diagnostics' }
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
        <p className="subtitle">Manage country inputs and expected talent output used by the FAX squash simulation engine.</p>
      </div>
      <LinkCardGrid
        cards={[
          {
            title: 'Countries',
            description: 'Edit country inputs, country model data, style DNA, and future country profiles.',
            to: '/admin/world/countries'
          },
          {
            title: 'Talent Preview',
            description: 'Preview expected Elite Talents, Tour Talents, and Pro Depth by country before generating player intakes.',
            to: '/admin/world/talent-preview'
          },
        ]}
      />
    </section>
  )
}


export function AdminTourSeasonsPage(): JSX.Element {
  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Tour & Seasons</h2>
        <p className="subtitle">Manage categories, recurring tournaments, season templates, concrete season calendars, and validation workflows.</p>
      </div>
      <LinkCardGrid
        cards={[
          {
            title: 'Categories',
            description: 'Rules packages valid across season ranges. Transitional: currently managed through Tournament Templates tooling.',
            to: '/admin/tour-seasons/categories'
          },
          {
            title: 'Tournaments',
            description: 'Reusable master tournament brands. Planned split from category/template tooling.',
            to: '/admin/tour-seasons/tournaments'
          },
          {
            title: 'Season Templates',
            description: 'Reusable calendar plans that can be copied into concrete seasons.',
            to: '/admin/tour-seasons/season-templates'
          },
          {
            title: 'Seasons',
            description: 'Concrete 61-week season calendars from 2000/01 through 2039/40.',
            to: '/admin/seasons'
          },
          {
            title: 'Calendar Compare / Apply',
            description: 'Planned workflow for comparing seasons/templates and applying event-level decisions.',
            to: '/admin/tour-seasons/compare'
          },
          {
            title: 'Calendar Validation',
            description: 'Planned validation hub for week blocks, draw footprints, mandatory events, and schedule conflicts.',
            to: '/admin/tour-seasons/validation'
          }
        ]}
      />
    </section>
  )
}

export function AdminTournamentTemplatesPage(): JSX.Element {
  return <TournamentTemplatesPage />
}


export function AdminSeasonsPage(): JSX.Element {
  return <SeasonBootstrapAdminSeasonsPage />
}


export function AdminPlayersPage(): JSX.Element {
  return <AdminPlayersHubPage />
}

export function AdminPlayersDatabasePage(): JSX.Element {
  return <InitialPoolAdminPlayersPage />
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
  return <ViewerRankingsReadOnlyPage />
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

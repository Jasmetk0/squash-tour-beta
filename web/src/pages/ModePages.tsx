import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AdminPlayersPage as InitialPoolAdminPlayersPage } from './AdminPlayersPage'
import { AdminPlayersHubPage } from './AdminPlayersHubPage'
import { AdminSeasonsPage as SeasonBootstrapAdminSeasonsPage } from './AdminSeasonsPage'
import { TournamentTemplatesPage } from './TournamentTemplatesPage'
import { getCountriesMetadata, getTournamentTemplatesMetadata, listRuns } from '../api/client'

import { LinkCardGrid } from '../components/LinkCardGrid'
import { ViewerJumpToWeekButton } from '../components/ViewerContextControls'
import { useViewerContext } from '../viewer/ViewerContext'

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
            title: 'Season Registry',
            description: 'Read-only fixed registry for seasons 2000/01 through 2039/40, 61 weeks per season, SW1 = YW37.',
            to: '/admin/tour-seasons/season-registry'
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


type ViewerShellPageProps = {
  title: string
  kicker?: string
  description?: string
  children?: ReactNode
}

function ViewerContextLine(): JSX.Element {
  const context = useViewerContext()
  return (
    <p className="status">
      Viewer context: Season {context.selectedSeason} · W{context.selectedWeek}. This page is read-only and uses scaffold content until the relevant backend read model is connected.
    </p>
  )
}

export function ViewerShellPage({ title, kicker = 'Viewer read-only scaffold', description, children }: ViewerShellPageProps): JSX.Element {
  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <span className="eyebrow">{kicker}</span>
        <h2>{title}</h2>
        <p className="subtitle">
          {description ?? 'This sports-facing Viewer section is a safe Phase 1A shell. Future data will connect here without adding mutating controls.'}
        </p>
      </div>
      <ViewerContextLine />
      {children ?? <p className="empty-state">No authoritative backend data is rendered for this section in Viewer Phase 1A.</p>}
    </section>
  )
}

export function ViewerHomePage(): JSX.Element {
  const context = useViewerContext()
  const cards = [
    'Featured Tournament Hero',
    'Other Tournaments This Week',
    'Top 10 Rankings',
    'Race to Finals',
    'Featured Matches',
    'Predictions & Upset Watch',
    'Storylines'
  ]

  return (
    <section className="panel viewer-home viewer-home--msa">
      <div className="page-intro viewer-home__hero">
        <span className="eyebrow">MSA Homepage</span>
        <h2>MSA Squash — Season {context.selectedSeason} · W{context.selectedWeek}</h2>
        <p className="subtitle">
          Public-style, read-only squash tour homepage shell for the selected Viewer context. Data cards are intentionally empty until read models are connected.
        </p>
      </div>
      <div className="viewer-home-grid">
        {cards.map((title) => (
          <article key={title} className="viewer-home-card">
            <h3>{title}</h3>
            <p className="status">Viewer read-only scaffold — no authoritative data is available in Phase 1A.</p>
          </article>
        ))}
      </div>
    </section>
  )
}

export function ViewerRankingsPage(): JSX.Element {
  return <ViewerShellPage title="MSA Rankings" description="Official ranking table shell for the selected Season/Week context." />
}

export function ViewerTournamentsPage(): JSX.Element {
  return <ViewerShellPage title="All Tournaments" description="Tournament database shell for future read-only filtering and archives." />
}

export function ViewerPlayersPage(): JSX.Element {
  return <ViewerShellPage title="Players Hub" description="Player spotlight and browse hub shell for the selected Viewer context." />
}

export function ViewerCountriesPage(): JSX.Element {
  return <ViewerShellPage title="Countries Hub" description="Country overview shell for national rankings, hosting, pipelines, and records." />
}

export function ViewerHistoryPage(): JSX.Element {
  return <ViewerShellPage title="History" description="Read-only history shell retained for run-scoped archive entry points." />
}

export function ViewerRecordsPage(): JSX.Element {
  return <ViewerShellPage title="Records" description="Record book landing shell for statistics and historical achievements." />
}

export function ViewerTourCalendarPage(): JSX.Element {
  return (
    <ViewerShellPage title="Season Calendar" description="Calendar shell demonstrating the reusable Jump to Week primitive without backend mutation.">
      <div className="viewer-jump-demo" aria-label="Jump to Week demo">
        <p className="status">Demo card for future calendar/event cards.</p>
        <ViewerJumpToWeekButton week={24} />
      </div>
    </ViewerShellPage>
  )
}

export function ViewerCountryRankingPage(): JSX.Element {
  return <ViewerShellPage title="Country Ranking" description="Shared Country Ranking destination used by Rankings and Countries navigation." />
}

export function ViewerPlayerComparisonPage(): JSX.Element {
  return <ViewerShellPage title="Player Comparison" description="Shared Player Comparison destination used by Players and H2H navigation." />
}

export function ViewerMatchPredictorPage(): JSX.Element {
  return <ViewerShellPage title="Match Predictor" description="Shared read-only predictor shell used by H2H and Predictions navigation." />
}

export function ViewerFinalsReadOnlyPage(): JSX.Element {
  return <ViewerShellPage title="World Tour Finals" description="Read-only Finals shell. Admin simulation controls are intentionally not rendered in Viewer." />
}

export function ViewerPlannedEventReadOnlyPage(): JSX.Element {
  return <ViewerShellPage title="Planned Event" description="Read-only planned event detail shell. Commissioner event controls are intentionally not rendered in Viewer." />
}

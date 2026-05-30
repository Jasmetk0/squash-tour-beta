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
      Viewer context: Season {context.selectedSeason} · W{context.selectedWeek}. This section is ready for read-only tour data once the Viewer read model is connected.
    </p>
  )
}

export function ViewerShellPage({ title, kicker = 'Read-only Viewer section', description, children }: ViewerShellPageProps): JSX.Element {
  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <span className="eyebrow">{kicker}</span>
        <h2>{title}</h2>
        <p className="subtitle">
          {description ?? 'This Viewer section is ready for read-only data. Future tour information will appear here once the read model is connected.'}
        </p>
      </div>
      <ViewerContextLine />
      {children ?? <p className="empty-state">No authoritative data is shown in this Phase 1B shell.</p>}
    </section>
  )
}

export function ViewerHomePage(): JSX.Element {
  const context = useViewerContext()
  const cards = [
    {
      title: 'Featured Tournament Hero',
      subtitle: 'The marquee tournament spotlight is reserved for the current Viewer week once authoritative event data is available.',
      tone: 'hero'
    },
    {
      title: 'Other Tournaments This Week',
      subtitle: 'A read-only weekly schedule lane for additional tour stops in the selected context.',
      tone: 'standard'
    },
    {
      title: 'Top 10 Rankings',
      subtitle: 'The leading ranking table will surface here after the official Viewer rankings read model is connected.',
      tone: 'standard'
    },
    {
      title: 'Race to Finals',
      subtitle: 'Season-long qualification standings will appear here without exposing engine controls or future knowledge.',
      tone: 'standard'
    },
    {
      title: 'Featured Matches',
      subtitle: 'Match cards are prepared for notable fixtures, rivalry hooks, and selected-week score browsing.',
      tone: 'standard'
    },
    {
      title: 'Predictions & Upset Watch',
      subtitle: 'Prediction surfaces remain read-only and will stay empty until deterministic analytics are available.',
      tone: 'standard'
    },
    {
      title: 'Storylines',
      subtitle: 'Editorial-style storyline cards will summarize real simulated context when the history feed supports them.',
      tone: 'standard'
    }
  ]

  return (
    <section className="panel viewer-home viewer-home--msa">
      <div className="page-intro viewer-home__hero">
        <span className="eyebrow">MSA Homepage</span>
        <h2>MSA Squash — Season {context.selectedSeason} · W{context.selectedWeek}</h2>
        <p className="subtitle">
          A premium, public-style squash tour homepage for the selected Viewer context. These cards are intentionally read-only and do not show authoritative data until the connected read models are ready.
        </p>
      </div>
      <div className="viewer-home-grid">
        {cards.map((card) => (
          <article key={card.title} className={`viewer-home-card viewer-home-card--${card.tone}`}>
            <span className="eyebrow">Read-only scaffold</span>
            <h3>{card.title}</h3>
            <p>{card.subtitle}</p>
            <p className="status">No authoritative data is shown in this Phase 1B shell.</p>
          </article>
        ))}
      </div>
    </section>
  )
}

export function ViewerRankingsPage(): JSX.Element {
  return <ViewerShellPage title="MSA Rankings" description="Official rankings destination for the selected Season/Week context. Future rankings data will appear here once the read model is connected." />
}

export function ViewerTournamentsPage(): JSX.Element {
  return <ViewerShellPage title="All Tournaments" description="Tournament archive destination prepared for read-only schedules, results, and historical browsing." />
}

export function ViewerPlayersPage(): JSX.Element {
  return <ViewerShellPage title="Players Hub" description="Player hub prepared for read-only spotlights, profiles, and browsing in the selected Viewer context." />
}

export function ViewerCountriesPage(): JSX.Element {
  return <ViewerShellPage title="Countries Hub" description="Country hub prepared for read-only national rankings, hosting stories, talent pipelines, and records." />
}

export function ViewerHistoryPage(): JSX.Element {
  return <ViewerShellPage title="History" description="History destination prepared for read-only activity, archive, and storyline browsing." />
}

export function ViewerRecordsPage(): JSX.Element {
  return <ViewerShellPage title="Records" description="Record book destination prepared for statistics, milestones, and historical achievements." />
}

export function ViewerTourCalendarPage(): JSX.Element {
  return (
    <ViewerShellPage title="Season Calendar" description="Season calendar destination prepared for weekly tour browsing and read-only event cards.">
      <div className="viewer-jump-demo" aria-label="Jump to Week demo">
        <p className="status">Sample calendar card for future read-only weekly event browsing.</p>
        <ViewerJumpToWeekButton week={24} />
      </div>
    </ViewerShellPage>
  )
}

export function ViewerCountryRankingPage(): JSX.Element {
  return <ViewerShellPage title="Country Ranking" description="Shared Country Ranking destination used by Rankings and Countries navigation. Future country standings will appear here once connected." />
}

export function ViewerPlayerComparisonPage(): JSX.Element {
  return <ViewerShellPage title="Player Comparison" description="Shared Player Comparison destination used by Players and H2H navigation. Future comparison data will remain read-only." />
}

export function ViewerMatchPredictorPage(): JSX.Element {
  return <ViewerShellPage title="Match Predictor" description="Shared read-only predictor destination used by H2H and Predictions navigation. No predictions are shown until deterministic analytics are connected." />
}

export function ViewerFinalsReadOnlyPage(): JSX.Element {
  return <ViewerShellPage title="World Tour Finals" description="Read-only World Tour Finals destination. Draws, qualification, and results can be surfaced here without Viewer simulation controls." />
}

export function ViewerPlannedEventReadOnlyPage(): JSX.Element {
  return <ViewerShellPage title="Planned Event" description="Read-only planned event destination. Event context can be surfaced here without commissioner controls." />
}

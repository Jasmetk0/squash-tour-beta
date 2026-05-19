import { type ReactNode, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AdminPlayersPage as InitialPoolAdminPlayersPage } from './AdminPlayersPage'
import { AdminPlayersHubPage } from './AdminPlayersHubPage'
import { AdminSeasonsPage as SeasonBootstrapAdminSeasonsPage } from './AdminSeasonsPage'
import { TournamentTemplatesPage } from './TournamentTemplatesPage'
import { getCountriesMetadata, getTournamentTemplatesMetadata, listRuns } from '../api/client'

import { ViewerRunSelector } from '../components/ViewerRunSelector'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { ViewerRankingsReadOnlyPage } from './RankingTables'
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

function TourSeasonsShellPage({
  title,
  subtitle,
  children
}: {
  title: string
  subtitle: string
  children: ReactNode
}): JSX.Element {
  return (
    <section className="panel">
      <PageIntro title={title} subtitle={subtitle} />
      <SectionCard title="Planned model">
        {children}
      </SectionCard>
      <SectionCard title="Current tooling">
        <p>
          This page is a transitional shell. Continue operational editing in{' '}
          <Link to="/admin/tournament-templates">Tournament Templates</Link> and{' '}
          <Link to="/admin/seasons">Seasons</Link>.
        </p>
        <p>
          Return to the <Link to="/admin/tour-seasons">Tour &amp; Seasons hub</Link>.
        </p>
      </SectionCard>
    </section>
  )
}

export function AdminTourSeasonsCategoriesPage(): JSX.Element {
  return (
    <TourSeasonsShellPage title="Categories" subtitle="Category = rules package valid for a season range.">
      <p>Examples: Diamond 2000/01–2015/16 and Diamond 2016/17–2039/40.</p>
      <p>
        Planned category fields: category name, valid season range, tour level, prestige rank, mandatory flag, main draw size,
        qualification draw size, direct entries, qualifiers, wildcards, lucky losers, seeds count, points by round, prize money,
        match format, entry rules, qualification rules, and schedule footprint.
      </p>
      <p>
        Transitional: currently managed through <Link to="/admin/tournament-templates">Tournament Templates tooling</Link>.
      </p>
    </TourSeasonsShellPage>
  )
}

export function AdminTourSeasonsTournamentsPage(): JSX.Element {
  return (
    <TourSeasonsShellPage title="Tournaments" subtitle="Tournament = reusable master tournament brand.">
      <p>Examples: Némarque Open, Ameriga Open, Bogemia Gold, and World Championship.</p>
      <p>
        Concrete season edition example: Némarque Open 2030/31. Entries, draw, results, champion, and points awarded belong to
        the edition, not the master tournament.
      </p>
      <p>
        Planned split from category/template tooling. Use <Link to="/admin/tournament-templates">Tournament Templates</Link> for
        current operations.
      </p>
    </TourSeasonsShellPage>
  )
}

export function AdminTourSeasonsSeasonTemplatesPage(): JSX.Element {
  return (
    <TourSeasonsShellPage title="Season Templates" subtitle="Reusable calendar plans that can be copied into concrete seasons.">
      <p>
        Season creation is planned to support: blank calendar, season template, another season, tournament copied from anywhere,
        or blank custom tournament.
      </p>
      <p>
        Current operational calendar tooling remains in <Link to="/admin/seasons">Seasons</Link>.
      </p>
    </TourSeasonsShellPage>
  )
}

export function AdminTourSeasonsComparePage(): JSX.Element {
  return (
    <TourSeasonsShellPage title="Calendar Compare / Apply" subtitle="Compare a current season with a template or another season.">
      <p>Planned statuses: Same, Modified, Missing from current, Only in current, and Conflict.</p>
      <p>Planned actions: Apply to this season, Replace current, Keep current, Ignore, and Open editor.</p>
      <p>
        Current operational calendar editing remains in <Link to="/admin/seasons">Seasons</Link>.
      </p>
    </TourSeasonsShellPage>
  )
}

export function AdminTourSeasonsValidationPage(): JSX.Element {
  return (
    <TourSeasonsShellPage title="Calendar Validation" subtitle="Validation hub for deterministic season schedule safety checks.">
      <ul className="dashboard-help-list">
        <li>W01–W61 range</li>
        <li>Multi-week blocks must be consecutive</li>
        <li>Qualifying must be before main draw</li>
        <li>Diamond: 1 qualifying week + 2 main draw weeks (if applicable)</li>
        <li>Mandatory events present</li>
        <li>Schedule conflicts</li>
        <li>Invalid or missing category or host</li>
      </ul>
      <p>
        For current workflows, use <Link to="/admin/seasons">Seasons</Link> and{' '}
        <Link to="/admin/diagnostics">Diagnostics</Link>.
      </p>
    </TourSeasonsShellPage>
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


export function AdminSimulatePage(): JSX.Element {
  const lastRunId = typeof window === 'undefined' ? null : window.localStorage.getItem('beta_engine:last_run_id')

  const levelCards: LinkCard[] = [
    {
      title: 'Match',
      description:
        'Simulate or manually enter one match result. Future controls support lock/unlock and downstream invalidation.',
      to: lastRunId ? `/admin/runs/${lastRunId}` : '/admin/runs#match'
    },
    {
      title: 'Round',
      description: 'Simulate all unlocked matches in a tournament round.',
      to: lastRunId ? `/admin/runs/${lastRunId}/events` : '/admin/runs#round'
    },
    {
      title: 'Tournament',
      description: 'Simulate or resimulate a tournament/event block, respecting locked/manual results.',
      to: lastRunId ? `/admin/runs/${lastRunId}/events` : '/admin/runs#tournament'
    },
    {
      title: 'Week',
      description: 'Simulate a season week. Multi-week tournaments may only advance the portion assigned to that week.',
      to: lastRunId ? `/admin/runs/${lastRunId}/calendar` : '/admin/runs#week'
    },
    {
      title: 'Season',
      description: 'Simulate rest of season or selected season-week range.',
      to: lastRunId ? `/admin/runs/${lastRunId}` : '/admin/runs#season'
    },
    {
      title: 'Full Timeline',
      description: 'Future high-risk action to simulate through 2039/40. Requires explicit confirmation when implemented.',
      to: '/admin/runs#timeline'
    }
  ]

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Simulate</h2>
        <p className="subtitle">Simulation launcher for match, round, tournament, week, season, and full timeline workflows.</p>
      </div>

      <SectionCard title="Transitional note">
        <p className="status">
          Top-level launcher is being aligned with the target simulation model. Real deterministic commands currently remain run-scoped in Run Detail and related run pages.
        </p>
      </SectionCard>

      <SectionCard title="Choose active run">
        <p>Open a run first. Simulation commands operate against an explicit run context.</p>
        <p>
          <Link to="/admin/runs">Open Runs</Link>
          {lastRunId ? (
            <>
              {' '}· Last opened run:{' '}
              <Link to={`/admin/runs/${lastRunId}`}>{lastRunId}</Link>
            </>
          ) : (
            <> · No run has been opened in this browser yet.</>
          )}
        </p>
      </SectionCard>

      <SectionCard title="Simulation levels">
        <LinkCardGrid cards={levelCards} />
      </SectionCard>

      <SectionCard title="Shortcut concepts">
        <ul className="dashboard-help-list">
          <li><strong>Next Match</strong> — Status: Existing in run detail. Advances one deterministic match in the selected run.</li>
          <li><strong>Next Round</strong> — Status: Existing in run detail. Advances all eligible matches in the current round.</li>
          <li><strong>Next Tournament</strong> — Status: Existing in run detail. Advances tournament scope within run context.</li>
          <li><strong>Next Week</strong> — Status: Existing in run detail. Needed separately because tournaments can span multiple weeks.</li>
          <li><strong>Rest of Season</strong> — Status: Run-scoped today. Full season command is available from run detail quick actions.</li>
          <li><strong>Full Timeline</strong> — Status: Planned. Not implemented as a top-level launcher action yet.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Manual controls / locks (planned model)">
        <p className="status">
          Manual results and locks are future central launcher concepts unless already supported in run-scoped event/run pages.
        </p>
        <ul className="dashboard-help-list">
          <li>simulate</li>
          <li>resimulate</li>
          <li>resimulate unlocked</li>
          <li>enter manual result</li>
          <li>lock result</li>
          <li>unlock</li>
          <li>downstream invalidation</li>
        </ul>
      </SectionCard>

      <SectionCard title="Narrative / Outcome Locks (planned)">
        <p>Future narrative tooling will support deterministic guardrails and pre-simulation constraint previews.</p>
        <ul className="dashboard-help-list">
          <li>Soft Lock</li>
          <li>Hard Lock</li>
          <li>Winner Lock</li>
          <li>Round Lock</li>
          <li>Exact Match Lock</li>
          <li>Path Lock</li>
          <li>Estimated natural probability (future)</li>
        </ul>
        <p className="status">Example: Arebady must win Némarque Open 2030/31. Estimated natural probability: 42%. Status: Plausible.</p>
      </SectionCard>
    </section>
  )
}

export function AdminDiagnosticsPage(): JSX.Element {
  const lastRunId = typeof window === 'undefined' ? null : window.localStorage.getItem('beta_engine:last_run_id')
  const lastRunDiagnosticsPath = lastRunId ? `/admin/runs/${lastRunId}/diagnostics` : null

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Diagnostics</h2>
        <p className="subtitle">Control center for world balance, calendar validation, run health, invalidated data, narrative locks, and audit warnings.</p>
      </div>
      <p className="status">Top-level diagnostics is being consolidated here. Operational diagnostics currently remain run-scoped in Run Diagnostics.</p>

      <SectionCard title="Overview">
        <p>Open a run first to inspect current operational diagnostics.</p>
        <p>
          <Link to="/admin/runs">Open Runs</Link>
          {lastRunDiagnosticsPath ? (
            <>
              {' '}
              · <Link to={lastRunDiagnosticsPath}>Open last run diagnostics ({lastRunId})</Link>
            </>
          ) : null}
        </p>
      </SectionCard>

      <div className="dashboard-stack">
        <SectionCard title="World Balance">
          <p>
            Checks country input completeness, talent distribution balance, population dominance risk, small-country zero-chance
            risk, and Talent Preview anomalies.
          </p>
          <p>
            Current action: <Link to="/admin/world/talent-preview">Talent Preview</Link> ·{' '}
            <Link to="/admin/world/countries">Countries</Link>
          </p>
        </SectionCard>

        <SectionCard title="Calendar Validation">
          <p>
            Checks W01–W61 range, multi-week event blocks, qualifying before main draw, mandatory events, invalid
            categories/hosts, and schedule conflicts.
          </p>
          <p>
            Current action: <Link to="/admin/tour-seasons/validation">Calendar Validation</Link> · <Link to="/admin/seasons">Seasons</Link>
          </p>
        </SectionCard>

        <SectionCard title="Run Health">
          <p>Checks run progress, incomplete events, missing results, stale artifacts, snapshots, and operational blockers.</p>
          <p>
            Current action: <Link to="/admin/runs">Runs</Link>
            {lastRunDiagnosticsPath ? (
              <>
                {' '}
                · <Link to={lastRunDiagnosticsPath}>Last run diagnostics</Link>
              </>
            ) : null}
          </p>
        </SectionCard>

        <SectionCard title="Invalidated Data">
          <p>
            Planned downstream invalidation tracking after calendar, entry, draw, result, points, or ranking edits.
          </p>
          <p className="status">Current action: Planned / run-scoped diagnostics later.</p>
        </SectionCard>

        <SectionCard title="Narrative Locks">
          <p>Planned conflict/plausibility checks for Soft/Hard/Winner/Round/Exact Match/Path locks.</p>
          <p className="status">Current action: Planned.</p>
        </SectionCard>

        <SectionCard title="Audit / Warnings">
          <p>
            Future consolidated feed for manual edits, lock changes, regeneration skips, invalidation events, and warning
            history.
          </p>
          <p className="status">Current action: Audit remains embedded in specific operational pages.</p>
        </SectionCard>
      </div>

      <SectionCard title="What Diagnostics should explain">
        <ul className="dashboard-help-list">
          <li>what happened</li>
          <li>why it matters</li>
          <li>what is affected</li>
          <li>what to do next</li>
          <li>where to click</li>
        </ul>
      </SectionCard>

      <SectionCard title="Current vs planned">
        <p>
          <strong>Current:</strong> real diagnostics are mostly run-scoped; this top-level page is a launcher/triage shell;
          existing Run Diagnostics is the operational source today.
        </p>
        <p>
          <strong>Planned:</strong> top-level aggregation across World, Calendar, Runs, Invalidated Data, Narrative Locks,
          and Audit.
        </p>
      </SectionCard>
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

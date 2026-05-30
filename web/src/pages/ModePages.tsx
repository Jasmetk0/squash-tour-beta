import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'
import { AdminPlayersPage as InitialPoolAdminPlayersPage } from './AdminPlayersPage'
import { AdminPlayersHubPage } from './AdminPlayersHubPage'
import { AdminSeasonsPage as SeasonBootstrapAdminSeasonsPage } from './AdminSeasonsPage'
import { TournamentTemplatesPage } from './TournamentTemplatesPage'
import { getCountriesMetadata, getFinalsSummary, getRun, getRunActivity, getRunStatusSummary, getTournamentTemplatesMetadata, listEvents, listRaceSnapshots, listRankingSnapshots, listRuns } from '../api/client'

import { LinkCardGrid } from '../components/LinkCardGrid'
import { ViewerJumpToWeekButton } from '../components/ViewerContextControls'
import { useViewerContext } from '../viewer/ViewerContext'
import { VIEWER_ACTIVE_RUN_CHANGED_EVENT, readViewerActiveRunId } from '../viewer/activeRun'
import type { EventRecord, RankingSnapshot, RaceSnapshot, RunActivityItem, SeasonStateResponse } from '../api/types'

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



function useActiveViewerRunId(): string | null {
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

type ActiveRunBridgeProps = {
  title: string
  emptyMessage: string
  target: (runId: string) => string
  description?: string
}

function ViewerActiveRunBridge({ title, emptyMessage, target, description }: ActiveRunBridgeProps): JSX.Element {
  const activeRunId = useActiveViewerRunId()

  if (activeRunId) {
    return <Navigate to={target(activeRunId)} replace />
  }

  return (
    <ViewerShellPage title={title} description={description}>
      <p className="empty-state">{emptyMessage}</p>
    </ViewerShellPage>
  )
}

const activeRunLinks = [
  { title: 'Active Run Rankings', href: (runId: string) => `/viewer/runs/${runId}/rankings` },
  { title: 'Active Run Race', href: (runId: string) => `/viewer/runs/${runId}/race` },
  { title: 'Active Run Tournaments', href: (runId: string) => `/viewer/runs/${runId}/tournaments` },
  { title: 'Active Run Calendar', href: (runId: string) => `/viewer/runs/${runId}/calendar` },
  { title: 'Active Run Players', href: (runId: string) => `/viewer/runs/${runId}/players` },
  { title: 'Active Run Countries', href: (runId: string) => `/viewer/runs/${runId}/countries` },
  { title: 'Active Run History', href: (runId: string) => `/viewer/runs/${runId}/history` },
  { title: 'Active Run Finals', href: (runId: string) => `/viewer/runs/${runId}/finals` }
]

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

type HomepageEventSummary = {
  eventId: string
  week: number | null
  category: string | null
  tour: string | null
  templateId: string | null
  status: 'Next scheduled event' | 'Most recent completed event'
}

function buildPlannedEventMap(runData: SeasonStateResponse | undefined): Map<string, SeasonStateResponse['season_state']['ordered_events'][number]> {
  const map = new Map<string, SeasonStateResponse['season_state']['ordered_events'][number]>()
  ;(runData?.season_state.ordered_events ?? []).forEach((event) => {
    map.set(event.event_id, event)
  })
  return map
}

function selectHomepageEvent(runData: SeasonStateResponse | undefined, events: EventRecord[]): HomepageEventSummary | null {
  const orderedEvents = runData?.season_state.ordered_events ?? []
  const nextIndex = runData?.season_state.next_event_index ?? runData?.run.next_event_index ?? null
  const plannedMap = buildPlannedEventMap(runData)

  if (nextIndex != null && orderedEvents[nextIndex]) {
    const event = orderedEvents[nextIndex]
    return {
      eventId: event.event_id,
      week: event.week,
      category: event.category,
      tour: event.tour,
      templateId: event.template_id,
      status: 'Next scheduled event'
    }
  }

  const mostRecentCompleted = [...events].sort((a, b) => b.event_sequence - a.event_sequence)[0]
  if (mostRecentCompleted) {
    const planned = plannedMap.get(mostRecentCompleted.event_id)
    return {
      eventId: mostRecentCompleted.event_id,
      week: mostRecentCompleted.week ?? planned?.week ?? null,
      category: planned?.category ?? null,
      tour: planned?.tour ?? null,
      templateId: mostRecentCompleted.template_id ?? planned?.template_id ?? null,
      status: 'Most recent completed event'
    }
  }

  return null
}

function latestSnapshot<T extends RankingSnapshot | RaceSnapshot>(snapshots: T[]): T | null {
  return [...snapshots].sort((a, b) => b.snapshot_sequence - a.snapshot_sequence)[0] ?? null
}

function formatSource(sourceType: string | undefined, parentRunId: string | null | undefined): string {
  if (!sourceType) return 'Not available yet'
  return parentRunId ? `${sourceType} from ${parentRunId}` : sourceType
}

function formatActivityItem(item: RunActivityItem): string {
  const parts = [item.label]
  if (item.season != null) parts.push(`Season ${item.season}`)
  if (item.week != null) parts.push(`W${item.week}`)
  if (item.event_id) parts.push(item.event_id)
  return parts.join(' · ')
}

export function ViewerHomePage(): JSX.Element {
  const context = useViewerContext()
  const activeRunId = useActiveViewerRunId()
  const queryEnabled = Boolean(activeRunId)

  const runQuery = useQuery({ queryKey: ['viewer-home-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const statusQuery = useQuery({ queryKey: ['viewer-home-run-status', activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-home-events', activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-home-ranking-snapshots', activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-home-race-snapshots', activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const activityQuery = useQuery({ queryKey: ['viewer-home-activity', activeRunId], queryFn: () => getRunActivity(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-home-finals', activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: queryEnabled, retry: false })

  const activeQueries = [runQuery, statusQuery, eventsQuery, rankingSnapshotsQuery, raceSnapshotsQuery, activityQuery, finalsQuery]
  const isActiveSummaryLoading = queryEnabled && activeQueries.some((query) => query.isLoading)
  const isActiveSummaryUnavailable = queryEnabled && activeQueries.some((query) => query.isError)

  const featuredEvent = useMemo(() => selectHomepageEvent(runQuery.data, eventsQuery.data?.events ?? []), [eventsQuery.data?.events, runQuery.data])
  const nearbyEvents = useMemo(() => {
    const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
    if (!featuredEvent) return orderedEvents.slice(0, 3)
    return orderedEvents.filter((event) => event.event_id !== featuredEvent.eventId && event.week === featuredEvent.week).slice(0, 3)
  }, [featuredEvent, runQuery.data?.season_state.ordered_events])
  const latestRankingSnapshot = latestSnapshot(rankingSnapshotsQuery.data?.snapshots ?? [])
  const latestRaceSnapshot = latestSnapshot(raceSnapshotsQuery.data?.snapshots ?? [])
  const activityItems = activityQuery.data?.items ?? []
  const latestActivityItem = activityItems[0] ?? null

  return (
    <section className="panel viewer-home viewer-home--msa">
      <div className="page-intro viewer-home__hero">
        <span className="eyebrow">MSA Homepage</span>
        <h2>MSA Squash — Season {context.selectedSeason} · W{context.selectedWeek}</h2>
        <p className="subtitle">
          A premium, public-style squash tour homepage for the selected Viewer context. These cards are read-only and show small real summaries only when existing safe run APIs provide them.
        </p>
      </div>
      <section className="viewer-active-run-panel" aria-label="Active Viewer run status">
        {activeRunId ? (
          <>
            <div>
              <span className="eyebrow">Active Viewer run</span>
              <h3>Active run data is available</h3>
              {isActiveSummaryLoading ? <p className="status">Loading current tour summary from the active Viewer run…</p> : null}
              {isActiveSummaryUnavailable ? <p className="empty-state">Active run summary is temporarily unavailable. Try opening the run pages below for more detail.</p> : null}
              {!isActiveSummaryLoading && !isActiveSummaryUnavailable ? (
                <>
                  <p className="status">Using Viewer run <strong>{activeRunId}</strong> for read-only run pages.</p>
                  <dl className="viewer-home-summary-list" aria-label="Active run summary fields">
                    <div><dt>Run id</dt><dd>{statusQuery.data?.run_id ?? runQuery.data?.run.run_id ?? activeRunId}</dd></div>
                    <div><dt>Season</dt><dd>{statusQuery.data?.season ?? runQuery.data?.run.season ?? 'Not available yet'}</dd></div>
                    <div><dt>Seed</dt><dd>{statusQuery.data?.seed ?? runQuery.data?.run.seed ?? 'Not available yet'}</dd></div>
                    <div><dt>Progress</dt><dd>{statusQuery.data ? `${statusQuery.data.progress.completed_event_count}/${statusQuery.data.progress.total_events} events complete` : `${runQuery.data?.run.completed_event_ids.length ?? 0}/${runQuery.data?.run.total_events ?? 0} events complete`}</dd></div>
                    <div><dt>Next event index</dt><dd>{statusQuery.data?.progress.next_event_index ?? runQuery.data?.run.next_event_index ?? 'Not available yet'}</dd></div>
                    <div><dt>Finals</dt><dd>{statusQuery.data?.finals.result_available || finalsQuery.data?.result ? 'Result available' : statusQuery.data?.finals.qualification_available || finalsQuery.data?.qualification ? 'Qualification available' : 'Not available yet'}</dd></div>
                    <div><dt>Lineage/source</dt><dd>{formatSource(statusQuery.data?.source?.source_type, statusQuery.data?.source?.parent_run_id)}</dd></div>
                  </dl>
                </>
              ) : null}
            </div>
            <div className="viewer-active-run-link-grid">
              {activeRunLinks.map((link) => (
                <Link key={link.title} className="viewer-active-run-link" to={link.href(activeRunId)}>
                  {link.title}
                </Link>
              ))}
            </div>
          </>
        ) : (
          <p className="empty-state">Active run data is unavailable until a Viewer run is selected. No authoritative tournament, rankings, race, match, prediction, or storyline data is shown.</p>
        )}
      </section>
      <div className="viewer-home-grid">
        <article className="viewer-home-card viewer-home-card--hero">
          <span className="eyebrow">Featured Tournament Hero</span>
          <h3>Featured Tournament Hero</h3>
          {activeRunId && featuredEvent ? (
            <>
              <p>{featuredEvent.status}: <strong>{featuredEvent.eventId}</strong></p>
              <p className="status">{featuredEvent.category ?? 'Category unavailable'} · {featuredEvent.tour ?? 'Tour unavailable'} · {featuredEvent.week != null ? `W${featuredEvent.week}` : 'Week unavailable'} · Template {featuredEvent.templateId ?? 'unavailable'}</p>
              <Link className="viewer-active-run-link" to={`/viewer/runs/${activeRunId}/calendar`}>Open active run calendar</Link>
            </>
          ) : (
            <p className="empty-state">{activeRunId ? 'No current event summary available yet.' : 'Select a Viewer run to see the current event summary.'}</p>
          )}
        </article>

        <article className="viewer-home-card viewer-home-card--standard">
          <span className="eyebrow">Read-only schedule</span>
          <h3>Other Tournaments This Week</h3>
          {activeRunId && nearbyEvents.length ? (
            <ul>
              {nearbyEvents.map((event) => (
                <li key={event.event_id}>{event.event_id} · {event.category} · W{event.week}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">{activeRunId ? 'No additional same-week event summary is available yet.' : 'Active-run schedule data is unavailable until a Viewer run is selected.'}</p>
          )}
        </article>

        <article className="viewer-home-card viewer-home-card--standard">
          <span className="eyebrow">Read-only rankings</span>
          <h3>Top 10 Rankings</h3>
          {activeRunId && latestRankingSnapshot ? (
            <p>Latest ranking snapshot #{latestRankingSnapshot.snapshot_sequence} from {latestRankingSnapshot.source_event_id ?? 'run history'} · {rankingSnapshotsQuery.data?.snapshots.length ?? 0} snapshots stored.</p>
          ) : (
            <p className="empty-state">{activeRunId ? 'No ranking snapshot metadata is available yet.' : 'Select a Viewer run to see ranking snapshot metadata.'}</p>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={`/viewer/runs/${activeRunId}/rankings`}>Open active run rankings</Link> : null}
        </article>

        <article className="viewer-home-card viewer-home-card--standard">
          <span className="eyebrow">Read-only race</span>
          <h3>Race to Finals</h3>
          {activeRunId && latestRaceSnapshot ? (
            <p>Latest race snapshot #{latestRaceSnapshot.snapshot_sequence} from {latestRaceSnapshot.source_event_id ?? 'run history'} · {raceSnapshotsQuery.data?.snapshots.length ?? 0} snapshots stored.</p>
          ) : (
            <p className="empty-state">{activeRunId ? 'No race snapshot metadata is available yet.' : 'Select a Viewer run to see Race snapshot metadata.'}</p>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={`/viewer/runs/${activeRunId}/race`}>Open active run race</Link> : null}
        </article>

        <article className="viewer-home-card viewer-home-card--standard">
          <span className="eyebrow">Read-only matches</span>
          <h3>Featured Matches</h3>
          <p className="empty-state">Match cards need the match read model.</p>
          {activeRunId ? <Link className="viewer-active-run-link" to={`/viewer/runs/${activeRunId}/tournaments`}>Open active run tournaments</Link> : null}
        </article>

        <article className="viewer-home-card viewer-home-card--standard">
          <span className="eyebrow">Read-only analytics</span>
          <h3>Predictions &amp; Upset Watch</h3>
          <p className="empty-state">Prediction analytics are not connected yet.</p>
        </article>

        <article className="viewer-home-card viewer-home-card--standard">
          <span className="eyebrow">Read-only storylines</span>
          <h3>Storylines</h3>
          {activeRunId && latestActivityItem ? (
            <p>{activityItems.length} activity items · Latest: {formatActivityItem(latestActivityItem)}</p>
          ) : (
            <p className="empty-state">{activeRunId ? 'No activity storyline summary is available yet.' : 'Select a Viewer run to see activity storyline metadata.'}</p>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={`/viewer/runs/${activeRunId}/history`}>Open active run history</Link> : null}
        </article>
      </div>
    </section>
  )
}

type ViewerSnapshotLandingMode = 'ranking' | 'race'

type ViewerSnapshotLandingConfig = {
  mode: ViewerSnapshotLandingMode
  title: string
  description: string
  emptyMessage: string
  noSnapshotsMessage: string
  countLabel: string
  openLabel: string
  latestLabel: string
  runScopedPath: (runId: string) => string
  detailPath: (runId: string, snapshotSequence: number) => string
}

function ViewerSnapshotLandingPage({ config }: { config: ViewerSnapshotLandingConfig }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const snapshotsQuery = useQuery({
    queryKey: ['viewer-top-level-snapshots', config.mode, activeRunId],
    queryFn: () => (config.mode === 'ranking' ? listRankingSnapshots(activeRunId ?? '') : listRaceSnapshots(activeRunId ?? '')),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description={config.description}>
        <p className="empty-state">{config.emptyMessage}</p>
      </ViewerShellPage>
    )
  }

  const snapshots = snapshotsQuery.data?.snapshots ?? []
  const latest = latestSnapshot(snapshots)

  return (
    <ViewerShellPage title={config.title} description={config.description}>
      <article className="viewer-active-run-card" aria-label={`${config.title} active run snapshot summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} snapshot landing</h3>
        <dl className="metadata-list">
          <div>
            <dt>Active run ID</dt>
            <dd>{activeRunId}</dd>
          </div>
          <div>
            <dt>{config.countLabel}</dt>
            <dd>{snapshotsQuery.isLoading ? 'Loading…' : snapshots.length}</dd>
          </div>
          <div>
            <dt>Latest snapshot sequence</dt>
            <dd>{latest ? latest.snapshot_sequence : '—'}</dd>
          </div>
          <div>
            <dt>Latest source event ID</dt>
            <dd>{latest?.source_event_id ?? '—'}</dd>
          </div>
          <div>
            <dt>Latest snapshot kind</dt>
            <dd>{latest?.snapshot_kind ?? '—'}</dd>
          </div>
        </dl>

        {snapshotsQuery.isError ? <p className="empty-state">Snapshot metadata is temporarily unavailable for this run.</p> : null}
        {!snapshotsQuery.isLoading && !snapshotsQuery.isError && !latest ? <p className="empty-state">{config.noSnapshotsMessage}</p> : null}

        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={config.runScopedPath(activeRunId)}>
            {config.openLabel}
          </Link>
          {latest ? (
            <>
              {' '}
              <Link className="viewer-active-run-link" to={config.detailPath(activeRunId, latest.snapshot_sequence)}>
                {config.latestLabel}
              </Link>
            </>
          ) : null}
        </p>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerRankingsPage(): JSX.Element {
  return (
    <ViewerSnapshotLandingPage
      config={{
        mode: 'ranking',
        title: 'MSA Rankings',
        description: 'Official rankings destination for the selected Season/Week context.',
        emptyMessage: 'Select a Viewer run to view MSA Rankings.',
        noSnapshotsMessage: 'No ranking snapshots are available for this run yet.',
        countLabel: 'Ranking snapshot count',
        openLabel: 'Open active run rankings',
        latestLabel: 'View latest ranking snapshot',
        runScopedPath: (runId) => `/viewer/runs/${runId}/rankings`,
        detailPath: (runId, snapshotSequence) => `/viewer/runs/${runId}/rankings/${snapshotSequence}`
      }}
    />
  )
}

export function ViewerRacePage(): JSX.Element {
  return (
    <ViewerSnapshotLandingPage
      config={{
        mode: 'race',
        title: 'Race to Finals',
        description: 'Season-long qualification standings for the selected Viewer run.',
        emptyMessage: 'Select a Viewer run to view Race to Finals.',
        noSnapshotsMessage: 'No race snapshots are available for this run yet.',
        countLabel: 'Race snapshot count',
        openLabel: 'Open active run race',
        latestLabel: 'View latest race snapshot',
        runScopedPath: (runId) => `/viewer/runs/${runId}/race`,
        detailPath: (runId, snapshotSequence) => `/viewer/runs/${runId}/race/${snapshotSequence}`
      }}
    />
  )
}

export function ViewerTournamentsPage(): JSX.Element {
  return (
    <ViewerActiveRunBridge
      title="All Tournaments"
      description="Tournament archive destination for read-only schedules, results, and historical browsing."
      emptyMessage="Select a Viewer run to view MSA Tournaments."
      target={(runId) => `/viewer/runs/${runId}/tournaments`}
    />
  )
}

export function ViewerPlayersPage(): JSX.Element {
  return (
    <ViewerActiveRunBridge
      title="Players Hub"
      description="Player hub for read-only spotlights, profiles, and browsing in the selected Viewer context."
      emptyMessage="Select a Viewer run to view MSA Players."
      target={(runId) => `/viewer/runs/${runId}/players`}
    />
  )
}

export function ViewerCountriesPage(): JSX.Element {
  return (
    <ViewerActiveRunBridge
      title="Countries Hub"
      description="Country hub for read-only national rankings, hosting stories, talent pipelines, and records."
      emptyMessage="Select a Viewer run to view MSA Countries."
      target={(runId) => `/viewer/runs/${runId}/countries`}
    />
  )
}

export function ViewerHistoryPage(): JSX.Element {
  return (
    <ViewerActiveRunBridge
      title="History"
      description="History destination for read-only activity, archive, and storyline browsing."
      emptyMessage="Select a Viewer run to view MSA History."
      target={(runId) => `/viewer/runs/${runId}/history`}
    />
  )
}

export function ViewerRecordsPage(): JSX.Element {
  return <ViewerShellPage title="Records" description="Record book destination prepared for statistics, milestones, and historical achievements." />
}

export function ViewerTourCalendarPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()

  return (
    <ViewerShellPage title="Season Calendar" description="Season calendar destination prepared for weekly tour browsing and read-only event cards.">
      <div className="viewer-jump-demo" aria-label="Jump to Week demo">
        <p className="status">Sample calendar card for future read-only weekly event browsing.</p>
        <ViewerJumpToWeekButton week={24} />
      </div>
      {activeRunId ? (
        <article className="viewer-active-run-card">
          <span className="eyebrow">Active Viewer run</span>
          <h3>Open active run calendar</h3>
          <p className="status">Use the real read-only calendar for Viewer run {activeRunId}.</p>
          <Link className="viewer-active-run-link" to={`/viewer/runs/${activeRunId}/calendar`}>
            Open active run calendar
          </Link>
        </article>
      ) : null}
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

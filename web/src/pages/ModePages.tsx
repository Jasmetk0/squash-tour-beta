import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { AdminPlayersPage as InitialPoolAdminPlayersPage } from './AdminPlayersPage'
import { AdminPlayersHubPage } from './AdminPlayersHubPage'
import { AdminSeasonsPage as SeasonBootstrapAdminSeasonsPage } from './AdminSeasonsPage'
import { TournamentTemplatesPage } from './TournamentTemplatesPage'
import { getCountriesMetadata, getFinalsSummary, getRun, getRunActivity, getRunStatusSummary, getTournamentTemplatesMetadata, listEvents, listRaceSnapshots, listRankingSnapshots, listRunNations, listRunPlayers, listRuns } from '../api/client'

import { LinkCardGrid } from '../components/LinkCardGrid'
import { ViewerActiveRunCard, ViewerActiveRunLinks, ViewerDeferredFeatureList, ViewerEmptyState, ViewerLandingGrid, ViewerMetadataList, ViewerSampleList, ViewerSectionCard, ViewerStatusMessage } from '../components/viewer/ViewerLandingComponents'
import { ViewerJumpToWeekButton } from '../components/ViewerContextControls'
import { ViewerRunSelector } from '../components/ViewerRunSelector'
import { useViewerContext } from '../viewer/ViewerContext'
import { VIEWER_ACTIVE_RUN_CHANGED_EVENT, readViewerActiveRunId } from '../viewer/activeRun'
import { RacePreviewTable } from '../viewer/RacePreviewTable'
import { RankingPreviewTable } from '../viewer/RankingPreviewTable'
import { buildViewerRunBrowserLinks, viewerRunMetadataFields, type ViewerRunBrowserListItem } from '../viewer/runBrowserDisplay'
import { buildActiveRunHubLinks } from '../viewer/viewerHubLinks'
import { parseRacePreviewPayload } from '../viewer/racePayload'
import { parseRankingPreviewPayload } from '../viewer/rankingPayload'
import {
  viewerCountriesPath,
  viewerHomePath,
  viewerCountryProfilePath,
  viewerFinalsPath,
  viewerHistoryPath,
  viewerPlannedEventPath,
  viewerPlayerProfilePath,
  viewerPlayersPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingsPath,
  viewerRankingSnapshotPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTopH2HPath,
  viewerTopMatchPredictorPath,
  viewerTopRecordsPath,
  viewerTopSearchPath,
  viewerTopStatsPath,
  viewerWeekDetailPath,
  viewerTournamentsPath,
  viewerTournamentDetailPath
} from '../viewer/viewerRoutes'
import type { EventRecord, FinalsSummaryResponse, RankingSnapshot, RaceSnapshot, RunActivityItem, RunNationSummaryItem, RunPlayerListItem, RunStatusSummary, RunsIndexResponse, SeasonStateResponse } from '../api/types'

export function LandingPage(): JSX.Element {
  return (
    <section className="panel landing-panel">
      <div className="page-intro">
        <h2>Squash Tour Beta Engine</h2>
        <p className="subtitle">Choose how you want to use the deterministic FAX squash world.</p>
      </div>
      <div className="mode-choice-grid">
        <Link className="mode-choice mode-choice--viewer" to={viewerHomePath()}>
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



export function ViewerRunBrowserPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const runsQuery = useQuery({ queryKey: ['viewer-run-selector-runs'], queryFn: listRuns, retry: false })
  const runs = (runsQuery.data?.runs ?? []) as ViewerRunBrowserListItem[]

  return (
    <ViewerShellPage
      title="Run Browser"
      kicker="Read-only Viewer runs"
      description="Browse available generated runs and open run-scoped Viewer pages using existing run list metadata only."
    >
      <ViewerRunSelector />

      <section className="viewer-active-run-panel" aria-label="Run Browser active run">
        <span className="eyebrow">Active run</span>
        <h3>Active run</h3>
        {activeRunId ? (
          <p className="status">Current active Viewer run id: <strong>{activeRunId}</strong></p>
        ) : (
          <ViewerEmptyState>No active Viewer run selected.</ViewerEmptyState>
        )}
      </section>

      <section className="viewer-active-run-card" aria-label="Available runs">
        <span className="eyebrow">Run Browser</span>
        <h3>Available runs</h3>
        {runsQuery.isLoading ? <p className="status">Loading available runs…</p> : null}
        {runsQuery.isError ? <ViewerEmptyState>Run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        {!runsQuery.isLoading && !runsQuery.isError && runs.length > 0 ? (
          <div className="viewer-run-browser-list">
            {runs.map((run) => {
              const fields = viewerRunMetadataFields(run)
              return (
                <article className="viewer-active-run-card" key={run.run_id} aria-label={`Run ${run.run_id}`}>
                  <h4>{run.run_id}</h4>
                  <ViewerMetadataList ariaLabel={`Run ${run.run_id} metadata`} items={fields} />
                  <div className="viewer-run-browser-links" aria-label={`Run ${run.run_id} links`}>
                    <h5>Links</h5>
                    <ViewerActiveRunLinks layout="grid" links={buildViewerRunBrowserLinks(run.run_id)} />
                  </div>
                </article>
              )
            })}
          </div>
        ) : null}
      </section>
    </ViewerShellPage>
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
    <ViewerStatusMessage>
      Viewer context: Season {context.selectedSeason} · W{context.selectedWeek}. This section is ready for read-only tour data once the Viewer read model is connected.
    </ViewerStatusMessage>
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
      {children ?? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>}
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

type OrderedSeasonEvent = SeasonStateResponse['season_state']['ordered_events'][number]

function selectNextOrderedEvent(runData: SeasonStateResponse | undefined): OrderedSeasonEvent | null {
  const orderedEvents = runData?.season_state.ordered_events ?? []
  const nextIndex = runData?.season_state.next_event_index ?? runData?.run.next_event_index ?? null
  return nextIndex != null ? orderedEvents[nextIndex] ?? null : null
}

function selectLatestPersistedEvent(events: EventRecord[]): EventRecord | null {
  return [...events].sort((a, b) => b.event_sequence - a.event_sequence)[0] ?? null
}

function formatFinalsAvailability(summary: FinalsSummaryResponse | undefined): string {
  if (!summary) return 'Loading or unavailable'
  if (summary.result) return 'Finals result available'
  if (summary.qualification) return 'Finals qualification available'
  return 'Finals summary not available yet'
}

function renderLinkedEventId(runId: string, eventId: string | null | undefined): ReactNode {
  if (!eventId) return '—'
  return <Link to={viewerPlannedEventPath(runId, eventId)}>{eventId}</Link>
}

function renderLinkedWeek(runId: string, week: number | string | null | undefined): ReactNode {
  if (week == null || week === '') return '—'
  return <Link to={viewerWeekDetailPath(runId, week)}>W{week}</Link>
}

function renderOrderedEventMetadata(event: OrderedSeasonEvent, runId?: string): JSX.Element {
  const eventId = runId ? renderLinkedEventId(runId, event.event_id) : event.event_id
  const week = runId ? renderLinkedWeek(runId, event.week) : event.week

  return (
    <dl className="metadata-list">
      <div><dt>Event ID</dt><dd>{eventId}</dd></div>
      <div><dt>Week</dt><dd>{week}</dd></div>
      <div><dt>Category</dt><dd>{event.category}</dd></div>
      <div><dt>Tour</dt><dd>{event.tour}</dd></div>
      <div><dt>Template ID</dt><dd>{event.template_id}</dd></div>
    </dl>
  )
}

function renderEventSummary(event: OrderedSeasonEvent, runId: string): ReactNode {
  return <>{renderLinkedEventId(runId, event.event_id)} · {renderLinkedWeek(runId, event.week)} · {event.category} · {event.tour} · {event.template_id}</>
}

function renderPersistedEventSummary(event: EventRecord | null, plannedMap: Map<string, OrderedSeasonEvent>, runId?: string): ReactNode {
  if (!event) return '—'
  const planned = plannedMap.get(event.event_id)
  const week = event.week ?? planned?.week ?? null
  const templateId = event.template_id ?? planned?.template_id ?? '—'
  const category = planned?.category ?? '—'
  const tour = planned?.tour ?? '—'
  const eventId = runId ? renderLinkedEventId(runId, event.event_id) : event.event_id
  const weekValue = runId ? renderLinkedWeek(runId, week) : week != null ? `W${week}` : 'W—'
  return <>{eventId} · {weekValue} · {category} · {tour} · {templateId}</>
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


type DeferredSourceMetadata = {
  eventCount: number | null
  rankingSnapshotCount: number | null
  raceSnapshotCount: number | null
  latestPersistedEvent: EventRecord | null
  latestRankingSnapshot: RankingSnapshot | null
  latestRaceSnapshot: RaceSnapshot | null
  finalsAvailability: string
  hasFinalsAvailability: boolean
}

type DeferredSourceMetadataItem = {
  label: string
  value: ReactNode
}

function resolveFinalsAvailability(finals: FinalsSummaryResponse | undefined, status: RunStatusSummary | undefined): string {
  if (finals) return formatFinalsAvailability(finals)
  if (status?.finals.result_available) return 'Finals result available'
  if (status?.finals.qualification_available) return 'Finals qualification available'
  return 'Finals summary not available yet'
}

function hasAvailableFinals(finalsAvailability: string): boolean {
  return finalsAvailability !== 'Finals summary not available yet' && finalsAvailability !== 'Loading or unavailable'
}

function buildDeferredSourceMetadata(args: {
  events: EventRecord[] | undefined
  rankingSnapshots: RankingSnapshot[] | undefined
  raceSnapshots: RaceSnapshot[] | undefined
  status: RunStatusSummary | undefined
  finals: FinalsSummaryResponse | undefined
  eventCount?: number | null
}): DeferredSourceMetadata {
  const events = args.events ?? []
  const rankingSnapshots = args.rankingSnapshots ?? []
  const raceSnapshots = args.raceSnapshots ?? []
  const eventCount = args.eventCount ?? args.events?.length ?? args.status?.history_counts.events ?? null
  const rankingSnapshotCount = args.rankingSnapshots?.length ?? args.status?.history_counts.ranking_snapshots ?? null
  const raceSnapshotCount = args.raceSnapshots?.length ?? args.status?.history_counts.race_snapshots ?? null
  const finalsAvailability = resolveFinalsAvailability(args.finals, args.status)

  return {
    eventCount,
    rankingSnapshotCount,
    raceSnapshotCount,
    latestPersistedEvent: selectLatestPersistedEvent(events),
    latestRankingSnapshot: latestSnapshot(rankingSnapshots),
    latestRaceSnapshot: latestSnapshot(raceSnapshots),
    finalsAvailability,
    hasFinalsAvailability: hasAvailableFinals(finalsAvailability)
  }
}

function renderSourceMetadataList(items: DeferredSourceMetadataItem[]): JSX.Element {
  return (
    <dl className="metadata-list">
      {items.map((item) => (
        <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>
      ))}
    </dl>
  )
}

function renderLoadingValue(isLoading: boolean, value: ReactNode | null | undefined): ReactNode {
  return isLoading && value == null ? 'Loading…' : value ?? '—'
}

function renderFinalsSourceValue(activeRunId: string, finalsAvailability: string, isLoading: boolean): ReactNode {
  if (isLoading) return 'Loading…'
  return hasAvailableFinals(finalsAvailability) ? <Link to={viewerFinalsPath(activeRunId)}>{finalsAvailability}</Link> : finalsAvailability
}

function renderLatestPersistedEventSourceValue(activeRunId: string, event: EventRecord | null): ReactNode {
  return event?.event_id ? <Link to={viewerTournamentDetailPath(activeRunId, event.event_id)}>{event.event_id}</Link> : '—'
}

function renderLatestRankingSnapshotSourceValue(activeRunId: string, snapshot: RankingSnapshot | null): ReactNode {
  return snapshot ? <Link to={viewerRankingSnapshotPath(activeRunId, snapshot.snapshot_sequence)}>#{snapshot.snapshot_sequence}</Link> : '—'
}

function renderLatestRaceSnapshotSourceValue(activeRunId: string, snapshot: RaceSnapshot | null): ReactNode {
  return snapshot ? <Link to={viewerRaceSnapshotPath(activeRunId, snapshot.snapshot_sequence)}>#{snapshot.snapshot_sequence}</Link> : '—'
}

function commonDeferredSourceMetadataItems(args: {
  activeRunId: string
  metadata: DeferredSourceMetadata
  eventsLoading: boolean
  rankingSnapshotsLoading: boolean
  raceSnapshotsLoading: boolean
  finalsLoading: boolean
}): DeferredSourceMetadataItem[] {
  return [
    { label: 'Active run ID', value: args.activeRunId },
    { label: 'Completed/persisted event count', value: renderLoadingValue(args.eventsLoading, args.metadata.eventCount) },
    { label: 'Ranking snapshot count', value: renderLoadingValue(args.rankingSnapshotsLoading, args.metadata.rankingSnapshotCount) },
    { label: 'Race snapshot count', value: renderLoadingValue(args.raceSnapshotsLoading, args.metadata.raceSnapshotCount) },
    { label: 'Finals availability', value: renderFinalsSourceValue(args.activeRunId, args.metadata.finalsAvailability, args.finalsLoading) },
    { label: 'Latest persisted event', value: renderLatestPersistedEventSourceValue(args.activeRunId, args.metadata.latestPersistedEvent) },
    { label: 'Latest ranking snapshot', value: renderLatestRankingSnapshotSourceValue(args.activeRunId, args.metadata.latestRankingSnapshot) },
    { label: 'Latest race snapshot', value: renderLatestRaceSnapshotSourceValue(args.activeRunId, args.metadata.latestRaceSnapshot) }
  ]
}

function hasAnyDeferredSourceMetadata(metadata: DeferredSourceMetadata, orderedEventCount?: number | null): boolean {
  return (metadata.eventCount ?? 0) > 0 || (orderedEventCount ?? 0) > 0 || (metadata.rankingSnapshotCount ?? 0) > 0 || (metadata.raceSnapshotCount ?? 0) > 0 || metadata.hasFinalsAvailability
}

function renderDeferredSourceLinks(links: { label: string; to: string }[]): JSX.Element {
  return <ViewerActiveRunLinks links={links} />
}

function formatSource(sourceType: string | undefined, parentRunId: string | null | undefined): string {
  if (!sourceType) return 'Not available yet'
  return parentRunId ? `${sourceType} from ${parentRunId}` : sourceType
}

type ActivityLinkContext = {
  plannedEvents: Map<string, OrderedSeasonEvent>
  persistedEvents: Map<string, EventRecord>
}

function renderActivityItem(item: RunActivityItem, runId: string, context: ActivityLinkContext): ReactNode {
  const eventId = item.event_id
  const plannedEvent = eventId ? context.plannedEvents.get(eventId) : null
  const persistedEvent = eventId ? context.persistedEvents.get(eventId) : null
  const resolvedWeek = plannedEvent?.week ?? persistedEvent?.week ?? null

  const parts: ReactNode[] = [item.label]
  if (item.season != null) parts.push(`Season ${item.season}`)
  if (resolvedWeek != null) {
    parts.push(renderLinkedWeek(runId, resolvedWeek))
  } else if (item.week != null) {
    parts.push(`W${item.week}`)
  }
  if (eventId) {
    parts.push(plannedEvent ? renderLinkedEventId(runId, eventId) : eventId)
    if (persistedEvent) {
      parts.push(<Link to={viewerTournamentDetailPath(runId, eventId)}>Tournament detail {eventId}</Link>)
    }
  }
  if (item.snapshot_sequence != null) {
    if (item.kind === 'ranking_snapshot') {
      parts.push(<Link to={viewerRankingSnapshotPath(runId, item.snapshot_sequence)}>Ranking snapshot #{item.snapshot_sequence}</Link>)
    } else if (item.kind === 'race_snapshot') {
      parts.push(<Link to={viewerRaceSnapshotPath(runId, item.snapshot_sequence)}>Race snapshot #{item.snapshot_sequence}</Link>)
    }
  }

  return parts.map((part, index) => (
    <span key={index}>
      {index > 0 ? ' · ' : null}
      {part}
    </span>
  ))
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
  const activityLinkContext = useMemo<ActivityLinkContext>(() => ({
    plannedEvents: buildPlannedEventMap(runQuery.data),
    persistedEvents: new Map((eventsQuery.data?.events ?? []).map((event) => [event.event_id, event]))
  }), [eventsQuery.data?.events, runQuery.data])

  return (
    <section className="panel viewer-home viewer-home--msa">
      <div className="page-intro viewer-home__hero">
        <span className="eyebrow">MSA Homepage</span>
        <h2>MSA Squash — Season {context.selectedSeason} · W{context.selectedWeek}</h2>
        <p className="subtitle">
          A premium, public-style squash tour homepage for the selected Viewer context. These cards are read-only and show small real summaries only when existing safe run APIs provide them.
        </p>
      </div>
      <ViewerRunSelector compact />
      <p className="viewer-active-run-actions">
        <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
      </p>
      <section className="viewer-active-run-panel" aria-label="Active Viewer run status">
        {activeRunId ? (
          <>
            <div>
              <span className="eyebrow">Active Viewer run</span>
              <h3>Active run data is available</h3>
              {isActiveSummaryLoading ? <p className="status">Loading current tour summary from the active Viewer run…</p> : null}
              {isActiveSummaryUnavailable ? <ViewerEmptyState>Active run summary is temporarily unavailable. Try opening the run pages below for more detail.</ViewerEmptyState> : null}
              {!isActiveSummaryLoading && !isActiveSummaryUnavailable ? (
                <>
                  <p className="status">Using Viewer run <strong>{activeRunId}</strong> for read-only run pages.</p>
                  <ViewerMetadataList
                    className="viewer-home-summary-list"
                    ariaLabel="Active run summary fields"
                    items={[
                      { label: 'Run id', value: statusQuery.data?.run_id ?? runQuery.data?.run.run_id ?? activeRunId },
                      { label: 'Season', value: statusQuery.data?.season ?? runQuery.data?.run.season ?? 'Not available yet' },
                      { label: 'Seed', value: statusQuery.data?.seed ?? runQuery.data?.run.seed ?? 'Not available yet' },
                      { label: 'Progress', value: statusQuery.data ? `${statusQuery.data.progress.completed_event_count}/${statusQuery.data.progress.total_events} events complete` : `${runQuery.data?.run.completed_event_ids.length ?? 0}/${runQuery.data?.run.total_events ?? 0} events complete` },
                      { label: 'Next event index', value: statusQuery.data?.progress.next_event_index ?? runQuery.data?.run.next_event_index ?? 'Not available yet' },
                      { label: 'Finals', value: statusQuery.data?.finals.result_available || finalsQuery.data?.result ? 'Result available' : statusQuery.data?.finals.qualification_available || finalsQuery.data?.qualification ? 'Qualification available' : 'Not available yet' },
                      { label: 'Lineage/source', value: formatSource(statusQuery.data?.source?.source_type, statusQuery.data?.source?.parent_run_id) }
                    ]}
                  />
                </>
              ) : null}
            </div>
            <ViewerActiveRunLinks
              layout="grid"
              links={buildActiveRunHubLinks(activeRunId)}
            />
          </>
        ) : (
          <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
        )}
      </section>
      <ViewerLandingGrid>
        <ViewerSectionCard kicker="Featured Tournament Hero" title="Featured Tournament Hero" variant="hero">
          {activeRunId && featuredEvent ? (
            <>
              <p>{featuredEvent.status}: <strong>{renderLinkedEventId(activeRunId, featuredEvent.eventId)}</strong></p>
              <p className="status">{featuredEvent.category ?? 'Category unavailable'} · {featuredEvent.tour ?? 'Tour unavailable'} · {featuredEvent.week != null ? renderLinkedWeek(activeRunId, featuredEvent.week) : 'Week unavailable'} · Template {featuredEvent.templateId ?? 'unavailable'}</p>
              <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>Open active run schedule</Link>
            </>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only schedule" title="Other Tournaments This Week">
          {activeRunId && nearbyEvents.length ? (
            <ul>
              {nearbyEvents.map((event) => (
                <li key={event.event_id}>{renderLinkedEventId(activeRunId, event.event_id)} · {event.category} · {renderLinkedWeek(activeRunId, event.week)}</li>
              ))}
            </ul>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only rankings" title="Top 10 Rankings">
          {activeRunId && latestRankingSnapshot ? (
            <p>Latest ranking snapshot <Link to={viewerRankingSnapshotPath(activeRunId, latestRankingSnapshot.snapshot_sequence)}>#{latestRankingSnapshot.snapshot_sequence}</Link> from {latestRankingSnapshot.source_event_id ?? 'run history'} · {rankingSnapshotsQuery.data?.snapshots.length ?? 0} snapshots stored.</p>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={viewerRankingsPath(activeRunId)}>Open active run rankings</Link> : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only race" title="Race to Finals">
          {activeRunId && latestRaceSnapshot ? (
            <p>Latest race snapshot <Link to={viewerRaceSnapshotPath(activeRunId, latestRaceSnapshot.snapshot_sequence)}>#{latestRaceSnapshot.snapshot_sequence}</Link> from {latestRaceSnapshot.source_event_id ?? 'run history'} · {raceSnapshotsQuery.data?.snapshots.length ?? 0} snapshots stored.</p>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={viewerRacePath(activeRunId)}>Open active run race</Link> : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only matches" title="Featured Matches">
          <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
          {activeRunId ? <Link className="viewer-active-run-link" to={viewerTournamentsPath(activeRunId)}>Open active run tournaments</Link> : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only analytics" title="Predictions &amp; Upset Watch">
          <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only storylines" title="Storylines">
          {activeRunId && latestActivityItem ? (
            <p>{activityItems.length} activity items · Latest: {renderActivityItem(latestActivityItem, activeRunId, activityLinkContext)}</p>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={viewerHistoryPath(activeRunId)}>Open active run history</Link> : null}
        </ViewerSectionCard>
      </ViewerLandingGrid>
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
        <ViewerEmptyState>{config.emptyMessage}</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const snapshots = snapshotsQuery.data?.snapshots ?? []
  const latest = latestSnapshot(snapshots)
  const rankingPreview = config.mode === 'ranking' && latest ? parseRankingPreviewPayload(latest.payload) : null
  const racePreview = config.mode === 'race' && latest ? parseRacePreviewPayload(latest.payload) : null

  return (
    <ViewerShellPage title={config.title} description={config.description}>
      <ViewerActiveRunCard ariaLabel={`${config.title} active run snapshot summary`} title={`${config.title} snapshot landing`}>
        <ViewerMetadataList
          items={[
            { label: 'Active run ID', value: activeRunId },
            { label: config.countLabel, value: snapshotsQuery.isLoading ? 'Loading…' : snapshots.length },
            { label: 'Latest snapshot sequence', value: latest ? latest.snapshot_sequence : '—' },
            { label: 'Latest source event ID', value: latest?.source_event_id ?? '—' },
            { label: 'Latest snapshot kind', value: latest?.snapshot_kind ?? '—' }
          ]}
        />

        {snapshotsQuery.isError ? <ViewerEmptyState>Snapshot metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
        {!snapshotsQuery.isLoading && !snapshotsQuery.isError && !latest ? <ViewerEmptyState>{config.noSnapshotsMessage}</ViewerEmptyState> : null}
        {rankingPreview?.rows.length ? (
          <div>
            <h4>Top 10 Ranking Preview</h4>
            <RankingPreviewTable rows={rankingPreview.rows} ariaLabel="Latest Top 10 ranking preview table" runId={activeRunId} />
          </div>
        ) : null}
        {racePreview?.rows.length ? (
          <div>
            <h4>Top 10 Race Preview</h4>
            <RacePreviewTable rows={racePreview.rows} ariaLabel="Latest Top 10 race preview table" runId={activeRunId} />
          </div>
        ) : null}

        <ViewerActiveRunLinks
          links={[
            { label: config.openLabel, to: config.runScopedPath(activeRunId) },
            ...(latest ? [{ label: config.latestLabel, to: config.detailPath(activeRunId, latest.snapshot_sequence) }] : [])
          ]}
        />
      </ViewerActiveRunCard>
    </ViewerShellPage>
  )
}


type ViewerRankingDeferredKind = 'next-gen' | 'elo' | 'power' | 'form' | 'no1-history'

type ViewerRankingDeferredConfig = {
  title: string
  deferredCopy: string
}

const VIEWER_RANKING_DEFERRED_CONFIG: Record<ViewerRankingDeferredKind, ViewerRankingDeferredConfig> = {
  'next-gen': {
    title: 'Next Gen Race',
    deferredCopy: 'No Next Gen ranking table is shown until a real Next Gen ranking read model exists.'
  },
  elo: {
    title: 'Elo Ranking',
    deferredCopy: 'No Elo ranking table is shown until a real Elo ranking read model exists.'
  },
  power: {
    title: 'Power Rating',
    deferredCopy: 'No Power Rating table is shown until a real Power Rating read model exists.'
  },
  form: {
    title: 'Form Ranking',
    deferredCopy: 'No form ranking table is shown until a real form ranking read model exists.'
  },
  'no1-history': {
    title: 'No.1 History',
    deferredCopy: 'No No.1 history table is shown until a real ranking history read model exists.'
  }
}

export function ViewerRankingDeferredPage({ kind }: { kind: ViewerRankingDeferredKind }): JSX.Element {
  const config = VIEWER_RANKING_DEFERRED_CONFIG[kind]
  const activeRunId = useActiveViewerRunId()
  const runQuery = useQuery({ queryKey: ['viewer-ranking-deferred-run', kind, activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const statusQuery = useQuery({ queryKey: ['viewer-ranking-deferred-status', kind, activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-ranking-deferred-events', kind, activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-ranking-deferred-ranking-snapshots', kind, activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-ranking-deferred-race-snapshots', kind, activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-ranking-deferred-finals', kind, activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description="Read-only rankings destination requiring an active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data
  })
  const orderedEventCount = runQuery.data?.season_state.ordered_events.length ?? statusQuery.data?.progress.total_events ?? runQuery.data?.run.total_events ?? null
  const season = statusQuery.data?.season ?? runQuery.data?.season_state.season ?? runQuery.data?.run.season ?? finalsQuery.data?.season ?? null
  const nextScheduledEvent = selectNextOrderedEvent(runQuery.data)
  const isLoadingMetadata = runQuery.isLoading || statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading || finalsQuery.isLoading
  const hasMetadataError = runQuery.isError || statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError || finalsQuery.isError
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(metadata, orderedEventCount)

  return (
    <ViewerShellPage title={config.title} description="Conservative read-only rankings page using existing active-run metadata only.">
      <article className="viewer-active-run-card" aria-label={`${config.title} active run metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">No real read model exists yet. This page only shows safe source availability from the active Viewer run.</p>
        {isLoadingMetadata ? <p className="status">Loading active run metadata…</p> : null}
        {hasMetadataError ? <ViewerEmptyState>Some active run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList([
            { label: 'Active run ID', value: activeRunId },
            { label: 'Season', value: renderLoadingValue(runQuery.isLoading, season) },
            { label: 'Ranking snapshot count', value: renderLoadingValue(rankingSnapshotsQuery.isLoading, metadata.rankingSnapshotCount) },
            { label: 'Race snapshot count', value: renderLoadingValue(raceSnapshotsQuery.isLoading, metadata.raceSnapshotCount) },
            { label: 'Completed/persisted event count', value: renderLoadingValue(eventsQuery.isLoading, metadata.eventCount) },
            { label: 'Ordered calendar event count', value: renderLoadingValue(runQuery.isLoading, orderedEventCount) },
            { label: 'Finals availability', value: renderFinalsSourceValue(activeRunId, metadata.finalsAvailability, finalsQuery.isLoading) },
            { label: 'Latest ranking snapshot', value: renderLatestRankingSnapshotSourceValue(activeRunId, metadata.latestRankingSnapshot) },
            { label: 'Latest race snapshot', value: renderLatestRaceSnapshotSourceValue(activeRunId, metadata.latestRaceSnapshot) },
            { label: 'Latest persisted event', value: renderLatestPersistedEventSourceValue(activeRunId, metadata.latestPersistedEvent) },
            { label: 'Next scheduled event', value: nextScheduledEvent ? <Link to={viewerPlannedEventPath(activeRunId, nextScheduledEvent.event_id)}>{nextScheduledEvent.event_id}</Link> : '—' }
          ])}
          {!isLoadingMetadata && !hasMetadataError && !hasAnySourceMetadata ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        </section>
        <section aria-label={`${config.title} deferred output explanation`}>
          <h3>Deferred output</h3>
          <p className="status">{config.deferredCopy}</p>
        </section>
        <section aria-label={`${config.title} source links`}>
          <h3>Source links</h3>
          <ViewerActiveRunLinks
            links={[
              { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
              { label: 'Open active run race', to: viewerRacePath(activeRunId) },
              { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) },
              { label: 'Open active run calendar', to: viewerSeasonCalendarPath(activeRunId) },
              { label: 'Open run browser', to: viewerRunsPath() }
            ]}
          />
        </section>
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
        description: 'Read-only rankings publication for the selected season and week context.',
        emptyMessage: 'No data is available for this run yet.',
        noSnapshotsMessage: 'No data is available for this run yet.',
        countLabel: 'Ranking snapshot count',
        openLabel: 'Open active run rankings',
        latestLabel: 'View latest ranking snapshot',
        runScopedPath: (runId) => viewerRankingsPath(runId),
        detailPath: (runId, snapshotSequence) => viewerRankingSnapshotPath(runId, snapshotSequence)
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
        description: 'Read-only Race to Finals publication for the selected Viewer run.',
        emptyMessage: 'No data is available for this run yet.',
        noSnapshotsMessage: 'No data is available for this run yet.',
        countLabel: 'Race snapshot count',
        openLabel: 'Open active run race',
        latestLabel: 'View latest race snapshot',
        runScopedPath: (runId) => viewerRacePath(runId),
        detailPath: (runId, snapshotSequence) => viewerRaceSnapshotPath(runId, snapshotSequence)
      }}
    />
  )
}

export function ViewerSeasonHubPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()

  const runQuery = useQuery({ queryKey: ['viewer-season-hub-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const statusQuery = useQuery({ queryKey: ['viewer-season-hub-status', activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-season-hub-events', activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-season-hub-finals', activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Season Hub" description="Read-only season hub for the selected Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const persistedEvents = eventsQuery.data?.events ?? []
  const plannedMap = buildPlannedEventMap(runQuery.data)
  const nextEvent = selectNextOrderedEvent(runQuery.data)
  const latestPersistedEvent = selectLatestPersistedEvent(persistedEvents)
  const progress = statusQuery.data?.progress
  const season = statusQuery.data?.season ?? runQuery.data?.season_state.season ?? runQuery.data?.run.season ?? '—'
  const eventCount = orderedEvents.length || runQuery.data?.run.total_events || persistedEvents.length

  return (
    <ViewerShellPage title="Season Hub" description="Read-only top-level season summary from the active Viewer run's existing calendar and event APIs.">
      <article className="viewer-active-run-card" aria-label="Season Hub active run summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>Season Hub summary</h3>
        {runQuery.isLoading || statusQuery.isLoading || eventsQuery.isLoading || finalsQuery.isLoading ? <p className="status">Loading active run tour summary…</p> : null}
        {runQuery.isError || statusQuery.isError || eventsQuery.isError || finalsQuery.isError ? <ViewerEmptyState>Some active run tour metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Season</dt><dd>{season}</dd></div>
          <div><dt>Progress</dt><dd>{progress ? `${progress.completed_event_count}/${progress.total_events} events complete` : `${runQuery.data?.run.completed_event_ids.length ?? persistedEvents.length}/${eventCount} events complete`}</dd></div>
          <div><dt>Next event index</dt><dd>{progress?.next_event_index ?? runQuery.data?.season_state.next_event_index ?? runQuery.data?.run.next_event_index ?? '—'}</dd></div>
          <div><dt>Event count</dt><dd>{eventCount}</dd></div>
          <div><dt>Next scheduled event</dt><dd>{nextEvent ? renderEventSummary(nextEvent, activeRunId) : '—'}</dd></div>
          <div><dt>Most recent persisted event</dt><dd>{renderPersistedEventSummary(latestPersistedEvent, plannedMap, activeRunId)}</dd></div>
          <div><dt>Finals availability</dt><dd>{formatFinalsAvailability(finalsQuery.data)}</dd></div>
        </dl>
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(activeRunId)}>Open active run tournaments</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>Open active run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerFinalsPath(activeRunId)}>Open active run finals</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerCurrentWeekPage(): JSX.Element {
  const context = useViewerContext()
  const activeRunId = useActiveViewerRunId()
  const runQuery = useQuery({ queryKey: ['viewer-current-week-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Current Week" description="Read-only current week schedule for the active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const eventsForWeek = (runQuery.data?.season_state.ordered_events ?? []).filter((event) => event.week === context.selectedWeek)

  return (
    <ViewerShellPage title="Current Week" description="Read-only current week schedule from the active Viewer run calendar.">
      <article className="viewer-active-run-card" aria-label="Current Week active run summary">
        <span className="eyebrow">Selected Viewer week</span>
        <h3>Season {context.selectedSeason} · W{context.selectedWeek}</h3>
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Selected season</dt><dd>{context.selectedSeason}</dd></div>
          <div><dt>Selected week</dt><dd>{context.selectedWeek}</dd></div>
        </dl>
        {runQuery.isLoading ? <p className="status">Loading selected-week events…</p> : null}
        {runQuery.isError ? <ViewerEmptyState>Selected-week event metadata is temporarily unavailable.</ViewerEmptyState> : null}
        {!runQuery.isLoading && !runQuery.isError && !eventsForWeek.length ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        {eventsForWeek.length ? (
          <ul className="viewer-home-list" aria-label="Selected week ordered events">
            {eventsForWeek.map((event) => (
              <li key={event.event_id}>{renderOrderedEventMetadata(event, activeRunId)}</li>
            ))}
          </ul>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>Open active run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerTournamentsPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const runQuery = useQuery({ queryKey: ['viewer-tournaments-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-tournaments-events', activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="All Tournaments" description="Read-only tournament schedule and results archive for the selected Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const persistedEvents = eventsQuery.data?.events ?? []
  const plannedMap = buildPlannedEventMap(runQuery.data)
  const nextEvent = selectNextOrderedEvent(runQuery.data)
  const latestPersistedEvent = selectLatestPersistedEvent(persistedEvents)
  const sampleEvents = orderedEvents.slice(0, 5)
  const hasMetadata = orderedEvents.length > 0 || persistedEvents.length > 0

  return (
    <ViewerShellPage title="All Tournaments" description="Read-only tournament schedule and publications from the active Viewer run.">
      <article className="viewer-active-run-card" aria-label="All Tournaments active run summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>All Tournaments summary</h3>
        {runQuery.isLoading || eventsQuery.isLoading ? <p className="status">Loading tournament metadata…</p> : null}
        {runQuery.isError || eventsQuery.isError ? <ViewerEmptyState>Tournament metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Total ordered calendar events</dt><dd>{runQuery.isLoading ? 'Loading…' : orderedEvents.length || '—'}</dd></div>
          <div><dt>Persisted event count</dt><dd>{eventsQuery.isLoading ? 'Loading…' : persistedEvents.length}</dd></div>
          <div><dt>Next scheduled event</dt><dd>{nextEvent ? renderEventSummary(nextEvent, activeRunId) : '—'}</dd></div>
          <div><dt>Latest persisted event</dt><dd>{renderPersistedEventSummary(latestPersistedEvent, plannedMap, activeRunId)}</dd></div>
        </dl>
        {!runQuery.isLoading && !eventsQuery.isLoading && !runQuery.isError && !eventsQuery.isError && !hasMetadata ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        {sampleEvents.length ? (
          <div>
            <h4>Sample schedule events</h4>
            <ul className="viewer-home-list" aria-label="Sample ordered tournament events">
              {sampleEvents.map((event) => (
                <li key={event.event_id}>{renderOrderedEventMetadata(event, activeRunId)}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(activeRunId)}>Open active run tournaments</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>Open active run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}

function renderLinkedPlayer(runId: string, playerId: string | null | undefined, label: ReactNode): ReactNode {
  if (!playerId) return label || '—'
  return <Link to={viewerPlayerProfilePath(runId, playerId)}>{label || playerId}</Link>
}

function renderLinkedCountry(runId: string, countryCode: string | null | undefined, label?: ReactNode): ReactNode {
  if (!countryCode) return label ?? '—'
  return <Link to={viewerCountryProfilePath(runId, countryCode)}>{label ?? countryCode}</Link>
}

function renderPlayerSampleMetadata(player: RunPlayerListItem, runId?: string, options: { includeQualityBand?: boolean } = {}): JSX.Element {
  const playerLabel = player.name || player.player_id || '—'
  const playerId = player.player_id || '—'
  const country = player.country_code || '—'

  const items = [
    { label: 'Player', value: runId ? renderLinkedPlayer(runId, player.player_id, playerLabel) : playerLabel },
    { label: 'Player ID', value: runId ? renderLinkedPlayer(runId, player.player_id, playerId) : playerId },
    { label: 'Country', value: runId ? renderLinkedCountry(runId, player.country_code) : country },
    { label: 'Age', value: player.age ?? '—' },
    { label: 'Power Rating', value: player.overall ?? '—' }
  ]

  if (options.includeQualityBand) {
    items.push({ label: 'Quality band', value: player.quality_band ?? '—' })
  }

  return <ViewerMetadataList items={items} />
}

function renderCountrySampleMetadata(nation: RunNationSummaryItem, runId?: string): JSX.Element {
  const countryCode = nation.country_code || '—'
  const countryName = nation.country_name ?? nation.country_code ?? '—'
  const topPlayer = nation.top_player_name ?? nation.top_player_id ?? '—'

  return (
    <ViewerMetadataList
      items={[
        { label: 'Country code', value: runId ? renderLinkedCountry(runId, nation.country_code) : countryCode },
        { label: 'Country name', value: runId ? renderLinkedCountry(runId, nation.country_code, countryName) : countryName },
        { label: 'Player count', value: nation.total_players ?? '—' },
        { label: 'Average Power Rating', value: nation.average_overall ?? '—' },
        { label: 'Top player', value: runId ? renderLinkedPlayer(runId, nation.top_player_id, topPlayer) : topPlayer },
        { label: 'Top player Power Rating', value: nation.top_player_overall ?? '—' }
      ]}
    />
  )
}


type ViewerPlayersDeferredKind = 'all' | 'active' | 'next-gen' | 'retired'

type ViewerPlayersDeferredConfig = {
  title: string
  deferredCopy: string
}

const viewerPlayersDeferredConfigs: Record<ViewerPlayersDeferredKind, ViewerPlayersDeferredConfig> = {
  all: {
    title: 'All Players',
    deferredCopy: 'No full player directory is shown until a real player directory read model exists.'
  },
  active: {
    title: 'Active Players',
    deferredCopy: 'No active-player list is shown until a real player status read model exists.'
  },
  'next-gen': {
    title: 'Prospects / Next Gen',
    deferredCopy: 'No prospects list is shown until a real Next Gen player read model exists.'
  },
  retired: {
    title: 'Retired Players',
    deferredCopy: 'No retired-player list is shown until a real player career-status read model exists.'
  }
}

export function ViewerPlayersDeferredPage({ kind }: { kind: ViewerPlayersDeferredKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerPlayersDeferredConfigs[kind]
  const playersQuery = useQuery({
    queryKey: ['viewer-players-deferred-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })
  const statusQuery = useQuery({
    queryKey: ['viewer-players-deferred-status', activeRunId],
    queryFn: () => getRunStatusSummary(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-players-deferred-events', activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-players-deferred-ranking-snapshots', activeRunId],
    queryFn: () => listRankingSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-players-deferred-race-snapshots', activeRunId],
    queryFn: () => listRaceSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description="Read-only Players destination requiring an active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players ?? []
  const samplePlayers = players.slice(0, 5)
  const completedEventCount = eventsQuery.data?.events.length ?? statusQuery.data?.history_counts.events ?? null
  const rankingSnapshotCount = rankingSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.ranking_snapshots ?? null
  const raceSnapshotCount = raceSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.race_snapshots ?? null
  const isLoadingMetadata = playersQuery.isLoading || statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading
  const hasMetadataError = playersQuery.isError || statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError

  return (
    <ViewerShellPage title={config.title} description="Conservative read-only Players page using existing active-run player metadata only.">
      <article className="viewer-active-run-card" aria-label={`${config.title} active run player metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">No real read model exists yet. This page only shows safe player and source metadata from the active Viewer run.</p>
        {isLoadingMetadata ? <p className="status">Loading active run player metadata…</p> : null}
        {hasMetadataError ? <ViewerEmptyState>Some active run player metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          <dl className="metadata-list">
            <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
            <div><dt>Total player count</dt><dd>{playersQuery.isLoading ? 'Loading…' : playersQuery.data?.total ?? '—'}</dd></div>
            <div><dt>Returned/sample player count</dt><dd>{playersQuery.isLoading ? 'Loading…' : `${players.length}/${samplePlayers.length}`}</dd></div>
            <div><dt>Completed/persisted event count</dt><dd>{eventsQuery.isLoading && completedEventCount == null ? 'Loading…' : completedEventCount ?? '—'}</dd></div>
            <div><dt>Ranking snapshot count</dt><dd>{rankingSnapshotsQuery.isLoading && rankingSnapshotCount == null ? 'Loading…' : rankingSnapshotCount ?? '—'}</dd></div>
            <div><dt>Race snapshot count</dt><dd>{raceSnapshotsQuery.isLoading && raceSnapshotCount == null ? 'Loading…' : raceSnapshotCount ?? '—'}</dd></div>
          </dl>
          {!isLoadingMetadata && !hasMetadataError && players.length === 0 && completedEventCount === 0 && rankingSnapshotCount === 0 && raceSnapshotCount === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        </section>
        <section aria-label={`${config.title} sample players`}>
          <h3>Sample players</h3>
          <p className="status">Read-only sample from the active run player endpoint using identifiers and metadata fields already returned by the API.</p>
          <ViewerSampleList
            title="Sample active run players"
            label={`${config.title} safe sample players`}
            items={samplePlayers}
            getKey={(player) => player.player_id || player.name || 'unknown-player'}
            renderItem={(player) => renderPlayerSampleMetadata(player, activeRunId, { includeQualityBand: true })}
          />
        </section>
        <section aria-label={`${config.title} deferred output explanation`}>
          <h3>Deferred output</h3>
          <p className="status">{config.deferredCopy}</p>
        </section>
        <section aria-label={`${config.title} source links`}>
          <h3>Source links</h3>
          <ViewerActiveRunLinks
            links={[
              { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
              { label: 'Open active run countries', to: viewerCountriesPath(activeRunId) },
              { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
              { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) },
              { label: 'Open Viewer search', to: viewerTopSearchPath() },
              { label: 'Open run browser', to: viewerRunsPath() }
            ]}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerPlayersPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const playersQuery = useQuery({
    queryKey: ['viewer-players-hub-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 5, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title="Players"
        description="Read-only player profiles and browsing in the selected Viewer context."
      >
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players ?? []

  return (
    <ViewerShellPage title="Players" description="Read-only player profiles using existing active-run player data.">
      <article className="viewer-active-run-card" aria-label="Players active run summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>Players summary</h3>
        {playersQuery.isLoading ? <p className="status">Loading active run player metadata…</p> : null}
        {playersQuery.isError ? <ViewerEmptyState>Player metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Total player count</dt><dd>{playersQuery.isLoading ? 'Loading…' : playersQuery.data?.total ?? '—'}</dd></div>
          <div><dt>Returned player count</dt><dd>{playersQuery.isLoading ? 'Loading…' : players.length}</dd></div>
        </dl>
        {!playersQuery.isLoading && !playersQuery.isError && players.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        <ViewerSampleList
          title="Sample players"
          label="Sample active run players"
          items={players}
          getKey={(player) => player.player_id || player.name || 'unknown-player'}
          renderItem={(player) => renderPlayerSampleMetadata(player, activeRunId)}
        />
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerPlayersPath(activeRunId)}>Open active run players</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}


type ViewerCountriesDeferredKind = 'ranking' | 'all' | 'hosting' | 'talent-pipeline' | 'records'

type ViewerCountriesDeferredConfig = {
  title: string
  deferredCopy: string
}

const viewerCountriesDeferredConfigs: Record<ViewerCountriesDeferredKind, ViewerCountriesDeferredConfig> = {
  ranking: {
    title: 'Country Ranking',
    deferredCopy: 'No country ranking table is shown until a real country ranking read model exists.'
  },
  all: {
    title: 'All Countries',
    deferredCopy: 'No full country directory is shown until a real country directory read model exists.'
  },
  hosting: {
    title: 'Hosting Nations',
    deferredCopy: 'No hosting nation table is shown until a real hosting read model exists.'
  },
  'talent-pipeline': {
    title: 'Talent Pipeline',
    deferredCopy: 'No talent pipeline table is shown until a real country talent read model exists.'
  },
  records: {
    title: 'Country Records',
    deferredCopy: 'No country records table is shown until a real country records read model exists.'
  }
}

export function ViewerCountriesDeferredPage({ kind }: { kind: ViewerCountriesDeferredKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerCountriesDeferredConfigs[kind]
  const nationsQuery = useQuery({
    queryKey: ['viewer-countries-deferred-run-nations', activeRunId],
    queryFn: () => listRunNations(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })
  const statusQuery = useQuery({
    queryKey: ['viewer-countries-deferred-status', activeRunId],
    queryFn: () => getRunStatusSummary(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-countries-deferred-events', activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-countries-deferred-ranking-snapshots', activeRunId],
    queryFn: () => listRankingSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-countries-deferred-race-snapshots', activeRunId],
    queryFn: () => listRaceSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description="Read-only Countries destination requiring an active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const nations = nationsQuery.data?.nations ?? []
  const sampleNations = nations.slice(0, 5)
  const completedEventCount = eventsQuery.data?.events.length ?? statusQuery.data?.history_counts.events ?? null
  const rankingSnapshotCount = rankingSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.ranking_snapshots ?? null
  const raceSnapshotCount = raceSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.race_snapshots ?? null
  const isLoadingMetadata = nationsQuery.isLoading || statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading
  const hasMetadataError = nationsQuery.isError || statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError

  return (
    <ViewerShellPage title={config.title} description="Conservative read-only Countries page using existing active-run country metadata only.">
      <article className="viewer-active-run-card" aria-label={`${config.title} active run country metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">No real read model exists yet. This page only shows safe country and source metadata from the active Viewer run.</p>
        {isLoadingMetadata ? <p className="status">Loading active run country metadata…</p> : null}
        {hasMetadataError ? <ViewerEmptyState>Some active run country metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          <dl className="metadata-list">
            <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
            <div><dt>Total country/nation count</dt><dd>{nationsQuery.isLoading ? 'Loading…' : nationsQuery.data?.total ?? '—'}</dd></div>
            <div><dt>Returned/sample country count</dt><dd>{nationsQuery.isLoading ? 'Loading…' : `${nations.length}/${sampleNations.length}`}</dd></div>
            <div><dt>Completed/persisted event count</dt><dd>{eventsQuery.isLoading && completedEventCount == null ? 'Loading…' : completedEventCount ?? '—'}</dd></div>
            <div><dt>Ranking snapshot count</dt><dd>{rankingSnapshotsQuery.isLoading && rankingSnapshotCount == null ? 'Loading…' : rankingSnapshotCount ?? '—'}</dd></div>
            <div><dt>Race snapshot count</dt><dd>{raceSnapshotsQuery.isLoading && raceSnapshotCount == null ? 'Loading…' : raceSnapshotCount ?? '—'}</dd></div>
          </dl>
          {!isLoadingMetadata && !hasMetadataError && nations.length === 0 && completedEventCount === 0 && rankingSnapshotCount === 0 && raceSnapshotCount === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        </section>
        <section aria-label={`${config.title} sample countries`}>
          <h3>Sample countries</h3>
          <p className="status">Read-only sample from the active run nations endpoint using identifiers and metadata fields already returned by the API.</p>
          <ViewerSampleList
            title="Sample active run countries"
            label={`${config.title} safe sample countries`}
            items={sampleNations}
            getKey={(nation) => nation.country_code || nation.country_name || 'unknown-country'}
            renderItem={(nation) => renderCountrySampleMetadata(nation, activeRunId)}
          />
        </section>
        <section aria-label={`${config.title} deferred output explanation`}>
          <h3>Deferred output</h3>
          <p className="status">{config.deferredCopy}</p>
        </section>
        <section aria-label={`${config.title} source links`}>
          <h3>Source links</h3>
          <ViewerActiveRunLinks
            links={[
              { label: 'Open active run countries', to: viewerCountriesPath(activeRunId) },
              { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
              { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
              { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) },
              { label: 'Open Viewer search', to: viewerTopSearchPath() },
              { label: 'Open run browser', to: viewerRunsPath() }
            ]}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerCountriesPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const nationsQuery = useQuery({
    queryKey: ['viewer-countries-hub-run-nations', activeRunId],
    queryFn: () => listRunNations(activeRunId ?? '', { limit: 5, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Countries" description="Read-only country profiles and national summaries in the selected Viewer context.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const nations = nationsQuery.data?.nations ?? []

  return (
    <ViewerShellPage title="Countries" description="Read-only country profiles using existing active-run country data.">
      <article className="viewer-active-run-card" aria-label="Countries active run summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>Countries summary</h3>
        {nationsQuery.isLoading ? <p className="status">Loading active run country metadata…</p> : null}
        {nationsQuery.isError ? <ViewerEmptyState>Country metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Total country count</dt><dd>{nationsQuery.isLoading ? 'Loading…' : nationsQuery.data?.total ?? '—'}</dd></div>
          <div><dt>Returned country count</dt><dd>{nationsQuery.isLoading ? 'Loading…' : nations.length}</dd></div>
        </dl>
        {!nationsQuery.isLoading && !nationsQuery.isError && nations.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        <ViewerSampleList
          title="Sample countries"
          label="Sample active run countries"
          items={nations}
          getKey={(nation) => nation.country_code}
          renderItem={(nation) => renderCountrySampleMetadata(nation, activeRunId)}
        />
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerCountriesPath(activeRunId)}>Open active run countries</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}

function selectLatestActivityItem(items: RunActivityItem[]): RunActivityItem | null {
  return [...items].sort((a, b) => (b.sequence ?? -1) - (a.sequence ?? -1))[0] ?? null
}

export function ViewerHistoryPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const activityQuery = useQuery({ queryKey: ['viewer-history-activity', activeRunId], queryFn: () => getRunActivity(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const runQuery = useQuery({ queryKey: ['viewer-history-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const statusQuery = useQuery({ queryKey: ['viewer-history-run-status', activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-history-events', activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-history-ranking-snapshots', activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-history-race-snapshots', activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="History" description="Read-only history and season timeline for the selected Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const activityItems = activityQuery.data?.items ?? []
  const latestActivity = selectLatestActivityItem(activityItems)
  const eventCount = eventsQuery.data?.events.length ?? statusQuery.data?.history_counts.events ?? null
  const rankingSnapshotCount = rankingSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.ranking_snapshots ?? null
  const raceSnapshotCount = raceSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.race_snapshots ?? null
  const latestRankingSnapshot = latestSnapshot(rankingSnapshotsQuery.data?.snapshots ?? [])
  const latestRaceSnapshot = latestSnapshot(raceSnapshotsQuery.data?.snapshots ?? [])
  const activityLinkContext: ActivityLinkContext = {
    plannedEvents: buildPlannedEventMap(runQuery.data),
    persistedEvents: new Map((eventsQuery.data?.events ?? []).map((event) => [event.event_id, event]))
  }
  const hasAnyMetadata = activityItems.length > 0 || (eventCount ?? 0) > 0 || (rankingSnapshotCount ?? 0) > 0 || (raceSnapshotCount ?? 0) > 0

  return (
    <ViewerShellPage title="History" description="Read-only history using existing active-run activity, event, and publication data only.">
      <article className="viewer-active-run-card" aria-label="History active run metadata summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>History summary</h3>
        {activityQuery.isLoading || runQuery.isLoading || statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading ? <p className="status">Loading active run history metadata…</p> : null}
        {activityQuery.isError || runQuery.isError || statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError ? <ViewerEmptyState>Some active run history metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Activity item count</dt><dd>{activityQuery.isLoading ? 'Loading…' : activityItems.length}</dd></div>
          <div><dt>Latest activity item</dt><dd>{latestActivity ? renderActivityItem(latestActivity, activeRunId, activityLinkContext) : '—'}</dd></div>
          <div><dt>Event count</dt><dd>{eventsQuery.isLoading && eventCount == null ? 'Loading…' : eventCount ?? '—'}</dd></div>
          <div><dt>Ranking snapshot count</dt><dd>{rankingSnapshotsQuery.isLoading && rankingSnapshotCount == null ? 'Loading…' : rankingSnapshotCount ?? '—'}</dd></div>
          <div><dt>Latest ranking snapshot sequence</dt><dd>{latestRankingSnapshot ? <Link to={viewerRankingSnapshotPath(activeRunId, latestRankingSnapshot.snapshot_sequence)}>#{latestRankingSnapshot.snapshot_sequence}</Link> : '—'}</dd></div>
          <div><dt>Race snapshot count</dt><dd>{raceSnapshotsQuery.isLoading && raceSnapshotCount == null ? 'Loading…' : raceSnapshotCount ?? '—'}</dd></div>
          <div><dt>Latest race snapshot sequence</dt><dd>{latestRaceSnapshot ? <Link to={viewerRaceSnapshotPath(activeRunId, latestRaceSnapshot.snapshot_sequence)}>#{latestRaceSnapshot.snapshot_sequence}</Link> : '—'}</dd></div>
        </dl>
        {!activityQuery.isLoading && !runQuery.isLoading && !statusQuery.isLoading && !eventsQuery.isLoading && !rankingSnapshotsQuery.isLoading && !raceSnapshotsQuery.isLoading && !hasAnyMetadata ? (
          <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerHistoryPath(activeRunId)}>Open active run history</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}

type ViewerRecordsLandingKind = 'records' | 'stats'

const deferredRecordGroups = [
  { title: 'Title Leaders', description: 'needs dedicated records read model.' },
  { title: 'Weeks at No.1', description: 'needs dedicated records read model.' },
  { title: 'Streaks', description: 'needs dedicated records read model.' },
  { title: 'Biggest Upsets', description: 'needs match/prediction read model.' },
  { title: 'Best Seasons', description: 'needs historical stats read model.' }
]

const deferredStatsGroups = [
  { title: 'Player Stats', description: 'needs dedicated player statistics read model.' },
  { title: 'Tournament Stats', description: 'needs dedicated tournament statistics read model.' },
  { title: 'Country Stats', description: 'needs dedicated country statistics read model.' },
  { title: 'Awards', description: 'needs dedicated awards read model.' },
  { title: 'Hall of Fame', description: 'needs dedicated Hall of Fame read model.' },
  { title: 'Era Rankings', description: 'needs dedicated era comparison read model.' }
]

function ViewerRecordsStatsLandingPage({ kind }: { kind: ViewerRecordsLandingKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const statusQuery = useQuery({ queryKey: ['viewer-records-status', kind, activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-records-events', kind, activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-records-ranking-snapshots', kind, activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-records-race-snapshots', kind, activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-records-finals', kind, activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  const isStats = kind === 'stats'
  const title = isStats ? 'Stats' : 'Records'

  if (!activeRunId) {
    return (
      <ViewerShellPage title={title} description={isStats ? 'Stats library destination prepared for connected run-scoped statistical read models.' : 'Record book destination prepared for statistics, milestones, and historical achievements.'}>
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data
  })
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(metadata)
  const deferredGroups = isStats ? deferredStatsGroups : deferredRecordGroups

  return (
    <ViewerShellPage title={title} description={isStats ? 'Conservative Stats landing using existing active-run metadata only.' : 'Conservative Records landing using existing active-run metadata only.'}>
      <article className="viewer-active-run-card" aria-label={`${title} active run metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{isStats ? 'Stats Overview' : 'Records Overview'}</h3>
        <p className="subtitle">
          {isStats
            ? 'Read-only statistics landing showing only available active-run source metadata until real stat read models exist.'
            : 'Read-only record book landing showing only available active-run source metadata until real record read models exist.'}
        </p>
        {statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading || finalsQuery.isLoading ? <p className="status">Loading active run metadata…</p> : null}
        {statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError || finalsQuery.isError ? <ViewerEmptyState>Some active run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${title} source metadata`}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList(commonDeferredSourceMetadataItems({
            activeRunId,
            metadata,
            eventsLoading: eventsQuery.isLoading,
            rankingSnapshotsLoading: rankingSnapshotsQuery.isLoading,
            raceSnapshotsLoading: raceSnapshotsQuery.isLoading,
            finalsLoading: finalsQuery.isLoading
          }))}
          {!statusQuery.isLoading && !eventsQuery.isLoading && !rankingSnapshotsQuery.isLoading && !raceSnapshotsQuery.isLoading && !finalsQuery.isLoading && !hasAnySourceMetadata ? (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          ) : null}
        </section>
        <section aria-label={`${title} deferred groups`}>
          <ViewerDeferredFeatureList
            title={isStats ? 'Deferred stat groups' : 'Deferred record groups'}
            label={isStats ? 'Deferred stat groups' : 'Deferred record groups'}
            features={deferredGroups}
          />
        </section>
        <section aria-label={`${title} links`}>
          <h3>Links</h3>
          <ViewerActiveRunLinks
            links={[
              { label: 'Open run browser', to: viewerRunsPath() },
              { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) },
              { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
              { label: 'Open active run race', to: viewerRacePath(activeRunId) },
              { label: 'Open active run finals', to: viewerFinalsPath(activeRunId) }
            ]}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerRecordsPage(): JSX.Element {
  return <ViewerRecordsStatsLandingPage kind="records" />
}

export function ViewerStatsPage(): JSX.Element {
  return <ViewerRecordsStatsLandingPage kind="stats" />
}


type ViewerStatsDeferredKind =
  | 'title-leaders'
  | 'no1-weeks'
  | 'streaks'
  | 'upsets'
  | 'best-seasons'
  | 'player-stats'
  | 'tournament-stats'
  | 'country-stats'
  | 'awards'
  | 'hall-of-fame'
  | 'era-rankings'

type ViewerStatsDeferredConfig = {
  title: string
  deferredCopy: string
}

const viewerStatsDeferredConfigs: Record<ViewerStatsDeferredKind, ViewerStatsDeferredConfig> = {
  'title-leaders': { title: 'Title Leaders', deferredCopy: 'No title leader table is shown until a real records read model exists.' },
  'no1-weeks': { title: 'Weeks at No.1', deferredCopy: 'No weeks-at-No.1 table is shown until a real ranking history read model exists.' },
  streaks: { title: 'Streaks', deferredCopy: 'No streak table is shown until a real streak records read model exists.' },
  upsets: { title: 'Biggest Upsets', deferredCopy: 'No upset table is shown until real match and ranking history read models exist.' },
  'best-seasons': { title: 'Best Seasons', deferredCopy: 'No best-season table is shown until a real season statistics read model exists.' },
  'player-stats': { title: 'Player Stats', deferredCopy: 'No player statistics table is shown until a real player statistics read model exists.' },
  'tournament-stats': { title: 'Tournament Stats', deferredCopy: 'No tournament statistics table is shown until a real tournament statistics read model exists.' },
  'country-stats': { title: 'Country Stats', deferredCopy: 'No country statistics table is shown until a real country statistics read model exists.' },
  awards: { title: 'Awards', deferredCopy: 'No awards are shown until a real awards read model exists.' },
  'hall-of-fame': { title: 'Hall of Fame', deferredCopy: 'No Hall of Fame entries are shown until a real Hall of Fame read model exists.' },
  'era-rankings': { title: 'Era Rankings', deferredCopy: 'No era rankings are shown until a real era comparison read model exists.' }
}

export function ViewerStatsDeferredPage({ kind }: { kind: ViewerStatsDeferredKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerStatsDeferredConfigs[kind]
  const statusQuery = useQuery({ queryKey: ['viewer-stats-deferred-status', kind, activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-stats-deferred-events', kind, activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-stats-deferred-ranking-snapshots', kind, activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-stats-deferred-race-snapshots', kind, activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-stats-deferred-finals', kind, activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description="Read-only stats and records destination requiring an active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data
  })
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(metadata)
  const isLoadingMetadata = statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading || finalsQuery.isLoading
  const hasMetadataError = statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError || finalsQuery.isError

  return (
    <ViewerShellPage title={config.title} description="Conservative read-only stats and records page using existing active-run metadata only.">
      <article className="viewer-active-run-card" aria-label={`${config.title} active run metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">No records or statistics are calculated here yet. This page only shows safe source availability from the active Viewer run.</p>
        {isLoadingMetadata ? <p className="status">Loading active run metadata…</p> : null}
        {hasMetadataError ? <ViewerEmptyState>Some active run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList(commonDeferredSourceMetadataItems({
            activeRunId,
            metadata,
            eventsLoading: eventsQuery.isLoading,
            rankingSnapshotsLoading: rankingSnapshotsQuery.isLoading,
            raceSnapshotsLoading: raceSnapshotsQuery.isLoading,
            finalsLoading: finalsQuery.isLoading
          }))}
          {!isLoadingMetadata && !hasMetadataError && !hasAnySourceMetadata ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        </section>
        <section aria-label={`${config.title} deferred output explanation`}>
          <h3>Deferred output</h3>
          <p className="status">{config.deferredCopy}</p>
        </section>
        <section aria-label={`${config.title} links`}>
          <h3>Source links</h3>
          {renderDeferredSourceLinks([
            { label: 'Open records', to: viewerTopRecordsPath() },
            { label: 'Open stats', to: viewerTopStatsPath() },
            { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) },
            { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
            { label: 'Open active run race', to: viewerRacePath(activeRunId) },
            { label: 'Open run browser', to: viewerRunsPath() }
          ])}
        </section>
      </article>
    </ViewerShellPage>
  )
}


type ViewerTourDeferredKind = 'matches' | 'categories' | 'champions'

type ViewerTourDeferredConfig = {
  title: string
  deferredCopy: string
}

const viewerTourDeferredConfigs: Record<ViewerTourDeferredKind, ViewerTourDeferredConfig> = {
  matches: { title: 'Match Center', deferredCopy: 'No match list is shown until a real match read model exists.' },
  categories: { title: 'Tournament Categories', deferredCopy: 'No connected category breakdown is shown until a real category read model exists.' },
  champions: { title: 'Past Champions', deferredCopy: 'No champions index is shown until a real champions read model exists.' }
}

export function ViewerTourDeferredPage({ kind }: { kind: ViewerTourDeferredKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerTourDeferredConfigs[kind]
  const runQuery = useQuery({ queryKey: ['viewer-tour-deferred-run', kind, activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const statusQuery = useQuery({ queryKey: ['viewer-tour-deferred-status', kind, activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-tour-deferred-events', kind, activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-tour-deferred-ranking-snapshots', kind, activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-tour-deferred-race-snapshots', kind, activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-tour-deferred-finals', kind, activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description="Read-only Tour destination requiring an active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data,
    eventCount: eventsQuery.data?.events.length ?? statusQuery.data?.progress.completed_event_count ?? statusQuery.data?.history_counts.events ?? null
  })
  const orderedEventCount = runQuery.data?.season_state.ordered_events.length ?? runQuery.data?.run.total_events ?? statusQuery.data?.progress.total_events ?? null
  const season = runQuery.data?.season_state.season ?? runQuery.data?.run.season ?? statusQuery.data?.season ?? finalsQuery.data?.season ?? null
  const nextScheduledEvent = selectNextOrderedEvent(runQuery.data)
  const isLoadingMetadata = runQuery.isLoading || statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading || finalsQuery.isLoading
  const hasMetadataError = runQuery.isError || statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError || finalsQuery.isError
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(metadata, orderedEventCount)

  return (
    <ViewerShellPage title={config.title} description="Conservative read-only Tour page using existing active-run metadata only.">
      <article className="viewer-active-run-card" aria-label={`${config.title} active run metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">No real read model exists yet. This page only shows safe source availability from the active Viewer run.</p>
        {isLoadingMetadata ? <p className="status">Loading active run metadata…</p> : null}
        {hasMetadataError ? <ViewerEmptyState>Some active run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList([
            { label: 'Active run ID', value: activeRunId },
            { label: 'Season', value: renderLoadingValue(runQuery.isLoading, season) },
            { label: 'Completed/persisted event count', value: renderLoadingValue(eventsQuery.isLoading, metadata.eventCount) },
            { label: 'Ordered calendar event count', value: renderLoadingValue(runQuery.isLoading, orderedEventCount) },
            { label: 'Ranking snapshot count', value: renderLoadingValue(rankingSnapshotsQuery.isLoading, metadata.rankingSnapshotCount) },
            { label: 'Race snapshot count', value: renderLoadingValue(raceSnapshotsQuery.isLoading, metadata.raceSnapshotCount) },
            { label: 'Finals availability', value: renderFinalsSourceValue(activeRunId, metadata.finalsAvailability, finalsQuery.isLoading) },
            { label: 'Next scheduled event', value: nextScheduledEvent ? <Link to={viewerPlannedEventPath(activeRunId, nextScheduledEvent.event_id)}>{nextScheduledEvent.event_id}</Link> : '—' },
            { label: 'Latest persisted event', value: renderLatestPersistedEventSourceValue(activeRunId, metadata.latestPersistedEvent) },
            { label: 'Latest ranking snapshot', value: renderLatestRankingSnapshotSourceValue(activeRunId, metadata.latestRankingSnapshot) },
            { label: 'Latest race snapshot', value: renderLatestRaceSnapshotSourceValue(activeRunId, metadata.latestRaceSnapshot) }
          ])}
          {!isLoadingMetadata && !hasMetadataError && !hasAnySourceMetadata ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        </section>
        <section aria-label={`${config.title} deferred output explanation`}>
          <h3>Deferred output</h3>
          <p className="status">{config.deferredCopy}</p>
        </section>
        <section aria-label={`${config.title} source links`}>
          <h3>Source links</h3>
          <ViewerActiveRunLinks
            links={[
              { label: 'Open active run calendar', to: viewerSeasonCalendarPath(activeRunId) },
              { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) },
              { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
              { label: 'Open active run race', to: viewerRacePath(activeRunId) },
              { label: 'Open run browser', to: viewerRunsPath() }
            ]}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerTourCalendarPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const runQuery = useQuery({ queryKey: ['viewer-tour-calendar-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const orderedEventCount = runQuery.data?.season_state.ordered_events.length ?? runQuery.data?.run.total_events ?? null

  return (
    <ViewerShellPage title="Season Calendar" description="Read-only season timeline and schedule destination for weekly tour browsing.">
      <div className="viewer-jump-demo" aria-label="Jump to Week demo">
        <p className="status">This section uses existing read-only run data only.</p>
        <ViewerJumpToWeekButton week={24} />
      </div>
      {activeRunId ? (
        <article className="viewer-active-run-card">
          <span className="eyebrow">Active Viewer run</span>
          <h3>Open active run schedule</h3>
          <p className="status">Use the real read-only calendar for Viewer run {activeRunId}.</p>
          <dl className="metadata-list">
            <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
            <div><dt>Ordered event count</dt><dd>{runQuery.isLoading ? 'Loading…' : orderedEventCount ?? '—'}</dd></div>
          </dl>
          {runQuery.isError ? <ViewerEmptyState>Active run calendar metadata is temporarily unavailable.</ViewerEmptyState> : null}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>
            Open active run schedule
          </Link>
        </article>
      ) : (
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      )}
    </ViewerShellPage>
  )
}

export function ViewerCountryRankingPage(): JSX.Element {
  return <ViewerCountriesDeferredPage kind="ranking" />
}

type ViewerComparisonRouteKind = 'h2h' | 'compare'

const comparisonStatFields = [
  { key: 'overall', label: 'Power Rating difference' },
  { key: 'technique', label: 'Technique difference' },
  { key: 'movement', label: 'Movement difference' },
  { key: 'physical', label: 'Physical difference' },
  { key: 'mental', label: 'Mental difference' },
  { key: 'age', label: 'Age difference' }
] as const

function playerNumericField(player: RunPlayerListItem, field: typeof comparisonStatFields[number]['key']): number | null {
  const value = player[field]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function formatComparisonDifference(playerA: RunPlayerListItem, playerB: RunPlayerListItem, field: typeof comparisonStatFields[number]['key']): string {
  const valueA = playerNumericField(playerA, field)
  const valueB = playerNumericField(playerB, field)
  if (valueA === null || valueB === null) return '—'
  const difference = valueA - valueB
  return difference > 0 ? `+${difference}` : String(difference)
}

type ViewerComparisonQueryParams = {
  playerAParam: string
  playerBParam: string
  hasPlayerParams: boolean
}

type ViewerSelectedComparisonPlayers = ViewerComparisonQueryParams & {
  playerA: RunPlayerListItem | null
  playerB: RunPlayerListItem | null
  hasMissingRequestedPlayer: boolean
}

function readViewerComparisonQueryParams(searchParams: URLSearchParams): ViewerComparisonQueryParams {
  const playerAParam = searchParams.get('playerA') || searchParams.get('player_a') || searchParams.get('a') || ''
  const playerBParam = searchParams.get('playerB') || searchParams.get('player_b') || searchParams.get('b') || ''
  return {
    playerAParam,
    playerBParam,
    hasPlayerParams: Boolean(playerAParam || playerBParam)
  }
}

function selectViewerComparisonPlayers(players: RunPlayerListItem[], searchParams: URLSearchParams): ViewerSelectedComparisonPlayers {
  const params = readViewerComparisonQueryParams(searchParams)
  const playerA = params.playerAParam ? players.find((player) => player.player_id === params.playerAParam) ?? null : null
  const playerB = params.playerBParam ? players.find((player) => player.player_id === params.playerBParam) ?? null : null
  return {
    ...params,
    playerA,
    playerB,
    hasMissingRequestedPlayer: params.hasPlayerParams && (!params.playerAParam || !params.playerBParam || !playerA || !playerB)
  }
}

function selectedComparisonPlayers(selection: Pick<ViewerSelectedComparisonPlayers, 'playerA' | 'playerB'>): RunPlayerListItem[] {
  return [selection.playerA, selection.playerB].filter((player): player is RunPlayerListItem => Boolean(player))
}

function buildPlayerSearchLink(player: RunPlayerListItem): string {
  return `${viewerTopSearchPath()}?q=${encodeURIComponent(player.player_id || player.name || '')}`
}

function buildSelectedPlayerSearchLinks(players: RunPlayerListItem[]): { label: string; to: string }[] {
  return players
    .filter((player) => player.player_id || player.name)
    .map((player) => ({ label: `Search ${player.name || player.player_id}`, to: buildPlayerSearchLink(player) }))
}

function buildSelectedH2HPath(selection: Pick<ViewerSelectedComparisonPlayers, 'playerA' | 'playerB'>): string {
  return selection.playerA && selection.playerB ? `${viewerTopH2HPath()}?playerA=${encodeURIComponent(selection.playerA.player_id)}&playerB=${encodeURIComponent(selection.playerB.player_id)}` : viewerTopH2HPath()
}

function ViewerPlayerComparisonLinks({ activeRunId, players }: { activeRunId: string; players: RunPlayerListItem[] }): JSX.Element {
  return (
    <ViewerSectionCard title="Links" kicker="Read-only navigation">
      <ViewerActiveRunLinks
        links={[
          { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
          { label: 'Open Viewer search', to: viewerTopSearchPath() },
          ...buildSelectedPlayerSearchLinks(players)
        ]}
      />
    </ViewerSectionCard>
  )
}

function ViewerComparisonPlayerCard({ activeRunId, title, player }: { activeRunId: string; title: string; player: RunPlayerListItem | null }): JSX.Element {
  return (
    <ViewerSectionCard title={title} kicker="Selected player">
      {player ? (
        <ViewerMetadataList
          ariaLabel={`${title} comparison fields`}
          items={[
            { label: 'Player', value: renderLinkedPlayer(activeRunId, player.player_id, player.name || player.player_id || '—') },
            { label: 'Player ID', value: renderLinkedPlayer(activeRunId, player.player_id, player.player_id || '—') },
            { label: 'Country', value: renderLinkedCountry(activeRunId, player.country_code) },
            { label: 'Age', value: player.age ?? '—' },
            { label: 'Power Rating', value: player.overall ?? '—' },
            { label: 'Technique', value: player.technique ?? '—' },
            { label: 'Movement', value: player.movement ?? '—' },
            { label: 'Physical', value: player.physical ?? '—' },
            { label: 'Mental', value: player.mental ?? '—' },
            { label: 'Quality band', value: player.quality_band ?? '—' }
          ]}
        />
      ) : (
        <ViewerEmptyState>Player data is not available for this run yet.</ViewerEmptyState>
      )}
    </ViewerSectionCard>
  )
}

function ViewerComparisonSummary({ playerA, playerB, title = 'Comparison Summary' }: { playerA: RunPlayerListItem | null; playerB: RunPlayerListItem | null; title?: string }): JSX.Element {
  return (
    <ViewerSectionCard title={title} kicker="Numeric field differences">
      {playerA && playerB ? (
        <ViewerMetadataList
          ariaLabel={`${title} differences`}
          items={comparisonStatFields.map((field) => ({
            label: field.label,
            value: formatComparisonDifference(playerA, playerB, field.key)
          }))}
        />
      ) : (
        <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
      )}
    </ViewerSectionCard>
  )
}

function ViewerPlayerComparisonContent({ routeKind }: { routeKind: ViewerComparisonRouteKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const [searchParams] = useSearchParams()
  const playersQuery = useQuery({
    queryKey: ['viewer-player-comparison-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Player Comparison" description="Read-only player comparison using the active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players ?? []
  const selectedPlayers = selectViewerComparisonPlayers(players, searchParams)
  const { playerA, playerB, hasPlayerParams, hasMissingRequestedPlayer } = selectedPlayers

  return (
    <ViewerShellPage
      title="Player Comparison"
      description={routeKind === 'h2h' ? 'Read-only H2H comparison using existing active-run player fields only.' : 'Read-only player comparison using existing active-run player fields only.'}
    >
      <ViewerLandingGrid>
        <ViewerSectionCard title="Player Comparison" kicker="Active Viewer run" variant="hero">
          {playersQuery.isLoading ? <p className="status">Loading active run player metadata…</p> : null}
          {playersQuery.isError ? <ViewerEmptyState>Player metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
          <ViewerMetadataList
            items={[
              { label: 'Active run ID', value: activeRunId },
              { label: 'Total player count', value: playersQuery.isLoading ? 'Loading…' : playersQuery.data?.total ?? '—' },
              { label: 'Returned player count', value: playersQuery.isLoading ? 'Loading…' : players.length }
            ]}
          />
          {!playersQuery.isLoading && !playersQuery.isError && players.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
          {!playersQuery.isLoading && !playersQuery.isError && hasMissingRequestedPlayer ? <ViewerEmptyState>Player data is not available for this run yet.</ViewerEmptyState> : null}
          {!playersQuery.isLoading && !playersQuery.isError && !hasPlayerParams ? (
            <>
              <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
              <ViewerSamplePlayersList players={players} label="Sample active run players for comparison links" runId={activeRunId} />
            </>
          ) : null}
        </ViewerSectionCard>
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player A" player={playerA} />
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player B" player={playerB} />
        <ViewerComparisonSummary playerA={playerA} playerB={playerB} />
        <ViewerPlayerComparisonLinks activeRunId={activeRunId} players={selectedComparisonPlayers(selectedPlayers)} />
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}

export function ViewerPlayerComparisonPage(): JSX.Element {
  return <ViewerPlayerComparisonContent routeKind="compare" />
}

type ViewerH2HSubrouteKind = 'rivalries' | 'most-played' | 'finals-rivalries'

function ViewerActiveRunSportsLinks({ activeRunId }: { activeRunId: string }): JSX.Element {
  return (
    <ViewerActiveRunLinks
      links={[
        { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
        { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) }
      ]}
    />
  )
}

function ViewerSamplePlayersList({ players, label, runId }: { players: RunPlayerListItem[]; label: string; runId?: string }): JSX.Element | null {
  return (
    <ViewerSampleList
      title="Sample players"
      label={label}
      items={players}
      getKey={(player) => player.player_id || player.name || 'unknown-player'}
      renderItem={(player) => renderPlayerSampleMetadata(player, runId)}
    />
  )
}

export function ViewerH2HPage(): JSX.Element {
  return <ViewerPlayerComparisonContent routeKind="h2h" />
}

export function ViewerH2HSubroutePage({ kind }: { kind: ViewerH2HSubrouteKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const content = {
    rivalries: {
      title: 'Rivalries',
      note: 'No rivalry list is shown until direct match records are available.'
    },
    'most-played': {
      title: 'Most Played Matchups',
      note: 'No matchup list is shown until completed match counts are available.'
    },
    'finals-rivalries': {
      title: 'Finals Rivalries',
      note: 'No finals rivalry list is shown until final-round match records are available.'
    }
  }[kind]
  const queryEnabled = Boolean(activeRunId)
  const statusQuery = useQuery({ queryKey: ['viewer-h2h-subroute-status', kind, activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const playersQuery = useQuery({ queryKey: ['viewer-h2h-subroute-players', kind, activeRunId], queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }), enabled: queryEnabled, retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-h2h-subroute-events', kind, activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-h2h-subroute-ranking-snapshots', kind, activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-h2h-subroute-race-snapshots', kind, activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-h2h-subroute-finals', kind, activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: queryEnabled, retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={content.title} description="Read-only H2H Explorer that defers analytics until authoritative match history exists.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const samplePlayers = playersQuery.data?.players ?? []
  const playerTotal = playersQuery.data?.total
  const completedEventCount = eventsQuery.data?.events.length ?? statusQuery.data?.history_counts.events ?? statusQuery.data?.progress.completed_event_count
  const rankingSnapshotCount = rankingSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.ranking_snapshots
  const raceSnapshotCount = raceSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.race_snapshots
  const finalsAvailability = finalsQuery.data ? formatFinalsAvailability(finalsQuery.data) : statusQuery.data?.finals.result_available ? 'Finals result available' : statusQuery.data?.finals.qualification_available ? 'Finals qualification available' : 'Finals summary not available yet'
  const hasFinalsAvailability = finalsAvailability !== 'Finals summary not available yet' && finalsAvailability !== 'Loading or unavailable'

  return (
    <ViewerShellPage title={content.title} description="Read-only H2H Explorer that defers analytics until authoritative match history exists.">
      <ViewerLandingGrid>
        <ViewerActiveRunCard ariaLabel={`${content.title} source metadata`} kicker="Active Viewer run" title={`${content.title} source metadata`}>
          {statusQuery.isLoading || playersQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading || finalsQuery.isLoading ? <p className="status">Loading active-run metadata…</p> : null}
          <ViewerMetadataList
            ariaLabel={`${content.title} source metadata values`}
            items={[
              { label: 'Active run ID', value: activeRunId },
              { label: 'Total player count', value: playersQuery.isLoading ? 'Loading…' : playerTotal ?? '—' },
              { label: 'Returned/sample player count', value: playersQuery.isLoading ? 'Loading…' : samplePlayers.length },
              { label: 'Completed/persisted event count', value: eventsQuery.isLoading ? 'Loading…' : completedEventCount ?? '—' },
              { label: 'Ranking snapshot count', value: rankingSnapshotsQuery.isLoading ? 'Loading…' : rankingSnapshotCount ?? '—' },
              { label: 'Race snapshot count', value: raceSnapshotsQuery.isLoading ? 'Loading…' : raceSnapshotCount ?? '—' },
              { label: 'Finals availability', value: finalsQuery.isLoading ? 'Loading…' : hasFinalsAvailability ? <Link to={viewerFinalsPath(activeRunId)}>{finalsAvailability}</Link> : finalsAvailability }
            ]}
          />
          {!playersQuery.isLoading && !playersQuery.isError && samplePlayers.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
          <ViewerSamplePlayersList players={samplePlayers} label={`${content.title} sample players`} runId={activeRunId} />
        </ViewerActiveRunCard>
        <ViewerSectionCard title="Deferred H2H outputs" kicker="No authoritative match read model">
          <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
          <p className="status">{content.note}</p>
        </ViewerSectionCard>
        <ViewerSectionCard title="Source links" kicker="Read-only navigation">
          <ViewerActiveRunLinks
            links={[
              { label: 'Open H2H comparison', to: viewerTopH2HPath() },
              { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
              { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) },
              { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
              { label: 'Open active run race', to: viewerRacePath(activeRunId) },
              { label: 'Open run browser', to: viewerRunsPath() }
            ]}
          />
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}

export function ViewerMatchPredictorPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const [searchParams] = useSearchParams()
  const playersQuery = useQuery({
    queryKey: ['viewer-match-predictor-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Match Predictor" description="Read-only Match Predictor destination used by H2H and Predictions navigation.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players ?? []
  const selectedPlayers = selectViewerComparisonPlayers(players, searchParams)
  const { playerA, playerB, hasPlayerParams, hasMissingRequestedPlayer } = selectedPlayers
  const h2hPath = buildSelectedH2HPath(selectedPlayers)

  return (
    <ViewerShellPage title="Match Predictor" description="Read-only Match Predictor using existing active-run player data only.">
      <ViewerLandingGrid>
        <ViewerSectionCard title="Match Predictor" kicker="Active Viewer run" variant="hero">
          {playersQuery.isLoading ? <p className="status">Loading active run player metadata…</p> : null}
          {playersQuery.isError ? <ViewerEmptyState>Player metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
          <ViewerMetadataList
            ariaLabel="Match Predictor active run summary"
            items={[
              { label: 'Active run ID', value: activeRunId },
              { label: 'Total player count', value: playersQuery.isLoading ? 'Loading…' : playersQuery.data?.total ?? '—' },
              { label: 'Returned player count', value: playersQuery.isLoading ? 'Loading…' : players.length }
            ]}
          />
          {!playersQuery.isLoading && !playersQuery.isError && players.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        </ViewerSectionCard>
        <ViewerSectionCard title="Predictor Inputs" kicker="Read-only player fields">
          {!playersQuery.isLoading && !playersQuery.isError && hasMissingRequestedPlayer ? <ViewerEmptyState>Player data is not available for this run yet.</ViewerEmptyState> : null}
          {!playersQuery.isLoading && !playersQuery.isError && !hasPlayerParams ? (
            <>
              <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
              <ViewerSamplePlayersList players={players} label="Sample active run players for future predictor inputs" runId={activeRunId} />
            </>
          ) : null}
          {!playersQuery.isLoading && !playersQuery.isError && playerA && playerB ? <p className="status">Matched players are shown from active-run player data only.</p> : null}
        </ViewerSectionCard>
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player A" player={playerA} />
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player B" player={playerB} />
        <ViewerComparisonSummary playerA={playerA} playerB={playerB} title="Input Comparison" />
        <ViewerSectionCard title="Links" kicker="Read-only navigation">
          <ViewerActiveRunLinks
            links={[
              { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
              { label: 'Open Viewer search', to: viewerTopSearchPath() },
              { label: 'Open H2H comparison', to: h2hPath }
            ]}
          />
        </ViewerSectionCard>
        <ViewerSectionCard title="Deferred Predictor Outputs" kicker="No prediction read model">
          <ul className="viewer-home-list" aria-label="Deferred Predictor Outputs">
            <li>This preview is not connected for this data shape yet.</li>
            <li>No prediction is shown until a real prediction read model exists.</li>
            <li>No odds are shown until a real odds read model exists.</li>
          </ul>
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}

type ViewerSearchPlannedEvent = SeasonStateResponse['season_state']['ordered_events'][number]

type ViewerSearchTournamentResult = {
  eventId: string
  season: number | null
  week: number | null
  tour: string | null
  category: string | null
  templateId: string | null
  hasPlannedEvent: boolean
  hasPersistedEvent: boolean
}

function normalizeViewerSearchQuery(searchParams: URLSearchParams): string {
  return (searchParams.get('q') ?? searchParams.get('query') ?? searchParams.get('search') ?? '').trim()
}

function searchTextMatches(query: string, values: Array<string | number | null | undefined>): boolean {
  const normalizedQuery = query.toLowerCase()
  return values.some((value) => String(value ?? '').toLowerCase().includes(normalizedQuery))
}

function buildSearchTournamentResults(plannedEvents: ViewerSearchPlannedEvent[], persistedEvents: EventRecord[], query: string): ViewerSearchTournamentResult[] {
  const plannedById = new Map(plannedEvents.map((event) => [event.event_id, event]))
  const persistedById = new Map(persistedEvents.map((event) => [event.event_id, event]))
  const eventIds = Array.from(new Set([...plannedById.keys(), ...persistedById.keys()]))

  return eventIds
    .map((eventId) => {
      const planned = plannedById.get(eventId)
      const persisted = persistedById.get(eventId)
      return {
        eventId,
        season: planned?.season ?? persisted?.season ?? null,
        week: planned?.week ?? persisted?.week ?? null,
        tour: planned?.tour ?? null,
        category: planned?.category ?? null,
        templateId: planned?.template_id ?? persisted?.template_id ?? null,
        hasPlannedEvent: Boolean(planned),
        hasPersistedEvent: Boolean(persisted)
      }
    })
    .filter((event) => searchTextMatches(query, [event.eventId, event.tour, event.category, event.templateId, event.week]))
}

function renderSearchTournamentMetadata(runId: string, event: ViewerSearchTournamentResult): JSX.Element {
  return (
    <ViewerMetadataList
      items={[
        { label: 'Event ID', value: event.hasPlannedEvent ? <Link to={viewerPlannedEventPath(runId, event.eventId)}>Planned Event: {event.eventId}</Link> : event.eventId },
        { label: 'Season', value: event.season ?? '—' },
        { label: 'Week', value: event.week ? <Link to={viewerWeekDetailPath(runId, event.week)}>Week Detail: W{event.week}</Link> : '—' },
        { label: 'Tour', value: event.tour ?? '—' },
        { label: 'Category', value: event.category ?? '—' },
        { label: 'Template', value: event.templateId ?? '—' },
        { label: 'Persisted availability', value: event.hasPersistedEvent ? 'Available' : 'Not available' },
        { label: 'Tournament detail', value: event.hasPersistedEvent ? <Link to={viewerTournamentDetailPath(runId, event.eventId)}>Tournament Detail: {event.eventId}</Link> : '—' }
      ]}
    />
  )
}


type ViewerPredictionDeferredKind = 'match-odds' | 'tournament-odds' | 'finals-qualification' | 'season-end-no1' | 'upset-watch' | 'futures'

type ViewerPredictionDeferredConfig = {
  title: string
  deferredCopy: string
}

const viewerPredictionDeferredConfigs: Record<ViewerPredictionDeferredKind, ViewerPredictionDeferredConfig> = {
  'match-odds': {
    title: 'Match Odds',
    deferredCopy: 'No odds are shown until a real odds read model exists.'
  },
  'tournament-odds': {
    title: 'Tournament Odds',
    deferredCopy: 'No tournament odds are shown until a real tournament odds read model exists.'
  },
  'finals-qualification': {
    title: 'Finals Qualification',
    deferredCopy: 'No finals qualification probability is shown until a real qualification probability read model exists.'
  },
  'season-end-no1': {
    title: 'Season-End No.1',
    deferredCopy: 'No season-end No.1 probability is shown until a real season projection read model exists.'
  },
  'upset-watch': {
    title: 'Upset Watch',
    deferredCopy: 'No upset chance is shown until a real upset model exists.'
  },
  futures: {
    title: 'Futures',
    deferredCopy: 'No futures markets are shown until a real futures read model exists.'
  }
}

export function ViewerPredictionDeferredPage({ kind }: { kind: ViewerPredictionDeferredKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerPredictionDeferredConfigs[kind]
  const statusQuery = useQuery({ queryKey: ['viewer-prediction-deferred-status', kind, activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-prediction-deferred-events', kind, activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-prediction-deferred-ranking-snapshots', kind, activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-prediction-deferred-race-snapshots', kind, activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-prediction-deferred-finals', kind, activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description="Read-only predictions destination requiring an active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data
  })
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(metadata)
  const isLoadingMetadata = statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading || finalsQuery.isLoading
  const hasMetadataError = statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError || finalsQuery.isError

  return (
    <ViewerShellPage title={config.title} description="Conservative read-only predictions page using existing active-run metadata only.">
      <article className="viewer-active-run-card" aria-label={`${config.title} active run metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">Outputs remain deferred. This page only shows safe source availability from the active Viewer run.</p>
        {isLoadingMetadata ? <p className="status">Loading active run metadata…</p> : null}
        {hasMetadataError ? <ViewerEmptyState>Some active run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList(commonDeferredSourceMetadataItems({
            activeRunId,
            metadata,
            eventsLoading: eventsQuery.isLoading,
            rankingSnapshotsLoading: rankingSnapshotsQuery.isLoading,
            raceSnapshotsLoading: raceSnapshotsQuery.isLoading,
            finalsLoading: finalsQuery.isLoading
          }))}
          {!isLoadingMetadata && !hasMetadataError && !hasAnySourceMetadata ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        </section>
        <section aria-label={`${config.title} deferred output explanation`}>
          <h3>Deferred output</h3>
          <p className="status">{config.deferredCopy}</p>
        </section>
        <section aria-label={`${config.title} links`}>
          <h3>Source links</h3>
          <ViewerActiveRunLinks
            links={[
              { label: 'Open match predictor', to: viewerTopMatchPredictorPath() },
              { label: 'Open active run tournaments', to: viewerTournamentsPath(activeRunId) },
              { label: 'Open active run rankings', to: viewerRankingsPath(activeRunId) },
              { label: 'Open active run race', to: viewerRacePath(activeRunId) },
              { label: 'Open run browser', to: viewerRunsPath() }
            ]}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerSearchPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const [searchParams] = useSearchParams()
  const urlQuery = normalizeViewerSearchQuery(searchParams)
  const [query, setQuery] = useState(urlQuery)
  const hasSearchQuery = urlQuery.length > 0

  useEffect(() => {
    setQuery(urlQuery)
  }, [urlQuery])

  const playersQuery = useQuery({
    queryKey: ['viewer-search-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId && hasSearchQuery),
    retry: false
  })
  const nationsQuery = useQuery({
    queryKey: ['viewer-search-run-nations', activeRunId],
    queryFn: () => listRunNations(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId && hasSearchQuery),
    retry: false
  })
  const runQuery = useQuery({
    queryKey: ['viewer-search-run-calendar', activeRunId],
    queryFn: () => getRun(activeRunId ?? ''),
    enabled: Boolean(activeRunId && hasSearchQuery),
    retry: false
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-search-run-events', activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: Boolean(activeRunId && hasSearchQuery),
    retry: false
  })

  if (!activeRunId || !hasSearchQuery) {
    return (
      <ViewerShellPage title="Search" description="Read-only Viewer Search using active-run data only.">
        <article className="viewer-active-run-card" aria-label="Search">
          <span className="eyebrow">Viewer search</span>
          <h3>Search{urlQuery ? `: ${urlQuery}` : ''}</h3>
          <label className="field-label" htmlFor="viewer-search-shell-input">Search</label>
          <input
            id="viewer-search-shell-input"
            aria-label="Read-only Viewer search shell"
            placeholder="Search players, countries, tournaments…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
        </article>
      </ViewerShellPage>
    )
  }

  const players = (playersQuery.data?.players ?? []).filter((player) => searchTextMatches(urlQuery, [player.player_id, player.name, player.country_code, player.quality_band]))
  const nations = (nationsQuery.data?.nations ?? []).filter((nation) => searchTextMatches(urlQuery, [nation.country_code, nation.country_name, nation.top_player_name, nation.top_player_id]))
  const tournaments = buildSearchTournamentResults(runQuery.data?.season_state.ordered_events ?? [], eventsQuery.data?.events ?? [], urlQuery)
  const isLoading = playersQuery.isLoading || nationsQuery.isLoading || runQuery.isLoading || eventsQuery.isLoading
  const hasError = playersQuery.isError || nationsQuery.isError || runQuery.isError || eventsQuery.isError
  const hasResults = players.length > 0 || nations.length > 0 || tournaments.length > 0

  return (
    <ViewerShellPage title="Search" description="Read-only Viewer Search using active-run player, country, and tournament data only.">
      <article className="viewer-active-run-card" aria-label="Search">
        <span className="eyebrow">Active Viewer run</span>
        <h3>Search: {urlQuery}</h3>
        {isLoading ? <p className="status">Loading active run search results…</p> : null}
        {hasError ? <ViewerEmptyState>Some active run searchable metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Query</dt><dd>{urlQuery}</dd></div>
        </dl>
        <label className="field-label" htmlFor="viewer-search-shell-input">Search</label>
        <input
          id="viewer-search-shell-input"
          aria-label="Read-only Viewer search shell"
          placeholder="Search players, countries, tournaments…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {!isLoading && !hasError && !hasResults ? <ViewerEmptyState>No matching Viewer results found.</ViewerEmptyState> : null}

        <section aria-label="Players">
          <h4>Players</h4>
          {players.length ? (
            <ul className="viewer-home-list">
              {players.map((player) => (
                <li key={player.player_id}>{renderPlayerSampleMetadata(player, activeRunId)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching players.</p>}
        </section>

        <section aria-label="Countries">
          <h4>Countries</h4>
          {nations.length ? (
            <ul className="viewer-home-list">
              {nations.map((nation) => (
                <li key={nation.country_code}>{renderCountrySampleMetadata(nation, activeRunId)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching countries.</p>}
        </section>

        <section aria-label="Tournaments">
          <h4>Tournaments</h4>
          {tournaments.length ? (
            <ul className="viewer-home-list">
              {tournaments.map((event) => (
                <li key={event.eventId}>{renderSearchTournamentMetadata(activeRunId, event)}</li>
              ))}
            </ul>
          ) : <p className="status">No matching tournaments.</p>}
        </section>

        <section aria-label="Links">
          <h4>Links</h4>
          <ViewerActiveRunLinks links={[{ label: 'Open run browser', to: viewerRunsPath() }]} />
          <p className="status">Result links are shown only when player, country, event, or week IDs are available.</p>
        </section>
      </article>
    </ViewerShellPage>
  )
}

export function ViewerFinalsReadOnlyPage(): JSX.Element {
  return <ViewerShellPage title="World Tour Finals" description="Read-only World Tour Finals destination for qualification and results." />
}

export function ViewerPlannedEventReadOnlyPage(): JSX.Element {
  return <ViewerShellPage title="Planned Event" description="Read-only schedule event destination. Event context can be surfaced here without commissioner controls." />
}

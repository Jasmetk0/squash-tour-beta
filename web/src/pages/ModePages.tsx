import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AdminPlayersPage as InitialPoolAdminPlayersPage } from './AdminPlayersPage'
import { AdminPlayersHubPage } from './AdminPlayersHubPage'
import { AdminSeasonsPage as SeasonBootstrapAdminSeasonsPage } from './AdminSeasonsPage'
import { TournamentTemplatesPage } from './TournamentTemplatesPage'
export { ViewerRunBrowserPage } from './viewer/ViewerRunBrowserPage'
export { ViewerHomePage } from './viewer/ViewerHomePage'
export { ViewerRankingsPage, ViewerRacePage } from './viewer/rankings'
export { ViewerSeasonHubPage, ViewerTourCalendarPage, ViewerCurrentWeekPage, ViewerTournamentsPage } from './viewer/tour'
export { ViewerPlayersPage, ViewerCountriesPage } from './viewer/people'
export { ViewerSearchPage, ViewerH2HPage, ViewerPlayerComparePage, ViewerPlayerComparisonPage, ViewerMatchPredictorPage } from './viewer/explore'
export { ViewerHistoryPage, ViewerFinalsReadOnlyPage } from './viewer/history'
import { getCountriesMetadata, getFinalsSummary, getRun, getRunStatusSummary, getTournamentTemplatesMetadata, listEvents, listRaceSnapshots, listRankingSnapshots, listRunNations, listRunPlayers, listRuns } from '../api/client'

import { LinkCardGrid } from '../components/LinkCardGrid'
import { ViewerActiveRunCard, ViewerActiveRunLinks, ViewerDeferredFeatureList, ViewerEmptyState, ViewerLandingGrid, ViewerMetadataList, ViewerSampleList, ViewerSectionCard, ViewerStatusMessage } from '../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../viewer/useActiveViewerRunId'
import { latestSnapshot } from './viewer/rankings/viewerSnapshotDisplay'
import { formatFinalsAvailability, selectLatestPersistedEvent, selectNextOrderedEvent } from './viewer/tour/viewerTourDisplay'
import { renderCountrySampleMetadata, renderPlayerSampleMetadata } from './viewer/people'
import { ViewerSamplePlayersList } from './viewer/explore/viewerComparisonRender'
import {
  viewerCountriesPath,
  viewerHomePath,
  viewerFinalsPath,
  viewerPlannedEventPath,
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
  viewerTournamentsPath,
  viewerTournamentDetailPath
} from '../viewer/viewerRoutes'
import type { EventRecord, FinalsSummaryResponse, RankingSnapshot, RaceSnapshot, RunPlayerListItem, RunStatusSummary, RunsIndexResponse } from '../api/types'

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



export function ViewerCountryRankingPage(): JSX.Element {
  return <ViewerCountriesDeferredPage kind="ranking" />
}

type ViewerH2HSubrouteKind = 'rivalries' | 'most-played' | 'finals-rivalries'

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

export function ViewerPlannedEventReadOnlyPage(): JSX.Element {
  return <ViewerShellPage title="Planned Event" description="Read-only schedule event destination. Event context can be surfaced here without commissioner controls." />
}

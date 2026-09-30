import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import { getRun, getViewerTournamentHistory, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
import type { EventRecord, RaceSnapshot, RankingSnapshot, SeasonStateResponse } from '../api/types'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  JsonPayloadBlock,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { tournamentResultPayloadMetadataItems } from '../viewer/TournamentResultMetadata'
import { findPersistedEventById, findPlannedEventById } from './viewer/tour/viewerEventDetailDisplay'
import {
  buildPlannedEventContextLinks,
  buildPlannedEventDetailMetadataItems,
  resolvePlannedEventStatusLabel
} from './viewer/tour/viewerPlannedEventDetailDisplay'
import {
  buildWeekContextLinks,
  buildWeekDetailMetadataItems,
  buildWeekEventLinks,
  buildWeekPersistedEventMetadataItems,
  buildWeekPlannedEventMetadataItems,
  completedPlannedEventsForWeek,
  parseViewerWeekParam,
  persistedEventsByExactId,
  persistedEventsForWeek,
  plannedEventsForWeek,
  snapshotsForWeekSourceEvents,
  sourceEventIdsForWeek
} from './viewer/tour/viewerWeekDetailDisplay'
import {
  viewerPlannedEventPath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'

function plannedStatus({
  index,
  nextEventIndex,
  completedEventIds,
  eventId
}: {
  index: number
  nextEventIndex: number
  completedEventIds: Set<string>
  eventId: string
}): string {
  if (completedEventIds.has(eventId)) return 'completed'
  if (index === nextEventIndex) return 'current/next'
  if (index > nextEventIndex) return 'upcoming'
  return 'planned'
}

function eventStatusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function eventIsCompleted(completedEventIds: Set<string>, eventId: string): string {
  return completedEventIds.has(eventId) ? 'Yes' : 'No'
}

function isScalar(value: unknown): value is string | number {
  return typeof value === 'string' || typeof value === 'number'
}

function safeText(value: unknown, fallback: string | number = '—'): string | number {
  return isScalar(value) ? value : fallback
}

function safeWeekLabel(value: unknown): string {
  return typeof value === 'number' && Number.isInteger(value) && value > 0 ? `W${value}` : '—'
}

function safeOrderedEvents(data: SeasonStateResponse | undefined): SeasonStateResponse['season_state']['ordered_events'] {
  const orderedEvents = data?.season_state?.ordered_events
  if (!Array.isArray(orderedEvents)) return []

  return orderedEvents.filter((event) =>
    event &&
    typeof event === 'object' &&
    typeof event.event_id === 'string' &&
    typeof event.week === 'number' &&
    Number.isInteger(event.week) &&
    event.week > 0
  )
}

function safeCompletedEventIds(data: SeasonStateResponse | undefined): string[] {
  const completedEventIds = data?.season_state?.completed_event_ids
  return Array.isArray(completedEventIds) ? completedEventIds.filter((eventId) => typeof eventId === 'string') : []
}

function safeEventRecords(events: EventRecord[] | undefined): EventRecord[] {
  if (!Array.isArray(events)) return []
  return events.filter((event) => event && typeof event === 'object' && typeof event.event_id === 'string')
}

function safeSnapshotRecords<T extends RankingSnapshot | RaceSnapshot>(snapshots: T[] | undefined): T[] {
  if (!Array.isArray(snapshots)) return []
  return snapshots.filter((snapshot) => snapshot && typeof snapshot === 'object' && typeof snapshot.snapshot_sequence === 'number')
}


export function ViewerRunCalendarPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()

  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const tournaments = historyQuery.data?.tournaments ?? []
  const seasons = Array.from(new Set(tournaments.map((event) => event.season)))
  const publishedCount = historyQuery.data?.published_result_count ?? 0

  return (
    <section className="panel">
      <RunScopedHeader
        title="Season Calendar"
        runId={runId}
        subtitle="Canonical read-only schedule from the selected Viewer Branch's saved Calendar Packages."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: historyQuery.data?.viewer_branch_id ?? '—' },
          { label: 'Saved seasons', value: seasons.length },
          { label: 'Tournament count', value: historyQuery.data?.tournament_count ?? 0 },
          { label: 'Published results', value: publishedCount }
        ]}
      />

      <SectionCard title="Saved Calendar overview">
        {historyQuery.isLoading ? <p className="status">Loading canonical season calendar…</p> : null}
        {historyQuery.error && !isApiNotFound(historyQuery.error) ? (
          <p className="error">Failed to load canonical season calendar: {formatApiError(historyQuery.error)}</p>
        ) : null}
        {isApiNotFound(historyQuery.error) ? (
          <EmptyState message="No saved Calendar Package is available for this Viewer Branch yet." />
        ) : null}
        {historyQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Saved seasons', value: seasons.length },
                { label: 'Tournament count', value: historyQuery.data.tournament_count },
                { label: 'Published results', value: publishedCount }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Active run id', value: runId || 'unknown' },
                { label: 'Viewer Branch', value: historyQuery.data.viewer_branch_id },
                { label: 'Calendar source', value: 'Saved Run Package Calendar authority' },
                { label: 'Seasons', value: seasons.length ? seasons.join(', ') : '—' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Canonical season timeline">
        {historyQuery.data && tournaments.length === 0 ? (
          <EmptyState message="No tournaments are present in the saved Calendar Packages." />
        ) : null}
        {tournaments.length > 0 ? (
          <ol className="item-list" aria-label="Viewer canonical season calendar events">
            {tournaments.map((event, index) => (
              <li key={event.event_id}>
                <strong>{event.event_name || event.event_id}</strong>
                <MetadataList
                  items={[
                    { label: 'Event ID', value: event.event_id },
                    { label: 'Season', value: event.season },
                    { label: 'Week', value: `W${event.season_week}` },
                    { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                    { label: 'Category', value: event.category || '—' },
                    { label: 'Template ID', value: event.template_id },
                    { label: 'Host', value: event.host_city ? `${event.host_city}, ${event.host_country}` : event.host_country },
                    { label: 'Calendar position', value: `${index + 1} of ${tournaments.length}` },
                    { label: 'Result publication', value: event.result_published ? 'Published' : 'Not published' },
                    { label: 'Champion', value: event.champion_player_id ?? '—' }
                  ]}
                />
                <p>
                  <Link to={viewerPlannedEventPath(runId, event.event_id)}>Open planned event</Link>
                  {' · '}
                  <Link to={viewerWeekDetailPath(runId, event.season_week)}>Open week detail</Link>
                  {' · '}
                  <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                </p>
              </li>
            ))}
          </ol>
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunPlannedEventPage(): JSX.Element {
  const { eventId = '' } = useParams()
  const { productRunId: runId } = useViewerProductRunRouteContext()

  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const event = historyQuery.data?.tournaments.find((item) => item.event_id === eventId)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Planned Event"
        runId={runId}
        subtitle="Canonical saved Calendar event detail for the selected Viewer Branch."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Season', value: event?.season ?? '—' },
          { label: 'Week', value: event ? `W${event.season_week}` : '—' }
        ]}
      />

      <SectionCard title="Source context links">
        {!runId || !eventId ? <EmptyState message="No planned event route context was provided." /> : null}
        {runId && event ? (
          <ul className="item-list" aria-label="Planned event source links">
            <li><Link to={viewerSeasonCalendarPath(runId)}>Season calendar</Link></li>
            <li><Link to={viewerWeekDetailPath(runId, event.season_week)}>{`Week W${event.season_week}`}</Link></li>
            <li><Link to={viewerTournamentDetailPath(runId, event.event_id)}>Tournament detail</Link></li>
          </ul>
        ) : null}
      </SectionCard>

      <SectionCard title="Planned event summary">
        {historyQuery.isLoading ? <p className="status">Loading canonical planned event…</p> : null}
        {historyQuery.error && !isApiNotFound(historyQuery.error) ? (
          <p className="error">Failed to load canonical planned event: {formatApiError(historyQuery.error)}</p>
        ) : null}
        {isApiNotFound(historyQuery.error) ? (
          <EmptyState message="No saved Calendar Package is available for this Viewer Branch yet." />
        ) : null}
        {!eventId ? <EmptyState message="No planned event ID was provided in the URL." /> : null}
        {eventId && historyQuery.data && !event ? (
          <EmptyState message="This event is not present in the saved Calendar Packages." />
        ) : null}
        {event ? (
          <>
            <SummaryPills
              items={[
                { label: 'Result publication', value: event.result_published ? 'Published' : 'Not published' },
                { label: 'Main draw', value: event.main_draw_size },
                { label: 'Qualification draw', value: event.qualification_draw_size },
                { label: 'Seeds', value: event.seeds_count },
                { label: 'Qualifier spots', value: event.qualifier_spots },
                { label: 'Wild Cards', value: event.wild_cards },
                { label: 'BYEs', value: event.byes }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Active run id', value: runId || 'unknown' },
                { label: 'Event ID', value: event.event_id },
                { label: 'Event name', value: event.event_name || event.event_id },
                { label: 'Season', value: event.season },
                { label: 'Week', value: `W${event.season_week}` },
                { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                { label: 'Category', value: event.category || '—' },
                { label: 'Template ID', value: event.template_id },
                { label: 'Host', value: event.host_city ? `${event.host_city}, ${event.host_country}` : event.host_country },
                { label: 'Region', value: event.region },
                { label: 'Ranking status', value: event.ranking_status },
                { label: 'Champion', value: event.champion_player_id ?? '—' },
                { label: 'Finalist', value: event.finalist_player_id ?? '—' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunWeekPage(): JSX.Element {
  const { week = '' } = useParams()
  const { productRunId: runId, legacySimulationRunId } = useViewerProductRunRouteContext()
  const parsedWeek = parseViewerWeekParam(week)
  const hasValidWeek = parsedWeek != null
  const queriesEnabled = Boolean(runId && hasValidWeek)

  const runQuery = useQuery({ queryKey: ['run', runId, legacySimulationRunId], queryFn: () => getRun(legacySimulationRunId), enabled: queriesEnabled, retry: false })
  const eventsQuery = useQuery({ queryKey: ['events', runId, legacySimulationRunId], queryFn: () => listEvents(legacySimulationRunId), enabled: queriesEnabled, retry: false })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-week-ranking-snapshots', runId, legacySimulationRunId],
    queryFn: () => listRankingSnapshots(legacySimulationRunId),
    enabled: queriesEnabled,
    retry: false
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-week-race-snapshots', runId, legacySimulationRunId],
    queryFn: () => listRaceSnapshots(legacySimulationRunId),
    enabled: queriesEnabled,
    retry: false
  })

  const orderedEvents = safeOrderedEvents(runQuery.data)
  const weekEvents = useMemo(() => plannedEventsForWeek(runQuery.data?.season_state, parsedWeek), [parsedWeek, runQuery.data?.season_state])
  const weekEventIds = useMemo(() => sourceEventIdsForWeek(weekEvents), [weekEvents])
  const nextEventIndex = runQuery.data?.season_state.next_event_index ?? 0
  const completedEventIds = useMemo(
    () => new Set(safeCompletedEventIds(runQuery.data)),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const eventRecords = useMemo(() => (runQuery.data ? safeEventRecords(eventsQuery.data?.events) : []), [eventsQuery.data?.events, runQuery.data])
  const eventRecordsById = useMemo(() => persistedEventsByExactId(eventRecords), [eventRecords])
  const persistedWeekEvents = useMemo(
    () => persistedEventsForWeek(eventRecords, parsedWeek, weekEventIds),
    [eventRecords, parsedWeek, weekEventIds]
  )
  const rankingPublications = useMemo(
    () => snapshotsForWeekSourceEvents(safeSnapshotRecords(rankingSnapshotsQuery.data?.snapshots), weekEventIds),
    [rankingSnapshotsQuery.data?.snapshots, weekEventIds]
  )
  const racePublications = useMemo(
    () => snapshotsForWeekSourceEvents(safeSnapshotRecords(raceSnapshotsQuery.data?.snapshots), weekEventIds),
    [raceSnapshotsQuery.data?.snapshots, weekEventIds]
  )
  const completedWeekEvents = useMemo(() => completedPlannedEventsForWeek(weekEvents, completedEventIds), [completedEventIds, weekEvents])
  const hasPublicationMatches = rankingPublications.length > 0 || racePublications.length > 0
  const hasAnyWeekData = weekEvents.length > 0 || persistedWeekEvents.length > 0 || hasPublicationMatches
  const contextLinks = hasValidWeek
    ? buildWeekContextLinks({
        runId,
        week: parsedWeek,
        rankingSnapshotSequences: rankingPublications.map((snapshot) => snapshot.snapshot_sequence),
        raceSnapshotSequences: racePublications.map((snapshot) => snapshot.snapshot_sequence)
      })
    : []

  return (
    <section className="panel">
      <RunScopedHeader title="Week Detail" runId={runId} subtitle="Read-only sports-facing detail for the selected week." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Week', value: hasValidWeek ? `W${parsedWeek}` : '—' },
          { label: 'Season', value: runQuery.data?.season_state.season ?? '—' },
          { label: 'Planned events', value: weekEvents.length },
          { label: 'Persisted events', value: persistedWeekEvents.length },
          { label: 'Ranking publications', value: rankingPublications.length },
          { label: 'Race publications', value: racePublications.length }
        ]}
      />

      <SectionCard title="Week context">
        {!runId ? <EmptyState message="No run route context was provided." /> : null}
        {!hasValidWeek ? <EmptyState message="Week must be a positive whole number in the URL (for example /weeks/12)." /> : null}
        {runQuery.isLoading ? <p className="status">Loading week detail…</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {hasValidWeek && runQuery.data && !hasAnyWeekData ? <EmptyState message="No planned or persisted tournament records are available for this week." /> : null}
        {hasValidWeek ? (
          <CompactSummaryCard
            items={buildWeekDetailMetadataItems({
              runId,
              week: parsedWeek,
              season: runQuery.data?.season_state.season,
              plannedEventCount: weekEvents.length,
              persistedEventCount: persistedWeekEvents.length,
              rankingPublicationCount: rankingPublications.length,
              racePublicationCount: racePublications.length,
              nextEventIndex: runQuery.data?.season_state.next_event_index,
              completedPlannedEventCount: completedWeekEvents.length
            })}
          />
        ) : null}
      </SectionCard>

      <SectionCard title="Source context links">
        {!hasValidWeek ? <EmptyState message="No valid week route context is available for source links." /> : null}
        {hasValidWeek ? (
          <ul className="item-list" aria-label="Week source links">
            {contextLinks.map((link) => (
              <li key={link.label}>
                <Link to={link.href}>{link.label}</Link>
              </li>
            ))}
          </ul>
        ) : null}
      </SectionCard>

      <SectionCard title="Planned events this week">
        {hasValidWeek && runQuery.data && weekEvents.length === 0 ? <EmptyState message="No planned tournaments are available for this week." /> : null}
        {weekEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer week planned events">
            {weekEvents.map((event) => {
              const eventRecord = eventRecordsById.get(event.event_id)
              const eventLinks = buildWeekEventLinks({ runId, eventId: event.event_id, hasPlanned: true, hasPersisted: Boolean(eventRecord) })

              return (
                <li key={event.event_id}>
                  <strong>{event.event_id}</strong>
                  <MetadataList
                    items={buildWeekPlannedEventMetadataItems({
                      event,
                      orderedEventCount: orderedEvents.length,
                      nextEventIndex,
                      completedEventIds,
                      persistedEvent: eventRecord
                    })}
                  />
                  <p>
                    {eventLinks.map((link, index) => (
                      <span key={link.label}>
                        {index > 0 ? ' · ' : null}
                        <Link to={link.href}>{link.label}</Link>
                      </span>
                    ))}
                  </p>
                </li>
              )
            })}
          </ol>
        ) : null}
      </SectionCard>

      <SectionCard title="Persisted tournament records this week">
        {eventsQuery.error ? <p className="error">Failed to load tournament records: {formatApiError(eventsQuery.error)}</p> : null}
        {!eventsQuery.error && hasValidWeek && runQuery.data && persistedWeekEvents.length === 0 ? (
          <EmptyState message="No persisted tournament records are available for this week." />
        ) : null}
        {!eventsQuery.error && persistedWeekEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer week persisted events">
            {persistedWeekEvents.map((event) => {
              const eventLinks = buildWeekEventLinks({ runId, eventId: event.event_id, hasPersisted: true })

              return (
                <li key={event.event_id}>
                  <strong>{event.event_id}</strong>
                  <MetadataList items={buildWeekPersistedEventMetadataItems(event)} />
                  <p>
                    {eventLinks.map((link) => (
                      <Link key={link.label} to={link.href}>
                        {link.label}
                      </Link>
                    ))}
                  </p>
                </li>
              )
            })}
          </ol>
        ) : null}
      </SectionCard>

      <SectionCard title="Publications this week">
        {rankingSnapshotsQuery.error ? <p className="error">Failed to load ranking publications: {formatApiError(rankingSnapshotsQuery.error)}</p> : null}
        {raceSnapshotsQuery.error ? <p className="error">Failed to load race publications: {formatApiError(raceSnapshotsQuery.error)}</p> : null}
        {!rankingSnapshotsQuery.error && !raceSnapshotsQuery.error && hasValidWeek ? (
          <MetadataList
            items={[
              { label: 'Ranking publications count', value: rankingPublications.length },
              { label: 'Race publications count', value: racePublications.length }
            ]}
          />
        ) : null}
        {!rankingSnapshotsQuery.error && rankingPublications.length > 0 ? (
          <ul className="item-list" aria-label="Week ranking publications">
            {rankingPublications.map((snapshot) => (
              <li key={`ranking-${snapshot.snapshot_sequence}`}>
                <Link to={viewerRankingSnapshotPath(runId, snapshot.snapshot_sequence)}>Ranking publication #{snapshot.snapshot_sequence}</Link>{' '}
                <span className="status">Source {safeText(snapshot.source_event_id)}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {!raceSnapshotsQuery.error && racePublications.length > 0 ? (
          <ul className="item-list" aria-label="Week race publications">
            {racePublications.map((snapshot) => (
              <li key={`race-${snapshot.snapshot_sequence}`}>
                <Link to={viewerRaceSnapshotPath(runId, snapshot.snapshot_sequence)}>Race publication #{snapshot.snapshot_sequence}</Link>{' '}
                <span className="status">Source {safeText(snapshot.source_event_id)}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {!rankingSnapshotsQuery.error && !raceSnapshotsQuery.error && !hasPublicationMatches && weekEvents.length > 0 ? (
          <p className="status">No ranking or race publications are source-matched to this week.</p>
        ) : null}
      </SectionCard>
    </section>
  )
}

import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import { getRun, getViewerCompletedTournaments, getViewerRunCalendar, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
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
import { formatApiError } from '../utils/apiErrors'
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

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const completedQuery = useQuery({
    queryKey: ['viewer-completed-tournaments', runId],
    queryFn: () => getViewerCompletedTournaments(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const completedById = useMemo(
    () => new Map((completedQuery.data?.tournaments ?? []).map((item) => [item.event_id, item])),
    [completedQuery.data]
  )

  return (
    <section className="panel">
      <RunScopedHeader
        title="Season Calendar"
        runId={runId}
        subtitle="Read-only Saved-Revision Calendar Package for the selected Product Run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Saved seasons', value: calendarQuery.data?.season_count ?? 0 },
          { label: 'Saved calendar events', value: calendarQuery.data?.event_count ?? 0 },
          { label: 'Canonical completed results', value: completedQuery.data?.tournament_count ?? 0 }
        ]}
      />

      <SectionCard title="Season timeline overview">
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar…</p> : null}
        {calendarQuery.error ? (
          <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p>
        ) : null}
        {completedQuery.error ? (
          <p className="error">Failed to load canonical completed tournament history: {formatApiError(completedQuery.error)}</p>
        ) : null}
        {calendarQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Saved seasons', value: calendarQuery.data.season_count },
                { label: 'Calendar events', value: calendarQuery.data.event_count },
                { label: 'Completed result publications', value: completedQuery.data?.tournament_count ?? 0 }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Active run id', value: runId || 'unknown' },
                { label: 'Viewer Branch', value: calendarQuery.data.viewer_branch_id },
                { label: 'Calendar authority', value: 'Saved Run Package state' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Season timeline">
        {calendarQuery.data?.event_count === 0 ? (
          <EmptyState message="The Saved Calendar Package contains no events." />
        ) : null}
        {calendarQuery.data?.seasons.map((season) => (
          <section key={String(season.season)}>
            <h3>{String(season.season)}</h3>
            <ol className="item-list" aria-label={`Viewer season calendar events ${String(season.season)}`}>
              {season.events.map((event, index) => {
                const canonicalResult = completedById.get(event.event_id)
                const status = canonicalResult
                  ? 'Completed · canonical result published'
                  : event.status.charAt(0).toUpperCase() + event.status.slice(1)

                return (
                  <li key={event.event_id}>
                    <strong>{event.event_id}</strong>
                    <MetadataList
                      items={[
                        { label: 'Status', value: status },
                        { label: 'Event ID', value: event.event_id },
                        { label: 'Event name', value: event.event_name || '—' },
                        { label: 'Season', value: event.season },
                        { label: 'Week', value: `W${event.season_week}` },
                        { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                        { label: 'Category', value: event.category || '—' },
                        { label: 'Template ID', value: event.template_id },
                        { label: 'Host', value: [event.host_city, event.host_country].filter(Boolean).join(', ') },
                        { label: 'Main / Q draw', value: `${event.main_draw_size} / ${event.qualification_draw_size}` },
                        { label: 'Seeds / Q spots / WC / BYE', value: `${event.seeds_count} / ${event.qualifier_spots} / ${event.wild_cards} / ${event.byes}` },
                        { label: 'Season position', value: `${index + 1} of ${season.events.length}` }
                      ]}
                    />
                    {canonicalResult ? (
                      <SummaryPills
                        items={[
                          { label: 'Champion', value: canonicalResult.champion_player_id },
                          { label: 'Finalist', value: canonicalResult.finalist_player_id },
                          { label: 'Matches', value: canonicalResult.match_count }
                        ]}
                      />
                    ) : null}
                    <p>
                      <Link to={viewerPlannedEventPath(runId, event.event_id)}>Open planned event</Link>
                      {' · '}
                      <Link to={viewerWeekDetailPath(runId, event.season_week)}>Open week detail</Link>
                      {' · '}
                      <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                    </p>
                  </li>
                )
              })}
            </ol>
          </section>
        ))}
      </SectionCard>

      {calendarQuery.data ? (
        <SectionCard title="Read-only data">
          <details>
            <summary>Show technical calendar data</summary>
            <p className="status">Read-only public Saved Calendar projection. Package/source fingerprints and Admin provenance are excluded by the API.</p>
            <JsonPayloadBlock title="Canonical Viewer Calendar" emptyText="No technical data is available." payload={calendarQuery.data} />
          </details>
        </SectionCard>
      ) : null}
    </section>
  )
}

export function ViewerRunPlannedEventPage(): JSX.Element {
  const { eventId = '' } = useParams()
  const { productRunId: runId, legacySimulationRunId } = useViewerProductRunRouteContext()

  const runQuery = useQuery({ queryKey: ['run', runId, legacySimulationRunId], queryFn: () => getRun(legacySimulationRunId), enabled: Boolean(runId && eventId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['events', runId, legacySimulationRunId], queryFn: () => listEvents(legacySimulationRunId), enabled: Boolean(runId && eventId), retry: false })

  const orderedEvents = safeOrderedEvents(runQuery.data)
  const nextEventIndex = runQuery.data?.season_state.next_event_index ?? 0
  const completedEventIds = useMemo(
    () => new Set(safeCompletedEventIds(runQuery.data)),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const eventRecords = useMemo(() => safeEventRecords(eventsQuery.data?.events), [eventsQuery.data?.events])
  const plannedEvent = useMemo(() => findPlannedEventById(runQuery.data?.season_state, eventId), [eventId, runQuery.data?.season_state])
  const eventRecord = useMemo(() => findPersistedEventById(eventRecords, eventId), [eventRecords, eventId])
  const hasEventRecord = Boolean(eventRecord)
  const statusLabel = plannedEvent
    ? resolvePlannedEventStatusLabel({
        eventId: plannedEvent.event_id,
        planIndex: plannedEvent.planIndex,
        nextEventIndex,
        completedEventIds
      })
    : null
  const plannedMetadataItems = plannedEvent
    ? buildPlannedEventDetailMetadataItems({
        runId,
        plannedEvent,
        orderedEventCount: orderedEvents.length,
        nextEventIndex,
        completedEventIds,
        persistedEvent: eventRecord
      })
    : []
  const contextLinks = runId && eventId
    ? buildPlannedEventContextLinks({
        runId,
        eventId,
        week: plannedEvent?.week,
        hasPersisted: hasEventRecord
      })
    : []

  return (
    <section className="panel">
      <RunScopedHeader
        title="Planned Event"
        runId={runId}
        subtitle="Read-only schedule event page for the selected run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Season', value: plannedEvent?.season ?? runQuery.data?.season_state.season ?? '—' },
          { label: 'Next event index', value: runQuery.data ? nextEventIndex : '—' }
        ]}
      />

      <SectionCard title="Source context links">
        {!runId || !eventId ? <EmptyState message="No planned event route context was provided." /> : null}
        {runId && eventId ? (
          <ul className="item-list" aria-label="Planned event source links">
            {contextLinks.map((link) => (
              <li key={link.label}>
                <Link to={link.href}>{link.label}</Link>
              </li>
            ))}
          </ul>
        ) : null}
      </SectionCard>

      <SectionCard title="Planned event summary">
        {runQuery.isLoading ? <p className="status">Loading planned event…</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {eventsQuery.error ? <p className="error">Failed to load tournament records: {formatApiError(eventsQuery.error)}</p> : null}
        {!eventId ? <EmptyState message="No planned event ID was provided in the URL." /> : null}
        {eventId && runQuery.data && !plannedEvent ? (
          <EmptyState message="This preview is not connected for this data shape yet." />
        ) : null}
        {plannedEvent ? (
          <>
            <SummaryPills
              items={[
                { label: 'Status', value: statusLabel ?? 'Planned' },
                { label: 'Plan position', value: `${plannedEvent.planIndex + 1} of ${orderedEvents.length}` },
                { label: 'Next event index', value: nextEventIndex },
                { label: 'Completed', value: eventIsCompleted(completedEventIds, plannedEvent.event_id) }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Active run id', value: runId || 'unknown' },
                { label: 'Event ID', value: plannedEvent.event_id },
                { label: 'Season', value: plannedEvent.season },
                { label: 'Week', value: `W${plannedEvent.week}` },
                { label: 'Tour', value: plannedEvent.tour },
                { label: 'Category', value: plannedEvent.category },
                { label: 'Template ID', value: plannedEvent.template_id }
              ]}
            />
            <MetadataList items={plannedMetadataItems} />
            {!hasEventRecord ? <p className="status">No persisted tournament record is available for this planned event yet.</p> : null}
          </>
        ) : null}
      </SectionCard>

      {plannedEvent ? (
        <SectionCard title="Read-only data">
          <details>
            <summary>Show technical planned event data</summary>
            <p className="status">Read-only technical planned-event data for audit/debugging. Viewer planned event pages do not mutate run state.</p>
            <JsonPayloadBlock title="Technical planned event record" emptyText="No technical data is available." payload={plannedEvent} />
          </details>
        </SectionCard>
      ) : null}
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

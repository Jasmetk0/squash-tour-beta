import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getRun, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
import type { RaceSnapshot, RankingSnapshot } from '../api/types'
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
import { tournamentResultPayloadMetadataItems } from '../viewer/TournamentResultMetadata'
import { findPersistedEventById, findPlannedEventById } from './viewer/tour/viewerEventDetailDisplay'
import {
  buildPlannedEventContextLinks,
  buildPlannedEventDetailMetadataItems,
  resolvePlannedEventStatusLabel
} from './viewer/tour/viewerPlannedEventDetailDisplay'
import {
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentsPath,
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

function snapshotDetailPath(kind: 'ranking' | 'race', runId: string, snapshotSequence: number): string {
  return kind === 'ranking' ? viewerRankingSnapshotPath(runId, snapshotSequence) : viewerRaceSnapshotPath(runId, snapshotSequence)
}

function snapshotsForEventIds<T extends RankingSnapshot | RaceSnapshot>(snapshots: T[], eventIds: Set<string>): T[] {
  return snapshots.filter((snapshot) => Boolean(snapshot.source_event_id && eventIds.has(snapshot.source_event_id)))
}

export function ViewerRunCalendarPage(): JSX.Element {
  const { runId = '' } = useParams()

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId), retry: false })

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const nextEventIndex = runQuery.data?.season_state.next_event_index ?? 0
  const completedEventIds = useMemo(
    () => new Set(runQuery.data?.season_state.completed_event_ids ?? []),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const eventRecords = useMemo(() => eventsQuery.data?.events ?? [], [eventsQuery.data?.events])
  const eventRecordIds = useMemo(() => new Set(eventRecords.map((event) => event.event_id)), [eventRecords])
  const eventRecordsById = useMemo(() => new Map(eventRecords.map((event) => [event.event_id, event])), [eventRecords])
  const completedCount = completedEventIds.size

  return (
    <section className="panel">
      <RunScopedHeader
        title="Season Calendar"
        runId={runId}
        subtitle="Read-only season schedule for the selected run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Season', value: runQuery.data?.season_state.season ?? '—' },
          { label: 'Ordered events', value: orderedEvents.length },
          { label: 'Completed events', value: completedCount },
          { label: 'Next event index', value: runQuery.data ? nextEventIndex : '—' }
        ]}
      />

      <SectionCard title="Season timeline overview">
        {runQuery.isLoading ? <p className="status">Loading season calendar…</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {eventsQuery.error ? <p className="error">Failed to load tournament records: {formatApiError(eventsQuery.error)}</p> : null}
        {runQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Season', value: runQuery.data.season_state.season },
                { label: 'Ordered event count', value: orderedEvents.length },
                { label: 'Completed event count', value: completedCount },
                { label: 'Next event index', value: nextEventIndex }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Active run id', value: runId || 'unknown' },
                { label: 'Season', value: runQuery.data.season_state.season },
                { label: 'Calendar source', value: 'Ordered season plan' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Season timeline">
        {runQuery.data && orderedEvents.length === 0 ? <EmptyState message="No data is available for this run yet." /> : null}
        {runQuery.data && orderedEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer season calendar events">
            {orderedEvents.map((event, index) => {
              const status = plannedStatus({ index, nextEventIndex, completedEventIds, eventId: event.event_id })
              const eventRecord = eventRecordsById.get(event.event_id)
              const hasEventRecord = eventRecordIds.has(event.event_id)
              const resultMetadataItems = eventRecord?.tournament_result
                ? tournamentResultPayloadMetadataItems(eventRecord.tournament_result, { runId })
                : []

              return (
                <li key={event.event_id}>
                  <strong>{event.event_id}</strong>
                  <MetadataList
                    items={[
                      { label: 'Status', value: eventStatusLabel(status) },
                      { label: 'Event ID', value: event.event_id },
                      { label: 'Season', value: event.season },
                      { label: 'Week', value: `W${event.week}` },
                      { label: 'Tour', value: event.tour },
                      { label: 'Category', value: event.category },
                      { label: 'Template ID', value: event.template_id },
                      { label: 'Plan position', value: `${index + 1} of ${orderedEvents.length}` },
                      ...resultMetadataItems
                    ]}
                  />
                  <p>
                    <Link to={viewerPlannedEventPath(runId, event.event_id)}>Open planned event</Link>
                    {' · '}
                    <Link to={viewerWeekDetailPath(runId, event.week)}>Open week detail</Link>
                    {hasEventRecord ? (
                      <>
                        {' · '}
                        <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                      </>
                    ) : null}
                  </p>
                </li>
              )
            })}
          </ol>
        ) : null}
      </SectionCard>

      {runQuery.data ? (
        <SectionCard title="Read-only data">
          <details>
            <summary>Show technical calendar data</summary>
            <p className="status">Read-only technical calendar data for audit/debugging. Viewer calendar pages do not mutate run state.</p>
            <JsonPayloadBlock title="Technical calendar record" emptyText="No technical data is available." payload={runQuery.data} />
          </details>
        </SectionCard>
      ) : null}
    </section>
  )
}

export function ViewerRunPlannedEventPage(): JSX.Element {
  const { runId = '', eventId = '' } = useParams()

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId && eventId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId && eventId), retry: false })

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const nextEventIndex = runQuery.data?.season_state.next_event_index ?? 0
  const completedEventIds = useMemo(
    () => new Set(runQuery.data?.season_state.completed_event_ids ?? []),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const eventRecords = useMemo(() => eventsQuery.data?.events ?? [], [eventsQuery.data?.events])
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
        eventId: plannedEvent?.event_id ?? eventId,
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
  const { runId = '', week = '' } = useParams()
  const parsedWeek = Number(week)
  const hasValidWeek = Number.isInteger(parsedWeek)

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId), retry: false })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-week-ranking-snapshots', runId],
    queryFn: () => listRankingSnapshots(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-week-race-snapshots', runId],
    queryFn: () => listRaceSnapshots(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const weekEvents = hasValidWeek ? orderedEvents.filter((event) => event.week === parsedWeek) : []
  const weekEventIds = useMemo(() => new Set(weekEvents.map((event) => event.event_id)), [weekEvents])
  const nextEventIndex = runQuery.data?.season_state.next_event_index ?? 0
  const completedEventIds = useMemo(
    () => new Set(runQuery.data?.season_state.completed_event_ids ?? []),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const eventRecords = eventsQuery.data?.events ?? []
  const eventRecordsById = useMemo(() => new Map(eventRecords.map((event) => [event.event_id, event])), [eventRecords])
  const persistedWeekEvents = hasValidWeek
    ? eventRecords.filter((event) => event.week === parsedWeek || weekEventIds.has(event.event_id))
    : []
  const rankingPublications = snapshotsForEventIds(rankingSnapshotsQuery.data?.snapshots ?? [], weekEventIds)
  const racePublications = snapshotsForEventIds(raceSnapshotsQuery.data?.snapshots ?? [], weekEventIds)
  const hasPublicationMatches = rankingPublications.length > 0 || racePublications.length > 0
  const hasAnyWeekData = weekEvents.length > 0 || hasPublicationMatches

  return (
    <section className="panel">
      <RunScopedHeader title="Week Detail" runId={runId} subtitle="Read-only sports-facing detail for the selected week." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Week', value: hasValidWeek ? `W${parsedWeek}` : '—' },
          { label: 'Season', value: runQuery.data?.season_state.season ?? '—' },
          { label: 'Planned events', value: weekEvents.length },
          { label: 'Persisted events', value: persistedWeekEvents.length }
        ]}
      />

      <SectionCard title="Week context">
        {runQuery.isLoading ? <p className="status">Loading week detail…</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {eventsQuery.error ? <p className="error">Failed to load tournament records: {formatApiError(eventsQuery.error)}</p> : null}
        {!hasValidWeek ? <EmptyState message="Week must be a whole number in the URL (for example /weeks/12)." /> : null}
        {hasValidWeek && runQuery.data && !hasAnyWeekData ? <EmptyState message="No data is available for this run yet." /> : null}
        {hasValidWeek ? (
          <CompactSummaryCard
            items={[
              { label: 'Active run id', value: runId || 'unknown' },
              { label: 'Week number', value: parsedWeek },
              { label: 'Season', value: runQuery.data?.season_state.season ?? '—' },
              { label: 'Planned events this week', value: weekEvents.length },
              { label: 'Persisted/completed events this week', value: persistedWeekEvents.length }
            ]}
          />
        ) : null}
      </SectionCard>

      <SectionCard title="Tournaments this week">
        {hasValidWeek && runQuery.data && weekEvents.length === 0 ? <EmptyState message="No planned tournaments are available for this week." /> : null}
        {weekEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer week events">
            {weekEvents.map((event) => {
              const planIndex = orderedEvents.indexOf(event)
              const status = plannedStatus({ index: planIndex, nextEventIndex, completedEventIds, eventId: event.event_id })
              const eventRecord = eventRecordsById.get(event.event_id)
              const hasEventRecord = Boolean(eventRecord)
              const hasResult = Boolean(eventRecord?.tournament_result)
              const resultMetadataItems = eventRecord?.tournament_result
                ? tournamentResultPayloadMetadataItems(eventRecord.tournament_result, { runId })
                : []

              return (
                <li key={event.event_id}>
                  <strong>{event.event_id}</strong>
                  <MetadataList
                    items={[
                      { label: 'Event ID', value: event.event_id },
                      { label: 'Season', value: event.season },
                      { label: 'Week', value: `W${event.week}` },
                      { label: 'Tour', value: event.tour },
                      { label: 'Category', value: event.category },
                      { label: 'Template', value: event.template_id },
                      { label: 'Status', value: eventStatusLabel(status) },
                      { label: 'Persisted event record', value: hasEventRecord ? 'Yes' : 'No' },
                      { label: 'Result availability', value: hasResult ? 'Available' : 'Not available' },
                      ...resultMetadataItems
                    ]}
                  />
                  <p>
                    <Link to={viewerPlannedEventPath(runId, event.event_id)}>Open planned event</Link>
                    {hasEventRecord ? (
                      <>
                        {' · '}
                        <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                      </>
                    ) : null}
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
        {!rankingSnapshotsQuery.error && !raceSnapshotsQuery.error && hasPublicationMatches ? (
          <MetadataList
            items={[
              {
                label: 'Ranking publications count',
                value: (
                  <span>
                    {rankingPublications.length}
                    {rankingPublications.length > 0 ? (
                      <ul className="item-list">
                        {rankingPublications.map((snapshot) => (
                          <li key={`ranking-${snapshot.snapshot_sequence}`}>
                            <Link to={snapshotDetailPath('ranking', runId, snapshot.snapshot_sequence)}>
                              Ranking publication #{snapshot.snapshot_sequence}
                            </Link>{' '}
                            <span className="status">Source {snapshot.source_event_id}</span>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </span>
                )
              },
              {
                label: 'Race publications count',
                value: (
                  <span>
                    {racePublications.length}
                    {racePublications.length > 0 ? (
                      <ul className="item-list">
                        {racePublications.map((snapshot) => (
                          <li key={`race-${snapshot.snapshot_sequence}`}>
                            <Link to={snapshotDetailPath('race', runId, snapshot.snapshot_sequence)}>
                              Race publication #{snapshot.snapshot_sequence}
                            </Link>{' '}
                            <span className="status">Source {snapshot.source_event_id}</span>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </span>
                )
              }
            ]}
          />
        ) : null}
        {!rankingSnapshotsQuery.error && !raceSnapshotsQuery.error && !hasPublicationMatches && weekEvents.length > 0 ? (
          <p className="status">This preview is not connected for this data shape yet.</p>
        ) : null}
      </SectionCard>

      <SectionCard title="Links">
        <p>
          <Link to={viewerSeasonCalendarPath(runId)}>Back to season calendar</Link>
          {' · '}
          <Link to={viewerTournamentsPath(runId)}>Open tournaments</Link>
          {' · '}
          <Link to={viewerRankingsPath(runId)}>Open rankings</Link>
          {' · '}
          <Link to={viewerRacePath(runId)}>Open race</Link>
        </p>
      </SectionCard>
    </section>
  )
}

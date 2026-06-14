import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getEvent, getRun, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
import type { EventRecord, SeasonStateResponse } from '../api/types'
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
import {
  TournamentResultMetadataList,
  tournamentResultMetadataItems
} from '../viewer/TournamentResultMetadata'
import { parseTournamentResultPayload } from '../viewer/tournamentResultPayload'
import {
  viewerPlannedEventPath,
  viewerTournamentsPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'
import {
  buildEventDetailLinks,
  snapshotsForSourceEvent
} from './viewer/tour/viewerEventDetailDisplay'
import { getPlannedEventStatus } from './plannedEventUtils'

type PlannedEvent = SeasonStateResponse['season_state']['ordered_events'][number]

type PlannedTournamentContext = PlannedEvent & {
  planPosition: number
}

function buildPlannedContext(runData: SeasonStateResponse | undefined): Map<string, PlannedTournamentContext> {
  const plannedContext = new Map<string, PlannedTournamentContext>()
  const orderedEvents = runData?.season_state?.ordered_events

  if (!Array.isArray(orderedEvents)) return plannedContext

  orderedEvents.forEach((event, index) => {
    if (event && typeof event === 'object' && typeof event.event_id === 'string') {
      plannedContext.set(event.event_id, { ...event, planPosition: index })
    }
  })
  return plannedContext
}

function isScalar(value: unknown): value is string | number {
  return typeof value === 'string' || typeof value === 'number'
}

function safeText(value: unknown, fallback: string | number = '—'): string | number {
  return isScalar(value) ? value : fallback
}

function safeNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function safeEventRecords(events: EventRecord[] | undefined): EventRecord[] {
  if (!Array.isArray(events)) return []
  return events.filter((event) => event && typeof event === 'object' && typeof event.event_id === 'string')
}

function safeCompletedEventIds(data: SeasonStateResponse | undefined): string[] {
  const completedEventIds = data?.season_state?.completed_event_ids
  return Array.isArray(completedEventIds) ? completedEventIds.filter((eventId) => typeof eventId === 'string') : []
}

function safeSnapshotRecords<T extends { snapshot_sequence: number }>(snapshots: T[] | undefined): T[] {
  if (!Array.isArray(snapshots)) return []
  return snapshots.filter((snapshot) => snapshot && typeof snapshot === 'object' && typeof snapshot.snapshot_sequence === 'number')
}

function eventWeek(event: EventRecord | null | undefined, planned: PlannedTournamentContext | undefined): number | null {
  return safeNumber(event?.week) ?? safeNumber(planned?.week) ?? null
}

function eventSeason(event: EventRecord | null | undefined, planned: PlannedTournamentContext | undefined): number | null {
  return safeNumber(event?.season) ?? safeNumber(planned?.season) ?? null
}

function resultAvailability(event: EventRecord | null | undefined): string {
  if (!event) return 'Not loaded'
  return event.tournament_result ? 'Result publication available' : 'No result publication recorded'
}

function completionStatus(event: EventRecord, completedEventIds: Set<string>): string {
  return completedEventIds.has(event.event_id) ? 'Completed in season plan' : 'Completion not recorded in plan'
}

function displayValue(value: unknown): number | string {
  return safeText(value)
}

function displayWeekDetailLink(runId: string, week: number | null): ReactNode {
  if (week == null) return '—'

  return <Link to={viewerWeekDetailPath(runId, week)}>{`W${week}`}</Link>
}

function TournamentListResultMetadata({ event, runId }: { event: EventRecord; runId: string }): JSX.Element | null {
  return (
    <TournamentResultMetadataList
      payload={event.tournament_result}
      runId={runId}
      matches="matchCount"
      playerLabelMode="identityWithCountry"
    />
  )
}

export function ViewerRunTournamentsPage(): JSX.Element {
  const { runId = '' } = useParams()

  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId), retry: false })

  const events = safeEventRecords(eventsQuery.data?.events)
  const plannedContext = useMemo(() => buildPlannedContext(runQuery.data), [runQuery.data])
  const completedEventIds = useMemo(
    () => new Set(safeCompletedEventIds(runQuery.data)),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const completedPersistedCount = events.filter((event) => completedEventIds.has(event.event_id)).length

  return (
    <section className="panel">
      <RunScopedHeader
        title="Tournaments"
        runId={runId}
        subtitle="Read-only tournament schedule and results for the selected run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Event count', value: events.length },
          { label: 'Completed events', value: completedEventIds.size },
          { label: 'Completed persisted events', value: completedPersistedCount }
        ]}
      />

      <SectionCard title="Tournament publications">
        {eventsQuery.isLoading && <p className="status">Loading tournaments...</p>}
        {eventsQuery.error && <p className="error">Failed to load tournaments: {formatApiError(eventsQuery.error)}</p>}
        {runQuery.error && <p className="error">Failed to load ordered calendar context: {formatApiError(runQuery.error)}</p>}
        {!eventsQuery.isLoading && !eventsQuery.error && events.length === 0 && (
          <EmptyState message="No data is available for this run yet." />
        )}
        {events.length > 0 && (
          <ul className="item-list" aria-label="Tournament event list">
            {events.map((event) => {
              const planned = plannedContext.get(event.event_id)
              const week = eventWeek(event, planned)
              const season = eventSeason(event, planned)

              return (
                <li key={event.event_id} id={`event-${event.event_id}`}>
                  <strong>{event.event_id}</strong>
                  <MetadataList
                    items={[
                      { label: 'Sequence', value: safeText(event.event_sequence) },
                      { label: 'Season', value: season ?? '—' },
                      { label: 'Week', value: displayWeekDetailLink(runId, week) },
                      { label: 'Template', value: safeText(planned?.template_id ?? event.template_id) },
                      { label: 'Category', value: safeText(planned?.category, 'No ordered-calendar category') },
                      { label: 'Tour', value: safeText(planned?.tour, 'No ordered-calendar tour') },
                      { label: 'Completion', value: completionStatus(event, completedEventIds) },
                      { label: 'Result availability', value: resultAvailability(event) }
                    ]}
                  />
                  <TournamentListResultMetadata event={event} runId={runId} />
                  <p>
                    <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                  </p>
                </li>
              )
            })}
          </ul>
        )}
      </SectionCard>
    </section>
  )
}

export function ViewerRunTournamentDetailPage(): JSX.Element {
  const { runId = '', eventId = '' } = useParams()

  const eventQuery = useQuery({
    queryKey: ['event', runId, eventId],
    queryFn: () => getEvent(runId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId && eventId), retry: false })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-tournament-ranking-snapshots', runId, eventId],
    queryFn: () => listRankingSnapshots(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-tournament-race-snapshots', runId, eventId],
    queryFn: () => listRaceSnapshots(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })

  const plannedContext = useMemo(() => buildPlannedContext(runQuery.data), [runQuery.data])
  const planned = plannedContext.get(eventId)
  const orderedEvents = Array.isArray(runQuery.data?.season_state?.ordered_events) ? runQuery.data.season_state.ordered_events : []
  const completedEventIds = useMemo(
    () => new Set(safeCompletedEventIds(runQuery.data)),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const plannedStatus = planned
    ? getPlannedEventStatus({
        index: planned.planPosition,
        nextEventIndex: runQuery.data?.season_state.next_event_index ?? 0,
        completedEventIds,
        eventId: planned.event_id
      })
    : null
  const event = eventQuery.data
  const resultPreview = useMemo(() => parseTournamentResultPayload(event?.tournament_result), [event?.tournament_result])
  const week = eventWeek(event, planned)
  const season = eventSeason(event, planned)
  const templateId = planned?.template_id ?? event?.template_id ?? null
  const rankingPublications = snapshotsForSourceEvent(safeSnapshotRecords(rankingSnapshotsQuery.data?.snapshots), eventId)
  const racePublications = snapshotsForSourceEvent(safeSnapshotRecords(raceSnapshotsQuery.data?.snapshots), eventId)
  const sourceLinks = buildEventDetailLinks({
    runId,
    eventId,
    week,
    hasPlanned: Boolean(planned),
    hasPersisted: Boolean(event),
    rankingSnapshotSequences: rankingPublications.map((snapshot) => snapshot.snapshot_sequence),
    raceSnapshotSequences: racePublications.map((snapshot) => snapshot.snapshot_sequence)
  })

  return (
    <section className="panel">
      <RunScopedHeader
        title="Tournament Detail"
        runId={runId}
        subtitle="Read-only tournament detail for the selected run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Result availability', value: resultAvailability(event) }
        ]}
      />

      <SectionCard title="Tournament links">
        <p>
          <Link to={viewerTournamentsPath(runId)}>Back to tournaments</Link>
          {planned ? (
            <>
              {' · '}
              <Link to={viewerPlannedEventPath(runId, eventId)}>Open calendar event</Link>
            </>
          ) : null}
          {week != null ? (
            <>
              {' · '}
              <Link to={viewerWeekDetailPath(runId, week)}>Open week detail</Link>
            </>
          ) : null}
        </p>
      </SectionCard>

      {!eventId && (
        <SectionCard title="Tournament lookup">
          <EmptyState message="No event ID was provided in the URL." />
        </SectionCard>
      )}

      {eventId && (
        <>
          <SectionCard title="Tournament metadata">
            {eventQuery.isLoading && <p className="status">Loading tournament detail...</p>}
            {eventQuery.error && !isApiNotFound(eventQuery.error) && (
              <p className="error">Failed to load tournament detail: {formatApiError(eventQuery.error)}</p>
            )}
            {isApiNotFound(eventQuery.error) && <EmptyState message={`Event ${eventId} was not found for this run.`} />}
            {runQuery.error && <p className="error">Failed to load ordered calendar context: {formatApiError(runQuery.error)}</p>}
            {event ? (
              <>
                <SummaryPills
                  items={[
                    { label: 'Status', value: plannedStatus ?? completionStatus(event, completedEventIds) },
                    { label: 'Result availability', value: resultAvailability(event) },
                    { label: 'Ordered-calendar match', value: planned ? 'Available' : 'Not available' }
                  ]}
                />
                <CompactSummaryCard
                  items={[
                    { label: 'Event ID', value: event.event_id },
                    { label: 'Run ID', value: runId || 'unknown' },
                    { label: 'Sequence', value: safeText(event.event_sequence) },
                    { label: 'Season', value: season ?? '—' },
                    { label: 'Week', value: displayWeekDetailLink(runId, week) },
                    { label: 'Tour', value: safeText(planned?.tour, 'No ordered-calendar tour') },
                    { label: 'Category', value: safeText(planned?.category, 'No ordered-calendar category') },
                    { label: 'Template', value: safeText(templateId) }
                  ]}
                />
                {planned ? (
                  <MetadataList
                    items={[
                      { label: 'Plan position', value: `${planned.planPosition + 1} of ${orderedEvents.length}` },
                      { label: 'Plan index', value: planned.planPosition },
                      { label: 'Current next event index', value: runQuery.data?.season_state.next_event_index ?? '—' }
                    ]}
                  />
                ) : null}
              </>
            ) : null}
          </SectionCard>

          {event ? (
            <SectionCard title="Source context links">
              {rankingSnapshotsQuery.error ? <p className="error">Failed to load ranking publications: {formatApiError(rankingSnapshotsQuery.error)}</p> : null}
              {raceSnapshotsQuery.error ? <p className="error">Failed to load race publications: {formatApiError(raceSnapshotsQuery.error)}</p> : null}
              <MetadataList
                items={[
                  { label: 'Ranking publications from event', value: rankingPublications.length },
                  { label: 'Race publications from event', value: racePublications.length },
                  {
                    label: 'Safe links',
                    value: (
                      <ul className="item-list">
                        {sourceLinks.map((link) => (
                          <li key={`${link.label}-${link.href}`}>
                            <Link to={link.href}>{link.label}</Link>
                          </li>
                        ))}
                      </ul>
                    )
                  }
                ]}
              />
            </SectionCard>
          ) : null}

          {event ? (
            <SectionCard title="Tournament Result Preview">
              {resultPreview.summary ? (
                <MetadataList
                  items={[
                    ...tournamentResultMetadataItems(resultPreview.summary, {
                      runId,
                      includeFinalist: true,
                      includeResultStatus: false,
                      matches: false,
                      includeEmptyValues: true,
                      playerLabelMode: 'identityWithCountry'
                    }),
                    { label: 'Final score', value: displayValue(resultPreview.summary.finalScore) },
                    { label: 'Match count', value: displayValue(resultPreview.summary.matchCount) },
                    { label: 'Completed matches', value: displayValue(resultPreview.summary.completedMatchCount) },
                    { label: 'Draw size', value: displayValue(resultPreview.summary.drawSize) },
                    { label: 'Round count', value: displayValue(resultPreview.summary.roundCount) },
                    ...tournamentResultMetadataItems(resultPreview.summary, {
                      runId,
                      includeChampion: false,
                      includeResultStatus: true,
                      matches: false,
                      includeEmptyValues: true,
                      playerLabelMode: 'identityWithCountry'
                    })
                  ]}
                />
              ) : (
                <EmptyState message="This preview is not connected for this data shape yet." />
              )}
            </SectionCard>
          ) : null}

          {event ? (
            <SectionCard title="Read-only data">
              <details>
                <summary>Show technical event data</summary>
                <p className="status">Read-only technical event/result data for audit/debugging. Viewer tournament detail pages do not mutate run state.</p>
                <JsonPayloadBlock title="Technical event record" emptyText="No technical event data is available for this event." payload={event} />
              </details>
            </SectionCard>
          ) : null}
        </>
      )}
    </section>
  )
}

import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getEvent, getRun, listEvents } from '../api/client'
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
import { getPlannedEventStatus } from './plannedEventUtils'

type PlannedEvent = SeasonStateResponse['season_state']['ordered_events'][number]

type PlannedTournamentContext = PlannedEvent & {
  planPosition: number
}

function buildPlannedContext(runData: SeasonStateResponse | undefined): Map<string, PlannedTournamentContext> {
  const plannedContext = new Map<string, PlannedTournamentContext>()
  const orderedEvents = runData?.season_state.ordered_events ?? []

  orderedEvents.forEach((event, index) => {
    plannedContext.set(event.event_id, { ...event, planPosition: index })
  })
  return plannedContext
}

function eventWeek(event: EventRecord | null | undefined, planned: PlannedTournamentContext | undefined): number | null {
  return event?.week ?? planned?.week ?? null
}

function eventSeason(event: EventRecord | null | undefined, planned: PlannedTournamentContext | undefined): number | null {
  return event?.season ?? planned?.season ?? null
}

function resultAvailability(event: EventRecord | null | undefined): string {
  if (!event) return 'Not loaded'
  return event.tournament_result ? 'Result payload available' : 'No result payload recorded'
}

function completionStatus(event: EventRecord, completedEventIds: Set<string>): string {
  return completedEventIds.has(event.event_id) ? 'Completed in season plan' : 'Completion not recorded in plan'
}

export function ViewerRunTournamentsPage(): JSX.Element {
  const { runId = '' } = useParams()

  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId), retry: false })

  const events = eventsQuery.data?.events ?? []
  const plannedContext = useMemo(() => buildPlannedContext(runQuery.data), [runQuery.data])
  const completedEventIds = useMemo(
    () => new Set(runQuery.data?.season_state.completed_event_ids ?? []),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const completedPersistedCount = events.filter((event) => completedEventIds.has(event.event_id)).length

  return (
    <section className="panel">
      <RunScopedHeader
        title="Tournaments"
        runId={runId}
        subtitle="Read-only tournament/event history for the selected run."
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
                      { label: 'Sequence', value: event.event_sequence ?? '—' },
                      { label: 'Season', value: season ?? '—' },
                      { label: 'Week', value: week != null ? `W${week}` : '—' },
                      { label: 'Template', value: planned?.template_id ?? event.template_id ?? '—' },
                      { label: 'Category', value: planned?.category ?? 'No ordered-calendar category' },
                      { label: 'Tour', value: planned?.tour ?? 'No ordered-calendar tour' },
                      { label: 'Completion', value: completionStatus(event, completedEventIds) },
                      { label: 'Result availability', value: resultAvailability(event) }
                    ]}
                  />
                  <p>
                    <Link to={`/viewer/runs/${runId}/tournaments/${encodeURIComponent(event.event_id)}`}>Open tournament detail</Link>
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

  const plannedContext = useMemo(() => buildPlannedContext(runQuery.data), [runQuery.data])
  const planned = plannedContext.get(eventId)
  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const completedEventIds = useMemo(
    () => new Set(runQuery.data?.season_state.completed_event_ids ?? []),
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
  const week = eventWeek(event, planned)
  const season = eventSeason(event, planned)
  const templateId = planned?.template_id ?? event?.template_id ?? null

  return (
    <section className="panel">
      <RunScopedHeader
        title="Tournament Detail"
        runId={runId}
        subtitle="Read-only tournament/event metadata for the selected run."
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
          <Link to={`/viewer/runs/${runId}/tournaments`}>Back to tournaments</Link>
          {planned ? (
            <>
              {' · '}
              <Link to={`/viewer/runs/${runId}/calendar/${encodeURIComponent(eventId)}`}>Open calendar event</Link>
            </>
          ) : null}
          {week != null ? (
            <>
              {' · '}
              <Link to={`/viewer/runs/${runId}/weeks/${week}`}>Open week detail</Link>
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
                    { label: 'Sequence', value: event.event_sequence ?? '—' },
                    { label: 'Season', value: season ?? '—' },
                    { label: 'Week', value: week != null ? `W${week}` : '—' },
                    { label: 'Tour', value: planned?.tour ?? 'No ordered-calendar tour' },
                    { label: 'Category', value: planned?.category ?? 'No ordered-calendar category' },
                    { label: 'Template', value: templateId ?? '—' }
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
            <SectionCard title="Tournament result preview">
              <EmptyState message="This preview is not connected for this data shape yet." />
            </SectionCard>
          ) : null}

          {event ? (
            <SectionCard title="Read-only data">
              <details>
                <summary>Show technical event data</summary>
                <p className="status">Read-only technical event/result data for audit/debugging. Viewer tournament pages do not mutate run state.</p>
                <JsonPayloadBlock title="Technical event record" emptyText="No technical event data is available for this event." payload={event} />
              </details>
            </SectionCard>
          ) : null}
        </>
      )}
    </section>
  )
}

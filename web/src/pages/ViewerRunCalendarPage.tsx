import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getRun, listEvents } from '../api/client'
import type { SeasonStateResponse } from '../api/types'
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

export type ViewerPlannedEvent = SeasonStateResponse['season_state']['ordered_events'][number]

type ViewerPlannedEventContext = ViewerPlannedEvent & {
  planIndex: number
}

function buildPlannedEventContext(runData: SeasonStateResponse | undefined): Map<string, ViewerPlannedEventContext> {
  const contexts = new Map<string, ViewerPlannedEventContext>()
  const orderedEvents = runData?.season_state.ordered_events ?? []

  orderedEvents.forEach((event, index) => {
    contexts.set(event.event_id, { ...event, planIndex: index })
  })

  return contexts
}

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
  const eventRecordIds = useMemo(() => new Set((eventsQuery.data?.events ?? []).map((event) => event.event_id)), [eventsQuery.data?.events])
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

      <SectionCard title="Season schedule overview">
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

      <SectionCard title="Calendar events">
        {runQuery.data && orderedEvents.length === 0 ? <EmptyState message="No ordered calendar events are available for this run." /> : null}
        {runQuery.data && orderedEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer season calendar events">
            {orderedEvents.map((event, index) => {
              const status = plannedStatus({ index, nextEventIndex, completedEventIds, eventId: event.event_id })
              const hasEventRecord = eventRecordIds.has(event.event_id)

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
                      { label: 'Plan position', value: `${index + 1} of ${orderedEvents.length}` }
                    ]}
                  />
                  <p>
                    <Link to={`/viewer/runs/${runId}/calendar/${encodeURIComponent(event.event_id)}`}>Open planned event</Link>
                    {' · '}
                    <Link to={`/viewer/runs/${runId}/weeks/${event.week}`}>Open week detail</Link>
                    {hasEventRecord ? (
                      <>
                        {' · '}
                        <Link to={`/viewer/runs/${runId}/tournaments/${encodeURIComponent(event.event_id)}`}>Open tournament detail</Link>
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
        <SectionCard title="Technical read-only data">
          <details>
            <summary>Show technical calendar data</summary>
            <p className="status">Read-only technical calendar data for audit/debugging. Viewer calendar pages do not mutate run state.</p>
            <JsonPayloadBlock title="Technical calendar record" emptyText="No technical calendar data is available." payload={runQuery.data} />
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
  const eventRecordIds = useMemo(() => new Set((eventsQuery.data?.events ?? []).map((event) => event.event_id)), [eventsQuery.data?.events])
  const plannedContext = useMemo(() => buildPlannedEventContext(runQuery.data), [runQuery.data])
  const plannedEvent = plannedContext.get(eventId)
  const status = plannedEvent
    ? plannedStatus({ index: plannedEvent.planIndex, nextEventIndex, completedEventIds, eventId: plannedEvent.event_id })
    : null
  const hasEventRecord = eventRecordIds.has(eventId)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Planned Event"
        runId={runId}
        subtitle="Read-only calendar event page for the selected run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Season', value: plannedEvent?.season ?? runQuery.data?.season_state.season ?? '—' },
          { label: 'Next event index', value: runQuery.data ? nextEventIndex : '—' }
        ]}
      />

      <SectionCard title="Planned event links">
        <p>
          <Link to={`/viewer/runs/${runId}/calendar`}>Back to season calendar</Link>
          {plannedEvent ? (
            <>
              {' · '}
              <Link to={`/viewer/runs/${runId}/weeks/${plannedEvent.week}`}>Open week detail</Link>
            </>
          ) : null}
          {hasEventRecord ? (
            <>
              {' · '}
              <Link to={`/viewer/runs/${runId}/tournaments/${encodeURIComponent(eventId)}`}>Open tournament detail</Link>
            </>
          ) : null}
        </p>
      </SectionCard>

      <SectionCard title="Planned event summary">
        {runQuery.isLoading ? <p className="status">Loading planned event…</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {eventsQuery.error ? <p className="error">Failed to load tournament records: {formatApiError(eventsQuery.error)}</p> : null}
        {!eventId ? <EmptyState message="No planned event ID was provided in the URL." /> : null}
        {eventId && runQuery.data && !plannedEvent ? (
          <EmptyState message="Planned event preview is not connected for this data shape yet." />
        ) : null}
        {plannedEvent ? (
          <>
            <SummaryPills
              items={[
                { label: 'Status', value: eventStatusLabel(status ?? 'planned') },
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
            <MetadataList
              items={[
                { label: 'Plan index', value: plannedEvent.planIndex },
                { label: 'Status', value: eventStatusLabel(status ?? 'planned') },
                { label: 'Completed indicator', value: eventIsCompleted(completedEventIds, plannedEvent.event_id) },
                { label: 'Tournament detail available', value: hasEventRecord ? 'Yes' : 'No' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      {plannedEvent ? (
        <SectionCard title="Technical read-only data">
          <details>
            <summary>Show technical planned event data</summary>
            <p className="status">Read-only technical planned-event data for audit/debugging. Viewer planned event pages do not mutate run state.</p>
            <JsonPayloadBlock title="Technical planned event record" emptyText="No technical planned event data is available." payload={plannedEvent} />
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

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const weekEvents = hasValidWeek ? orderedEvents.filter((event) => event.week === parsedWeek) : []
  const nextEventIndex = runQuery.data?.season_state.next_event_index ?? 0
  const completedEventIds = useMemo(
    () => new Set(runQuery.data?.season_state.completed_event_ids ?? []),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const eventRecordIds = useMemo(() => new Set((eventsQuery.data?.events ?? []).map((event) => event.event_id)), [eventsQuery.data?.events])

  return (
    <section className="panel">
      <RunScopedHeader title="Week Detail" runId={runId} subtitle="Read-only planned events for the selected calendar week." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Season', value: runQuery.data?.season_state.season ?? '—' },
          { label: 'Week', value: hasValidWeek ? `W${parsedWeek}` : '—' },
          { label: 'Events this week', value: weekEvents.length }
        ]}
      />

      <SectionCard title="Week schedule">
        {runQuery.isLoading ? <p className="status">Loading week detail…</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {eventsQuery.error ? <p className="error">Failed to load tournament records: {formatApiError(eventsQuery.error)}</p> : null}
        {!hasValidWeek ? <EmptyState message="Week must be a whole number in the URL (for example /weeks/12)." /> : null}
        {hasValidWeek && runQuery.data && weekEvents.length === 0 ? (
          <EmptyState message={`Week ${parsedWeek} is not present in this run's ordered season plan.`} />
        ) : null}
        {weekEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer week events">
            {weekEvents.map((event) => {
              const planIndex = orderedEvents.indexOf(event)
              const status = plannedStatus({ index: planIndex, nextEventIndex, completedEventIds, eventId: event.event_id })
              const hasEventRecord = eventRecordIds.has(event.event_id)

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
                      { label: 'Plan position', value: `${planIndex + 1} of ${orderedEvents.length}` }
                    ]}
                  />
                  <p>
                    <Link to={`/viewer/runs/${runId}/calendar/${encodeURIComponent(event.event_id)}`}>Open planned event</Link>
                    {hasEventRecord ? (
                      <>
                        {' · '}
                        <Link to={`/viewer/runs/${runId}/tournaments/${encodeURIComponent(event.event_id)}`}>Open tournament detail</Link>
                      </>
                    ) : null}
                  </p>
                </li>
              )
            })}
          </ol>
        ) : null}
      </SectionCard>
    </section>
  )
}

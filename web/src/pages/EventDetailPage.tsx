import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getEvent, getRun, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
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

export function EventDetailPage(): JSX.Element {
  const { runId = '', eventId = '' } = useParams()

  const eventQuery = useQuery({
    queryKey: ['event', runId, eventId],
    queryFn: () => getEvent(runId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const eventsQuery = useQuery({
    queryKey: ['events', runId],
    queryFn: () => listEvents(runId),
    enabled: Boolean(runId && eventId)
  })
  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['ranking-snapshots', runId],
    queryFn: () => listRankingSnapshots(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['race-snapshots', runId],
    queryFn: () => listRaceSnapshots(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })

  const events = eventsQuery.data?.events ?? []
  const currentEventIndex = events.findIndex((item) => item.event_id === eventId)
  const previousEvent = currentEventIndex > 0 ? events[currentEventIndex - 1] : null
  const nextEvent = currentEventIndex >= 0 && currentEventIndex < events.length - 1 ? events[currentEventIndex + 1] : null
  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const plannedEventIndex = orderedEvents.findIndex((item) => item.event_id === eventId)
  const plannedEvent = plannedEventIndex >= 0 ? orderedEvents[plannedEventIndex] : null
  const previousPlannedEvent = plannedEventIndex > 0 ? orderedEvents[plannedEventIndex - 1] : null
  const nextPlannedEvent =
    plannedEventIndex >= 0 && plannedEventIndex < orderedEvents.length - 1 ? orderedEvents[plannedEventIndex + 1] : null
  const completedEventIds = new Set(runQuery.data?.season_state.completed_event_ids ?? [])
  const plannedStatus = plannedEvent
    ? getPlannedEventStatus({
        index: plannedEventIndex,
        nextEventIndex: runQuery.data?.season_state.next_event_index ?? 0,
        completedEventIds,
        eventId: plannedEvent.event_id
      })
    : null
  const relatedRankingSnapshots = (rankingSnapshotsQuery.data?.snapshots ?? []).filter(
    (snapshot) => snapshot.source_event_id === eventId
  )
  const relatedRaceSnapshots = (raceSnapshotsQuery.data?.snapshots ?? []).filter((snapshot) => snapshot.source_event_id === eventId)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Event detail"
        runId={runId}
        subtitle="Inspect event metadata and raw event payload for a single history event."
      />

      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Status', value: eventQuery.data ? 'Loaded' : 'Pending' }
        ]}
      />

      <SectionCard title="Event context">
        <p>
          <Link to={`/runs/${runId}/calendar`}>Back to Season Calendar</Link>
          {' · '}
          <Link to={`/runs/${runId}/calendar/${encodeURIComponent(eventId)}`}>Open planned-event detail</Link>
          {' · '}
          <Link to={`/runs/${runId}/events`}>Back to events history</Link>
          {' · '}
          <Link to={`/runs/${runId}/activity`}>Open activity</Link>
        </p>
        <p>
          Previous:{' '}
          {previousEvent ? (
            <Link to={`/runs/${runId}/events/${encodeURIComponent(previousEvent.event_id)}`}>{previousEvent.event_id}</Link>
          ) : (
            <span>None</span>
          )}{' '}
          · Next:{' '}
          {nextEvent ? (
            <Link to={`/runs/${runId}/events/${encodeURIComponent(nextEvent.event_id)}`}>{nextEvent.event_id}</Link>
          ) : (
            <span>None</span>
          )}
        </p>
        <p>
          <Link to={`/runs/${runId}/events#event-${encodeURIComponent(eventId)}`}>Back to events history at this event</Link>
        </p>
      </SectionCard>

      {!eventId && (
        <SectionCard title="Event lookup">
          <EmptyState message="No event ID was provided in the URL." />
        </SectionCard>
      )}

      {eventId && (
        <>
          <SectionCard title="Event summary">
            {eventQuery.isLoading && <p className="status">Loading event details...</p>}
            {eventQuery.error && !isApiNotFound(eventQuery.error) && (
              <p className="error">Failed to load event detail: {formatApiError(eventQuery.error)}</p>
            )}
            {isApiNotFound(eventQuery.error) && (
              <EmptyState message={`Event ${eventId} was not found for this run.`} />
            )}
            {eventQuery.data && (
              <CompactSummaryCard
                items={[
                  { label: 'Event ID', value: eventQuery.data.event_id },
                  { label: 'Sequence', value: eventQuery.data.event_sequence },
                  { label: 'Season', value: eventQuery.data.season ?? '—' },
                  { label: 'Week', value: eventQuery.data.week ?? '—' },
                  { label: 'Template', value: eventQuery.data.template_id ?? '—' }
                ]}
              />
            )}
          </SectionCard>

          <SectionCard title="Planned-season context">
            {runQuery.isLoading && <p className="status">Loading planned season context...</p>}
            {runQuery.error && <p className="error">Failed to load planned season context: {formatApiError(runQuery.error)}</p>}
            {runQuery.data && !plannedEvent && (
              <EmptyState message={`Event ${eventId} is not present in this run's ordered season plan.`} />
            )}
            {plannedEvent && (
              <>
                <SummaryPills
                  items={[
                    { label: 'Planned status', value: plannedStatus ?? '—' },
                    { label: 'Plan position', value: `${plannedEventIndex + 1} of ${orderedEvents.length}` }
                  ]}
                />
                <CompactSummaryCard
                  items={[
                    { label: 'Season', value: plannedEvent.season },
                    { label: 'Week', value: plannedEvent.week },
                    { label: 'Tour', value: plannedEvent.tour },
                    { label: 'Category', value: plannedEvent.category },
                    { label: 'Template', value: plannedEvent.template_id }
                  ]}
                />
                <MetadataList
                  items={[
                    { label: 'Event ID', value: plannedEvent.event_id },
                    { label: 'Plan index', value: plannedEventIndex },
                    { label: 'Current next_event_index', value: runQuery.data?.season_state.next_event_index ?? '—' }
                  ]}
                />
                <p>
                  <Link to={`/runs/${runId}/calendar/${encodeURIComponent(eventId)}`}>Open planned-event detail page</Link>
                  {' · '}
                  <Link to={`/runs/${runId}/weeks/${plannedEvent.week}`}>Open week detail</Link>
                </p>
                <p>
                  Previous planned:{' '}
                  {previousPlannedEvent ? (
                    <Link to={`/runs/${runId}/calendar/${encodeURIComponent(previousPlannedEvent.event_id)}`}>
                      {previousPlannedEvent.event_id}
                    </Link>
                  ) : (
                    <span>None</span>
                  )}{' '}
                  · Next planned:{' '}
                  {nextPlannedEvent ? (
                    <Link to={`/runs/${runId}/calendar/${encodeURIComponent(nextPlannedEvent.event_id)}`}>
                      {nextPlannedEvent.event_id}
                    </Link>
                  ) : (
                    <span>None</span>
                  )}
                </p>
              </>
            )}
          </SectionCard>

          <SectionCard title="Related artifacts">
            {rankingSnapshotsQuery.error ? (
              <p className="error">Failed to load ranking snapshots: {formatApiError(rankingSnapshotsQuery.error)}</p>
            ) : null}
            {raceSnapshotsQuery.error ? (
              <p className="error">Failed to load race snapshots: {formatApiError(raceSnapshotsQuery.error)}</p>
            ) : null}
            {!rankingSnapshotsQuery.error && !raceSnapshotsQuery.error && (
              <MetadataList
                items={[
                  {
                    label: 'Ranking snapshots',
                    value:
                      relatedRankingSnapshots.length > 0 ? (
                        <ul className="item-list">
                          {relatedRankingSnapshots.map((snapshot) => (
                            <li key={`ranking-${snapshot.snapshot_sequence}`}>
                              <Link to={`/runs/${runId}/snapshots/ranking/${snapshot.snapshot_sequence}`}>
                                Ranking snapshot #{snapshot.snapshot_sequence}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        'None linked to this event.'
                      )
                  },
                  {
                    label: 'Race snapshots',
                    value:
                      relatedRaceSnapshots.length > 0 ? (
                        <ul className="item-list">
                          {relatedRaceSnapshots.map((snapshot) => (
                            <li key={`race-${snapshot.snapshot_sequence}`}>
                              <Link to={`/runs/${runId}/snapshots/race/${snapshot.snapshot_sequence}`}>
                                Race snapshot #{snapshot.snapshot_sequence}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        'None linked to this event.'
                      )
                  }
                ]}
              />
            )}
          </SectionCard>

          <SectionCard title="Raw event payload">
            {eventQuery.data && (
              <JsonPayloadBlock
                title="Event record"
                emptyText="No event data is available for this event."
                payload={eventQuery.data}
              />
            )}
          </SectionCard>
        </>
      )}
    </section>
  )
}

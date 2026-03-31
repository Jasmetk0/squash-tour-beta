import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { getEvent, listEvents } from '../api/client'
import { JsonPayloadBlock, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function EventsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)

  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const events = eventsQuery.data?.events ?? []

  useEffect(() => {
    if (!events.length) {
      setSelectedEventId(null)
      return
    }

    if (!selectedEventId || !events.some((event) => event.event_id === selectedEventId)) {
      setSelectedEventId(events[0].event_id)
    }
  }, [events, selectedEventId])

  const selectedEvent = events.find((event) => event.event_id === selectedEventId) ?? null

  const eventDetailQuery = useQuery({
    queryKey: ['event', runId, selectedEventId],
    queryFn: () => getEvent(runId, selectedEventId ?? ''),
    enabled: Boolean(runId && selectedEventId)
  })

  return (
    <section className="panel">
      <RunScopedHeader title="Events history" runId={runId} />

      <SectionCard title="Event timeline">
        {eventsQuery.isLoading && <p className="status">Loading events history...</p>}
        {eventsQuery.error && <p className="error">Failed to load events history: {formatApiError(eventsQuery.error)}</p>}
        {!eventsQuery.isLoading && !eventsQuery.error && events.length === 0 && (
          <p className="status">No events are available for this run yet.</p>
        )}

        {events.length > 0 && (
          <ul className="item-list">
            {events.map((event) => (
              <li key={event.event_id}>
                <button className="linkish" onClick={() => setSelectedEventId(event.event_id)}>
                  {event.event_sequence}. {event.event_id}
                </button>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Selected event detail">
        {selectedEvent ? (
          <>
            <dl className="kv-grid">
              <div>
                <dt>Event ID</dt>
                <dd>{selectedEvent.event_id}</dd>
              </div>
              <div>
                <dt>Sequence</dt>
                <dd>{selectedEvent.event_sequence}</dd>
              </div>
              <div>
                <dt>Season</dt>
                <dd>{selectedEvent.season ?? '—'}</dd>
              </div>
              <div>
                <dt>Week</dt>
                <dd>{selectedEvent.week ?? '—'}</dd>
              </div>
            </dl>

            {eventDetailQuery.isLoading && <p className="status">Loading selected event payload...</p>}
            {eventDetailQuery.error && (
              <p className="error">Failed to load selected event payload: {formatApiError(eventDetailQuery.error)}</p>
            )}
            {eventDetailQuery.data && (
              <JsonPayloadBlock
                title="Event payload"
                emptyText="No event payload is available for this item."
                payload={eventDetailQuery.data}
              />
            )}
          </>
        ) : (
          <p className="status">Select an event to inspect details.</p>
        )}
      </SectionCard>
    </section>
  )
}

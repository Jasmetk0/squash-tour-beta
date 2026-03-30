import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { getEvent, listEvents } from '../api/client'

export function EventsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)

  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const eventDetailQuery = useQuery({
    queryKey: ['event', runId, selectedEventId],
    queryFn: () => getEvent(runId, selectedEventId ?? ''),
    enabled: Boolean(runId && selectedEventId)
  })

  return (
    <section className="panel">
      <h2>Events history</h2>
      {eventsQuery.error && <p className="error">Failed to load events: {String(eventsQuery.error)}</p>}
      <ul className="item-list">
        {eventsQuery.data?.events.map((event) => (
          <li key={event.event_id}>
            <button className="linkish" onClick={() => setSelectedEventId(event.event_id)}>
              #{event.event_sequence} · {event.event_id}
            </button>
          </li>
        ))}
      </ul>

      {eventDetailQuery.data && (
        <>
          <h3>Event detail</h3>
          <pre className="json-block">{JSON.stringify(eventDetailQuery.data, null, 2)}</pre>
        </>
      )}
    </section>
  )
}

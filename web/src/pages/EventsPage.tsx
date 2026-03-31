import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { getEvent, listEvents } from '../api/client'
import { CurrentContextStrip, EmptyState, JsonPayloadBlock, MetadataList, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import { SelectableHistoryList } from '../components/SelectableHistoryList'
import { formatApiError } from '../utils/apiErrors'

export function EventsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const requestedEventId = searchParams.get('selectedEventId')

  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const events = eventsQuery.data?.events ?? []

  useEffect(() => {
    if (!events.length) {
      setSelectedEventId(null)
      return
    }

    if (requestedEventId && events.some((event) => event.event_id === requestedEventId)) {
      if (selectedEventId !== requestedEventId) {
        setSelectedEventId(requestedEventId)
      }
      return
    }

    if (!selectedEventId || !events.some((event) => event.event_id === selectedEventId)) {
      setSelectedEventId(events[0].event_id)
    }
  }, [events, requestedEventId, selectedEventId])

  const selectedEvent = events.find((event) => event.event_id === selectedEventId) ?? null

  const eventDetailQuery = useQuery({
    queryKey: ['event', runId, selectedEventId],
    queryFn: () => getEvent(runId, selectedEventId ?? ''),
    enabled: Boolean(runId && selectedEventId)
  })

  return (
    <section className="panel">
      <RunScopedHeader
        title="Events history"
        runId={runId}
        subtitle="Browse the event timeline and inspect payload details for each event."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Events', value: events.length },
          { label: 'Selected', value: selectedEvent?.event_id ?? 'None' }
        ]}
      />

      <SectionCard title="Event timeline">
        {eventsQuery.isLoading && <p className="status">Loading events history...</p>}
        {eventsQuery.error && <p className="error">Failed to load events history: {formatApiError(eventsQuery.error)}</p>}
        {!eventsQuery.isLoading && !eventsQuery.error && events.length === 0 && (
          <EmptyState message="No events are available for this run yet." />
        )}

        {events.length > 0 && (
          <SelectableHistoryList
            items={events}
            getKey={(event) => event.event_id}
            getLabel={(event) => `${event.event_sequence}. ${event.event_id}`}
            getSubLabel={(event) => (event.season != null && event.week != null ? `S${event.season} / W${event.week}` : undefined)}
            isSelected={(event) => event.event_id === selectedEventId}
            onSelect={(event) => {
              setSelectedEventId(event.event_id)
              setSearchParams((current) => {
                const next = new URLSearchParams(current)
                next.set('selectedEventId', event.event_id)
                return next
              })
            }}
            ariaLabel="Events history list"
          />
        )}
      </SectionCard>

      <SectionCard title="Selected event detail">
        {selectedEvent ? (
          <>
            <MetadataList
              items={[
                { label: 'Event ID', value: selectedEvent.event_id },
                { label: 'Sequence', value: selectedEvent.event_sequence },
                { label: 'Season', value: selectedEvent.season ?? '—' },
                { label: 'Week', value: selectedEvent.week ?? '—' }
              ]}
            />

            {eventDetailQuery.isLoading && <p className="status">Loading selected event payload...</p>}
            {eventDetailQuery.error && (
              <p className="error">Failed to load selected event payload: {formatApiError(eventDetailQuery.error)}</p>
            )}
            {eventDetailQuery.data && (
              <>
                <p>
                  <Link to={`/runs/${runId}/events/${selectedEvent.event_id}`}>Open dedicated event detail page</Link>
                </p>
                <JsonPayloadBlock
                  title="Event payload"
                  emptyText="No event payload is available for this item."
                  payload={eventDetailQuery.data}
                />
              </>
            )}
          </>
        ) : (
          <EmptyState message="Select an event to inspect details." />
        )}
      </SectionCard>
    </section>
  )
}

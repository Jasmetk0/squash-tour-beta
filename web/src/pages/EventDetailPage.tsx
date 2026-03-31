import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getEvent } from '../api/client'
import { CompactSummaryCard, CurrentContextStrip, EmptyState, JsonPayloadBlock, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

export function EventDetailPage(): JSX.Element {
  const { runId = '', eventId = '' } = useParams()

  const eventQuery = useQuery({
    queryKey: ['event', runId, eventId],
    queryFn: () => getEvent(runId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })

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
          <Link to={`/runs/${runId}/events`}>Back to events history</Link>
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

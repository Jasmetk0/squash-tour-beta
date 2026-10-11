import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { getEvent, getRun, listEvents } from '../api/client'
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
import { SelectableHistoryList } from '../components/SelectableHistoryList'
import { formatApiError } from '../utils/apiErrors'

export function EventsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [weekFilter, setWeekFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [textFilter, setTextFilter] = useState('')
  const requestedEventId = searchParams.get('selectedEventId')

  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const events = eventsQuery.data?.events ?? []

  const orderedEventContext = useMemo(() => {
    const map = new Map<string, { week: number; tour: string; category: string; templateId: string; planPosition: number }>()
    const orderedEvents = runQuery.data?.season_state.ordered_events ?? []

    orderedEvents.forEach((event, index) => {
      map.set(event.event_id, {
        week: event.week,
        tour: event.tour,
        category: event.category,
        templateId: event.template_id,
        planPosition: index
      })
    })

    return map
  }, [runQuery.data?.season_state.ordered_events])

  const normalizedTextFilter = textFilter.trim().toLowerCase()
  const filteredEvents = events.filter((event) => {
    const plannedContext = orderedEventContext.get(event.event_id)
    const effectiveWeek = event.week ?? plannedContext?.week ?? null
    const weekMatches = weekFilter ? String(effectiveWeek) === weekFilter : true
    const categoryMatches = categoryFilter ? plannedContext?.category === categoryFilter : true
    const textMatches = normalizedTextFilter
      ? event.event_id.toLowerCase().includes(normalizedTextFilter) ||
        (event.template_id?.toLowerCase().includes(normalizedTextFilter) ?? false) ||
        (plannedContext?.templateId.toLowerCase().includes(normalizedTextFilter) ?? false)
      : true

    return weekMatches && categoryMatches && textMatches
  })

  const weekOptions = useMemo(() => {
    const values = new Set<string>()

    events.forEach((event) => {
      const plannedContext = orderedEventContext.get(event.event_id)
      const effectiveWeek = event.week ?? plannedContext?.week ?? null
      if (effectiveWeek != null) {
        values.add(String(effectiveWeek))
      }
    })

    return Array.from(values)
  }, [events, orderedEventContext])

  const categoryOptions = useMemo(() => {
    const values = new Set<string>()

    events.forEach((event) => {
      const category = orderedEventContext.get(event.event_id)?.category
      if (category) {
        values.add(category)
      }
    })

    return Array.from(values)
  }, [events, orderedEventContext])

  useEffect(() => {
    if (!filteredEvents.length) {
      setSelectedEventId(null)
      return
    }

    if (requestedEventId && filteredEvents.some((event) => event.event_id === requestedEventId)) {
      if (selectedEventId !== requestedEventId) {
        setSelectedEventId(requestedEventId)
      }
      return
    }

    if (!selectedEventId || !filteredEvents.some((event) => event.event_id === selectedEventId)) {
      setSelectedEventId(filteredEvents[0].event_id)
    }
  }, [filteredEvents, requestedEventId, selectedEventId])

  const selectedEvent = filteredEvents.find((event) => event.event_id === selectedEventId) ?? null
  const selectedEventPlanContext = selectedEvent ? orderedEventContext.get(selectedEvent.event_id) : undefined
  const selectedEventWeek = selectedEvent ? selectedEvent.week ?? selectedEventPlanContext?.week ?? null : null

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
        subtitle="Browse persisted event history, map events back to the planned season, and jump to linked read-only detail views."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Persisted events', value: events.length },
          { label: 'Matching filters', value: filteredEvents.length },
          { label: 'Selected', value: selectedEvent?.event_id ?? 'None' }
        ]}
      />

      <SectionCard title="Filters">
        <div className="grid">
          <label>
            Week
            <select aria-label="Filter events by week" value={weekFilter} onChange={(event) => setWeekFilter(event.target.value)}>
              <option value="">All weeks</option>
              {weekOptions.map((week) => (
                <option key={week} value={week}>
                  W{week}
                </option>
              ))}
            </select>
          </label>
          <label>
            Category
            <select
              aria-label="Filter events by category"
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="">All categories</option>
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label>
            Event/template text
            <input
              aria-label="Filter events by event or template"
              value={textFilter}
              onChange={(event) => setTextFilter(event.target.value)}
              placeholder="Event ID or template ID"
            />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Event timeline">
        {eventsQuery.isLoading && <p className="status">Loading events history...</p>}
        {eventsQuery.error && <p className="error">Failed to load events history: {formatApiError(eventsQuery.error)}</p>}
        {!eventsQuery.isLoading && !eventsQuery.error && events.length === 0 && (
          <EmptyState message="No events are available for this run yet." />
        )}
        {!eventsQuery.isLoading && !eventsQuery.error && events.length > 0 && filteredEvents.length === 0 && (
          <EmptyState message="No persisted events match the current filters." />
        )}

        {filteredEvents.length > 0 && (
          <SelectableHistoryList
            items={filteredEvents}
            getKey={(event) => event.event_id}
            getLabel={(event) => `${event.event_sequence}. ${event.event_id}`}
            getSubLabel={(event) => {
              const plannedContext = orderedEventContext.get(event.event_id)
              const week = event.week ?? plannedContext?.week

              if (!plannedContext && week == null) {
                return 'No week or ordered-plan context'
              }

              const segments = []
              if (week != null) segments.push(`W${week}`)
              if (plannedContext) {
                segments.push(`Plan #${plannedContext.planPosition}`)
                segments.push(plannedContext.category)
                segments.push(plannedContext.tour)
              } else {
                segments.push('No ordered-plan match')
              }

              return segments.join(' · ')
            }}
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
                { label: 'Week', value: selectedEventWeek != null ? selectedEventWeek : '—' },
                { label: 'Plan position', value: selectedEventPlanContext ? selectedEventPlanContext.planPosition : 'No ordered-plan match' },
                { label: 'Planned tour', value: selectedEventPlanContext?.tour ?? 'No ordered-plan match' },
                { label: 'Planned category', value: selectedEventPlanContext?.category ?? 'No ordered-plan match' },
                { label: 'Planned template', value: selectedEventPlanContext?.templateId ?? selectedEvent.template_id ?? '—' }
              ]}
            />
            <SummaryPills
              items={[
                { label: 'Week context', value: selectedEventWeek != null ? `W${selectedEventWeek}` : 'Not available' },
                { label: 'Planned context', value: selectedEventPlanContext ? 'Matched' : 'No ordered-plan match' }
              ]}
            />
            <CompactSummaryCard
              items={[
                {
                  label: 'Persisted detail',
                  value: <Link to={`/runs/${runId}/events/${selectedEvent.event_id}`}>Open dedicated event detail page</Link>
                },
                {
                  label: 'Planned event detail',
                  value: selectedEventPlanContext ? (
                    <Link to={`/runs/${runId}/calendar/${selectedEvent.event_id}`}>Open planned-event detail page</Link>
                  ) : (
                    'No ordered-plan match for this persisted event.'
                  )
                },
                {
                  label: 'Week detail',
                  value:
                    selectedEventWeek != null ? (
                      <Link to={`/runs/${runId}/weeks/${selectedEventWeek}`}>Open week detail page (W{selectedEventWeek})</Link>
                    ) : (
                      'No week context available for this persisted event.'
                    )
                },
                {
                  label: 'Season calendar',
                  value: <Link to={`/runs/${runId}/calendar`}>Open season calendar browser</Link>
                }
              ]}
            />

            {runQuery.error ? <p className="error">Failed to load planned season context: {formatApiError(runQuery.error)}</p> : null}
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
          <EmptyState message="Select an event to inspect details." />
        )}
      </SectionCard>
    </section>
  )
}

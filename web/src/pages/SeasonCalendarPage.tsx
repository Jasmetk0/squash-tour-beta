import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getRun, listEvents } from '../api/client'
import { useAdminViewedSeasonState } from '../admin/useAdminViewedSeasonState'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { getPlannedEventStatus, getWeeksInSeasonOrder } from './plannedEventUtils'

export function SeasonCalendarPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [weekFilter, setWeekFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [textFilter, setTextFilter] = useState('')
  const viewed = useAdminViewedSeasonState()

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) && !viewed.historical })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) && !viewed.historical })

  const seasonState = viewed.historical ? viewed.seasonState : runQuery.data?.season_state
  const orderedEvents = seasonState?.ordered_events ?? []
  const nextEventIndex = seasonState?.next_event_index ?? 0
  const completedEventIds = useMemo(
    () => new Set(seasonState?.completed_event_ids ?? []),
    [seasonState?.completed_event_ids]
  )
  const persistedEventIds = useMemo(() => new Set((eventsQuery.data?.events ?? []).map((event) => event.event_id)), [eventsQuery.data?.events])

  const weekOptions = useMemo(() => {
    return getWeeksInSeasonOrder(orderedEvents)
  }, [orderedEvents])
  const categoryOptions = useMemo(() => {
    const categories = Array.from(new Set(orderedEvents.map((event) => event.category)))
    return categories
  }, [orderedEvents])

  const normalizedTextFilter = textFilter.trim().toLowerCase()
  const filteredEvents = orderedEvents.filter((event) => {
    const weekMatches = weekFilter ? String(event.week) === weekFilter : true
    const categoryMatches = categoryFilter ? event.category === categoryFilter : true
    const textMatches = normalizedTextFilter
      ? event.event_id.toLowerCase().includes(normalizedTextFilter) || event.template_id.toLowerCase().includes(normalizedTextFilter)
      : true
    return weekMatches && categoryMatches && textMatches
  })

  const completedCount = completedEventIds.size
  const totalCount = orderedEvents.length
  const nextEvent = orderedEvents[nextEventIndex] ?? null

  if (viewed.historical && viewed.unavailable) return <section className="panel"><h1>Historical calendar is not available for this checkpoint.</h1><p>Checkpoint: {viewed.time?.viewCheckpointId} · Kind: {viewed.time?.selectedCheckpoint?.kind ?? 'unknown'}</p><button onClick={() => viewed.time?.selectPresent()}>Return to Present</button> <Link to={`/admin/runs/${encodeURIComponent(runId)}`}>Open Run Home</Link></section>
  if (viewed.historical && viewed.query.isLoading) return <section className="panel"><p className="status">Loading historical calendar...</p></section>

  return (
    <section className="panel">
      <RunScopedHeader
        title="Season calendar"
        runId={runId}
        subtitle="Read-only ordered event plan for this run, including current position and completion state."
      />
      <CurrentContextStrip
        items={[
          { label: 'Time', value: viewed.historical ? 'Past' : 'Present' },
          { label: 'Checkpoint', value: viewed.time?.viewCheckpointId ?? '—' },
          { label: 'Season', value: seasonState?.season ?? '—' },
          { label: 'Next event index', value: nextEventIndex },
          { label: 'Completed', value: `${completedCount}/${totalCount}` }
        ]}
      />

      <SectionCard title="Season progress summary">
        {!viewed.historical && runQuery.isLoading ? <p className="status">Loading season calendar...</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {seasonState ? (
          <>
            <SummaryPills
              items={[
                { label: 'Total events', value: totalCount },
                { label: 'Completed', value: completedCount },
                { label: 'Next event index', value: nextEventIndex },
                { label: 'Remaining', value: Math.max(totalCount - completedCount, 0) }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: runId },
                { label: 'Season', value: seasonState.season },
                { label: 'Next event', value: nextEvent?.event_id ?? 'None (season complete)' }
              ]}
            />
            <p>
              <Link to={`/runs/${runId}`}>Back to Run Detail</Link>
              {' · '}
              {!viewed.historical ? <Link to={`/runs/${runId}/events`}>Open persisted Events history</Link> : <span>Persisted historical event detail is not available in this phase.</span>}
              {' · '}
              <Link to={`/runs/${runId}/activity`}>Open run Activity</Link>
            </p>
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Filters">
        <div className="grid">
          <label>
            Week
            <select aria-label="Filter by week" value={weekFilter} onChange={(event) => setWeekFilter(event.target.value)}>
              <option value="">All weeks</option>
              {weekOptions.map((week) => (
                <option key={week} value={String(week)}>
                  W{week}
                </option>
              ))}
            </select>
          </label>
          <label>
            Category
            <select aria-label="Filter by category" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
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
              aria-label="Filter by event or template"
              value={textFilter}
              onChange={(event) => setTextFilter(event.target.value)}
              placeholder="Event ID or template ID"
            />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Ordered season calendar">
        {seasonState && filteredEvents.length === 0 ? <EmptyState message="No calendar events match the current filters." /> : null}
        {seasonState && filteredEvents.length > 0 ? (
          <ol className="item-list" aria-label="Season calendar ordered list">
            {filteredEvents.map((event) => {
              const absoluteIndex = orderedEvents.indexOf(event)
              const status = getPlannedEventStatus({
                index: absoluteIndex,
                nextEventIndex,
                completedEventIds,
                eventId: event.event_id
              })
              const hasPersistedDetail = persistedEventIds.has(event.event_id)

              return (
                <li key={event.event_id}>
                  <MetadataList
                    items={[
                      { label: '#', value: absoluteIndex },
                      { label: 'Status', value: status },
                      {
                        label: 'Event ID',
                        value: (
                          <>
                            <Link to={`/runs/${runId}/calendar/${encodeURIComponent(event.event_id)}`}>{event.event_id}</Link>
                            {!viewed.historical && status === 'Completed' && hasPersistedDetail ? (
                              <>
                                {' '}·{' '}
                                <Link to={`/runs/${runId}/events/${encodeURIComponent(event.event_id)}`}>history</Link>
                              </>
                            ) : null}
                          </>
                        )
                      },
                      { label: 'Season', value: event.season },
                      { label: 'Week', value: <Link to={`/runs/${runId}/weeks/${event.week}`}>W{event.week}</Link> },
                      { label: 'Tour', value: event.tour },
                      { label: 'Category', value: event.category },
                      { label: 'Template', value: event.template_id }
                    ]}
                  />
                </li>
              )
            })}
          </ol>
        ) : null}
        {!viewed.historical && eventsQuery.error ? <p className="error">Failed to load persisted events: {formatApiError(eventsQuery.error)}</p> : null}
      </SectionCard>

      {nextEvent ? (
        <SectionCard title="Next event focus">
          <MetadataList
            items={[
              {
                label: 'Event ID',
                value: <Link to={`/runs/${runId}/calendar/${encodeURIComponent(nextEvent.event_id)}`}>{nextEvent.event_id}</Link>
              },
              { label: 'Season', value: nextEvent.season },
              { label: 'Week', value: nextEvent.week },
              { label: 'Tour', value: nextEvent.tour },
              { label: 'Category', value: nextEvent.category },
              { label: 'Template', value: nextEvent.template_id }
            ]}
          />
        </SectionCard>
      ) : null}
    </section>
  )
}

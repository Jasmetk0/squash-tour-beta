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

import { useHistoryText } from './runHistoryText'
export function EventsPage(): JSX.Element {
  const t = useHistoryText()
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [weekFilter, setWeekFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [textFilter, setTextFilter] = useState('')
  const requestedEventId = searchParams.get('selectedEventId')

  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const eventsMismatch = Boolean(eventsQuery.data?.run_id && eventsQuery.data.run_id !== runId)
  const events = eventsMismatch ? [] : eventsQuery.data?.events ?? []

  const runMismatch = Boolean(runQuery.data?.run.run_id && runQuery.data.run.run_id !== runId)
  const orderedEventContext = useMemo(() => {
    const map = new Map<string, { week: number; tour: string; category: string; templateId: string; planPosition: number }>()
    const orderedEvents = runQuery.data?.run.run_id === runId ? runQuery.data.season_state.ordered_events : []

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
  }, [runId, runQuery.data])

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

  const eventDetailMismatch = Boolean(eventDetailQuery.data && selectedEvent && eventDetailQuery.data.event_id !== selectedEvent.event_id)

  return (
    <section className="panel">
      <RunScopedHeader
        title={t('Events history')}
        runId={runId}
        subtitle={t('Browse persisted event history, map events back to the planned season, and jump to linked read-only detail views.')}
      />
      <p className="status">{t('Stored legacy SimulationRun history. This view does not verify Product Run Saved Revision authority.')}</p>
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          { label: t('Persisted events'), value: events.length },
          { label: t('Matching filters'), value: filteredEvents.length },
          { label: t('Selected'), value: selectedEvent?.event_id ?? t('None') }
        ]}
      />

      <SectionCard title={t('Filters')}>
        <div className="grid">
          <label>
            {t('Week')}
            <select data-run-navigation-readonly aria-label={t('Filter events by week')} value={weekFilter} onChange={(event) => setWeekFilter(event.target.value)}>
              <option value="">{t('All weeks')}</option>
              {weekOptions.map((week) => (
                <option key={week} value={week}>
                  W{week}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('Category')}
            <select data-run-navigation-readonly
              aria-label={t('Filter events by category')}
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="">{t('All categories')}</option>
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('Event/template text')}
            <input data-run-navigation-readonly
              aria-label={t('Filter events by event or template')}
              value={textFilter}
              onChange={(event) => setTextFilter(event.target.value)}
              placeholder={t('Event ID or template ID')}
            />
          </label>
        </div>
        <button type="button" onClick={() => { setWeekFilter(''); setCategoryFilter(''); setTextFilter('') }}>{t('Reset filters')}</button>
      </SectionCard>

      <SectionCard title={t('Event timeline')}>
        {eventsMismatch && <p role="alert" className="error">{t('Events response belongs to another Run; its records are hidden.')}</p>}
        <button type="button" onClick={() => void eventsQuery.refetch()}>{t('Refresh read-only data')}</button>
        {eventsQuery.isLoading && <p className="status">{t('Loading events history...')}</p>}
        {eventsQuery.error && <p className="error">{t('Failed to load events history')}: {formatApiError(eventsQuery.error)}</p>}
        {!eventsQuery.isLoading && !eventsQuery.error && !eventsMismatch && events.length === 0 && (
          <EmptyState message={t('No events are available for this run yet.')} />
        )}
        {!eventsQuery.isLoading && !eventsQuery.error && events.length > 0 && filteredEvents.length === 0 && (
          <EmptyState message={t('No persisted events match the current filters.')} />
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
                return t('No week or ordered-plan context')
              }

              const segments = []
              if (week != null) segments.push(`W${week}`)
              if (plannedContext) {
                segments.push(`${t('Plan')} #${plannedContext.planPosition}`)
                segments.push(plannedContext.category)
                segments.push(plannedContext.tour)
              } else {
                segments.push(t('No ordered-plan match'))
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
            ariaLabel={t('Events history list')}
          />
        )}
      </SectionCard>

      <SectionCard title={t('Selected event detail')}>
        {runMismatch && <p role="alert" className="error">{t('Planned context belongs to another Run.')}</p>}
        {selectedEvent ? (
          <>
            <MetadataList
              items={[
                { label: t('Event ID'), value: selectedEvent.event_id },
                { label: t('Sequence'), value: selectedEvent.event_sequence },
                { label: t('Persisted tournament result'), value: selectedEvent.tournament_result != null ? t('Recorded tournament result') : t('No tournament result evidenced') },
                { label: t('Season'), value: selectedEvent.season ?? '—' },
                { label: t('Week'), value: selectedEventWeek != null ? selectedEventWeek : '—' },
                { label: t('Plan position'), value: selectedEventPlanContext ? selectedEventPlanContext.planPosition : t('No ordered-plan match') },
                { label: t('Planned tour'), value: selectedEventPlanContext?.tour ?? t('No ordered-plan match') },
                { label: t('Planned category'), value: selectedEventPlanContext?.category ?? t('No ordered-plan match') },
                { label: t('Planned template'), value: selectedEventPlanContext?.templateId ?? selectedEvent.template_id ?? '—' }
              ]}
            />
            <SummaryPills
              items={[
                { label: t('Week context'), value: selectedEventWeek != null ? `W${selectedEventWeek}` : t('Not available') },
                { label: t('Planned context'), value: selectedEventPlanContext ? t('Matched') : t('No ordered-plan match') }
              ]}
            />
            <CompactSummaryCard
              items={[
                {
                  label: t('Persisted detail'),
                  value: <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(selectedEvent.event_id)}`}>{t('Open dedicated event detail page')}</Link>
                },
                {
                  label: t('Planned event detail'),
                  value: selectedEventPlanContext ? (
                    <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(selectedEvent.event_id)}`}>{t('Open planned-event detail page')}</Link>
                  ) : (
                    t('No ordered-plan match for this persisted event.')
                  )
                },
                {
                  label: t('Week detail'),
                  value:
                    selectedEventWeek != null ? (
                      <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${selectedEventWeek}`}>{t('Open week detail page')} (W{selectedEventWeek})</Link>
                    ) : (
                      t('No week context available for this persisted event.')
                    )
                },
                {
                  label: t('Season calendar'),
                  value: <Link to={`/runs/${encodeURIComponent(runId)}/calendar`}>{t('Open season calendar browser')}</Link>
                }
              ]}
            />

            {runQuery.error ? <p className="error">{t('Failed to load planned season context')}: {formatApiError(runQuery.error)}</p> : null}
            {eventDetailMismatch && <p role="alert" className="error">{t('Event detail does not match the selected event; its payload is hidden.')}</p>}
            <button type="button" onClick={() => void eventDetailQuery.refetch()} disabled={!selectedEvent}>{t('Refresh read-only data')}</button>
            {eventDetailQuery.isLoading && <p className="status">{t('Loading selected event payload...')}</p>}
            {eventDetailQuery.error && (
              <p className="error">{t('Failed to load selected event payload')}: {formatApiError(eventDetailQuery.error)}</p>
            )}
            {eventDetailQuery.data && !eventDetailMismatch && (
              <JsonPayloadBlock
                title={t('Event payload')}
                emptyText={t('No event payload is available for this item.')}
                payload={eventDetailQuery.data}
              />
            )}
          </>
        ) : (
          <EmptyState message={t('Select an event to inspect details.')} />
        )}
      </SectionCard>
    </section>
  )
}

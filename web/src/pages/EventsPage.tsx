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
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

import { useHistoryText } from './runHistoryText'
export function EventsPage(): JSX.Element {
  const t = useHistoryText()
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedEventSequence, setSelectedEventSequence] = useState<number | null>(null)
  const [weekFilter, setWeekFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [textFilter, setTextFilter] = useState('')
  const requestedEventId = searchParams.get('selectedEventId')
  const requestedSequenceText = searchParams.get('selectedEventSequence') ?? ''
  const requestedSequence = /^\d+$/.test(requestedSequenceText) ? Number(requestedSequenceText) : NaN
  const hasRequestedSequence = Number.isSafeInteger(requestedSequence) && requestedSequence > 0

  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const eventsMismatch = Boolean(eventsQuery.data?.run_id && eventsQuery.data.run_id !== runId)
  const events = eventsMismatch || eventsQuery.error ? [] : eventsQuery.data?.events ?? []

  const runMismatch = Boolean(runQuery.data?.run.run_id && runQuery.data.run.run_id !== runId)
  const planSeasonMismatch = Boolean(runQuery.data && runQuery.data.run.run_id === runId &&
    runQuery.data.season_state.season != null &&
    runQuery.data.season_state.season !== runQuery.data.run.season)
  const planUnavailable = runQuery.isLoading || Boolean(runQuery.error) || !runQuery.data || runMismatch || planSeasonMismatch
  const orderedEventContext = useMemo(() => {
    const map = new Map<string, { season: number; week: number; tour: string; category: string; templateId: string; planPosition: number }>()
    const orderedEvents = !planUnavailable ? runQuery.data?.season_state.ordered_events ?? [] : []

    orderedEvents.forEach((event, index) => {
      if (event.season !== runQuery.data?.season_state.season) return
      map.set(event.event_id, {
        season: event.season,
        week: event.week,
        tour: event.tour,
        category: event.category,
        templateId: event.template_id,
        planPosition: index + 1
      })
    })

    return map
  }, [runId, runQuery.data, planUnavailable])
  // Persisted event IDs may be reused across seasons; join only matching seasons.
  const getEventPlanContext = (event: (typeof events)[number]) => {
    const context = orderedEventContext.get(event.event_id)
    return context && (event.season == null || event.season === context.season) ? context : undefined
  }

  const normalizedTextFilter = textFilter.trim().toLowerCase()
  const filteredEvents = events.filter((event) => {
    const plannedContext = getEventPlanContext(event)
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
      const plannedContext = getEventPlanContext(event)
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
      const category = getEventPlanContext(event)?.category
      if (category) {
        values.add(category)
      }
    })

    return Array.from(values)
  }, [events, orderedEventContext])

  // event_id can be reused across seasons. Persisted sequence is the stable
  // selection identity; legacy ?selectedEventId links remain readable.
  useEffect(() => {
    if (!filteredEvents.length) {
      setSelectedEventSequence(null)
      return
    }
    const requestedBySequence = hasRequestedSequence
      ? filteredEvents.find((event) =>
          event.event_sequence === requestedSequence &&
          (!requestedEventId || event.event_id === requestedEventId))
      : undefined
    const requestedByLegacyId = requestedEventId
      ? filteredEvents.find((event) => event.event_id === requestedEventId)
      : undefined
    const remembered = filteredEvents.find((event) => event.event_sequence === selectedEventSequence)
    const next = requestedBySequence ?? requestedByLegacyId ?? remembered ?? filteredEvents[0]
    if (selectedEventSequence !== next.event_sequence) {
      setSelectedEventSequence(next.event_sequence)
    }
  }, [filteredEvents, hasRequestedSequence, requestedSequence, requestedEventId, selectedEventSequence])

  const selectedEvent = filteredEvents.find((event) => event.event_sequence === selectedEventSequence) ?? null
  const ambiguousEventId = Boolean(selectedEvent &&
    events.filter((event) => event.event_id === selectedEvent.event_id).length > 1)
  const selectedEventPlanContext = selectedEvent ? getEventPlanContext(selectedEvent) : undefined
  const selectedEventWeek = selectedEvent ? selectedEvent.week ?? selectedEventPlanContext?.week ?? null : null
  const weekLinkAvailable = selectedEvent && !planUnavailable &&
    selectedEvent.season != null && selectedEvent.season === runQuery.data?.run.season

  const eventDetailQuery = useQuery({
    queryKey: ['event', runId, selectedEvent?.event_id, selectedEvent?.event_sequence],
    queryFn: () => getEvent(runId, selectedEvent?.event_id ?? ''),
    enabled: Boolean(runId && selectedEvent)
  })

  // The list and detail may be read at different times. Do not present a
  // same-ID payload with contradictory stored sequence/season/week as evidence.
  const eventDetailMismatch = Boolean(eventDetailQuery.data && selectedEvent && (
    eventDetailQuery.data.event_id !== selectedEvent.event_id ||
    (ambiguousEventId && !Number.isSafeInteger(eventDetailQuery.data.event_sequence)) ||
    (Number.isSafeInteger(eventDetailQuery.data.event_sequence) && eventDetailQuery.data.event_sequence !== selectedEvent.event_sequence) ||
    (eventDetailQuery.data.season != null && selectedEvent.season != null && eventDetailQuery.data.season !== selectedEvent.season) ||
    (eventDetailQuery.data.week != null && selectedEvent.week != null && eventDetailQuery.data.week !== selectedEvent.week)
  ))

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
        {isApiNotFound(eventsQuery.error)
          ? <EmptyState message={t('Events history could not be found for this Run.')} />
          : eventsQuery.error && <p role="alert" className="error">{t('Failed to load events history')}: {formatApiError(eventsQuery.error)}</p>}
        {!eventsQuery.isLoading && !eventsQuery.error && !eventsMismatch && events.length === 0 && (
          <EmptyState message={t('No events are available for this run yet.')} />
        )}
        {!eventsQuery.isLoading && !eventsQuery.error && events.length > 0 && filteredEvents.length === 0 && (
          <EmptyState message={t('No persisted events match the current filters.')} />
        )}

        {filteredEvents.length > 0 && (
          <SelectableHistoryList
            items={filteredEvents}
            getKey={(event) => `${event.event_sequence}-${event.event_id}`}
            getLabel={(event) => `${event.event_sequence}. ${event.event_id}`}
            getSubLabel={(event) => {
              const plannedContext = getEventPlanContext(event)
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
            isSelected={(event) => event.event_sequence === selectedEventSequence}
            onSelect={(event) => {
              setSelectedEventSequence(event.event_sequence)
              setSearchParams((current) => {
                const next = new URLSearchParams(current)
                next.set('selectedEventId', event.event_id)
                next.set('selectedEventSequence', String(event.event_sequence))
                return next
              })
            }}
            ariaLabel={t('Events history list')}
          />
        )}
      </SectionCard>

      <SectionCard title={t('Selected event detail')}>
        {runMismatch && <p role="alert" className="error">{t('Planned context belongs to another Run.')}</p>}
        {planSeasonMismatch && <p role="alert" className="error">{t('Run season and ordered plan disagree. Planned links are unavailable.')}</p>}
        {selectedEvent ? (
          <>
            {ambiguousEventId && <p role="alert" className="error">{t('Event ID is reused in this Run. Use the selected sequence to identify the stored record; direct ID-only navigation is unavailable.')}</p>}
            <MetadataList
              items={[
                { label: t('Event ID'), value: selectedEvent.event_id },
                { label: t('Sequence'), value: selectedEvent.event_sequence },
                { label: t('Persisted tournament result'), value: selectedEvent.tournament_result != null ? t('Recorded tournament result') : t('No tournament result evidenced') },
                { label: t('Season'), value: selectedEvent.season ?? '—' },
                { label: t('Week'), value: selectedEventWeek != null ? selectedEventWeek : '—' },
                { label: t('Plan position'), value: selectedEventPlanContext ? selectedEventPlanContext.planPosition : planUnavailable ? t('Unavailable') : t('No ordered-plan match') },
                { label: t('Planned tour'), value: selectedEventPlanContext?.tour ?? (planUnavailable ? t('Unavailable') : t('No ordered-plan match')) },
                { label: t('Planned category'), value: selectedEventPlanContext?.category ?? (planUnavailable ? t('Unavailable') : t('No ordered-plan match')) },
                { label: t('Planned template'), value: selectedEventPlanContext?.templateId ?? selectedEvent.template_id ?? '—' }
              ]}
            />
            <SummaryPills
              items={[
                { label: t('Week context'), value: selectedEventWeek != null ? `W${selectedEventWeek}` : t('Not available') },
                { label: t('Planned context'), value: selectedEventPlanContext ? t('Matched') : planUnavailable ? t('Unavailable') : t('No ordered-plan match') }
              ]}
            />
            <CompactSummaryCard
              items={[
                {
                  label: t('Persisted detail'),
                  value: ambiguousEventId
                    ? t('Unavailable: the event ID identifies multiple stored records.')
                    : <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(selectedEvent.event_id)}`}>{t('Open dedicated event detail page')}</Link>
                },
                {
                  label: t('Planned event detail'),
                  value: selectedEventPlanContext ? (
                    <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(selectedEvent.event_id)}`}>{t('Open planned-event detail page')}</Link>
                  ) : (
                    planUnavailable ? t('Unavailable') : t('No ordered-plan match for this persisted event.')
                  )
                },
                {
                  label: t('Week detail'),
                  value:
                    selectedEventWeek != null && weekLinkAvailable ? (
                      <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${selectedEventWeek}`}>{t('Open week detail page')} (W{selectedEventWeek})</Link>
                    ) : (
                      !weekLinkAvailable ? t('Current-season week link unavailable for this historic event.') : t('No week context available for this persisted event.')
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
            {isApiNotFound(eventDetailQuery.error)
              ? <EmptyState message={t('Selected event detail is not found.')} />
              : eventDetailQuery.error && (
                <p role="alert" className="error">{t('Failed to load selected event payload')}: {formatApiError(eventDetailQuery.error)}</p>
              )}
            {eventDetailQuery.data && !eventDetailQuery.error && !eventDetailMismatch && (
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

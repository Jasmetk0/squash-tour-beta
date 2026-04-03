import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { assignEventWildcards, getEventWildcards, getRun, listEvents } from '../api/client'
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
import { getPlannedEventStatus } from './plannedEventUtils'

export function PlannedEventDetailPage(): JSX.Element {
  const { runId = '', eventId = '' } = useParams()
  const queryClient = useQueryClient()
  const [slotIndexInput, setSlotIndexInput] = useState('1')
  const [playerIdInput, setPlayerIdInput] = useState('')

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const eventsQuery = useQuery({
    queryKey: ['events', runId],
    queryFn: () => listEvents(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const wildcardsQuery = useQuery({
    queryKey: ['wildcards', runId, eventId],
    queryFn: () => getEventWildcards(runId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const wildcardMutation = useMutation({
    mutationFn: (values: { slotIndex: number; playerId: string }) =>
      assignEventWildcards(runId, eventId, {
        assignments: [{ slot_index: values.slotIndex, player_id: values.playerId }]
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['wildcards', runId, eventId] })
      setPlayerIdInput('')
    }
  })

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const nextEventIndex = runQuery.data?.season_state.next_event_index ?? 0
  const completedEventIds = new Set(runQuery.data?.season_state.completed_event_ids ?? [])
  const persistedEventIds = new Set((eventsQuery.data?.events ?? []).map((event) => event.event_id))

  const plannedEventIndex = orderedEvents.findIndex((event) => event.event_id === eventId)
  const plannedEvent = plannedEventIndex >= 0 ? orderedEvents[plannedEventIndex] : null
  const previousEvent = plannedEventIndex > 0 ? orderedEvents[plannedEventIndex - 1] : null
  const nextEvent = plannedEventIndex >= 0 && plannedEventIndex < orderedEvents.length - 1 ? orderedEvents[plannedEventIndex + 1] : null

  const status = plannedEvent
    ? getPlannedEventStatus({
        index: plannedEventIndex,
        nextEventIndex,
        completedEventIds,
        eventId: plannedEvent.event_id
      })
    : null

  const hasPersistedHistory = plannedEvent ? persistedEventIds.has(plannedEvent.event_id) : false

  function handleWildcardSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const slotIndex = Number(slotIndexInput)
    if (!Number.isFinite(slotIndex) || slotIndex < 1 || !playerIdInput.trim()) return
    wildcardMutation.mutate({ slotIndex, playerId: playerIdInput.trim() })
  }

  return (
    <section className="panel">
      <RunScopedHeader
        title="Planned event detail"
        runId={runId}
        subtitle="Read-only inspection route for a single event in this season's ordered plan."
      />

      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Season', value: runQuery.data?.season_state.season ?? '—' },
          { label: 'Planned event', value: eventId || 'unknown' }
        ]}
      />

      <SectionCard title="Navigation and context">
        <p>
          <Link to={`/runs/${runId}/calendar`}>Back to Season Calendar</Link>
          {' · '}
          {plannedEvent ? <Link to={`/runs/${runId}/weeks/${plannedEvent.week}`}>Open week detail</Link> : <span>Week detail unavailable</span>}
          {' · '}
          <Link to={`/runs/${runId}`}>Back to Run Detail</Link>
          {' · '}
          <Link to={`/runs/${runId}/events`}>Open Events history</Link>
        </p>
        {plannedEvent ? (
          <p>
            Previous:{' '}
            {previousEvent ? (
              <Link to={`/runs/${runId}/calendar/${encodeURIComponent(previousEvent.event_id)}`}>{previousEvent.event_id}</Link>
            ) : (
              <span>None</span>
            )}{' '}
            · Next:{' '}
            {nextEvent ? (
              <Link to={`/runs/${runId}/calendar/${encodeURIComponent(nextEvent.event_id)}`}>{nextEvent.event_id}</Link>
            ) : (
              <span>None</span>
            )}
          </p>
        ) : null}
      </SectionCard>

      <SectionCard title="Planned event summary">
        {runQuery.isLoading ? <p className="status">Loading planned event...</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {eventId && runQuery.data && !plannedEvent ? (
          <EmptyState message={`Event ${eventId} is not present in this run's ordered season plan.`} />
        ) : null}
        {!eventId ? <EmptyState message="No planned event ID was provided in the URL." /> : null}

        {plannedEvent ? (
          <>
            <SummaryPills
              items={[
                { label: 'Status', value: status ?? '—' },
                { label: 'Plan index', value: plannedEventIndex },
                { label: 'Plan size', value: orderedEvents.length }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Event ID', value: plannedEvent.event_id },
                { label: 'Season', value: plannedEvent.season },
                { label: 'Week', value: plannedEvent.week },
                { label: 'Tour', value: plannedEvent.tour },
                { label: 'Category', value: plannedEvent.category },
                { label: 'Template', value: plannedEvent.template_id }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      {plannedEvent ? (
        <SectionCard title="Season position and neighbors">
          <MetadataList
            items={[
              { label: 'Position', value: `${plannedEventIndex + 1} of ${orderedEvents.length}` },
              { label: 'Previous event', value: previousEvent?.event_id ?? 'None' },
              { label: 'Next event', value: nextEvent?.event_id ?? 'None' },
              { label: 'Current next_event_index', value: nextEventIndex }
            ]}
          />
        </SectionCard>
      ) : null}

      {plannedEvent ? (
        <SectionCard title="Status and persisted history">
          <MetadataList
            items={[
              { label: 'Planned status', value: status ?? '—' },
              { label: 'Completed in season state', value: completedEventIds.has(plannedEvent.event_id) ? 'Yes' : 'No' },
              { label: 'Persisted event record', value: hasPersistedHistory ? 'Available' : 'Not available' }
            ]}
          />
          {status === 'Completed' && hasPersistedHistory ? (
            <p>
              <Link to={`/runs/${runId}/events/${encodeURIComponent(plannedEvent.event_id)}`}>
                Inspect persisted event detail for {plannedEvent.event_id}
              </Link>
            </p>
          ) : null}
        </SectionCard>
      ) : null}

      {eventsQuery.error ? <p className="error">Failed to load persisted events: {formatApiError(eventsQuery.error)}</p> : null}

      {plannedEvent ? (
        <SectionCard title="Commissioner wildcards">
          {wildcardsQuery.isLoading ? <p className="status">Loading wildcard slots...</p> : null}
          {wildcardsQuery.error ? <p className="error">Failed to load wildcard state: {formatApiError(wildcardsQuery.error)}</p> : null}
          {wildcardsQuery.data ? (
            <>
              <MetadataList
                items={[
                  { label: 'Wildcard slots', value: wildcardsQuery.data.total_slots },
                  { label: 'Assignment allowed', value: wildcardsQuery.data.eligible ? 'Yes' : 'No' },
                  { label: 'Eligibility note', value: wildcardsQuery.data.eligibility_reason ?? 'Eligible' }
                ]}
              />
              {wildcardsQuery.data.slots.length > 0 ? (
                <ul>
                  {wildcardsQuery.data.slots.map((slot) => (
                    <li key={slot.entry_id}>
                      Slot {slot.slot_index}: {slot.assigned_player_id ?? 'Unassigned'}
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState message="This event has no wildcard slots configured." />
              )}
              {wildcardsQuery.data.eligible && wildcardsQuery.data.total_slots > 0 ? (
                <form onSubmit={handleWildcardSubmit}>
                  <label>
                    Slot
                    <input value={slotIndexInput} onChange={(e) => setSlotIndexInput(e.target.value)} />
                  </label>
                  <label>
                    Player ID
                    <input value={playerIdInput} onChange={(e) => setPlayerIdInput(e.target.value)} />
                  </label>
                  <button type="submit" disabled={wildcardMutation.isPending}>
                    Assign wildcard
                  </button>
                </form>
              ) : null}
              {wildcardMutation.error ? (
                <p className="error">Wildcard assignment failed: {formatApiError(wildcardMutation.error)}</p>
              ) : null}
            </>
          ) : null}
        </SectionCard>
      ) : null}
    </section>
  )
}

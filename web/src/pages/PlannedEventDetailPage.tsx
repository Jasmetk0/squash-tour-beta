import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  applyEventLateReplacement,
  applyEventPreDrawWithdrawal,
  assignEventWildcards,
  getEventLateReplacementActions,
  getEventLateReplacementCandidates,
  getEventLateReplacementState,
  getEventPreDrawWithdrawalActions,
  getEventPreDrawWithdrawalState,
  getCanonicalTournamentEntryFieldState,
  getCanonicalTournamentDrawState,
  getCanonicalTournamentDrawAuthority,
  commitCanonicalTournamentDrawInput,
  generateCanonicalTournamentDraw,
  getEventWildcardActions,
  getEventWildcardCandidates,
  getEventWildcards,
  getRun,
  listEvents
} from '../api/client'
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
import { useAdminViewedSeasonState } from '../admin/useAdminViewedSeasonState'

export function PlannedEventDetailPage(): JSX.Element {
  const { runId = '', eventId = '' } = useParams()
  const queryClient = useQueryClient()
  const viewed = useAdminViewedSeasonState()
  const [slotIndexInput, setSlotIndexInput] = useState('1')
  const [selectedPlayerId, setSelectedPlayerId] = useState('')
  const [withdrawnPlayerId, setWithdrawnPlayerId] = useState('')
  const [lateReplacementWithdrawnPlayerId, setLateReplacementWithdrawnPlayerId] = useState('')
  const [canonicalDrawSeed, setCanonicalDrawSeed] = useState(12345)
  const commissionerQueryKeys = [
    ['wildcards', runId, eventId],
    ['wildcard-candidates', runId, eventId],
    ['wildcard-actions', runId, eventId],
    ['pre-draw-withdrawal-state', runId, eventId],
    ['pre-draw-withdrawal-actions', runId, eventId],
    ['late-replacement-state', runId, eventId],
    ['late-replacement-candidates', runId, eventId],
    ['late-replacement-actions', runId, eventId]
  ] as const

  async function invalidateCommissionerQueries(): Promise<void> {
    await Promise.all(
      commissionerQueryKeys.map((queryKey) =>
        queryClient.invalidateQueries({
          queryKey
        })
      )
    )
  }

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId) && !viewed.historical,
    retry: false
  })
  const eventsQuery = useQuery({
    queryKey: ['events', runId],
    queryFn: () => listEvents(runId),
    enabled: Boolean(runId) && !viewed.historical,
    retry: false
  })
  const wildcardsQuery = useQuery({
    queryKey: ['wildcards', runId, eventId],
    queryFn: () => getEventWildcards(runId, eventId),
    enabled: Boolean(runId && eventId) && !viewed.historical,
    retry: false
  })
  const wildcardCandidatesQuery = useQuery({
    queryKey: ['wildcard-candidates', runId, eventId],
    queryFn: () => getEventWildcardCandidates(runId, eventId),
    enabled: Boolean(runId && eventId) && !viewed.historical,
    retry: false
  })
  const wildcardActionsQuery = useQuery({
    queryKey: ['wildcard-actions', runId, eventId],
    queryFn: () => getEventWildcardActions(runId, eventId),
    enabled: Boolean(runId && eventId) && !viewed.historical,
    retry: false
  })
  const preDrawWithdrawalStateQuery = useQuery({
    queryKey: ['pre-draw-withdrawal-state', runId, eventId],
    queryFn: () => getEventPreDrawWithdrawalState(runId, eventId),
    enabled: Boolean(runId && eventId) && !viewed.historical,
    retry: false
  })
  const activeBranchId = viewed.time?.branchId ?? ''
  const canonicalEntryFieldQuery = useQuery({
    queryKey: ['canonical-entry-field', runId, activeBranchId, eventId],
    queryFn: () => getCanonicalTournamentEntryFieldState(runId, activeBranchId, eventId),
    enabled: Boolean(runId && activeBranchId && eventId) && !viewed.historical,
    retry: false
  })
  const canonicalEntryFieldUnavailable = Boolean(
    canonicalEntryFieldQuery.error &&
      typeof canonicalEntryFieldQuery.error === 'object' &&
      'status' in canonicalEntryFieldQuery.error &&
      canonicalEntryFieldQuery.error.status === 404
  )
  const canonicalDrawStateQuery = useQuery({
    queryKey: ['canonical-tournament-draw-state', runId, activeBranchId, eventId],
    queryFn: () => getCanonicalTournamentDrawState(runId, activeBranchId, eventId),
    enabled: Boolean(runId && activeBranchId && eventId) && !viewed.historical,
    retry: false
  })
  const canonicalDrawStateUnavailable = Boolean(
    canonicalDrawStateQuery.error &&
      typeof canonicalDrawStateQuery.error === 'object' &&
      'status' in canonicalDrawStateQuery.error &&
      canonicalDrawStateQuery.error.status === 404
  )
  const canonicalDrawAuthorityQuery = useQuery({
    queryKey: ['canonical-tournament-draw-authority', runId, activeBranchId, eventId],
    queryFn: () => getCanonicalTournamentDrawAuthority(runId, activeBranchId, eventId),
    enabled:
      Boolean(runId && activeBranchId && eventId) &&
      !viewed.historical &&
      canonicalDrawStateQuery.data?.initial_draw_generated === true,
    retry: false
  })
  const preDrawWithdrawalActionsQuery = useQuery({
    queryKey: ['pre-draw-withdrawal-actions', runId, eventId],
    queryFn: () => getEventPreDrawWithdrawalActions(runId, eventId),
    enabled: Boolean(runId && eventId) && !viewed.historical,
    retry: false
  })
  const lateReplacementStateQuery = useQuery({
    queryKey: ['late-replacement-state', runId, eventId],
    queryFn: () => getEventLateReplacementState(runId, eventId),
    enabled: Boolean(runId && eventId) && !viewed.historical,
    retry: false
  })
  const lateReplacementCandidatesQuery = useQuery({
    queryKey: ['late-replacement-candidates', runId, eventId],
    queryFn: () => getEventLateReplacementCandidates(runId, eventId),
    enabled: Boolean(runId && eventId) && !viewed.historical,
    retry: false
  })
  const lateReplacementActionsQuery = useQuery({
    queryKey: ['late-replacement-actions', runId, eventId],
    queryFn: () => getEventLateReplacementActions(runId, eventId),
    enabled: Boolean(runId && eventId) && !viewed.historical,
    retry: false
  })
  const wildcardMutation = useMutation({
    mutationFn: (values: { slotIndex: number; playerId: string }) =>
      assignEventWildcards(runId, eventId, {
        assignments: [{ slot_index: values.slotIndex, player_id: values.playerId }]
      }),
    onSuccess: invalidateCommissionerQueries
  })
  const preDrawWithdrawalMutation = useMutation({
    mutationFn: (values: { withdrawnPlayerId: string }) =>
      applyEventPreDrawWithdrawal(runId, eventId, { withdrawn_player_id: values.withdrawnPlayerId }),
    onSuccess: invalidateCommissionerQueries
  })
  const lateReplacementMutation = useMutation({
    mutationFn: (values: { withdrawnPlayerId: string }) =>
      applyEventLateReplacement(runId, eventId, { withdrawn_player_id: values.withdrawnPlayerId }),
    onSuccess: invalidateCommissionerQueries
  })
  async function invalidateCanonicalDrawQueries(): Promise<void> {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['canonical-entry-field', runId, activeBranchId, eventId] }),
      queryClient.invalidateQueries({ queryKey: ['canonical-tournament-draw-state', runId, activeBranchId, eventId] }),
      queryClient.invalidateQueries({ queryKey: ['canonical-tournament-draw-authority', runId, activeBranchId, eventId] })
    ])
  }

  const canonicalDrawInputMutation = useMutation({
    mutationFn: () => {
      const field = canonicalEntryFieldQuery.data
      if (!field) throw new Error('Canonical Tournament Entry Field is required before Draw Input commitment.')
      if (!Number.isSafeInteger(canonicalDrawSeed)) throw new Error('Draw seed must be an integer.')
      const commandId = `admin-ui-draw-input-${field.field_fingerprint.slice(0, 16)}-${canonicalDrawSeed}`
      return commitCanonicalTournamentDrawInput(runId, activeBranchId, eventId, {
        schema_version: 'canonical_tournament_draw_input_commit_command.v1',
        command_id: commandId.slice(0, 128),
        run_id: runId,
        branch_id: activeBranchId,
        event_id: eventId,
        expected_field_fingerprint: field.field_fingerprint,
        draw_seed: canonicalDrawSeed
      })
    },
    onSuccess: invalidateCanonicalDrawQueries
  })

  const canonicalDrawGenerateMutation = useMutation({
    mutationFn: () => {
      const drawState = canonicalDrawStateQuery.data
      if (!drawState?.draw_input_fingerprint) {
        throw new Error('Committed canonical Draw Input is required before Draw generation.')
      }
      const commandId = `admin-ui-draw-generate-${drawState.draw_input_fingerprint.slice(0, 24)}`
      return generateCanonicalTournamentDraw(runId, activeBranchId, eventId, {
        schema_version: 'canonical_tournament_draw_generate_command.v1',
        command_id: commandId,
        run_id: runId,
        branch_id: activeBranchId,
        event_id: eventId,
        expected_draw_input_fingerprint: drawState.draw_input_fingerprint
      })
    },
    onSuccess: invalidateCanonicalDrawQueries
  })

  const seasonState = viewed.historical ? viewed.seasonState : runQuery.data?.season_state
  const orderedEvents = seasonState?.ordered_events ?? []
  const nextEventIndex = seasonState?.next_event_index ?? 0
  const completedEventIds = new Set(seasonState?.completed_event_ids ?? [])
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
  const canonicalQualificationBrackets = canonicalDrawAuthorityQuery.data
    ? canonicalDrawAuthorityQuery.data.qualification_sections?.length
      ? canonicalDrawAuthorityQuery.data.qualification_sections
      : canonicalDrawAuthorityQuery.data.qualification
        ? [canonicalDrawAuthorityQuery.data.qualification]
        : []
    : []

  useEffect(() => {
    const firstCandidateId = wildcardCandidatesQuery.data?.candidates[0]?.player_id ?? ''
    if (!selectedPlayerId && firstCandidateId) {
      setSelectedPlayerId(firstCandidateId)
    }
  }, [wildcardCandidatesQuery.data, selectedPlayerId])
  useEffect(() => {
    const firstWithdrawableId = preDrawWithdrawalStateQuery.data?.withdrawable_main_draw_players[0]?.player_id ?? ''
    if (!withdrawnPlayerId && firstWithdrawableId) {
      setWithdrawnPlayerId(firstWithdrawableId)
    }
  }, [preDrawWithdrawalStateQuery.data, withdrawnPlayerId])
  useEffect(() => {
    const firstWithdrawableId = lateReplacementStateQuery.data?.replaceable_main_draw_players[0]?.player_id ?? ''
    if (!lateReplacementWithdrawnPlayerId && firstWithdrawableId) {
      setLateReplacementWithdrawnPlayerId(firstWithdrawableId)
    }
  }, [lateReplacementStateQuery.data, lateReplacementWithdrawnPlayerId])

  function handleWildcardSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const slotIndex = Number(slotIndexInput)
    if (!Number.isFinite(slotIndex) || slotIndex < 1 || !selectedPlayerId.trim()) return
    wildcardMutation.mutate({ slotIndex, playerId: selectedPlayerId.trim() })
  }
  function handlePreDrawWithdrawalSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (!withdrawnPlayerId.trim()) return
    preDrawWithdrawalMutation.mutate({ withdrawnPlayerId: withdrawnPlayerId.trim() })
  }
  function handleLateReplacementSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (!lateReplacementWithdrawnPlayerId.trim()) return
    lateReplacementMutation.mutate({ withdrawnPlayerId: lateReplacementWithdrawnPlayerId.trim() })
  }

  if (viewed.historical && viewed.unavailable) return <section className="panel"><h1>Historical calendar is not available for this checkpoint.</h1><p>Checkpoint: {viewed.time?.viewCheckpointId}</p><button onClick={() => viewed.time?.selectPresent()}>Return to Present</button> <Link to={`/admin/runs/${encodeURIComponent(runId)}`}>Open Run Home</Link></section>
  if (viewed.historical && viewed.failed) return <section className="panel"><h1>Failed to load historical calendar state.</h1><p>Checkpoint: {viewed.time?.viewCheckpointId}</p><button onClick={() => viewed.time?.selectPresent()}>Return to Present</button> <Link to={`/admin/runs/${encodeURIComponent(runId)}`}>Open Run Home</Link></section>
  if (viewed.historical && viewed.query.isLoading) return <section className="panel"><p className="status">Loading historical planned event...</p></section>

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
          { label: 'Time', value: viewed.historical ? 'Past' : 'Present' },
          { label: 'Season', value: seasonState?.season ?? '—' },
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
          {!viewed.historical ? <Link to={`/runs/${runId}/events`}>Open Events history</Link> : <span>Persisted historical event detail is not available in this phase.</span>}
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
        {eventId && seasonState && !plannedEvent ? (
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
              { label: 'Persisted event record', value: viewed.historical ? 'Not available in this historical slice' : hasPersistedHistory ? 'Available' : 'Not available' }
            ]}
          />
          {!viewed.historical && status === 'Completed' && hasPersistedHistory ? (
            <p>
              <Link to={`/runs/${runId}/events/${encodeURIComponent(plannedEvent.event_id)}`}>
                Inspect persisted event detail for {plannedEvent.event_id}
              </Link>
            </p>
          ) : null}
        </SectionCard>
      ) : null}

      {eventsQuery.error ? <p className="error">Failed to load persisted events: {formatApiError(eventsQuery.error)}</p> : null}

      {plannedEvent && !viewed.historical && activeBranchId ? (
        <SectionCard title="Canonical Main Draw preflight">
          {canonicalEntryFieldQuery.isLoading ? <p className="status">Loading canonical Main Draw geometry...</p> : null}
          {canonicalEntryFieldUnavailable ? (
            <p className="status">Canonical Tournament Entry Field is not available for this event yet.</p>
          ) : null}
          {canonicalEntryFieldQuery.error && !canonicalEntryFieldUnavailable ? (
            <p className="error">
              Failed to load canonical Main Draw preflight: {formatApiError(canonicalEntryFieldQuery.error)}
            </p>
          ) : null}
          {canonicalEntryFieldQuery.data ? (
            <>
              <MetadataList
                items={[
                  { label: 'Active Branch', value: canonicalEntryFieldQuery.data.branch_id },
                  { label: 'Field version', value: canonicalEntryFieldQuery.data.field_sequence },
                  { label: 'Bracket capacity', value: canonicalEntryFieldQuery.data.main_draw_capacity },
                  { label: 'Current entrants', value: canonicalEntryFieldQuery.data.active_main_entrant_count },
                  { label: 'Effective BYEs', value: canonicalEntryFieldQuery.data.effective_main_bye_count },
                  {
                    label: 'Draw Input',
                    value: canonicalEntryFieldQuery.data.draw_input_committed ? 'Committed' : 'Not committed'
                  }
                ]}
              />
              {canonicalEntryFieldQuery.data.main_diagnostics.length > 0 ? (
                <ul aria-label="Main Draw warnings">
                  {canonicalEntryFieldQuery.data.main_diagnostics.map((diagnostic) => (
                    <li key={diagnostic.code}>
                      <strong>{diagnostic.message}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="status">No Main Draw geometry warnings.</p>
              )}
            </>
          ) : null}
        </SectionCard>
      ) : null}

      {plannedEvent && !viewed.historical && activeBranchId ? (
        <SectionCard title="Canonical Tournament Draw authority">
          {canonicalDrawStateQuery.isLoading ? <p className="status">Loading canonical Draw authority state...</p> : null}
          {canonicalDrawStateUnavailable ? (
            <p className="status">Canonical Tournament Entry Field is not available for this event yet.</p>
          ) : null}
          {canonicalDrawStateQuery.error && !canonicalDrawStateUnavailable ? (
            <p className="error">Failed to load canonical Draw state: {formatApiError(canonicalDrawStateQuery.error)}</p>
          ) : null}
          {canonicalDrawStateQuery.data ? (
            <>
              <MetadataList
                items={[
                  { label: 'Draw Input', value: canonicalDrawStateQuery.data.draw_input_committed ? 'Committed' : 'Not committed' },
                  { label: 'Initial Draw', value: canonicalDrawStateQuery.data.initial_draw_generated ? 'Generated / immutable' : 'Not generated' },
                  { label: 'Main seed count', value: canonicalDrawStateQuery.data.main_seed_count ?? 'Derived on commit' },
                  { label: 'Qualification seed count', value: canonicalDrawStateQuery.data.qualification_seed_count ?? 'Derived on commit' },
                  { label: 'Frozen draw seed', value: canonicalDrawStateQuery.data.draw_seed ?? '—' },
                  { label: 'Algorithm', value: canonicalDrawStateQuery.data.draw_algorithm_version ?? '—' }
                ]}
              />
              {!canonicalDrawStateQuery.data.draw_input_committed ? (
                <div className="grid">
                  <label>
                    Technical draw seed
                    <input
                      aria-label="Technical draw seed"
                      type="number"
                      value={canonicalDrawSeed}
                      onChange={(event) => setCanonicalDrawSeed(Number(event.target.value))}
                    />
                  </label>
                  <p className="status">
                    The seed freezes deterministic replay only. Bracket capacity, BYEs and seed counts remain Master-derived.
                  </p>
                  <button
                    type="button"
                    onClick={() => canonicalDrawInputMutation.mutate()}
                    disabled={
                      canonicalDrawInputMutation.isPending ||
                      !canonicalEntryFieldQuery.data ||
                      !Number.isSafeInteger(canonicalDrawSeed)
                    }
                  >
                    Commit canonical Draw Input
                  </button>
                </div>
              ) : null}
              {canonicalDrawStateQuery.data.draw_input_committed && !canonicalDrawStateQuery.data.initial_draw_generated ? (
                <button
                  type="button"
                  onClick={() => canonicalDrawGenerateMutation.mutate()}
                  disabled={canonicalDrawGenerateMutation.isPending || !canonicalDrawStateQuery.data.draw_input_fingerprint}
                >
                  Generate canonical initial Draw
                </button>
              ) : null}
              {canonicalDrawStateQuery.data.initial_draw_generated ? (
                <p className="status">Initial canonical Draw is frozen. Later changes use append-only Draw revision authorities.</p>
              ) : null}
              {canonicalDrawInputMutation.error ? (
                <p className="error">Draw Input commitment failed: {formatApiError(canonicalDrawInputMutation.error)}</p>
              ) : null}
              {canonicalDrawGenerateMutation.error ? (
                <p className="error">Draw generation failed: {formatApiError(canonicalDrawGenerateMutation.error)}</p>
              ) : null}
            </>
          ) : null}

          {canonicalDrawAuthorityQuery.isLoading ? <p className="status">Loading immutable canonical bracket...</p> : null}
          {canonicalDrawAuthorityQuery.error ? (
            <p className="error">Failed to load canonical Draw authority: {formatApiError(canonicalDrawAuthorityQuery.error)}</p>
          ) : null}
          {canonicalDrawAuthorityQuery.data ? (
            <>
              <SummaryPills
                items={[
                  { label: 'Main slots', value: canonicalDrawAuthorityQuery.data.main.bracket_size },
                  { label: 'Main BYEs', value: canonicalDrawAuthorityQuery.data.main.bye_slot_indexes.length },
                  { label: 'Q sections', value: canonicalQualificationBrackets.length },
                  { label: 'Algorithm', value: canonicalDrawAuthorityQuery.data.algorithm_version }
                ]}
              />
              <div className="table-wrap">
                <table aria-label="Canonical Main Draw slots">
                  <thead>
                    <tr><th>Slot</th><th>Idealized</th><th>Entrant</th><th>Seed</th><th>Status</th></tr>
                  </thead>
                  <tbody>
                    {canonicalDrawAuthorityQuery.data.main.slots.map((slot) => (
                      <tr key={slot.slot_index}>
                        <td>{slot.slot_index}</td>
                        <td>{slot.idealized_slot_number ?? '—'}</td>
                        <td>{slot.player_id ?? slot.placeholder_id ?? 'BYE'}</td>
                        <td>{slot.seed_number ?? '—'}</td>
                        <td>{slot.entry_status ?? slot.entrant_kind}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {canonicalQualificationBrackets.map((bracket) => (
                <div key={bracket.section_id ?? 'qualification'}>
                  <h4>{bracket.section_id ?? 'Qualification'}</h4>
                  <div className="table-wrap">
                    <table aria-label={`Canonical ${bracket.section_id ?? 'Qualification'} slots`}>
                      <thead>
                        <tr><th>Slot</th><th>Idealized</th><th>Entrant</th><th>Seed</th></tr>
                      </thead>
                      <tbody>
                        {bracket.slots.map((slot) => (
                          <tr key={slot.slot_index}>
                            <td>{slot.slot_index}</td>
                            <td>{slot.idealized_slot_number ?? '—'}</td>
                            <td>{slot.player_id ?? slot.placeholder_id ?? 'BYE'}</td>
                            <td>{slot.seed_number ?? '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </>
          ) : null}
        </SectionCard>
      ) : null}

      {plannedEvent && !viewed.historical ? (
        <SectionCard title="Commissioner late replacement lucky loser">
          {lateReplacementStateQuery.isLoading ? <p className="status">Loading late-replacement state...</p> : null}
          {lateReplacementStateQuery.error ? (
            <p className="error">Failed to load late-replacement state: {formatApiError(lateReplacementStateQuery.error)}</p>
          ) : null}
          {lateReplacementStateQuery.data ? (
            <>
              <MetadataList
                items={[
                  { label: 'Action allowed', value: lateReplacementStateQuery.data.eligible ? 'Yes' : 'No' },
                  { label: 'Eligibility note', value: lateReplacementStateQuery.data.eligibility_reason ?? 'Eligible' },
                  { label: 'Replaceable players', value: lateReplacementStateQuery.data.replaceable_main_draw_players.length },
                  { label: 'Remaining capacity', value: lateReplacementStateQuery.data.remaining_capacity }
                ]}
              />
              {lateReplacementStateQuery.data.eligible ? (
                <form onSubmit={handleLateReplacementSubmit}>
                  <label>
                    Main-draw player to withdraw
                    <select
                      value={lateReplacementWithdrawnPlayerId}
                      onChange={(e) => setLateReplacementWithdrawnPlayerId(e.target.value)}
                    >
                      <option value="">Select player</option>
                      {lateReplacementStateQuery.data.replaceable_main_draw_players.map((player) => (
                        <option key={`${player.player_id}-${player.entry_id}`} value={player.player_id}>
                          {player.player_name} ({player.player_id}) · {player.country_code}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="submit"
                    disabled={
                      lateReplacementMutation.isPending ||
                      !lateReplacementWithdrawnPlayerId ||
                      lateReplacementStateQuery.data.replaceable_main_draw_players.length === 0
                    }
                  >
                    Withdraw + late-replace
                  </button>
                </form>
              ) : null}
              {lateReplacementCandidatesQuery.isLoading ? <p className="status">Loading late-replacement candidates...</p> : null}
              {lateReplacementCandidatesQuery.error ? (
                <p className="error">
                  Failed to load late-replacement candidates: {formatApiError(lateReplacementCandidatesQuery.error)}
                </p>
              ) : null}
              {lateReplacementCandidatesQuery.data ? (
                lateReplacementCandidatesQuery.data.candidates.length > 0 ? (
                  <ul>
                    {lateReplacementCandidatesQuery.data.candidates.map((candidate) => (
                      <li key={`${candidate.player_id}-${candidate.entry_id}`}>
                        #{candidate.candidate_slot_index} · {candidate.player_name} ({candidate.player_id}) · {candidate.source} ·
                        ranking {candidate.ranking_priority ?? '—'}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState message="No late-replacement candidates are currently available for this event." />
                )
              ) : null}
              {lateReplacementMutation.error ? (
                <p className="error">Late-replacement command failed: {formatApiError(lateReplacementMutation.error)}</p>
              ) : null}
              {lateReplacementMutation.data ? (
                <p className="status">
                  Last action: withdrew {lateReplacementMutation.data.withdrawn_player_id} and late-replaced with{' '}
                  {lateReplacementMutation.data.replacement_player_id} ({lateReplacementMutation.data.replacement_source}).
                </p>
              ) : null}
            </>
          ) : null}
        </SectionCard>
      ) : null}

      {plannedEvent && !viewed.historical ? (
        <SectionCard title="Late-replacement action history">
          {lateReplacementActionsQuery.isLoading ? <p className="status">Loading late-replacement history...</p> : null}
          {lateReplacementActionsQuery.error ? (
            <p className="error">Failed to load late-replacement history: {formatApiError(lateReplacementActionsQuery.error)}</p>
          ) : null}
          {lateReplacementActionsQuery.data ? (
            lateReplacementActionsQuery.data.actions.length > 0 ? (
              <ol>
                {lateReplacementActionsQuery.data.actions.map((action) => (
                  <li key={action.action_sequence}>
                    #{action.action_sequence} · {action.action_kind} · {action.withdrawn_player_id} → {action.replacement_player_id} (
                    {action.replacement_source})
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState message="No late-replacement lucky loser actions have been recorded for this event yet." />
            )
          ) : null}
        </SectionCard>
      ) : null}

      {plannedEvent && !viewed.historical ? (
        <SectionCard title="Commissioner pre-draw withdrawal replacement">
          {preDrawWithdrawalStateQuery.isLoading ? <p className="status">Loading pre-draw withdrawal state...</p> : null}
          {preDrawWithdrawalStateQuery.error ? (
            <p className="error">Failed to load pre-draw withdrawal state: {formatApiError(preDrawWithdrawalStateQuery.error)}</p>
          ) : null}
          {preDrawWithdrawalStateQuery.data ? (
            <>
              <MetadataList
                items={[
                  { label: 'Action allowed', value: preDrawWithdrawalStateQuery.data.eligible ? 'Yes' : 'No' },
                  { label: 'Eligibility note', value: preDrawWithdrawalStateQuery.data.eligibility_reason ?? 'Eligible' },
                  {
                    label: 'Withdrawable players',
                    value: preDrawWithdrawalStateQuery.data.withdrawable_main_draw_players.length
                  }
                ]}
              />
              {preDrawWithdrawalStateQuery.data.eligible ? (
                <form onSubmit={handlePreDrawWithdrawalSubmit}>
                  <label>
                    Main-draw player to withdraw
                    <select value={withdrawnPlayerId} onChange={(e) => setWithdrawnPlayerId(e.target.value)}>
                      <option value="">Select player</option>
                      {preDrawWithdrawalStateQuery.data.withdrawable_main_draw_players.map((player) => (
                        <option key={`${player.player_id}-${player.entry_id}`} value={player.player_id}>
                          {player.player_name} ({player.player_id}) · {player.country_code}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="submit"
                    disabled={
                      preDrawWithdrawalMutation.isPending ||
                      !withdrawnPlayerId ||
                      preDrawWithdrawalStateQuery.data.withdrawable_main_draw_players.length === 0
                    }
                  >
                    Withdraw + auto-replace
                  </button>
                </form>
              ) : null}
              {preDrawWithdrawalMutation.error ? (
                <p className="error">Pre-draw withdrawal failed: {formatApiError(preDrawWithdrawalMutation.error)}</p>
              ) : null}
              {preDrawWithdrawalMutation.data ? (
                <p className="status">
                  Last action: withdrew {preDrawWithdrawalMutation.data.withdrawn_player_id} and auto-replaced with{' '}
                  {preDrawWithdrawalMutation.data.replacement_player_id} ({preDrawWithdrawalMutation.data.replacement_source}).
                </p>
              ) : null}
            </>
          ) : null}
        </SectionCard>
      ) : null}

      {plannedEvent && !viewed.historical ? (
        <SectionCard title="Pre-draw withdrawal action history">
          {preDrawWithdrawalActionsQuery.isLoading ? <p className="status">Loading pre-draw withdrawal history...</p> : null}
          {preDrawWithdrawalActionsQuery.error ? (
            <p className="error">
              Failed to load pre-draw withdrawal history: {formatApiError(preDrawWithdrawalActionsQuery.error)}
            </p>
          ) : null}
          {preDrawWithdrawalActionsQuery.data ? (
            preDrawWithdrawalActionsQuery.data.actions.length > 0 ? (
              <ol>
                {preDrawWithdrawalActionsQuery.data.actions.map((action) => (
                  <li key={action.action_sequence}>
                    #{action.action_sequence} · {action.action_kind} · {action.withdrawn_player_id} → {action.replacement_player_id} (
                    {action.replacement_source})
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState message="No pre-draw withdrawal replacement actions have been recorded for this event yet." />
            )
          ) : null}
        </SectionCard>
      ) : null}

      {plannedEvent && !viewed.historical ? (
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
                    <select value={slotIndexInput} onChange={(e) => setSlotIndexInput(e.target.value)}>
                      {wildcardsQuery.data.slots.map((slot) => (
                        <option key={slot.slot_index} value={String(slot.slot_index)}>
                          {slot.slot_index}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Candidate player
                    <select value={selectedPlayerId} onChange={(e) => setSelectedPlayerId(e.target.value)}>
                      <option value="">Select candidate</option>
                      {(wildcardCandidatesQuery.data?.candidates ?? []).map((candidate) => (
                        <option key={candidate.player_id} value={candidate.player_id}>
                          {candidate.player_name} ({candidate.player_id}) · {candidate.country_code} ·{' '}
                          {candidate.source === 'main_draw_waitlist'
                            ? 'Main waitlist'
                            : candidate.source === 'qualification_waitlist'
                              ? 'Qualification waitlist'
                              : 'Open pool'}
                          {candidate.source_priority ? ` #${candidate.source_priority}` : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="submit"
                    disabled={
                      wildcardMutation.isPending ||
                      !selectedPlayerId ||
                      (wildcardCandidatesQuery.data?.candidates.length ?? 0) === 0
                    }
                  >
                    Assign wildcard
                  </button>
                </form>
              ) : null}
              {wildcardCandidatesQuery.isLoading ? <p className="status">Loading wildcard candidates...</p> : null}
              {wildcardCandidatesQuery.error ? (
                <p className="error">
                  Failed to load wildcard candidates: {formatApiError(wildcardCandidatesQuery.error)}
                </p>
              ) : null}
              {wildcardsQuery.data.eligible &&
              wildcardsQuery.data.total_slots > 0 &&
              wildcardCandidatesQuery.data &&
              wildcardCandidatesQuery.data.candidates.length === 0 ? (
                <p className="status">No eligible wildcard candidates are currently available for this event.</p>
              ) : null}
              {wildcardMutation.error ? (
                <p className="error">Wildcard assignment failed: {formatApiError(wildcardMutation.error)}</p>
              ) : null}
            </>
          ) : null}
        </SectionCard>
      ) : null}
      {plannedEvent && !viewed.historical ? (
        <SectionCard title="Wildcard action history">
          <p className="status">
            Append-only event audit trail sourced from admin actions for this event.{' '}
            <Link to={`/runs/${runId}/activity`}>Open run activity</Link>
          </p>
          {wildcardActionsQuery.isLoading ? <p className="status">Loading wildcard action history...</p> : null}
          {wildcardActionsQuery.error ? (
            <p className="error">Failed to load wildcard action history: {formatApiError(wildcardActionsQuery.error)}</p>
          ) : null}
          {wildcardActionsQuery.data ? (
            wildcardActionsQuery.data.actions.length > 0 ? (
              <ol>
                {wildcardActionsQuery.data.actions.map((action) => (
                  <li key={action.action_sequence}>
                    #{action.action_sequence} · {action.action_kind} ·{' '}
                    {action.assignment_payload_summary.length > 0
                      ? action.assignment_payload_summary
                          .map((assignment) => `slot ${assignment.slot_index} → ${assignment.player_id}`)
                          .join(', ')
                      : 'No valid assignment payload entries'}
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState message="No wildcard commissioner actions have been recorded for this event yet." />
            )
          ) : null}
        </SectionCard>
      ) : null}
    </section>
  )
}

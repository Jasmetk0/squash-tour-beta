import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  adoptAuthoritativeWeekScheduleProposal,
  getAuthoritativeSimulationPosition,
  inspectAuthoritativeWeekSchedule,
  previewAuthoritativeSimulationSave,
  proposeAuthoritativeWeekSchedule,
  saveAuthoritativeSimulation,
  simulateAuthoritativeNextMatch,
  simulateAuthoritativeNextSlot
} from '../api/client'
import type {
  AuthoritativeSimulationCommandPayload,
  AuthoritativeWeekScheduleProposal
} from '../api/types'
import { newCommandId } from '../admin/branchSimulation'
import { EmptyState, MetadataList, SectionCard, SummaryPills } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

type Props = {
  runId: string
  branchId: string
  savedRevisionId: string | null
  blockedReason: string | null
}

export function AuthoritativeSimulationPanel({
  runId,
  branchId,
  savedRevisionId,
  blockedReason
}: Props): JSX.Element {
  const queryClient = useQueryClient()
  const enabled = Boolean(runId && branchId && savedRevisionId && !blockedReason)
  const [selectedGroupId, setSelectedGroupId] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [proposal, setProposal] = useState<AuthoritativeWeekScheduleProposal | null>(null)
  const [proposalRequestId, setProposalRequestId] = useState('')

  const positionQuery = useQuery({
    queryKey: ['authoritative-simulation-position', runId, branchId],
    queryFn: () => getAuthoritativeSimulationPosition(runId, branchId),
    enabled,
    retry: false
  })
  const scheduleQuery = useQuery({
    queryKey: ['authoritative-simulation-week-schedule', runId, branchId],
    queryFn: () => inspectAuthoritativeWeekSchedule(runId, branchId),
    enabled,
    retry: false
  })
  const savePreviewQuery = useQuery({
    queryKey: ['authoritative-simulation-save-preview', runId, branchId],
    queryFn: () => previewAuthoritativeSimulationSave(runId, branchId),
    enabled,
    retry: false
  })

  useEffect(() => {
    setProposal(null)
    setProposalRequestId('')
    setConfirmed(false)
    setSelectedGroupId('')
  }, [runId, branchId, savedRevisionId])

  useEffect(() => {
    const eligible = positionQuery.data?.eligible_match_ids ?? []
    if (!eligible.includes(selectedGroupId)) setSelectedGroupId(eligible[0] ?? '')
  }, [positionQuery.data, selectedGroupId])

  async function refreshCanonicalSimulation(): Promise<void> {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] }),
      queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-week-schedule', runId, branchId] }),
      queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-save-preview', runId, branchId] })
    ])
  }

  const proposalMutation = useMutation({
    mutationFn: () => proposeAuthoritativeWeekSchedule(runId, branchId),
    onSuccess: (value) => {
      setProposal(value)
      setProposalRequestId(newCommandId())
    }
  })

  const adoptMutation = useMutation({
    mutationFn: () => {
      if (!proposal || !proposalRequestId) throw new Error('Review a current topological schedule proposal first.')
      return adoptAuthoritativeWeekScheduleProposal(runId, branchId, {
        request_id: proposalRequestId,
        expected_week: proposal.schedule.week,
        expected_schedule_fingerprint: proposal.schedule_fingerprint,
        expected_position_fingerprint: proposal.position_fingerprint
      })
    },
    onSuccess: async () => {
      setProposal(null)
      setProposalRequestId('')
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: (error) => {
      if ((error as { status?: number }).status === 409) {
        setProposal(null)
        setProposalRequestId('')
      }
    }
  })

  function simulationPayload(groupId?: string): AuthoritativeSimulationCommandPayload {
    const position = positionQuery.data
    if (!position || !savedRevisionId) throw new Error('Current authoritative position and Saved Revision head are required.')
    return {
      command_id: newCommandId(),
      run_id: runId,
      branch_id: branchId,
      expected_week: position.current_week,
      expected_position_fingerprint: position.position_fingerprint,
      expected_revision_id: savedRevisionId,
      ...(groupId ? { group_id: groupId } : {})
    }
  }

  const nextMatchMutation = useMutation({
    mutationFn: () => {
      if (!selectedGroupId) throw new Error('Select one currently eligible match group.')
      return simulateAuthoritativeNextMatch(runId, branchId, simulationPayload(selectedGroupId))
    },
    onSuccess: async (position) => {
      queryClient.setQueryData(['authoritative-simulation-position', runId, branchId], position)
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setConfirmed(false)
        await refreshCanonicalSimulation()
      }
    }
  })

  const nextSlotMutation = useMutation({
    mutationFn: () => simulateAuthoritativeNextSlot(runId, branchId, simulationPayload()),
    onSuccess: async (position) => {
      queryClient.setQueryData(['authoritative-simulation-position', runId, branchId], position)
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setConfirmed(false)
        await refreshCanonicalSimulation()
      }
    }
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      const preview = savePreviewQuery.data
      if (!preview?.can_save) throw new Error('There are no reviewed authoritative simulation changes to Save.')
      return saveAuthoritativeSimulation(runId, branchId, {
        expected_draft_version: preview.draft_version,
        expected_simulation_fingerprint: preview.simulation_fingerprint
      })
    },
    onSuccess: async () => {
      setConfirmed(false)
      await Promise.all([
        refreshCanonicalSimulation(),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] })
      ])
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) await refreshCanonicalSimulation()
    }
  })

  const schedule = scheduleQuery.data?.schedule
  const position = positionQuery.data
  const actionPending = nextMatchMutation.isPending || nextSlotMutation.isPending

  return (
    <SectionCard title="Canonical authoritative sporting simulation">
      <p className="status">
        Run/Branch-owned sporting path: Position → dependency-safe Week Schedule → Next Match / Next Slot → Save.
        It does not use the legacy simulation-run binding.
      </p>

      {blockedReason ? <p role="alert" className="error">Canonical simulation blocked: {blockedReason}</p> : null}
      {!blockedReason && !savedRevisionId ? (
        <p role="alert" className="error">Canonical simulation blocked: Branch has no Saved Revision head.</p>
      ) : null}

      {(positionQuery.isLoading || scheduleQuery.isLoading || savePreviewQuery.isLoading) && enabled ? (
        <p className="status">Loading authoritative sporting position…</p>
      ) : null}
      {positionQuery.error ? <p className="error">Position unavailable: {formatApiError(positionQuery.error)}</p> : null}
      {scheduleQuery.error ? <p className="error">Week Schedule unavailable: {formatApiError(scheduleQuery.error)}</p> : null}
      {savePreviewQuery.error ? <p className="error">Save preview unavailable: {formatApiError(savePreviewQuery.error)}</p> : null}

      {position ? (
        <>
          <SummaryPills
            items={[
              { label: 'Week', value: `S${position.current_week.season_index} · W${position.current_week.week}` },
              { label: 'Current slot', value: position.current_slot_id ?? 'Not materialized' },
              { label: 'Eligible matches', value: position.eligible_match_ids.length },
              { label: 'Blocked matches', value: position.blocked_match_ids.length },
              { label: 'Week transition ready', value: position.week_ready_for_transition ? 'Yes' : 'No' }
            ]}
          />
          <MetadataList
            items={[
              { label: 'Slot ordinal', value: position.slot_ordinal ?? '—' },
              { label: 'Unresolved groups', value: position.unresolved_group_ids.length },
              { label: 'Current slot complete', value: position.current_slot_complete ? 'Yes' : 'No' },
              { label: 'Tournament complete', value: position.supported_tournament_complete ? 'Yes' : 'No' },
              {
                label: 'Transition blockers',
                value: position.transition_blockers.length ? position.transition_blockers.join(', ') : 'None'
              },
              { label: 'Saved Revision head', value: savedRevisionId ?? '—' }
            ]}
          />
        </>
      ) : null}

      {scheduleQuery.data ? (
        <>
          <h4>Week Simulation Schedule</h4>
          <MetadataList
            items={[
              { label: 'Schedule required', value: scheduleQuery.data.required ? 'Yes' : 'No' },
              { label: 'Events', value: scheduleQuery.data.event_ids.length },
              { label: 'Groups', value: scheduleQuery.data.group_ids.length },
              { label: 'Status', value: schedule ? 'Adopted / immutable' : 'Not adopted' }
            ]}
          />
          {schedule ? (
            <ol aria-label="Adopted authoritative week schedule">
              {schedule.slots.map((slot) => (
                <li key={slot.ordinal}>Slot {slot.ordinal}: {slot.group_ids.join(', ')}</li>
              ))}
            </ol>
          ) : scheduleQuery.data.required ? (
            <>
              <button
                type="button"
                onClick={() => proposalMutation.mutate()}
                disabled={proposalMutation.isPending || adoptMutation.isPending}
              >
                Build topological schedule proposal
              </button>
              {proposalMutation.error ? (
                <p className="error">Schedule proposal failed: {formatApiError(proposalMutation.error)}</p>
              ) : null}
              {proposal ? (
                <>
                  <p className="status">{proposal.provenance}</p>
                  <ol aria-label="Proposed authoritative week schedule">
                    {proposal.schedule.slots.map((slot) => (
                      <li key={slot.ordinal}>Slot {slot.ordinal}: {slot.group_ids.join(', ')}</li>
                    ))}
                  </ol>
                  <button
                    type="button"
                    onClick={() => adoptMutation.mutate()}
                    disabled={adoptMutation.isPending || !proposalRequestId}
                  >
                    Adopt reviewed topological schedule
                  </button>
                </>
              ) : null}
              {adoptMutation.error ? (
                <p className="error">Schedule adoption failed: {formatApiError(adoptMutation.error)}</p>
              ) : null}
            </>
          ) : (
            <p className="status">An explicit Week Schedule is not required for the current canonical topology.</p>
          )}
        </>
      ) : null}

      {position ? (
        <>
          <h4>Execute current canonical position</h4>
          {position.eligible_match_ids.length ? (
            <label>
              Eligible match group
              <select
                aria-label="Eligible authoritative match group"
                value={selectedGroupId}
                onChange={(event) => {
                  setSelectedGroupId(event.target.value)
                  setConfirmed(false)
                }}
              >
                {position.eligible_match_ids.map((groupId) => (
                  <option key={groupId} value={groupId}>{groupId}</option>
                ))}
              </select>
            </label>
          ) : (
            <EmptyState message="No currently eligible competitive match group." />
          )}
          <label>
            <input
              aria-label="Confirm authoritative simulation"
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />{' '}
            I reviewed the current canonical position and Saved Revision head.
          </label>
          <div className="quick-actions">
            <button
              type="button"
              onClick={() => nextMatchMutation.mutate()}
              disabled={!confirmed || !selectedGroupId || actionPending}
            >
              Simulate authoritative Next Match
            </button>
            <button
              type="button"
              onClick={() => nextSlotMutation.mutate()}
              disabled={!confirmed || position.eligible_match_ids.length === 0 || actionPending}
            >
              Simulate authoritative Next Slot
            </button>
          </div>
          {nextMatchMutation.error ? (
            <p className="error">Authoritative Next Match failed: {formatApiError(nextMatchMutation.error)}</p>
          ) : null}
          {nextSlotMutation.error ? (
            <p className="error">Authoritative Next Slot failed: {formatApiError(nextSlotMutation.error)}</p>
          ) : null}
        </>
      ) : null}

      {savePreviewQuery.data ? (
        <>
          <h4>Save canonical simulation draft</h4>
          <MetadataList
            items={[
              { label: 'Unsaved changes', value: savePreviewQuery.data.can_save ? 'Yes' : 'No' },
              { label: 'Draft version', value: savePreviewQuery.data.draft_version },
              { label: 'Can Save', value: savePreviewQuery.data.can_save ? 'Yes' : 'No' }
            ]}
          />
          <button
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={!savePreviewQuery.data.can_save || saveMutation.isPending}
          >
            Save authoritative simulation
          </button>
          {saveMutation.data ? (
            <p className="status">
              Saved as revision {saveMutation.data.saved_revision.revision_id}.
            </p>
          ) : null}
          {saveMutation.error ? (
            <p className="error">Authoritative simulation Save failed: {formatApiError(saveMutation.error)}</p>
          ) : null}
        </>
      ) : null}
    </SectionCard>
  )
}

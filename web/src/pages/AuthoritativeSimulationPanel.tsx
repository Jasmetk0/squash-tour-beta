import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  adoptAuthoritativeWeekScheduleProposal,
  getAuthoritativeSimulationPosition,
  getAuthoritativeSeasonTransitionPreflight,
  getAdminVisibleProspects,
  previewAuthoritativeSeasonTransitionConfiguration,
  advanceAuthoritativeOrdinarySeason,
  finalizeAuthoritativeFinalSeason,
  inspectAuthoritativeWeekSchedule,
  previewAuthoritativeSimulationSave,
  proposeAuthoritativeWeekSchedule,
  saveAuthoritativeSimulation,
  simulateAuthoritativeNextMatch,
  simulateAuthoritativeNextSlot,
  previewDerivedAuthoritativeWeekTransition,
  confirmAuthoritativeWeekTransition,
  previewRankingSave,
  saveRankingPreparation,
  previewDerivedRankingTransitionAuthority,
  confirmDerivedRankingTransitionAuthority
} from '../api/client'
import type {
  AuthoritativeSimulationCommandPayload,
  AuthoritativeWeekScheduleProposal,
  DerivedAuthoritativeWeekTransitionPreview
} from '../api/types'
import { newCommandId } from '../admin/branchSimulation'
import { EmptyState, MetadataList, SectionCard, SummaryPills } from '../components/RunScopedUi'
import type {
  DerivedRankingTransitionAuthorityPreview,
  DerivedRankingTransitionAuthorityRequest
} from '../api/rankingCandidates'
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
  const [nextMatchCommandId, setNextMatchCommandId] = useState(newCommandId)
  const [nextSlotCommandId, setNextSlotCommandId] = useState(newCommandId)
  const [weekTransitionCommandId, setWeekTransitionCommandId] = useState(newCommandId)
  const [weekTransitionReview, setWeekTransitionReview] =
    useState<DerivedAuthoritativeWeekTransitionPreview | null>(null)
  const [weekTransitionCommitted, setWeekTransitionCommitted] = useState(false)
  const [rankingAuthorityCommandId, setRankingAuthorityCommandId] = useState(newCommandId)
  const [rankingAuthorityActor, setRankingAuthorityActor] = useState('')
  const [rankingAuthorityReason, setRankingAuthorityReason] = useState('')
  const [rankingAuthorityReview, setRankingAuthorityReview] = useState<{
    payload: DerivedRankingTransitionAuthorityRequest
    preview: DerivedRankingTransitionAuthorityPreview
  } | null>(null)
  const [rankingAuthorityCommitted, setRankingAuthorityCommitted] = useState(false)
  const [ordinarySeasonCommandId, setOrdinarySeasonCommandId] = useState(newCommandId)
  const [ordinarySeasonRevisionId, setOrdinarySeasonRevisionId] = useState(newCommandId)
  const [ordinarySeasonAuditId, setOrdinarySeasonAuditId] = useState(newCommandId)
  const [ordinarySeasonConfirmed, setOrdinarySeasonConfirmed] = useState(false)
  const [finalSeasonCommandId, setFinalSeasonCommandId] = useState(newCommandId)
  const [finalSeasonRevisionId, setFinalSeasonRevisionId] = useState(newCommandId)
  const [finalSeasonAuditId, setFinalSeasonAuditId] = useState(newCommandId)
  const [finalSeasonConfirmed, setFinalSeasonConfirmed] = useState(false)

  const scheduleQuery = useQuery({
    queryKey: ['authoritative-simulation-week-schedule', runId, branchId],
    queryFn: () => inspectAuthoritativeWeekSchedule(runId, branchId),
    enabled,
    retry: false
  })
  const scheduleAllowsPosition = Boolean(
    scheduleQuery.data && (!scheduleQuery.data.required || scheduleQuery.data.schedule)
  )
  const positionQuery = useQuery({
    queryKey: ['authoritative-simulation-position', runId, branchId],
    queryFn: () => getAuthoritativeSimulationPosition(runId, branchId),
    enabled: enabled && scheduleAllowsPosition,
    retry: false
  })
  const visibleProspectsQuery = useQuery({
    queryKey: [
      'admin-visible-pre-tour-prospects',
      runId,
      branchId,
      positionQuery.data?.current_week.season_index,
      positionQuery.data?.current_week.week
    ],
    queryFn: () =>
      getAdminVisibleProspects(runId, branchId, {
        limit: 10,
        offset: 0
      }),
    enabled: Boolean(enabled && positionQuery.data),
    retry: false
  })

  const seasonTransitionPreflightQuery = useQuery({
    queryKey: [
      'authoritative-season-transition-preflight',
      runId,
      branchId,
      positionQuery.data?.position_fingerprint
    ],
    queryFn: () => getAuthoritativeSeasonTransitionPreflight(runId, branchId),
    enabled: Boolean(
      enabled &&
      positionQuery.data?.current_week.week === 61
    ),
    retry: false
  })

  const savePreviewQuery = useQuery({
    queryKey: ['authoritative-simulation-save-preview', runId, branchId],
    queryFn: () => previewAuthoritativeSimulationSave(runId, branchId),
    enabled: enabled && scheduleAllowsPosition,
    retry: false
  })
  const transitionSaveQuery = useQuery({
    queryKey: ['authoritative-week-transition-save-preview', runId, branchId],
    queryFn: () => previewRankingSave(runId, branchId),
    enabled: weekTransitionCommitted,
    retry: false
  })
  const authoritySaveQuery = useQuery({
    queryKey: ['ranking-transition-authority-save-preview', runId, branchId],
    queryFn: () => previewRankingSave(runId, branchId),
    enabled: rankingAuthorityCommitted,
    retry: false
  })

  useEffect(() => {
    setProposal(null)
    setProposalRequestId('')
    setConfirmed(false)
    setSelectedGroupId('')
    setNextMatchCommandId(newCommandId())
    setNextSlotCommandId(newCommandId())
    setWeekTransitionCommandId(newCommandId())
    setWeekTransitionReview(null)
    setWeekTransitionCommitted(false)
    setRankingAuthorityCommandId(newCommandId())
    setRankingAuthorityActor('')
    setRankingAuthorityReason('')
    setRankingAuthorityReview(null)
    setRankingAuthorityCommitted(false)
    setOrdinarySeasonCommandId(newCommandId())
    setOrdinarySeasonRevisionId(newCommandId())
    setOrdinarySeasonAuditId(newCommandId())
    setOrdinarySeasonConfirmed(false)
    setFinalSeasonCommandId(newCommandId())
    setFinalSeasonRevisionId(newCommandId())
    setFinalSeasonAuditId(newCommandId())
    setFinalSeasonConfirmed(false)
  }, [runId, branchId, savedRevisionId])

  useEffect(() => {
    const eligible = positionQuery.data?.eligible_match_ids ?? []
    if (!eligible.includes(selectedGroupId)) setSelectedGroupId(eligible[0] ?? '')
  }, [positionQuery.data, selectedGroupId])

  useEffect(() => {
    if (!positionQuery.data?.position_fingerprint) return
    setNextMatchCommandId(newCommandId())
    setNextSlotCommandId(newCommandId())
    setWeekTransitionCommandId(newCommandId())
    setWeekTransitionReview(null)
    setWeekTransitionCommitted(false)
    setRankingAuthorityCommandId(newCommandId())
    setRankingAuthorityReview(null)
    setRankingAuthorityCommitted(false)
    setOrdinarySeasonCommandId(newCommandId())
    setOrdinarySeasonRevisionId(newCommandId())
    setOrdinarySeasonAuditId(newCommandId())
    setOrdinarySeasonConfirmed(false)
    setFinalSeasonCommandId(newCommandId())
    setFinalSeasonRevisionId(newCommandId())
    setFinalSeasonAuditId(newCommandId())
    setFinalSeasonConfirmed(false)
    setConfirmed(false)
  }, [positionQuery.data?.position_fingerprint])

  useEffect(() => {
    if (!selectedGroupId) return
    setNextMatchCommandId(newCommandId())
    setConfirmed(false)
  }, [selectedGroupId])

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
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setProposal(null)
        setProposalRequestId('')
        await refreshCanonicalSimulation()
      }
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
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setProposal(null)
        setProposalRequestId('')
        await refreshCanonicalSimulation()
      }
    }
  })

  function simulationPayload(commandId: string, groupId?: string): AuthoritativeSimulationCommandPayload {
    const position = positionQuery.data
    if (!position || !savedRevisionId) throw new Error('Current authoritative position and Saved Revision head are required.')
    return {
      command_id: commandId,
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
      return simulateAuthoritativeNextMatch(runId, branchId, simulationPayload(nextMatchCommandId, selectedGroupId))
    },
    onSuccess: async (position) => {
      queryClient.setQueryData(['authoritative-simulation-position', runId, branchId], position)
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setConfirmed(false)
        await Promise.all([
          refreshCanonicalSimulation(),
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
        ])
      }
    }
  })

  const nextSlotMutation = useMutation({
    mutationFn: () => simulateAuthoritativeNextSlot(runId, branchId, simulationPayload(nextSlotCommandId)),
    onSuccess: async (position) => {
      queryClient.setQueryData(['authoritative-simulation-position', runId, branchId], position)
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setConfirmed(false)
        await Promise.all([
          refreshCanonicalSimulation(),
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
        ])
      }
    }
  })

  const ordinarySeasonMutation = useMutation({
    mutationFn: async () => {
      const preflight = seasonTransitionPreflightQuery.data
      if (
        !preflight ||
        preflight.final_season ||
        !preflight.target_week ||
        !preflight.ready_for_execution ||
        !preflight.saved_revision_id ||
        preflight.draft_version == null ||
        !preflight.default_configuration_fingerprint
      ) {
        throw new Error('Ordinary Season Transition preflight is not executable.')
      }
      if (!ordinarySeasonConfirmed) {
        throw new Error('Confirm ordinary Season Transition before execution.')
      }
      const preview = await previewAuthoritativeSeasonTransitionConfiguration(runId, branchId)
      if (preview.configuration_fingerprint !== preflight.default_configuration_fingerprint) {
        throw new Error('Season Transition configuration changed since preflight.')
      }
      return advanceAuthoritativeOrdinarySeason(runId, branchId, {
        command_id: ordinarySeasonCommandId,
        configuration: preview.configuration,
        expected_preflight_fingerprint: preflight.preflight_fingerprint,
        expected_saved_revision_id: preflight.saved_revision_id,
        expected_draft_version: preflight.draft_version,
        season_saved_revision_id: ordinarySeasonRevisionId,
        audit_event_id: ordinarySeasonAuditId
      })
    },
    onSuccess: async () => {
      setOrdinarySeasonConfirmed(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['authoritative-season-transition-preflight', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-week-schedule', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] })
      ])
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setOrdinarySeasonConfirmed(false)
        await refreshCanonicalSimulation()
      }
    }
  })

  const finalSeasonMutation = useMutation({
    mutationFn: () => {
      const preflight = seasonTransitionPreflightQuery.data
      if (
        !preflight ||
        !preflight.final_season ||
        !preflight.ready_for_execution ||
        !preflight.saved_revision_id ||
        preflight.draft_version == null
      ) {
        throw new Error('Final Season Transition preflight is not executable.')
      }
      if (!finalSeasonConfirmed) {
        throw new Error('Confirm final Run closure before execution.')
      }
      return finalizeAuthoritativeFinalSeason(runId, branchId, {
        command_id: finalSeasonCommandId,
        expected_preflight_fingerprint: preflight.preflight_fingerprint,
        expected_saved_revision_id: preflight.saved_revision_id,
        expected_draft_version: preflight.draft_version,
        final_saved_revision_id: finalSeasonRevisionId,
        audit_event_id: finalSeasonAuditId
      })
    },
    onSuccess: async () => {
      setFinalSeasonConfirmed(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['authoritative-season-transition-preflight', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] })
      ])
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setFinalSeasonConfirmed(false)
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

  const rankingAuthorityPreviewMutation = useMutation({
    mutationFn: (payload: DerivedRankingTransitionAuthorityRequest) =>
      previewDerivedRankingTransitionAuthority(runId, branchId, payload),
    onSuccess: (preview, payload) => {
      setRankingAuthorityReview({ payload, preview })
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setRankingAuthorityReview(null)
        await refreshCanonicalSimulation()
      }
    }
  })

  const rankingAuthorityConfirmMutation = useMutation({
    mutationFn: () => {
      if (!rankingAuthorityReview) {
        throw new Error('Review the derived Ranking Transition Authority first.')
      }
      return confirmDerivedRankingTransitionAuthority(
        runId,
        branchId,
        rankingAuthorityReview.payload,
        rankingAuthorityReview.preview
      )
    },
    onSuccess: async () => {
      setRankingAuthorityCommitted(true)
      await queryClient.invalidateQueries({
        queryKey: ['ranking-transition-authority-save-preview', runId, branchId]
      })
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setRankingAuthorityReview(null)
        setRankingAuthorityCommitted(false)
        setRankingAuthorityCommandId(newCommandId())
        await refreshCanonicalSimulation()
      }
    }
  })

  const rankingAuthoritySaveMutation = useMutation({
    mutationFn: () => {
      if (!authoritySaveQuery.data?.can_save) {
        throw new Error('Reviewed Ranking Transition Authority has no saveable ranking draft.')
      }
      return saveRankingPreparation(runId, branchId, authoritySaveQuery.data)
    },
    onSuccess: async () => {
      setRankingAuthorityReview(null)
      setRankingAuthorityCommitted(false)
      setRankingAuthorityCommandId(newCommandId())
      rankingAuthorityConfirmMutation.reset()
      rankingAuthorityPreviewMutation.reset()
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-candidates', runId, branchId] }),
        refreshCanonicalSimulation()
      ])
    },
    onError: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['ranking-transition-authority-save-preview', runId, branchId]
      })
    }
  })

  const weekTransitionPreviewMutation = useMutation({
    mutationFn: () => {
      if (!positionQuery.data?.week_ready_for_transition) {
        throw new Error('Canonical week is not ready for Week Transition.')
      }
      return previewDerivedAuthoritativeWeekTransition(runId, branchId, weekTransitionCommandId)
    },
    onSuccess: (preview) => setWeekTransitionReview(preview),
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setWeekTransitionReview(null)
        await refreshCanonicalSimulation()
      }
    }
  })

  const weekTransitionConfirmMutation = useMutation({
    mutationFn: () => {
      if (!weekTransitionReview) throw new Error('Review the derived Week Transition preview first.')
      return confirmAuthoritativeWeekTransition(runId, branchId, weekTransitionReview)
    },
    onSuccess: async () => {
      setWeekTransitionCommitted(true)
      await queryClient.invalidateQueries({
        queryKey: ['authoritative-week-transition-save-preview', runId, branchId]
      })
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setWeekTransitionReview(null)
        setWeekTransitionCommitted(false)
        setWeekTransitionCommandId(newCommandId())
        await Promise.all([
          refreshCanonicalSimulation(),
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] })
        ])
      }
    }
  })

  const weekTransitionSaveMutation = useMutation({
    mutationFn: () => {
      if (!transitionSaveQuery.data?.can_save) {
        throw new Error('Reviewed Week Transition has no saveable ranking/world draft.')
      }
      return saveRankingPreparation(runId, branchId, transitionSaveQuery.data)
    },
    onSuccess: async () => {
      setWeekTransitionReview(null)
      setWeekTransitionCommitted(false)
      setWeekTransitionCommandId(newCommandId())
      weekTransitionConfirmMutation.reset()
      weekTransitionPreviewMutation.reset()
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-candidates', runId, branchId] }),
        refreshCanonicalSimulation()
      ])
    },
    onError: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['authoritative-week-transition-save-preview', runId, branchId]
      })
    }
  })

  const schedule = scheduleQuery.data?.schedule
  const position = positionQuery.data
  const rankingAuthorityMissing = Boolean(
    position?.transition_blockers.includes('ranking_transition_authority_missing')
  )
  const rankingAuthorityCanPrepare = Boolean(
    position &&
    position.transition_blockers.length === 1 &&
    rankingAuthorityMissing
  )
  const actionPending = nextMatchMutation.isPending || nextSlotMutation.isPending

  return (
    <SectionCard title="Canonical authoritative sporting simulation">
      <p className="status">
        Run/Branch-owned sporting path: Week Schedule → Position → Next Match / Next Slot → Save.
        It does not use the legacy simulation-run binding.
      </p>

      {blockedReason ? <p role="alert" className="error">Canonical simulation blocked: {blockedReason}</p> : null}
      {!blockedReason && !savedRevisionId ? (
        <p role="alert" className="error">Canonical simulation blocked: Branch has no Saved Revision head.</p>
      ) : null}

      {(scheduleQuery.isLoading || savePreviewQuery.isLoading || (scheduleAllowsPosition && positionQuery.isLoading)) && enabled ? (
        <p className="status">Loading authoritative sporting state…</p>
      ) : null}
      {positionQuery.error ? <p className="error">Position unavailable: {formatApiError(positionQuery.error)}</p> : null}
      {scheduleQuery.error ? <p className="error">Week Schedule unavailable: {formatApiError(scheduleQuery.error)}</p> : null}
      {savePreviewQuery.error ? <p className="error">Save preview unavailable: {formatApiError(savePreviewQuery.error)}</p> : null}

      {position ? (
        <>
          <SummaryPills
            items={[
              { label: 'Week', value: `Season index ${position.current_week.season_index} · Week ${position.current_week.week}` },
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
          <h4>Historically visible pre-Tour prospects</h4>
          {visibleProspectsQuery.isLoading ? (
            <p className="status">Loading lifecycle-visible prospects…</p>
          ) : null}
          {visibleProspectsQuery.error ? (
            <p className="error">
              Prospect visibility unavailable: {formatApiError(visibleProspectsQuery.error)}
            </p>
          ) : null}
          {visibleProspectsQuery.data ? (
            <>
              <MetadataList
                items={[
                  { label: 'Visible prospect count', value: visibleProspectsQuery.data.total },
                  {
                    label: 'Lifecycle week',
                    value: `Season index ${visibleProspectsQuery.data.week.season_index} · Week ${visibleProspectsQuery.data.week.week}`
                  },
                  {
                    label: 'Returned',
                    value: visibleProspectsQuery.data.prospects.length
                  }
                ]}
              />
              {visibleProspectsQuery.data.prospects.length ? (
                <ul aria-label="Canonical visible pre-Tour prospects">
                  {visibleProspectsQuery.data.prospects.map((prospect) => (
                    <li key={prospect.player_id}>
                      {prospect.display_name} · {prospect.country_code} · age {prospect.age}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="status">No pre-Tour prospects are visible in this lifecycle week.</p>
              )}
            </>
          ) : null}
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
              <p className="status">
                Canonical Position and match execution stay locked until this required immutable Week Schedule is adopted.
              </p>
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

      {position && (rankingAuthorityMissing || rankingAuthorityCommitted) ? (
        <>
          <h4>Ranking Transition Authority</h4>
          <p className="status">
            The server derives the target-week lifecycle roster and reuses the predecessor Official Ranking policy. Admin supplies only audit provenance.
          </p>

          {!rankingAuthorityCommitted ? (
            rankingAuthorityCanPrepare ? (
              <>
                <label>
                  Operator label
                  <input
                    value={rankingAuthorityActor}
                    maxLength={128}
                    disabled={Boolean(rankingAuthorityReview) || rankingAuthorityPreviewMutation.isPending}
                    onChange={(event) => setRankingAuthorityActor(event.target.value)}
                  />
                </label>
                <label>
                  Authority reason
                  <textarea
                    value={rankingAuthorityReason}
                    maxLength={2000}
                    disabled={Boolean(rankingAuthorityReview) || rankingAuthorityPreviewMutation.isPending}
                    onChange={(event) => setRankingAuthorityReason(event.target.value)}
                  />
                </label>
                {!rankingAuthorityReview ? (
                  <button
                    type="button"
                    disabled={
                      !rankingAuthorityActor.trim() ||
                      !rankingAuthorityReason.trim() ||
                      rankingAuthorityPreviewMutation.isPending
                    }
                    onClick={() => rankingAuthorityPreviewMutation.mutate({
                      command_id: rankingAuthorityCommandId,
                      audit: {
                        actor_label: rankingAuthorityActor.trim(),
                        reason: rankingAuthorityReason.trim()
                      }
                    })}
                  >
                    Review derived Ranking Transition Authority
                  </button>
                ) : null}
                {rankingAuthorityPreviewMutation.error ? (
                  <p className="error">
                    Ranking Transition Authority preview failed: {formatApiError(rankingAuthorityPreviewMutation.error)}
                  </p>
                ) : null}
                {rankingAuthorityReview ? (
                  <>
                    <MetadataList
                      items={[
                        {
                          label: 'Completed week',
                          value: `Season index ${rankingAuthorityReview.preview.authority.completed_week.season_index} · Week ${rankingAuthorityReview.preview.authority.completed_week.week}`
                        },
                        {
                          label: 'Target week',
                          value: `Season index ${rankingAuthorityReview.preview.authority.target_week.season_index} · Week ${rankingAuthorityReview.preview.authority.target_week.week}`
                        },
                        { label: 'Target roster', value: rankingAuthorityReview.preview.authority.players.length },
                        { label: 'Policy ID', value: rankingAuthorityReview.preview.authority.policy.policy_id },
                        { label: 'Best N', value: rankingAuthorityReview.preview.authority.policy.best_n },
                        { label: 'Base Saved Revision', value: rankingAuthorityReview.preview.authority.base_revision_id },
                        { label: 'Authority fingerprint', value: rankingAuthorityReview.preview.authority_fingerprint }
                      ]}
                    />
                    <button
                      type="button"
                      disabled={rankingAuthorityConfirmMutation.isPending}
                      onClick={() => rankingAuthorityConfirmMutation.mutate()}
                    >
                      Confirm reviewed Ranking Transition Authority
                    </button>
                    <button
                      type="button"
                      disabled={rankingAuthorityConfirmMutation.isPending}
                      onClick={() => {
                        setRankingAuthorityReview(null)
                        rankingAuthorityPreviewMutation.reset()
                        rankingAuthorityConfirmMutation.reset()
                      }}
                    >
                      Edit authority audit
                    </button>
                  </>
                ) : null}
                {rankingAuthorityConfirmMutation.error ? (
                  <p className="error">
                    Ranking Transition Authority confirm failed: {formatApiError(rankingAuthorityConfirmMutation.error)}
                  </p>
                ) : null}
              </>
            ) : (
              <p className="status">
                Ranking Transition Authority is missing, but other canonical blockers must be resolved first.
              </p>
            )
          ) : null}

          {rankingAuthorityCommitted ? (
            <>
              <p className="status">
                Ranking Transition Authority is committed to the ranking draft. Save it as a recoverable Saved Revision before advancing the week.
              </p>
              {authoritySaveQuery.isLoading ? <p className="status">Loading authority Save preview…</p> : null}
              {authoritySaveQuery.error ? (
                <p className="error">Authority Save preview failed: {formatApiError(authoritySaveQuery.error)}</p>
              ) : null}
              {authoritySaveQuery.data ? (
                <button
                  type="button"
                  disabled={!authoritySaveQuery.data.can_save || rankingAuthoritySaveMutation.isPending}
                  onClick={() => rankingAuthoritySaveMutation.mutate()}
                >
                  Save Ranking Transition Authority
                </button>
              ) : null}
              {rankingAuthoritySaveMutation.error ? (
                <p className="error">Authority Save failed: {formatApiError(rankingAuthoritySaveMutation.error)}</p>
              ) : null}
            </>
          ) : null}
        </>
      ) : null}

      {position?.current_week.week === 61 ? (
        <>
          <h4>Canonical Season Transition preflight</h4>
          <p className="status">
            Week 61 crosses a season boundary. Ordinary rollover becomes executable when this exact persisted state has no branch blocker and no boundary-specific engine gap; the final 2049/50 closure uses its dedicated terminal path.
          </p>
          {seasonTransitionPreflightQuery.isLoading ? (
            <p className="status">Loading Season Transition preflight…</p>
          ) : null}
          {seasonTransitionPreflightQuery.error ? (
            <p className="error">
              Season Transition preflight failed: {formatApiError(seasonTransitionPreflightQuery.error)}
            </p>
          ) : null}
          {seasonTransitionPreflightQuery.data ? (
            <>
              <MetadataList
                items={[
                  {
                    label: 'Completed season boundary',
                    value: `Season index ${seasonTransitionPreflightQuery.data.completed_week.season_index} · Week ${seasonTransitionPreflightQuery.data.completed_week.week}`
                  },
                  {
                    label: 'Target',
                    value: seasonTransitionPreflightQuery.data.final_season
                      ? 'Final Run closure — no next season'
                      : `Season index ${seasonTransitionPreflightQuery.data.target_week?.season_index} · Week 1`
                  },
                  {
                    label: 'Saved Revision head',
                    value: seasonTransitionPreflightQuery.data.saved_revision_id ?? '—'
                  },
                  {
                    label: 'State blockers',
                    value: seasonTransitionPreflightQuery.data.state_blockers.length
                  },
                  {
                    label: 'Implementation gaps',
                    value: seasonTransitionPreflightQuery.data.implementation_gaps.length
                  },
                  {
                    label: 'Execution available',
                    value: seasonTransitionPreflightQuery.data.ready_for_execution ? 'Yes' : 'No'
                  },
                  {
                    label: 'Closing Ranking candidate',
                    value: seasonTransitionPreflightQuery.data.default_closing_ranking_fingerprint ?? '—'
                  },
                  {
                    label: 'Preflight fingerprint',
                    value: seasonTransitionPreflightQuery.data.preflight_fingerprint
                  }
                ]}
              />
              {seasonTransitionPreflightQuery.data.state_blockers.length ? (
                <>
                  <strong>Current branch blockers</strong>
                  <ul aria-label="Season Transition state blockers">
                    {seasonTransitionPreflightQuery.data.state_blockers.map((blocker) => (
                      <li key={blocker}>{blocker}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="status">
                  Current persisted Week 61 state has no additional branch-specific blocker.
                </p>
              )}
              {seasonTransitionPreflightQuery.data.implementation_gaps.length ? (
                <>
                  <strong>Engine implementation gaps</strong>
                  <ul aria-label="Season Transition implementation gaps">
                    {seasonTransitionPreflightQuery.data.implementation_gaps.map((gap) => (
                      <li key={gap}>{gap}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="status">
                  No boundary-specific engine implementation gap remains for this transition.
                </p>
              )}
              {!seasonTransitionPreflightQuery.data.final_season &&
              seasonTransitionPreflightQuery.data.ready_for_execution &&
              seasonTransitionPreflightQuery.data.target_week ? (
                <>
                  <p className="status">
                    Ordinary rollover is atomic: Closing Ranking, Season Summary/Marker, Week-1 sporting and lifecycle state, Official Ranking publication, world state and the new Saved Revision commit together.
                  </p>
                  {!ordinarySeasonConfirmed ? (
                    <button
                      type="button"
                      onClick={() => setOrdinarySeasonConfirmed(true)}
                      disabled={ordinarySeasonMutation.isPending}
                    >
                      Review Season Transition
                    </button>
                  ) : (
                    <>
                      <p className="status">
                        Confirm opening Season index {seasonTransitionPreflightQuery.data.target_week.season_index} · Week 1. A failure rolls back the complete rollover.
                      </p>
                      <button
                        type="button"
                        onClick={() => ordinarySeasonMutation.mutate()}
                        disabled={ordinarySeasonMutation.isPending}
                      >
                        Advance to next season
                      </button>
                      <button
                        type="button"
                        onClick={() => setOrdinarySeasonConfirmed(false)}
                        disabled={ordinarySeasonMutation.isPending}
                      >
                        Cancel
                      </button>
                    </>
                  )}
                  {ordinarySeasonMutation.error ? (
                    <p className="error">
                      Season Transition failed: {formatApiError(ordinarySeasonMutation.error)}
                    </p>
                  ) : null}
                  {ordinarySeasonMutation.data ? (
                    <MetadataList
                      items={[
                        { label: 'New Saved Revision', value: ordinarySeasonMutation.data.saved_revision_id },
                        { label: 'Closing Ranking', value: ordinarySeasonMutation.data.closing_ranking_fingerprint },
                        { label: 'Week-1 Official Ranking', value: ordinarySeasonMutation.data.official_ranking_fingerprint },
                        { label: 'Closure Marker', value: ordinarySeasonMutation.data.closure_marker_fingerprint }
                      ]}
                    />
                  ) : null}
                </>
              ) : null}
              {seasonTransitionPreflightQuery.data.final_season &&
              seasonTransitionPreflightQuery.data.ready_for_execution ? (
                <>
                  <p className="status">
                    Final closure is atomic: Closing Ranking, Season Summary, Closure Marker, final Saved Revision and Run Completed commit together. No 2050/51 Week 1 is created.
                  </p>
                  {!finalSeasonConfirmed ? (
                    <button
                      type="button"
                      onClick={() => setFinalSeasonConfirmed(true)}
                      disabled={finalSeasonMutation.isPending}
                    >
                      Review final Run closure
                    </button>
                  ) : (
                    <>
                      <p className="status">
                        Confirm permanent completion of this timeline at 2049/50 Week 61. Earlier Saved Revisions remain available for alternative branches.
                      </p>
                      <button
                        type="button"
                        onClick={() => finalSeasonMutation.mutate()}
                        disabled={finalSeasonMutation.isPending}
                      >
                        Finalize 2049/50
                      </button>
                      <button
                        type="button"
                        onClick={() => setFinalSeasonConfirmed(false)}
                        disabled={finalSeasonMutation.isPending}
                      >
                        Cancel
                      </button>
                    </>
                  )}
                  {finalSeasonMutation.error ? (
                    <p className="error">
                      Final Run closure failed: {formatApiError(finalSeasonMutation.error)}
                    </p>
                  ) : null}
                  {finalSeasonMutation.data ? (
                    <MetadataList
                      items={[
                        { label: 'Run status', value: finalSeasonMutation.data.run_status },
                        { label: 'Final Saved Revision', value: finalSeasonMutation.data.saved_revision_id },
                        { label: 'Closing Ranking', value: finalSeasonMutation.data.closing_ranking_fingerprint },
                        { label: 'Closure Marker', value: finalSeasonMutation.data.closure_marker_fingerprint }
                      ]}
                    />
                  ) : null}
                </>
              ) : null}
            </>
          ) : null}
        </>
      ) : null}

      {position && position.current_week.week !== 61 ? (
        <>
          <h4>Canonical Week Transition</h4>
          {!position.week_ready_for_transition ? (
            <p className="status">
              Week Transition is not ready. Resolve the canonical blockers shown above before advancing world time.
            </p>
          ) : (
            <>
              <p className="status">
                The server derives the exact transition request from the Saved Revision head, frozen Ranking Transition Authority and owned tournament sources.
              </p>
              {!weekTransitionCommitted ? (
                <button
                  type="button"
                  onClick={() => weekTransitionPreviewMutation.mutate()}
                  disabled={weekTransitionPreviewMutation.isPending || weekTransitionConfirmMutation.isPending}
                >
                  Review derived Week Transition
                </button>
              ) : null}
              {weekTransitionPreviewMutation.error ? (
                <p className="error">Week Transition preview failed: {formatApiError(weekTransitionPreviewMutation.error)}</p>
              ) : null}
              {weekTransitionReview ? (
                <>
                  <MetadataList
                    items={[
                      {
                        label: 'Completed week',
                        value: `Season index ${weekTransitionReview.command.completed_week.season_index} · Week ${weekTransitionReview.command.completed_week.week}`
                      },
                      {
                        label: 'Target week',
                        value: `Season index ${weekTransitionReview.command.target_week.season_index} · Week ${weekTransitionReview.command.target_week.week}`
                      },
                      { label: 'Tournament bindings', value: weekTransitionReview.command.tournaments.length },
                      { label: 'Base Saved Revision', value: weekTransitionReview.command.base_revision_id },
                      { label: 'Request fingerprint', value: weekTransitionReview.request_fingerprint },
                      { label: 'Preview ranking fingerprint', value: weekTransitionReview.result.official_ranking_fingerprint }
                    ]}
                  />
                  {!weekTransitionCommitted ? (
                    <button
                      type="button"
                      onClick={() => weekTransitionConfirmMutation.mutate()}
                      disabled={weekTransitionConfirmMutation.isPending}
                    >
                      Confirm reviewed Week Transition
                    </button>
                  ) : null}
                </>
              ) : null}
              {weekTransitionConfirmMutation.error ? (
                <p className="error">Week Transition confirm failed: {formatApiError(weekTransitionConfirmMutation.error)}</p>
              ) : null}
            </>
          )}

          {weekTransitionCommitted ? (
            <>
              <p className="status">
                Week Transition committed to the Branch Working Draft. Save it as a recoverable Saved Revision before continuing simulation.
              </p>
              {transitionSaveQuery.isLoading ? <p className="status">Loading transition Save preview…</p> : null}
              {transitionSaveQuery.error ? (
                <p className="error">Transition Save preview failed: {formatApiError(transitionSaveQuery.error)}</p>
              ) : null}
              {transitionSaveQuery.data ? (
                <button
                  type="button"
                  onClick={() => weekTransitionSaveMutation.mutate()}
                  disabled={!transitionSaveQuery.data.can_save || weekTransitionSaveMutation.isPending}
                >
                  Save transitioned week
                </button>
              ) : null}
              {weekTransitionSaveMutation.error ? (
                <p className="error">Transition Save failed: {formatApiError(weekTransitionSaveMutation.error)}</p>
              ) : null}
              {weekTransitionSaveMutation.isSuccess ? (
                <p className="status">Transitioned week saved. Canonical simulation can continue from the new world head.</p>
              ) : null}
            </>
          ) : null}
        </>
      ) : null}
    </SectionCard>
  )
}

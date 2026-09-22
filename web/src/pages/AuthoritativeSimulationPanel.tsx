import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  adoptAuthoritativeWeekScheduleProposal,
  adoptAuthoritativeWeekSchedule,
  getAuthoritativeSimulationPosition,
  inspectAuthoritativeEntryDecisionSlot,
  reviewAuthoritativeEntryDecisionSlot,
  inspectWeekTournamentLock,
  previewWeekTournamentLock,
  commitWeekTournamentLock,
  getAuthoritativeSeasonTransitionPreflight,
  getAdminVisibleProspects,
  previewAuthoritativeSeasonTransitionConfiguration,
  advanceAuthoritativeOrdinarySeason,
  finalizeAuthoritativeFinalSeason,
  inspectAuthoritativeWeekSchedule,
  previewAuthoritativeSimulationSave,
  proposeAuthoritativeWeekSchedule,
  previewAuthoritativeWeekSchedule,
  saveAuthoritativeSimulation,
  simulateAuthoritativeNextMatch,
  simulateAuthoritativeNextSlot,
  previewAuthoritativeNextMatchDay,
  simulateAuthoritativeNextMatchDay,
  previewAuthoritativeNextRound,
  simulateAuthoritativeNextRound,
  previewAuthoritativeNextTournament,
  simulateAuthoritativeNextTournament,
  previewAuthoritativeNextWeek,
  simulateAuthoritativeNextWeek,
  previewAuthoritativeNextSeason,
  simulateAuthoritativeNextSeason,
  previewAuthoritativeFullSimulation,
  simulateAuthoritativeFullSimulation,
  inspectAuthoritativeMatchReconstruction,
  previewAuthoritativeMatchReconstruction,
  commitAuthoritativeMatchReconstruction,
  previewDerivedAuthoritativeWeekTransition,
  confirmAuthoritativeWeekTransition,
  previewRankingSave,
  saveRankingPreparation,
  previewDerivedRankingTransitionAuthority,
  confirmDerivedRankingTransitionAuthority
} from '../api/client'
import type {
  AuthoritativeSimulationCommandPayload,
  AuthoritativeMatchDayPreview,
  AuthoritativeRoundPreview,
  AuthoritativeTournamentPreview,
  AuthoritativeWeekPreview,
  AuthoritativeWeekProgress,
  AuthoritativeSeasonPreview,
  AuthoritativeSeasonProgress,
  AuthoritativeFullSimulationPreview,
  AuthoritativeFullSimulationProgress,
  AuthoritativeWeekSchedule,
  AuthoritativeWeekScheduleProposal,
  AuthoritativeWeekScheduleManualPreview,
  AuthoritativeApplicationValidationReview,
  WeekTournamentLockPreview,
  WeekTournamentLockPreviewPayload,
  AuthoritativeMatchReconstructionPreview,
  AuthoritativeMatchReconstructionPreviewPayload,
  MatchReconstructionConstraints,
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

type EntryValidationDraft = {
  outcome: '' | 'valid' | 'invalid'
  reason: string
}

type MatchDayScheduleDraft = Record<
  string,
  {
    day: string
    order: string
  }
>

function seedMatchDayScheduleDraft(
  schedule: AuthoritativeWeekSchedule
): MatchDayScheduleDraft {
  const next: MatchDayScheduleDraft = {}
  for (const slot of schedule.slots) {
    const groupId = slot.group_ids[0]
    if (!groupId || slot.match_day_ordinal == null || slot.match_order == null) continue
    next[groupId] = {
      day: String(slot.match_day_ordinal),
      order: String(slot.match_order)
    }
  }
  return next
}

function editedMatchDaySchedule(
  source: AuthoritativeWeekSchedule,
  draft: MatchDayScheduleDraft
): AuthoritativeWeekSchedule {
  if (source.schema_version !== 'week_simulation_schedule.v2') {
    throw new Error('Manual Match Day editing requires Week Simulation Schedule v2.')
  }
  const ordinalPool = source.slots.map((slot) => slot.ordinal).sort((a, b) => a - b)
  const rows = source.slots.map((slot) => {
    const groupId = slot.group_ids[0]
    if (!groupId) throw new Error('Every Match Day slot must contain one group.')
    const value = draft[groupId]
    const day = Number(value?.day ?? slot.match_day_ordinal)
    const requestedOrder = Number(value?.order ?? slot.match_order)
    if (!Number.isInteger(day) || day < 1) {
      throw new Error(`Match Day for ${groupId} must be a positive integer.`)
    }
    if (!Number.isInteger(requestedOrder) || requestedOrder < 1) {
      throw new Error(`Match order for ${groupId} must be a positive integer.`)
    }
    return { slot, groupId, day, requestedOrder }
  })
  rows.sort(
    (a, b) =>
      a.day - b.day ||
      a.requestedOrder - b.requestedOrder ||
      a.slot.ordinal - b.slot.ordinal ||
      a.groupId.localeCompare(b.groupId)
  )

  const nextOrderByDay = new Map<number, number>()
  const slots = rows.map((row, index) => {
    const matchOrder = (nextOrderByDay.get(row.day) ?? 0) + 1
    nextOrderByDay.set(row.day, matchOrder)
    return {
      ...row.slot,
      ordinal: ordinalPool[index],
      match_day_ordinal: row.day,
      match_order: matchOrder
    }
  })
  return { ...source, slots }
}

function entryValidationKey(eventId: string, playerId: string): string {
  return `${eventId}\u001f${playerId}`
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
  const [reconstructionCandidateCount, setReconstructionCandidateCount] = useState('10')
  const [reconstructionWinnerId, setReconstructionWinnerId] = useState('')
  const [reconstructionMatchScore, setReconstructionMatchScore] = useState('')
  const [reconstructionGameScores, setReconstructionGameScores] = useState('')
  const [reconstructionOperator, setReconstructionOperator] = useState('')
  const [reconstructionReason, setReconstructionReason] = useState('')
  const [reconstructionCommandId, setReconstructionCommandId] = useState(newCommandId)
  const [reconstructionReview, setReconstructionReview] = useState<{
    payload: AuthoritativeMatchReconstructionPreviewPayload
    preview: AuthoritativeMatchReconstructionPreview
  } | null>(null)
  const [selectedReconstructionCandidate, setSelectedReconstructionCandidate] = useState('')
  const [proposal, setProposal] = useState<AuthoritativeWeekScheduleProposal | null>(null)
  const [proposalRequestId, setProposalRequestId] = useState('')
  const [manualScheduleDraft, setManualScheduleDraft] =
    useState<MatchDayScheduleDraft>({})
  const [manualScheduleRequestId, setManualScheduleRequestId] = useState(newCommandId)
  const [manualScheduleReview, setManualScheduleReview] = useState<{
    schedule: AuthoritativeWeekSchedule
    preview: AuthoritativeWeekScheduleManualPreview
  } | null>(null)
  const [nextMatchCommandId, setNextMatchCommandId] = useState(newCommandId)
  const [nextSlotCommandId, setNextSlotCommandId] = useState(newCommandId)
  const [nextMatchDayCommandId, setNextMatchDayCommandId] = useState(newCommandId)
  const [nextMatchDayReview, setNextMatchDayReview] =
    useState<AuthoritativeMatchDayPreview | null>(null)
  const [nextRoundCommandId, setNextRoundCommandId] = useState(newCommandId)
  const [nextRoundReview, setNextRoundReview] =
    useState<AuthoritativeRoundPreview | null>(null)
  const [nextTournamentCommandId, setNextTournamentCommandId] = useState(newCommandId)
  const [nextTournamentReview, setNextTournamentReview] =
    useState<AuthoritativeTournamentPreview | null>(null)
  const [nextWeekCommandId, setNextWeekCommandId] = useState(newCommandId)
  const [nextWeekOperator, setNextWeekOperator] = useState('')
  const [nextWeekReason, setNextWeekReason] = useState('')
  const [nextWeekReview, setNextWeekReview] =
    useState<AuthoritativeWeekPreview | null>(null)
  const [nextWeekProgress, setNextWeekProgress] =
    useState<AuthoritativeWeekProgress | null>(null)
  const [nextSeasonCommandId, setNextSeasonCommandId] = useState(newCommandId)
  const [nextSeasonOperator, setNextSeasonOperator] = useState('')
  const [nextSeasonReason, setNextSeasonReason] = useState('')
  const [nextSeasonReview, setNextSeasonReview] =
    useState<AuthoritativeSeasonPreview | null>(null)
  const [nextSeasonProgress, setNextSeasonProgress] =
    useState<AuthoritativeSeasonProgress | null>(null)
  const [fullSimulationCommandId, setFullSimulationCommandId] = useState(newCommandId)
  const [fullSimulationOperator, setFullSimulationOperator] = useState('')
  const [fullSimulationReason, setFullSimulationReason] = useState('')
  const [fullSimulationReview, setFullSimulationReview] =
    useState<AuthoritativeFullSimulationPreview | null>(null)
  const [fullSimulationProgress, setFullSimulationProgress] =
    useState<AuthoritativeFullSimulationProgress | null>(null)
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
  const [entryValidationCommandId, setEntryValidationCommandId] = useState(newCommandId)
  const [entryValidationOperator, setEntryValidationOperator] = useState('')
  const [entryValidationReason, setEntryValidationReason] = useState('')
  const [entryValidationDrafts, setEntryValidationDrafts] =
    useState<Record<string, EntryValidationDraft>>({})
  const [weekLockCommandId, setWeekLockCommandId] = useState(newCommandId)
  const [weekLockOperator, setWeekLockOperator] = useState('')
  const [weekLockReason, setWeekLockReason] = useState('')
  const [weekLockSelections, setWeekLockSelections] =
    useState<Record<string, string>>({})
  const [weekLockReview, setWeekLockReview] = useState<{
    payload: WeekTournamentLockPreviewPayload
    preview: WeekTournamentLockPreview
  } | null>(null)

  const weekLockQuery = useQuery({
    queryKey: ['authoritative-week-tournament-lock', runId, branchId],
    queryFn: () => inspectWeekTournamentLock(runId, branchId),
    enabled,
    retry: false
  })

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
  const reconstructionStateQuery = useQuery({
    queryKey: ['authoritative-match-reconstruction-state', runId, branchId, selectedGroupId],
    queryFn: () => inspectAuthoritativeMatchReconstruction(runId, branchId, selectedGroupId),
    enabled: Boolean(
      enabled &&
      positionQuery.data?.current_slot_kind === 'match' &&
      selectedGroupId
    ),
    retry: false
  })

  const currentEntrySlotOrdinal =
    positionQuery.data?.current_slot_kind === 'entry'
      ? positionQuery.data.slot_ordinal
      : null
  const entrySlotQuery = useQuery({
    queryKey: [
      'authoritative-entry-decision-slot',
      runId,
      branchId,
      currentEntrySlotOrdinal
    ],
    queryFn: () =>
      inspectAuthoritativeEntryDecisionSlot(
        runId,
        branchId,
        currentEntrySlotOrdinal as number
      ),
    enabled: Boolean(enabled && currentEntrySlotOrdinal != null),
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
    setNextSeasonCommandId(newCommandId())
    setNextSeasonOperator('')
    setNextSeasonReason('')
    setNextSeasonReview(null)
    setNextSeasonProgress(null)
  }, [runId, branchId])

  useEffect(() => {
    setFullSimulationCommandId(newCommandId())
    setFullSimulationOperator('')
    setFullSimulationReason('')
    setFullSimulationReview(null)
    setFullSimulationProgress(null)
  }, [runId, branchId])

  useEffect(() => {
    setProposal(null)
    setProposalRequestId('')
    setManualScheduleDraft({})
    setManualScheduleRequestId(newCommandId())
    setManualScheduleReview(null)
    setConfirmed(false)
    setSelectedGroupId('')
    setNextMatchCommandId(newCommandId())
    setNextSlotCommandId(newCommandId())
    setNextMatchDayCommandId(newCommandId())
    setNextMatchDayReview(null)
    setNextRoundCommandId(newCommandId())
    setNextRoundReview(null)
    setNextTournamentCommandId(newCommandId())
    setNextTournamentReview(null)
    setNextWeekCommandId(newCommandId())
    setNextWeekOperator('')
    setNextWeekReason('')
    setNextWeekReview(null)
    setNextWeekProgress(null)
    setReconstructionCandidateCount('10')
    setReconstructionWinnerId('')
    setReconstructionMatchScore('')
    setReconstructionGameScores('')
    setReconstructionOperator('')
    setReconstructionReason('')
    setReconstructionCommandId(newCommandId())
    setReconstructionReview(null)
    setSelectedReconstructionCandidate('')
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
    setEntryValidationCommandId(newCommandId())
    setEntryValidationOperator('')
    setEntryValidationReason('')
    setEntryValidationDrafts({})
    setWeekLockCommandId(newCommandId())
    setWeekLockOperator('')
    setWeekLockReason('')
    setWeekLockSelections({})
    setWeekLockReview(null)
  }, [runId, branchId, savedRevisionId])

  useEffect(() => {
    const inspection = weekLockQuery.data
    setWeekLockReview(null)
    setWeekLockCommandId(newCommandId())
    if (!inspection || inspection.lock_status !== 'required') {
      setWeekLockSelections({})
      return
    }
    const next: Record<string, string> = {}
    for (const conflict of inspection.conflicts) {
      next[conflict.player_id] = ''
    }
    setWeekLockSelections(next)
  }, [
    weekLockQuery.data?.position_fingerprint,
    weekLockQuery.data?.authority_fingerprint,
    weekLockQuery.data?.lock_status
  ])

  useEffect(() => {
    const eligible = positionQuery.data?.eligible_match_ids ?? []
    if (!eligible.includes(selectedGroupId)) setSelectedGroupId(eligible[0] ?? '')
  }, [positionQuery.data, selectedGroupId])

  useEffect(() => {
    if (!positionQuery.data?.position_fingerprint) return
    setNextMatchCommandId(newCommandId())
    setNextSlotCommandId(newCommandId())
    setNextMatchDayCommandId(newCommandId())
    setNextMatchDayReview(null)
    setNextRoundCommandId(newCommandId())
    setNextRoundReview(null)
    setNextTournamentCommandId(newCommandId())
    setNextTournamentReview(null)
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
    setEntryValidationCommandId(newCommandId())
    setConfirmed(false)
  }, [positionQuery.data?.position_fingerprint])

  useEffect(() => {
    const inspection = entrySlotQuery.data
    if (!inspection || inspection.validation_resolved) {
      setEntryValidationDrafts({})
      return
    }
    const nextDrafts: Record<string, EntryValidationDraft> = {}
    for (const decision of inspection.authority.decisions) {
      nextDrafts[entryValidationKey(decision.event_id, decision.player_id)] = {
        outcome: '',
        reason: ''
      }
    }
    setEntryValidationDrafts(nextDrafts)
    setEntryValidationCommandId(newCommandId())
    setEntryValidationOperator('')
    setEntryValidationReason('')
  }, [entrySlotQuery.data?.slot_fingerprint, entrySlotQuery.data?.validation_resolved])

  useEffect(() => {
    if (!selectedGroupId) return
    setNextMatchCommandId(newCommandId())
    setReconstructionCommandId(newCommandId())
    setReconstructionReview(null)
    setSelectedReconstructionCandidate('')
    setConfirmed(false)
  }, [selectedGroupId])

  async function refreshCanonicalSimulation(): Promise<void> {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] }),
      queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-week-schedule', runId, branchId] }),
      queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-save-preview', runId, branchId] }),
      queryClient.invalidateQueries({ queryKey: ['authoritative-entry-decision-slot', runId, branchId] }),
      queryClient.invalidateQueries({ queryKey: ['authoritative-week-tournament-lock', runId, branchId] }),
      queryClient.invalidateQueries({ queryKey: ['canonical-entry-field'] })
    ])
  }

  const proposalMutation = useMutation({
    mutationFn: () => proposeAuthoritativeWeekSchedule(runId, branchId),
    onSuccess: (value) => {
      setProposal(value)
      setProposalRequestId(newCommandId())
      setManualScheduleDraft(seedMatchDayScheduleDraft(value.schedule))
      setManualScheduleRequestId(newCommandId())
      setManualScheduleReview(null)
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setProposal(null)
        setProposalRequestId('')
        setManualScheduleDraft({})
        setManualScheduleReview(null)
        await refreshCanonicalSimulation()
      }
    }
  })

  const adoptMutation = useMutation({
    mutationFn: () => {
      if (!proposal || !proposalRequestId) throw new Error('Review the current Match Day schedule proposal first.')
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
      setManualScheduleDraft({})
      setManualScheduleReview(null)
      setManualScheduleRequestId(newCommandId())
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setProposal(null)
        setProposalRequestId('')
        setManualScheduleDraft({})
        setManualScheduleReview(null)
        await refreshCanonicalSimulation()
      }
    }
  })

  const manualSchedulePreviewMutation = useMutation({
    mutationFn: async () => {
      if (!proposal) {
        throw new Error('Build the canonical Match Day proposal before editing it.')
      }
      const schedule = editedMatchDaySchedule(
        proposal.schedule,
        manualScheduleDraft
      )
      const preview = await previewAuthoritativeWeekSchedule(
        runId,
        branchId,
        { schedule }
      )
      return { schedule, preview }
    },
    onSuccess: (review) => setManualScheduleReview(review),
    onError: async (error) => {
      setManualScheduleReview(null)
      if ((error as { status?: number }).status === 409) {
        await refreshCanonicalSimulation()
      }
    }
  })

  const manualScheduleAdoptMutation = useMutation({
    mutationFn: () => {
      if (!manualScheduleReview) {
        throw new Error('Review the edited Match Day schedule before adoption.')
      }
      return adoptAuthoritativeWeekSchedule(runId, branchId, {
        request_id: manualScheduleRequestId,
        schedule: manualScheduleReview.schedule,
        expected_position_fingerprint:
          manualScheduleReview.preview.position_fingerprint
      })
    },
    onSuccess: async () => {
      setProposal(null)
      setProposalRequestId('')
      setManualScheduleDraft({})
      setManualScheduleRequestId(newCommandId())
      setManualScheduleReview(null)
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setManualScheduleReview(null)
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

  function weekTournamentLockPayload(): WeekTournamentLockPreviewPayload {
    const inspection = weekLockQuery.data
    if (!inspection || inspection.lock_status !== 'required') {
      throw new Error('There is no unresolved Week Tournament Lock conflict to review.')
    }
    const operator = weekLockOperator.trim()
    const auditReason = weekLockReason.trim()
    if (!operator || !auditReason) {
      throw new Error('Week Tournament Lock operator and audit reason are required.')
    }
    const selections = inspection.conflicts.map((conflict) => {
      const selectedEventId = weekLockSelections[conflict.player_id] ?? ''
      if (!selectedEventId || !conflict.eligible_event_ids.includes(selectedEventId)) {
        throw new Error(
          `Choose exactly one eligible tournament for ${conflict.player_id}.`
        )
      }
      return {
        player_id: conflict.player_id,
        selected_event_id: selectedEventId
      }
    })
    return {
      command_id: weekLockCommandId,
      expected_week: inspection.week,
      expected_position_fingerprint: inspection.position_fingerprint,
      expected_revision_id: inspection.expected_revision_id,
      operator_label: operator,
      audit_reason: auditReason,
      selections
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

  function reconstructionConstraints(): MatchReconstructionConstraints {
    const constraints: MatchReconstructionConstraints = {}
    const winner = reconstructionWinnerId.trim()
    if (winner) constraints.winner_player_id = winner

    const matchScore = reconstructionMatchScore.trim()
    if (matchScore) {
      const match = /^(\d+)\s*[-:]\s*(\d+)$/.exec(matchScore)
      if (!match) throw new Error('Match score must use A-B form, for example 3-1.')
      constraints.player_a_sets_won = Number(match[1])
      constraints.player_b_sets_won = Number(match[2])
    }

    const gameScores = reconstructionGameScores.trim()
    if (gameScores) {
      constraints.exact_game_scores = gameScores.split(',').map((item) => {
        const match = /^(\d+)\s*[-:]\s*(\d+)$/.exec(item.trim())
        if (!match) throw new Error('Game scores must use comma-separated A-B values, for example 11-7, 8-11, 11-9, 11-6.')
        return {
          player_a_points: Number(match[1]),
          player_b_points: Number(match[2])
        }
      })
    }

    if (
      !constraints.winner_player_id &&
      constraints.player_a_sets_won == null &&
      !constraints.exact_game_scores?.length
    ) {
      throw new Error('Add at least one hard reconstruction constraint.')
    }
    return constraints
  }

  const reconstructionPreviewMutation = useMutation({
    mutationFn: async () => {
      const position = positionQuery.data
      if (!position || !savedRevisionId || !selectedGroupId) {
        throw new Error('Current canonical match position is required.')
      }
      const candidateCount = Number(reconstructionCandidateCount)
      if (!Number.isInteger(candidateCount) || candidateCount < 1 || candidateCount > 20) {
        throw new Error('Candidate count must be an integer from 1 to 20.')
      }
      const payload: AuthoritativeMatchReconstructionPreviewPayload = {
        expected_week: position.current_week,
        expected_position_fingerprint: position.position_fingerprint,
        expected_revision_id: savedRevisionId,
        group_id: selectedGroupId,
        candidate_count: candidateCount,
        constraints: reconstructionConstraints()
      }
      const preview = await previewAuthoritativeMatchReconstruction(runId, branchId, payload)
      return { payload, preview }
    },
    onSuccess: (review) => {
      setReconstructionReview(review)
      setSelectedReconstructionCandidate(review.preview.candidates[0]?.candidate_fingerprint ?? '')
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setReconstructionReview(null)
        setSelectedReconstructionCandidate('')
        await refreshCanonicalSimulation()
      }
    }
  })

  const reconstructionCommitMutation = useMutation({
    mutationFn: () => {
      if (!reconstructionReview) throw new Error('Generate and review reconstruction candidates first.')
      if (!selectedReconstructionCandidate) throw new Error('Select one reconstruction candidate.')
      const operator = reconstructionOperator.trim()
      const auditReason = reconstructionReason.trim()
      if (!operator || !auditReason) throw new Error('Operator label and audit reason are required.')
      return commitAuthoritativeMatchReconstruction(runId, branchId, {
        ...reconstructionReview.payload,
        command_id: reconstructionCommandId,
        expected_preview_fingerprint: reconstructionReview.preview.preview_fingerprint,
        selected_candidate_fingerprint: selectedReconstructionCandidate,
        operator_label: operator,
        audit_reason: auditReason
      })
    },
    onSuccess: async (result) => {
      queryClient.setQueryData(
        ['authoritative-simulation-position', runId, branchId],
        result.position
      )
      setReconstructionReview(null)
      setSelectedReconstructionCandidate('')
      setReconstructionOperator('')
      setReconstructionReason('')
      setReconstructionCommandId(newCommandId())
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setReconstructionReview(null)
        setSelectedReconstructionCandidate('')
        await refreshCanonicalSimulation()
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

  const nextMatchDayPreviewMutation = useMutation({
    mutationFn: () => previewAuthoritativeNextMatchDay(runId, branchId),
    onSuccess: (preview) => setNextMatchDayReview(preview),
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setNextMatchDayReview(null)
        setNextMatchDayCommandId(newCommandId())
        await refreshCanonicalSimulation()
      }
    }
  })

  const nextMatchDayMutation = useMutation({
    mutationFn: () => {
      if (!nextMatchDayReview) {
        throw new Error('Review the current canonical Match Day before simulation.')
      }
      return simulateAuthoritativeNextMatchDay(runId, branchId, {
        command_id: nextMatchDayCommandId,
        expected_week: nextMatchDayReview.week,
        expected_position_fingerprint:
          nextMatchDayReview.expected_position_fingerprint,
        expected_revision_id: nextMatchDayReview.expected_revision_id
      })
    },
    onSuccess: async (result) => {
      queryClient.setQueryData(
        ['authoritative-simulation-position', runId, branchId],
        result.position
      )
      setNextMatchDayReview(null)
      setNextMatchDayCommandId(newCommandId())
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setNextMatchDayReview(null)
        setNextMatchDayCommandId(newCommandId())
        setConfirmed(false)
        await Promise.all([
          refreshCanonicalSimulation(),
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
        ])
      }
    }
  })

  const nextRoundPreviewMutation = useMutation({
    mutationFn: () => previewAuthoritativeNextRound(runId, branchId),
    onSuccess: (preview) => setNextRoundReview(preview),
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setNextRoundReview(null)
        setNextRoundCommandId(newCommandId())
        await refreshCanonicalSimulation()
      }
    }
  })

  const nextRoundMutation = useMutation({
    mutationFn: () => {
      if (!nextRoundReview) {
        throw new Error('Review the current canonical Round before simulation.')
      }
      return simulateAuthoritativeNextRound(runId, branchId, {
        command_id: nextRoundCommandId,
        expected_week: nextRoundReview.week,
        expected_position_fingerprint:
          nextRoundReview.expected_position_fingerprint,
        expected_revision_id: nextRoundReview.expected_revision_id
      })
    },
    onSuccess: async (result) => {
      queryClient.setQueryData(
        ['authoritative-simulation-position', runId, branchId],
        result.position
      )
      setNextRoundReview(null)
      setNextRoundCommandId(newCommandId())
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setNextRoundReview(null)
        setNextRoundCommandId(newCommandId())
        setConfirmed(false)
        await Promise.all([
          refreshCanonicalSimulation(),
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
        ])
      }
    }
  })

  const nextTournamentPreviewMutation = useMutation({
    mutationFn: () => previewAuthoritativeNextTournament(runId, branchId),
    onSuccess: (preview) => setNextTournamentReview(preview),
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setNextTournamentReview(null)
        setNextTournamentCommandId(newCommandId())
        await refreshCanonicalSimulation()
      }
    }
  })

  const nextTournamentMutation = useMutation({
    mutationFn: () => {
      if (!nextTournamentReview) {
        throw new Error('Review the current canonical Tournament before simulation.')
      }
      return simulateAuthoritativeNextTournament(runId, branchId, {
        command_id: nextTournamentCommandId,
        expected_week: nextTournamentReview.week,
        expected_position_fingerprint:
          nextTournamentReview.expected_position_fingerprint,
        expected_revision_id: nextTournamentReview.expected_revision_id
      })
    },
    onSuccess: async (result) => {
      queryClient.setQueryData(
        ['authoritative-simulation-position', runId, branchId],
        result.position
      )
      setNextTournamentReview(null)
      setNextTournamentCommandId(newCommandId())
      setConfirmed(false)
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setNextTournamentReview(null)
        setNextTournamentCommandId(newCommandId())
        setConfirmed(false)
        await Promise.all([
          refreshCanonicalSimulation(),
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
        ])
      }
    }
  })

  const nextWeekPreviewMutation = useMutation({
    mutationFn: () => {
      const operator = nextWeekOperator.trim()
      const reason = nextWeekReason.trim()
      if (!operator || !reason) {
        throw new Error('Next Week requires an operator label and audit reason.')
      }
      return previewAuthoritativeNextWeek(runId, branchId, {
        command_id: nextWeekCommandId,
        operator_label: operator,
        audit_reason: reason
      })
    },
    onSuccess: (preview) => {
      setNextWeekReview(preview)
      setNextWeekProgress(null)
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setNextWeekReview(null)
        setNextWeekProgress(null)
        setNextWeekCommandId(newCommandId())
        await refreshCanonicalSimulation()
      }
    }
  })

  const nextWeekMutation = useMutation({
    mutationFn: () => {
      if (!nextWeekReview) {
        throw new Error('Review the current canonical Week before simulation.')
      }
      return simulateAuthoritativeNextWeek(runId, branchId, {
        command_id: nextWeekCommandId,
        operator_label: nextWeekOperator.trim(),
        audit_reason: nextWeekReason.trim(),
        expected_week: nextWeekReview.week,
        expected_position_fingerprint:
          nextWeekReview.expected_position_fingerprint,
        expected_revision_id: nextWeekReview.expected_revision_id,
        expected_preview_fingerprint: nextWeekReview.preview_fingerprint
      })
    },
    onSuccess: async (result) => {
      if (result.schema_version === 'authoritative_week_progress.v1') {
        setNextWeekProgress(result)
        queryClient.setQueryData(
          ['authoritative-simulation-position', runId, branchId],
          result.position
        )
        await refreshCanonicalSimulation()
        return
      }
      setNextWeekProgress(null)
      setNextWeekReview(null)
      setNextWeekCommandId(newCommandId())
      setNextWeekOperator('')
      setNextWeekReason('')
      setConfirmed(false)
      await Promise.all([
        refreshCanonicalSimulation(),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-candidates', runId, branchId] })
      ])
    },
    onError: async () => {
      // Keep the exact reviewed parent command. A 409 or lost response can happen
      // after durable child/transition work committed, so retry must reuse it.
      await Promise.all([
        refreshCanonicalSimulation(),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] })
      ])
    }
  })

  const nextSeasonPreviewMutation = useMutation({
    mutationFn: () => {
      const operator = nextSeasonOperator.trim()
      const reason = nextSeasonReason.trim()
      if (!operator || !reason) {
        throw new Error('Next Season requires an operator label and audit reason.')
      }
      return previewAuthoritativeNextSeason(runId, branchId, {
        command_id: nextSeasonCommandId,
        operator_label: operator,
        audit_reason: reason
      })
    },
    onSuccess: (preview) => {
      setNextSeasonReview(preview)
      setNextSeasonProgress(null)
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setNextSeasonReview(null)
        setNextSeasonProgress(null)
        setNextSeasonCommandId(newCommandId())
        await refreshCanonicalSimulation()
      }
    }
  })

  const nextSeasonMutation = useMutation({
    mutationFn: () => {
      if (!nextSeasonReview) {
        throw new Error('Review the current canonical Season before simulation.')
      }
      return simulateAuthoritativeNextSeason(runId, branchId, {
        command_id: nextSeasonCommandId,
        operator_label: nextSeasonOperator.trim(),
        audit_reason: nextSeasonReason.trim(),
        expected_start_week: nextSeasonReview.start_week,
        expected_position_fingerprint:
          nextSeasonReview.expected_position_fingerprint,
        expected_revision_id: nextSeasonReview.expected_revision_id,
        expected_preview_fingerprint: nextSeasonReview.preview_fingerprint
      })
    },
    onSuccess: async (result) => {
      queryClient.setQueryData(
        ['authoritative-simulation-position', runId, branchId],
        result.position
      )
      if (result.schema_version === 'authoritative_season_progress.v1') {
        setNextSeasonProgress(result)
        await Promise.all([
          refreshCanonicalSimulation(),
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] })
        ])
        return
      }
      setNextSeasonProgress(null)
      setNextSeasonReview(null)
      setNextSeasonCommandId(newCommandId())
      setNextSeasonOperator('')
      setNextSeasonReason('')
      setConfirmed(false)
      await Promise.all([
        refreshCanonicalSimulation(),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-candidates', runId, branchId] })
      ])
    },
    onError: async () => {
      // Preserve the exact parent ID: some failures can happen after many durable
      // week/empty-week children have already committed.
      await Promise.all([
        refreshCanonicalSimulation(),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] })
      ])
    }
  })

  const fullSimulationPreviewMutation = useMutation({
    mutationFn: () => {
      const operator = fullSimulationOperator.trim()
      const reason = fullSimulationReason.trim()
      if (!operator || !reason) {
        throw new Error('Full Simulation requires an operator label and audit reason.')
      }
      return previewAuthoritativeFullSimulation(runId, branchId, {
        command_id: fullSimulationCommandId,
        operator_label: operator,
        audit_reason: reason
      })
    },
    onSuccess: (preview) => {
      setFullSimulationReview(preview)
      setFullSimulationProgress(null)
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setFullSimulationReview(null)
        setFullSimulationProgress(null)
        setFullSimulationCommandId(newCommandId())
        await refreshCanonicalSimulation()
      }
    }
  })

  const fullSimulationMutation = useMutation({
    mutationFn: () => {
      if (!fullSimulationReview) {
        throw new Error('Review the canonical Full Simulation range first.')
      }
      return simulateAuthoritativeFullSimulation(runId, branchId, {
        command_id: fullSimulationCommandId,
        operator_label: fullSimulationOperator.trim(),
        audit_reason: fullSimulationReason.trim(),
        expected_start_week: fullSimulationReview.start_week,
        expected_position_fingerprint:
          fullSimulationReview.expected_position_fingerprint,
        expected_revision_id: fullSimulationReview.expected_revision_id,
        expected_preview_fingerprint: fullSimulationReview.preview_fingerprint
      })
    },
    onSuccess: async (result) => {
      if (result.schema_version === 'authoritative_full_simulation_progress.v1') {
        setFullSimulationProgress(result)
        if (result.position) {
          queryClient.setQueryData(
            ['authoritative-simulation-position', runId, branchId],
            result.position
          )
        }
        await Promise.all([
          refreshCanonicalSimulation(),
          queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
          queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] })
        ])
        return
      }
      setFullSimulationProgress(null)
      setFullSimulationReview(null)
      setFullSimulationCommandId(newCommandId())
      setFullSimulationOperator('')
      setFullSimulationReason('')
      setConfirmed(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-candidates', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-season-transition-preflight', runId, branchId] })
      ])
    },
    onError: async () => {
      // Preserve the reviewed Full Simulation parent across partial season work,
      // explicit Save boundaries, process reopen and final Run closure.
      await Promise.all([
        refreshCanonicalSimulation(),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revisions', runId, branchId] })
      ])
    }
  })

  const entryValidationMutation = useMutation({
    mutationFn: () => {
      const position = positionQuery.data
      const inspection = entrySlotQuery.data
      if (!position || position.current_slot_kind !== 'entry' || position.slot_ordinal == null) {
        throw new Error('The current canonical position is not an Entry decision slot.')
      }
      if (!inspection || inspection.validation_resolved) {
        throw new Error('The current Entry decision slot is not available for review.')
      }
      if (!savedRevisionId) {
        throw new Error('A Saved Revision head is required for Entry validation.')
      }
      const operator = entryValidationOperator.trim()
      const auditReason = entryValidationReason.trim()
      if (!operator || !auditReason) {
        throw new Error('Operator label and audit reason are required.')
      }

      const reviews: AuthoritativeApplicationValidationReview[] =
        inspection.authority.decisions.map((decision) => {
          const draft =
            entryValidationDrafts[
              entryValidationKey(decision.event_id, decision.player_id)
            ]
          if (!draft?.outcome) {
            throw new Error('Every frozen Entry decision must receive a validation outcome.')
          }
          const rejectionReason = draft.reason.trim()
          if (draft.outcome === 'invalid' && !rejectionReason) {
            throw new Error('Every invalid application requires a rejection reason.')
          }
          return {
            event_id: decision.event_id,
            player_id: decision.player_id,
            outcome: draft.outcome,
            reasons:
              draft.outcome === 'invalid'
                ? [rejectionReason]
                : []
          }
        })

      return reviewAuthoritativeEntryDecisionSlot(runId, branchId, {
        command_id: entryValidationCommandId,
        expected_week: position.current_week,
        expected_revision_id: savedRevisionId,
        expected_position_fingerprint: position.position_fingerprint,
        decision_slot_ordinal: position.slot_ordinal,
        expected_entry_slot_fingerprint: inspection.slot_fingerprint,
        operator_label: operator,
        reason: auditReason,
        reviews
      })
    },
    onSuccess: async () => {
      setEntryValidationOperator('')
      setEntryValidationReason('')
      setEntryValidationDrafts({})
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        await refreshCanonicalSimulation()
      }
    }
  })

  const weekLockPreviewMutation = useMutation({
    mutationFn: () => {
      const payload = weekTournamentLockPayload()
      return previewWeekTournamentLock(runId, branchId, payload).then((preview) => ({
        payload,
        preview
      }))
    },
    onSuccess: (review) => setWeekLockReview(review),
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setWeekLockReview(null)
        await refreshCanonicalSimulation()
      }
    }
  })

  const weekLockCommitMutation = useMutation({
    mutationFn: () => {
      if (!weekLockReview) {
        throw new Error('Review the Week Tournament Lock before committing it.')
      }
      return commitWeekTournamentLock(runId, branchId, {
        ...weekLockReview.payload,
        expected_authority_fingerprint:
          weekLockReview.preview.authority_fingerprint
      })
    },
    onSuccess: async () => {
      setWeekLockReview(null)
      setWeekLockSelections({})
      setWeekLockOperator('')
      setWeekLockReason('')
      setWeekLockCommandId(newCommandId())
      await refreshCanonicalSimulation()
    },
    onError: async (error) => {
      if ((error as { status?: number }).status === 409) {
        setWeekLockReview(null)
        await refreshCanonicalSimulation()
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
  const actionPending =
    nextMatchMutation.isPending ||
    nextSlotMutation.isPending ||
    nextMatchDayPreviewMutation.isPending ||
    nextMatchDayMutation.isPending ||
    nextRoundPreviewMutation.isPending ||
    nextRoundMutation.isPending ||
    nextTournamentPreviewMutation.isPending ||
    nextTournamentMutation.isPending ||
    nextWeekPreviewMutation.isPending ||
    nextWeekMutation.isPending ||
    nextSeasonPreviewMutation.isPending ||
    nextSeasonMutation.isPending ||
    fullSimulationPreviewMutation.isPending ||
    fullSimulationMutation.isPending ||
    reconstructionPreviewMutation.isPending ||
    reconstructionCommitMutation.isPending ||
    entryValidationMutation.isPending ||
    weekLockPreviewMutation.isPending ||
    weekLockCommitMutation.isPending
  const currentEntrySlot = position?.current_slot_kind === 'entry'
  const entryInspection = entrySlotQuery.data
  const entryValidationReady = Boolean(
    currentEntrySlot &&
    entryInspection &&
    !entryInspection.validation_resolved &&
    entryValidationOperator.trim() &&
    entryValidationReason.trim() &&
    entryInspection.authority.decisions.length > 0 &&
    entryInspection.authority.decisions.every((decision) => {
      const draft =
        entryValidationDrafts[
          entryValidationKey(decision.event_id, decision.player_id)
        ]
      return Boolean(
        draft?.outcome &&
        (draft.outcome === 'valid' || draft.reason.trim())
      )
    })
  )

  const weekLockReady = Boolean(
    weekLockQuery.data?.lock_status === 'required' &&
    weekLockOperator.trim() &&
    weekLockReason.trim() &&
    weekLockQuery.data.conflicts.length > 0 &&
    weekLockQuery.data.conflicts.every((conflict) =>
      conflict.eligible_event_ids.includes(
        weekLockSelections[conflict.player_id] ?? ''
      )
    )
  )


  return (
    <SectionCard title="Canonical authoritative sporting simulation">
      <p className="status">
        Run/Branch-owned sporting path: Week Schedule → Position → Next Match / Next Slot / Next Match Day / Next Round / Next Tournament / Next Week / Next Season / Full Simulation → Save / reviewed boundaries.
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

      {weekLockQuery.isLoading && enabled ? (
        <p className="status">Inspecting Week Tournament Lock conflicts…</p>
      ) : null}
      {weekLockQuery.error ? (
        <p className="error">
          Week Tournament Lock unavailable: {formatApiError(weekLockQuery.error)}
        </p>
      ) : null}
      {weekLockQuery.data ? (
        <>
          <h4>Week Tournament Lock</h4>
          <p className="status">
            Explicit pre-alpha Admin resolution of overlapping accepted tournament fields.
            The engine does not invent a preferred event or a Final Commitment deadline.
          </p>
          {weekLockQuery.data.lock_status === 'not_required' ? (
            <p className="status">No overlapping accepted-player field conflict requires a lock.</p>
          ) : null}
          {weekLockQuery.data.lock_status === 'locked' && weekLockQuery.data.authority ? (
            <>
              <MetadataList
                items={[
                  { label: 'Status', value: 'Locked' },
                  { label: 'Policy', value: weekLockQuery.data.authority.selection_policy_id },
                  { label: 'Operator', value: weekLockQuery.data.authority.operator_label },
                  { label: 'Authority fingerprint', value: weekLockQuery.data.authority_fingerprint ?? '—' }
                ]}
              />
              <ul aria-label="Week Tournament Lock selections">
                {weekLockQuery.data.authority.player_locks.map((lock) => (
                  <li key={lock.player_id}>
                    {lock.player_id} → {lock.selected_event_id}
                    {' '}({lock.eligible_event_ids.join(' / ')})
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {weekLockQuery.data.lock_status === 'required' ? (
            <>
              <p role="alert" className="error">
                Competitive play is blocked until every overlapping accepted player has exactly one selected event.
              </p>
              {weekLockQuery.data.conflicts.map((conflict) => (
                <label key={conflict.player_id}>
                  {conflict.player_id}
                  <select
                    aria-label={`Week Tournament Lock event for ${conflict.player_id}`}
                    value={weekLockSelections[conflict.player_id] ?? ''}
                    disabled={Boolean(weekLockReview)}
                    onChange={(event) => {
                      const selected = event.target.value
                      setWeekLockSelections((current) => ({
                        ...current,
                        [conflict.player_id]: selected
                      }))
                    }}
                  >
                    <option value="">Choose one tournament…</option>
                    {conflict.eligible_event_ids.map((eventId) => (
                      <option key={eventId} value={eventId}>{eventId}</option>
                    ))}
                  </select>
                </label>
              ))}
              <label>
                Operator label
                <input
                  aria-label="Week Tournament Lock operator"
                  value={weekLockOperator}
                  disabled={Boolean(weekLockReview)}
                  onChange={(event) => setWeekLockOperator(event.target.value)}
                />
              </label>
              <label>
                Audit reason
                <textarea
                  aria-label="Week Tournament Lock audit reason"
                  value={weekLockReason}
                  disabled={Boolean(weekLockReview)}
                  onChange={(event) => setWeekLockReason(event.target.value)}
                />
              </label>
              {!weekLockReview ? (
                <button
                  type="button"
                  disabled={!weekLockReady || actionPending}
                  onClick={() => weekLockPreviewMutation.mutate()}
                >
                  Review Week Tournament Lock
                </button>
              ) : (
                <>
                  <MetadataList
                    items={[
                      { label: 'Reviewed fingerprint', value: weekLockReview.preview.authority_fingerprint },
                      { label: 'Conflicts resolved', value: weekLockReview.preview.authority.player_locks.length }
                    ]}
                  />
                  <ul aria-label="Reviewed Week Tournament Lock selections">
                    {weekLockReview.preview.authority.player_locks.map((lock) => (
                      <li key={lock.player_id}>
                        {lock.player_id} → {lock.selected_event_id}
                      </li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    disabled={actionPending}
                    onClick={() => weekLockCommitMutation.mutate()}
                  >
                    Commit Week Tournament Lock
                  </button>
                  <button
                    type="button"
                    disabled={actionPending}
                    onClick={() => setWeekLockReview(null)}
                  >
                    Edit lock review
                  </button>
                </>
              )}
              {weekLockPreviewMutation.error ? (
                <p className="error">
                  Week Tournament Lock preview failed: {formatApiError(weekLockPreviewMutation.error)}
                </p>
              ) : null}
              {weekLockCommitMutation.error ? (
                <p className="error">
                  Week Tournament Lock commit failed: {formatApiError(weekLockCommitMutation.error)}
                </p>
              ) : null}
            </>
          ) : null}
          {weekLockCommitMutation.data?.field_repairs.length ? (
            <p className="status">
              Canonical field repairs applied to {weekLockCommitMutation.data.field_repairs.length} unselected event(s).
            </p>
          ) : null}
        </>
      ) : null}

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
              { label: 'Slot kind', value: position.current_slot_kind === 'entry' ? 'Entry decision' : position.current_slot_kind === 'match' ? 'Match' : '—' },
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
                <li key={slot.ordinal}>
                  {slot.match_day_ordinal != null
                    ? `Day ${slot.match_day_ordinal} · #${slot.match_order} · global slot ${slot.ordinal} · ${slot.event_id} · ${slot.draw_phase} R${slot.round_number}: ${slot.group_ids.join(', ')}`
                    : `Legacy global slot ${slot.ordinal}: ${slot.group_ids.join(', ')}`}
                </li>
              ))}
            </ol>
          ) : scheduleQuery.data.required ? (
            <>
              <p className="status">
                Canonical Position and match execution stay locked until this immutable Match Day / global-slot schedule is adopted.
              </p>
              <button
                type="button"
                onClick={() => proposalMutation.mutate()}
                disabled={proposalMutation.isPending || adoptMutation.isPending}
              >
                Build Match Day schedule proposal
              </button>
              {proposalMutation.error ? (
                <p className="error">Schedule proposal failed: {formatApiError(proposalMutation.error)}</p>
              ) : null}
              {proposal ? (
                <>
                  <p className="status">{proposal.provenance}</p>
                  <ol aria-label="Proposed authoritative week schedule">
                    {proposal.schedule.slots.map((slot) => (
                      <li key={slot.ordinal}>
                        {slot.match_day_ordinal != null
                          ? `Day ${slot.match_day_ordinal} · #${slot.match_order} · global slot ${slot.ordinal} · ${slot.event_id} · ${slot.draw_phase} R${slot.round_number}: ${slot.group_ids.join(', ')}`
                          : `Legacy global slot ${slot.ordinal}: ${slot.group_ids.join(', ')}`}
                      </li>
                    ))}
                  </ol>
                  <button
                    type="button"
                    onClick={() => adoptMutation.mutate()}
                    disabled={
                      adoptMutation.isPending ||
                      manualScheduleAdoptMutation.isPending ||
                      !proposalRequestId
                    }
                  >
                    Adopt reviewed Match Day schedule
                  </button>

                  {proposal.schedule.schema_version === 'week_simulation_schedule.v2' ? (
                    <>
                      <h5>Manual Match Day schedule edit</h5>
                      <p className="status">
                        Change only the playing day and within-day priority. Global Simulation Slot ordinals are rebuilt from the proposal's reserved ordinal pool. The server revalidates every hard scheduling constraint before adoption.
                      </p>
                      <ul aria-label="Editable Match Day schedule">
                        {proposal.schedule.slots.map((slot) => {
                          const groupId = slot.group_ids[0]
                          if (!groupId) return null
                          const draft = manualScheduleDraft[groupId] ?? {
                            day: String(slot.match_day_ordinal ?? ''),
                            order: String(slot.match_order ?? '')
                          }
                          return (
                            <li key={groupId}>
                              <strong>
                                {slot.event_id} · {slot.draw_phase} R{slot.round_number} · {groupId}
                              </strong>{' '}
                              <label>
                                Match Day
                                <input
                                  aria-label={`Match Day ${groupId}`}
                                  type="number"
                                  min={1}
                                  step={1}
                                  value={draft.day}
                                  onChange={(event) => {
                                    setManualScheduleDraft((current) => ({
                                      ...current,
                                      [groupId]: {
                                        day: event.target.value,
                                        order: current[groupId]?.order ?? draft.order
                                      }
                                    }))
                                    setManualScheduleReview(null)
                                  }}
                                  disabled={
                                    manualSchedulePreviewMutation.isPending ||
                                    manualScheduleAdoptMutation.isPending
                                  }
                                />
                              </label>{' '}
                              <label>
                                Preferred order
                                <input
                                  aria-label={`Match order ${groupId}`}
                                  type="number"
                                  min={1}
                                  step={1}
                                  value={draft.order}
                                  onChange={(event) => {
                                    setManualScheduleDraft((current) => ({
                                      ...current,
                                      [groupId]: {
                                        day: current[groupId]?.day ?? draft.day,
                                        order: event.target.value
                                      }
                                    }))
                                    setManualScheduleReview(null)
                                  }}
                                  disabled={
                                    manualSchedulePreviewMutation.isPending ||
                                    manualScheduleAdoptMutation.isPending
                                  }
                                />
                              </label>
                            </li>
                          )
                        })}
                      </ul>
                      <button
                        type="button"
                        onClick={() => manualSchedulePreviewMutation.mutate()}
                        disabled={
                          manualSchedulePreviewMutation.isPending ||
                          manualScheduleAdoptMutation.isPending
                        }
                      >
                        Review edited Match Day schedule
                      </button>
                      {manualSchedulePreviewMutation.error ? (
                        <p className="error">
                          Edited schedule review failed: {formatApiError(manualSchedulePreviewMutation.error)}
                        </p>
                      ) : null}
                      {manualScheduleReview ? (
                        <>
                          <MetadataList
                            items={[
                              {
                                label: 'Reviewed schedule fingerprint',
                                value: manualScheduleReview.preview.schedule_fingerprint
                              },
                              {
                                label: 'Reviewed position fingerprint',
                                value: manualScheduleReview.preview.position_fingerprint
                              }
                            ]}
                          />
                          <ol aria-label="Reviewed edited Match Day schedule">
                            {manualScheduleReview.schedule.slots.map((slot) => (
                              <li key={slot.ordinal}>
                                Day {slot.match_day_ordinal} · #{slot.match_order} · global slot {slot.ordinal} · {slot.event_id} · {slot.draw_phase} R{slot.round_number}: {slot.group_ids.join(', ')}
                              </li>
                            ))}
                          </ol>
                          <button
                            type="button"
                            onClick={() => manualScheduleAdoptMutation.mutate()}
                            disabled={manualScheduleAdoptMutation.isPending}
                          >
                            Adopt reviewed edited Match Day schedule
                          </button>
                        </>
                      ) : null}
                      {manualScheduleAdoptMutation.error ? (
                        <p className="error">
                          Edited schedule adoption failed: {formatApiError(manualScheduleAdoptMutation.error)}
                        </p>
                      ) : null}
                    </>
                  ) : null}
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
          {currentEntrySlot ? (
            <>
              <p className="status">
                The nearest unresolved Simulation Slot is an Entry decision slot. Complete its application validation before match simulation can continue.
              </p>
              <h4>Entry application validation</h4>
              <p className="status">
                This is an explicit audited Admin resolution over frozen Entry evidence. The engine does not infer the still-open automatic eligibility or deadline rules here.
              </p>
              {entrySlotQuery.isLoading ? (
                <p className="status">Loading frozen Entry decisions…</p>
              ) : null}
              {entrySlotQuery.error ? (
                <p className="error">
                  Entry decision inspection failed: {formatApiError(entrySlotQuery.error)}
                </p>
              ) : null}
              {entryInspection ? (
                <>
                  <MetadataList
                    items={[
                      { label: 'Entry slot fingerprint', value: entryInspection.slot_fingerprint },
                      { label: 'Frozen decisions', value: entryInspection.authority.decisions.length },
                      { label: 'Validation resolved', value: entryInspection.validation_resolved ? 'Yes' : 'No' }
                    ]}
                  />
                  {entryInspection.validation_resolved ? (
                    <p className="status">
                      This Entry slot already has immutable validation evidence.
                    </p>
                  ) : (
                    <>
                      <ul aria-label="Frozen Entry application decisions">
                        {entryInspection.authority.decisions.map((decision) => {
                          const key = entryValidationKey(decision.event_id, decision.player_id)
                          const draft = entryValidationDrafts[key] ?? {
                            outcome: '',
                            reason: ''
                          }
                          const decisionLabel = `${decision.event_id}/${decision.player_id}`
                          return (
                            <li key={key}>
                              <strong>
                                {decision.event_id} · {decision.player_id} · {decision.target}
                              </strong>{' '}
                              <label>
                                Outcome
                                <select
                                  aria-label={`Validation outcome ${decisionLabel}`}
                                  value={draft.outcome}
                                  onChange={(event) => {
                                    const outcome = event.target.value as EntryValidationDraft['outcome']
                                    setEntryValidationDrafts((current) => ({
                                      ...current,
                                      [key]: {
                                        outcome,
                                        reason: outcome === 'invalid' ? (current[key]?.reason ?? '') : ''
                                      }
                                    }))
                                  }}
                                  disabled={entryValidationMutation.isPending}
                                >
                                  <option value="">Pending review</option>
                                  <option value="valid">Valid</option>
                                  <option value="invalid">Invalid</option>
                                </select>
                              </label>
                              {draft.outcome === 'invalid' ? (
                                <label>
                                  Rejection reason
                                  <input
                                    aria-label={`Validation rejection reason ${decisionLabel}`}
                                    value={draft.reason}
                                    onChange={(event) =>
                                      setEntryValidationDrafts((current) => ({
                                        ...current,
                                        [key]: {
                                          outcome: 'invalid',
                                          reason: event.target.value
                                        }
                                      }))
                                    }
                                    disabled={entryValidationMutation.isPending}
                                  />
                                </label>
                              ) : null}
                            </li>
                          )
                        })}
                      </ul>
                      <label>
                        Entry validation operator
                        <input
                          aria-label="Entry validation operator"
                          value={entryValidationOperator}
                          onChange={(event) => setEntryValidationOperator(event.target.value)}
                          disabled={entryValidationMutation.isPending}
                        />
                      </label>
                      <label>
                        Entry validation audit reason
                        <input
                          aria-label="Entry validation audit reason"
                          value={entryValidationReason}
                          onChange={(event) => setEntryValidationReason(event.target.value)}
                          disabled={entryValidationMutation.isPending}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() => entryValidationMutation.mutate()}
                        disabled={!entryValidationReady || entryValidationMutation.isPending}
                      >
                        Commit explicit application validation
                      </button>
                    </>
                  )}
                </>
              ) : null}
              {entryValidationMutation.error ? (
                <p className="error">
                  Entry application validation failed: {formatApiError(entryValidationMutation.error)}
                </p>
              ) : null}
            </>
          ) : null}
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
          {position.current_slot_kind === 'match' && selectedGroupId ? (
            <>
              <h4>Minimum Match Reconstruction</h4>
              <p className="status">
                Preview is read-only. Winner, exact match score and exact game scores are hard constraints.
                Candidate probability, forcing and nearest-match search are intentionally not inferred in this first version.
              </p>
              {reconstructionStateQuery.isLoading ? (
                <p className="status">Loading frozen reconstruction target…</p>
              ) : null}
              {reconstructionStateQuery.error ? (
                <p className="error">
                  Reconstruction target unavailable: {formatApiError(reconstructionStateQuery.error)}
                </p>
              ) : null}
              {reconstructionStateQuery.data ? (
                <MetadataList
                  items={[
                    { label: 'Match', value: reconstructionStateQuery.data.match_id },
                    { label: 'Player A', value: reconstructionStateQuery.data.player_a_id },
                    { label: 'Player B', value: reconstructionStateQuery.data.player_b_id },
                    { label: 'Frozen slot start', value: reconstructionStateQuery.data.slot_start_fingerprint }
                  ]}
                />
              ) : null}
              {!reconstructionReview ? (
                <>
                  <label>
                    Candidate count
                    <input
                      aria-label="Reconstruction candidate count"
                      type="number"
                      min={1}
                      max={20}
                      value={reconstructionCandidateCount}
                      onChange={(event) => setReconstructionCandidateCount(event.target.value)}
                      disabled={reconstructionPreviewMutation.isPending}
                    />
                  </label>
                  <label>
                    Winner player ID (optional)
                    <input
                      aria-label="Reconstruction winner player ID"
                      value={reconstructionWinnerId}
                      placeholder={reconstructionStateQuery.data?.player_a_id ?? 'player ID'}
                      onChange={(event) => setReconstructionWinnerId(event.target.value)}
                      disabled={reconstructionPreviewMutation.isPending}
                    />
                  </label>
                  <label>
                    Exact match score A-B (optional)
                    <input
                      aria-label="Reconstruction exact match score"
                      value={reconstructionMatchScore}
                      placeholder="3-1"
                      onChange={(event) => setReconstructionMatchScore(event.target.value)}
                      disabled={reconstructionPreviewMutation.isPending}
                    />
                  </label>
                  <label>
                    Exact game scores A-B (optional)
                    <input
                      aria-label="Reconstruction exact game scores"
                      value={reconstructionGameScores}
                      placeholder="11-7, 8-11, 11-9, 11-6"
                      onChange={(event) => setReconstructionGameScores(event.target.value)}
                      disabled={reconstructionPreviewMutation.isPending}
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => reconstructionPreviewMutation.mutate()}
                    disabled={!reconstructionStateQuery.data || reconstructionPreviewMutation.isPending}
                  >
                    Generate matching scenarios
                  </button>
                </>
              ) : (
                <>
                  <p className="status">
                    Found {reconstructionReview.preview.candidate_count_found} of{' '}
                    {reconstructionReview.preview.candidate_count_requested} requested candidate(s) after{' '}
                    {reconstructionReview.preview.attempted_scenarios} deterministic scenario(s).
                  </p>
                  {reconstructionReview.preview.warnings.map((warning) => (
                    <p key={warning} className="status">{warning}</p>
                  ))}
                  <ul aria-label="Match Reconstruction candidates">
                    {reconstructionReview.preview.candidates.map((candidate, index) => (
                      <li key={candidate.candidate_fingerprint}>
                        <label>
                          <input
                            type="radio"
                            name="reconstruction-candidate"
                            aria-label={`Select reconstruction candidate ${index + 1}`}
                            checked={selectedReconstructionCandidate === candidate.candidate_fingerprint}
                            onChange={() => setSelectedReconstructionCandidate(candidate.candidate_fingerprint)}
                          />
                          Candidate {index + 1}: {candidate.winner_player_id} ·{' '}
                          {candidate.sets_won[candidate.player_a_id]}-{candidate.sets_won[candidate.player_b_id]} ·{' '}
                          {candidate.game_scores.map((score) => `${score.player_a_points}-${score.player_b_points}`).join(', ')}
                        </label>
                        <details>
                          <summary>Complete read-only candidate detail</summary>
                          <pre>{JSON.stringify(candidate.detail, null, 2)}</pre>
                        </details>
                      </li>
                    ))}
                  </ul>
                  <label>
                    Reconstruction operator
                    <input
                      aria-label="Reconstruction operator"
                      value={reconstructionOperator}
                      onChange={(event) => setReconstructionOperator(event.target.value)}
                      disabled={reconstructionCommitMutation.isPending}
                    />
                  </label>
                  <label>
                    Reconstruction audit reason
                    <textarea
                      aria-label="Reconstruction audit reason"
                      value={reconstructionReason}
                      onChange={(event) => setReconstructionReason(event.target.value)}
                      disabled={reconstructionCommitMutation.isPending}
                    />
                  </label>
                  <div className="quick-actions">
                    <button
                      type="button"
                      onClick={() => reconstructionCommitMutation.mutate()}
                      disabled={
                        !selectedReconstructionCandidate ||
                        !reconstructionOperator.trim() ||
                        !reconstructionReason.trim() ||
                        reconstructionCommitMutation.isPending
                      }
                    >
                      Select this reconstruction
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setReconstructionReview(null)
                        setSelectedReconstructionCandidate('')
                        setReconstructionCommandId(newCommandId())
                      }}
                      disabled={reconstructionCommitMutation.isPending}
                    >
                      Edit constraints and regenerate
                    </button>
                  </div>
                </>
              )}
              {reconstructionPreviewMutation.error ? (
                <p className="error">
                  Match Reconstruction preview failed: {formatApiError(reconstructionPreviewMutation.error)}
                </p>
              ) : null}
              {reconstructionCommitMutation.error ? (
                <p className="error">
                  Match Reconstruction commit failed: {formatApiError(reconstructionCommitMutation.error)}
                </p>
              ) : null}
              {reconstructionCommitMutation.data ? (
                <p className="status">
                  Selected reconstruction committed: {reconstructionCommitMutation.data.result_fingerprint}.
                </p>
              ) : null}
            </>
          ) : null}
          <label>
            <input
              aria-label="Confirm authoritative simulation"
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />{' '}
            I reviewed the current canonical position and Saved Revision head.
          </label>
          <div className="form-grid">
            <label>
              Next Week operator
              <input
                aria-label="Next Week operator"
                value={nextWeekOperator}
                maxLength={128}
                disabled={Boolean(nextWeekReview) || nextWeekMutation.isPending}
                onChange={(event) => setNextWeekOperator(event.target.value)}
              />
            </label>
            <label>
              Next Week audit reason
              <textarea
                aria-label="Next Week audit reason"
                value={nextWeekReason}
                maxLength={2000}
                disabled={Boolean(nextWeekReview) || nextWeekMutation.isPending}
                onChange={(event) => setNextWeekReason(event.target.value)}
              />
            </label>
            <label>
              Next Season operator
              <input
                aria-label="Next Season operator"
                value={nextSeasonOperator}
                maxLength={128}
                disabled={Boolean(nextSeasonReview) || nextSeasonMutation.isPending}
                onChange={(event) => setNextSeasonOperator(event.target.value)}
              />
            </label>
            <label>
              Next Season audit reason
              <textarea
                aria-label="Next Season audit reason"
                value={nextSeasonReason}
                maxLength={2000}
                disabled={Boolean(nextSeasonReview) || nextSeasonMutation.isPending}
                onChange={(event) => setNextSeasonReason(event.target.value)}
              />
            </label>
          </div>
          <div className="quick-actions">
            <button
              type="button"
              onClick={() => nextMatchMutation.mutate()}
              disabled={currentEntrySlot || !confirmed || !selectedGroupId || actionPending}
            >
              Simulate authoritative Next Match
            </button>
            <button
              type="button"
              onClick={() => nextSlotMutation.mutate()}
              disabled={currentEntrySlot || !confirmed || position.eligible_match_ids.length === 0 || actionPending}
            >
              Simulate authoritative Next Slot
            </button>
            <button
              type="button"
              onClick={() => nextMatchDayPreviewMutation.mutate()}
              disabled={
                currentEntrySlot ||
                position.current_slot_kind !== 'match' ||
                schedule?.schema_version !== 'week_simulation_schedule.v2' ||
                actionPending
              }
            >
              Review authoritative Next Match Day
            </button>
            <button
              type="button"
              onClick={() => nextRoundPreviewMutation.mutate()}
              disabled={
                currentEntrySlot ||
                position.current_slot_kind !== 'match' ||
                schedule?.schema_version !== 'week_simulation_schedule.v2' ||
                actionPending
              }
            >
              Review authoritative Next Round
            </button>
            <button
              type="button"
              onClick={() => nextTournamentPreviewMutation.mutate()}
              disabled={
                currentEntrySlot ||
                position.current_slot_kind !== 'match' ||
                schedule?.schema_version !== 'week_simulation_schedule.v2' ||
                actionPending
              }
            >
              Review authoritative Next Tournament
            </button>
            <button
              type="button"
              onClick={() => nextWeekPreviewMutation.mutate()}
              disabled={
                currentEntrySlot ||
                position.current_week.week === 61 ||
                !nextWeekOperator.trim() ||
                !nextWeekReason.trim() ||
                (position.current_slot_kind === 'match' &&
                  schedule?.schema_version !== 'week_simulation_schedule.v2') ||
                actionPending
              }
            >
              Review authoritative Next Week
            </button>
            <button
              type="button"
              onClick={() => nextSeasonPreviewMutation.mutate()}
              disabled={
                position.current_week.season_index >= 49 ||
                !nextSeasonOperator.trim() ||
                !nextSeasonReason.trim() ||
                actionPending
              }
            >
              Review authoritative Next Season
            </button>
          </div>
          {nextMatchDayReview ? (
            <>
              <h5>Reviewed canonical Match Day {nextMatchDayReview.match_day_ordinal}</h5>
              <MetadataList
                items={[
                  { label: 'Match Day', value: nextMatchDayReview.match_day_ordinal },
                  {
                    label: 'Global slots',
                    value: nextMatchDayReview.target_slot_ordinals.join(', ')
                  },
                  {
                    label: 'Competitive matches',
                    value: nextMatchDayReview.target_group_ids.length
                  },
                  {
                    label: 'Saved Revision',
                    value: nextMatchDayReview.expected_revision_id
                  },
                  {
                    label: 'Schedule fingerprint',
                    value: nextMatchDayReview.schedule_fingerprint
                  }
                ]}
              />
              <ol aria-label="Reviewed authoritative Match Day">
                {nextMatchDayReview.target_slot_ordinals.map((slotOrdinal, index) => (
                  <li key={slotOrdinal}>
                    Global slot {slotOrdinal}: {nextMatchDayReview.target_group_ids[index]}
                  </li>
                ))}
              </ol>
              <div className="quick-actions">
                <button
                  type="button"
                  onClick={() => nextMatchDayMutation.mutate()}
                  disabled={!confirmed || actionPending}
                >
                  Simulate reviewed authoritative Match Day
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNextMatchDayReview(null)
                    setNextMatchDayCommandId(newCommandId())
                  }}
                  disabled={nextMatchDayMutation.isPending}
                >
                  Discard Match Day review
                </button>
              </div>
            </>
          ) : null}
          {nextRoundReview ? (
            <>
              <h5>
                Reviewed canonical Round · {nextRoundReview.round_identity.event_id} ·{' '}
                {nextRoundReview.round_identity.draw_phase} R
                {nextRoundReview.round_identity.round_number}
              </h5>
              <MetadataList
                items={[
                  { label: 'Event', value: nextRoundReview.round_identity.event_id },
                  { label: 'Draw phase', value: nextRoundReview.round_identity.draw_phase },
                  { label: 'Round', value: nextRoundReview.round_identity.round_number },
                  {
                    label: 'Round matches',
                    value: nextRoundReview.target_group_ids.length
                  },
                  {
                    label: 'Chronology horizon slots',
                    value: nextRoundReview.horizon_slot_ordinals.join(', ')
                  },
                  {
                    label: 'Transit matches',
                    value: nextRoundReview.transit_group_ids.length
                  },
                  {
                    label: 'Saved Revision',
                    value: nextRoundReview.expected_revision_id
                  },
                  {
                    label: 'Schedule fingerprint',
                    value: nextRoundReview.schedule_fingerprint
                  }
                ]}
              />
              <ol aria-label="Reviewed authoritative Round target matches">
                {nextRoundReview.target_slot_ordinals.map((slotOrdinal, index) => (
                  <li key={slotOrdinal}>
                    Target slot {slotOrdinal}: {nextRoundReview.target_group_ids[index]}
                  </li>
                ))}
              </ol>
              {nextRoundReview.transit_slot_ordinals.length ? (
                <>
                  <p className="status">
                    Global chronology requires these interleaved matches before the
                    selected round can finish:
                  </p>
                  <ol aria-label="Reviewed authoritative Round transit matches">
                    {nextRoundReview.transit_slot_ordinals.map((slotOrdinal, index) => (
                      <li key={slotOrdinal}>
                        Transit slot {slotOrdinal}: {nextRoundReview.transit_group_ids[index]}
                      </li>
                    ))}
                  </ol>
                </>
              ) : null}
              <div className="quick-actions">
                <button
                  type="button"
                  onClick={() => nextRoundMutation.mutate()}
                  disabled={!confirmed || actionPending}
                >
                  Simulate reviewed authoritative Next Round
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNextRoundReview(null)
                    setNextRoundCommandId(newCommandId())
                  }}
                  disabled={nextRoundMutation.isPending}
                >
                  Discard Round review
                </button>
              </div>
            </>
          ) : null}
          {nextTournamentReview ? (
            <>
              <h5>Reviewed canonical Tournament · {nextTournamentReview.event_id}</h5>
              <MetadataList
                items={[
                  { label: 'Event', value: nextTournamentReview.event_id },
                  {
                    label: 'Tournament matches',
                    value: nextTournamentReview.target_group_ids.length
                  },
                  {
                    label: 'Chronology horizon slots',
                    value: nextTournamentReview.horizon_slot_ordinals.join(', ')
                  },
                  {
                    label: 'Transit matches',
                    value: nextTournamentReview.transit_group_ids.length
                  },
                  {
                    label: 'Saved Revision',
                    value: nextTournamentReview.expected_revision_id
                  },
                  {
                    label: 'Schedule fingerprint',
                    value: nextTournamentReview.schedule_fingerprint
                  }
                ]}
              />
              <ol aria-label="Reviewed authoritative Tournament target matches">
                {nextTournamentReview.target_slot_ordinals.map((slotOrdinal, index) => (
                  <li key={slotOrdinal}>
                    Target slot {slotOrdinal}: {nextTournamentReview.target_group_ids[index]}
                  </li>
                ))}
              </ol>
              {nextTournamentReview.transit_slot_ordinals.length ? (
                <>
                  <p className="status">
                    Global chronology requires these interleaved matches before the
                    selected tournament can finish:
                  </p>
                  <ol aria-label="Reviewed authoritative Tournament transit matches">
                    {nextTournamentReview.transit_slot_ordinals.map((slotOrdinal, index) => (
                      <li key={slotOrdinal}>
                        Transit slot {slotOrdinal}: {nextTournamentReview.transit_group_ids[index]}
                      </li>
                    ))}
                  </ol>
                </>
              ) : null}
              <div className="quick-actions">
                <button
                  type="button"
                  onClick={() => nextTournamentMutation.mutate()}
                  disabled={!confirmed || actionPending}
                >
                  Simulate reviewed authoritative Next Tournament
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNextTournamentReview(null)
                    setNextTournamentCommandId(newCommandId())
                  }}
                  disabled={nextTournamentMutation.isPending}
                >
                  Discard Tournament review
                </button>
              </div>
            </>
          ) : null}
          {nextWeekReview ? (
            <>
              <h5>
                Reviewed canonical Week · S{nextWeekReview.week.season_index} W
                {nextWeekReview.week.week} → W{nextWeekReview.target_week.week}
              </h5>
              <MetadataList
                items={[
                  {
                    label: 'Current week',
                    value: `Season index ${nextWeekReview.week.season_index} · Week ${nextWeekReview.week.week}`
                  },
                  {
                    label: 'Target week',
                    value: `Season index ${nextWeekReview.target_week.season_index} · Week ${nextWeekReview.target_week.week}`
                  },
                  {
                    label: 'Remaining competitive slots',
                    value: nextWeekReview.target_slot_ordinals.length
                  },
                  {
                    label: 'Ranking authority',
                    value: nextWeekReview.ranking_authority_mode
                  },
                  {
                    label: 'Saved Revision',
                    value: nextWeekReview.expected_revision_id
                  },
                  {
                    label: 'Ranking authority fingerprint',
                    value: nextWeekReview.ranking_authority_fingerprint
                  }
                ]}
              />
              {nextWeekReview.target_slot_ordinals.length ? (
                <p className="status">
                  Frozen remaining global slots: {nextWeekReview.target_slot_ordinals.join(', ')}.
                </p>
              ) : (
                <p className="status">
                  Sporting work is already complete; this reviewed range starts at Week Transition.
                </p>
              )}
              {nextWeekReview.initial_transition_blockers.length ? (
                <p className="status">
                  Expected in-progress blockers at review: {
                    nextWeekReview.initial_transition_blockers.join(', ')
                  }.
                </p>
              ) : null}
              {nextWeekProgress ? (
                <p role="alert" className="error">
                  Next Week paused after {nextWeekProgress.completed_slot_count} sporting slot(s).
                  Resolve: {nextWeekProgress.transition_blockers.join(', ')}. Retry this exact
                  reviewed command afterward.
                </p>
              ) : null}
              <div className="quick-actions">
                <button
                  type="button"
                  onClick={() => nextWeekMutation.mutate()}
                  disabled={!confirmed || actionPending}
                >
                  {nextWeekProgress
                    ? 'Retry reviewed authoritative Next Week'
                    : 'Simulate reviewed authoritative Next Week'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNextWeekReview(null)
                    setNextWeekProgress(null)
                    setNextWeekCommandId(newCommandId())
                  }}
                  disabled={nextWeekMutation.isPending}
                >
                  Discard Next Week review
                </button>
              </div>
            </>
          ) : null}
          {nextSeasonReview ? (
            <>
              <h5>
                Reviewed canonical Season · S{nextSeasonReview.start_week.season_index} W
                {nextSeasonReview.start_week.week} → S
                {nextSeasonReview.target_week.season_index} W
                {nextSeasonReview.target_week.week}
              </h5>
              <MetadataList
                items={[
                  {
                    label: 'Start',
                    value: `Season index ${nextSeasonReview.start_week.season_index} · Week ${nextSeasonReview.start_week.week}`
                  },
                  {
                    label: 'Target',
                    value: `Season index ${nextSeasonReview.target_week.season_index} · Week ${nextSeasonReview.target_week.week}`
                  },
                  {
                    label: 'Weeks including current',
                    value: nextSeasonReview.weeks_including_current
                  },
                  {
                    label: 'Initial action',
                    value: nextSeasonReview.initial_action
                  },
                  {
                    label: 'Empty-week policy',
                    value: nextSeasonReview.auto_empty_week_policy
                  },
                  {
                    label: 'Season Transition',
                    value: nextSeasonReview.season_transition_mode
                  },
                  {
                    label: 'Saved Revision at review',
                    value: nextSeasonReview.expected_revision_id
                  }
                ]}
              />
              {nextSeasonReview.initial_transition_blockers.length ? (
                <p className="status">
                  Initial canonical blockers: {
                    nextSeasonReview.initial_transition_blockers.join(', ')
                  }.
                </p>
              ) : null}
              <p className="status">
                This parent can cross ordinary weeks and Calendar-proven empty weeks.
                It will stop instead of inventing Entry/WC decisions, a hidden Save, or
                a hidden Season Transition confirmation.
              </p>
              {nextSeasonProgress ? (
                <>
                  <p role="alert" className="error">
                    Next Season paused at {nextSeasonProgress.checkpoint} after {
                      nextSeasonProgress.completed_week_count
                    } completed week(s). Current Week {
                      nextSeasonProgress.current_week.week
                    }.
                    {nextSeasonProgress.blockers.length
                      ? ` Resolve: ${nextSeasonProgress.blockers.join(', ')}.`
                      : ''}
                  </p>
                  {nextSeasonProgress.detail ? (
                    <p className="status">{nextSeasonProgress.detail}</p>
                  ) : null}
                  {nextSeasonProgress.checkpoint === 'season_transition_save_required' ? (
                    <p className="status">
                      Use <strong>Save authoritative simulation</strong> below, then retry
                      this exact reviewed Next Season command.
                    </p>
                  ) : null}
                  {nextSeasonProgress.checkpoint === 'season_transition_review_required' ? (
                    <p className="status">
                      Review and commit the existing canonical Season Transition below,
                      then retry this exact Next Season command once more.
                    </p>
                  ) : null}
                </>
              ) : null}
              <div className="quick-actions">
                <button
                  type="button"
                  onClick={() => nextSeasonMutation.mutate()}
                  disabled={!confirmed || actionPending}
                >
                  {nextSeasonProgress
                    ? 'Retry reviewed authoritative Next Season'
                    : 'Simulate reviewed authoritative Next Season'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNextSeasonReview(null)
                    setNextSeasonProgress(null)
                    setNextSeasonCommandId(newCommandId())
                  }}
                  disabled={nextSeasonMutation.isPending}
                >
                  Discard Next Season review
                </button>
              </div>
            </>
          ) : null}
          {nextMatchMutation.error ? (
            <p className="error">Authoritative Next Match failed: {formatApiError(nextMatchMutation.error)}</p>
          ) : null}
          {nextSlotMutation.error ? (
            <p className="error">Authoritative Next Slot failed: {formatApiError(nextSlotMutation.error)}</p>
          ) : null}
          {nextMatchDayPreviewMutation.error ? (
            <p className="error">
              Authoritative Match Day preview failed: {formatApiError(nextMatchDayPreviewMutation.error)}
            </p>
          ) : null}
          {nextMatchDayMutation.error ? (
            <p className="error">
              Authoritative Next Match Day failed: {formatApiError(nextMatchDayMutation.error)}
            </p>
          ) : null}
          {nextRoundPreviewMutation.error ? (
            <p className="error">
              Authoritative Round preview failed: {formatApiError(nextRoundPreviewMutation.error)}
            </p>
          ) : null}
          {nextRoundMutation.error ? (
            <p className="error">
              Authoritative Next Round failed: {formatApiError(nextRoundMutation.error)}
            </p>
          ) : null}
          {nextTournamentPreviewMutation.error ? (
            <p className="error">
              Authoritative Tournament preview failed: {formatApiError(nextTournamentPreviewMutation.error)}
            </p>
          ) : null}
          {nextTournamentMutation.error ? (
            <p className="error">
              Authoritative Next Tournament failed: {formatApiError(nextTournamentMutation.error)}
            </p>
          ) : null}
          {nextWeekPreviewMutation.error ? (
            <p className="error">
              Authoritative Week preview failed: {formatApiError(nextWeekPreviewMutation.error)}
            </p>
          ) : null}
          {nextWeekMutation.error ? (
            <p className="error">
              Authoritative Next Week failed: {formatApiError(nextWeekMutation.error)}.
              The reviewed command is preserved for exact retry.
            </p>
          ) : null}
          {nextSeasonPreviewMutation.error ? (
            <p className="error">
              Authoritative Season preview failed: {formatApiError(nextSeasonPreviewMutation.error)}
            </p>
          ) : null}
          {nextSeasonMutation.error ? (
            <p className="error">
              Authoritative Next Season failed: {formatApiError(nextSeasonMutation.error)}.
              The reviewed parent command is preserved for exact retry.
            </p>
          ) : null}
        </>
      ) : null}

      {entryValidationMutation.data ? (
        <p className="status">
          Entry validation committed: {entryValidationMutation.data.valid_submission_count} valid application(s), {entryValidationMutation.data.first_tour_entry_trigger_fingerprints.length} first Tour-entry trigger(s).
        </p>
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

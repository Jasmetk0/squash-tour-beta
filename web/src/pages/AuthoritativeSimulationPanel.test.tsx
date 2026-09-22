import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ComponentProps } from 'react'

import { AuthoritativeSimulationPanel } from './AuthoritativeSimulationPanel'

const api = vi.hoisted(() => ({
  getAuthoritativeSimulationPosition: vi.fn(),
  inspectAuthoritativeEntryDecisionSlot: vi.fn(),
  reviewAuthoritativeEntryDecisionSlot: vi.fn(),
  inspectWeekTournamentLock: vi.fn(),
  previewWeekTournamentLock: vi.fn(),
  commitWeekTournamentLock: vi.fn(),
  getAuthoritativeSeasonTransitionPreflight: vi.fn(),
  getAdminVisibleProspects: vi.fn(),
  previewAuthoritativeSeasonTransitionConfiguration: vi.fn(),
  advanceAuthoritativeOrdinarySeason: vi.fn(),
  finalizeAuthoritativeFinalSeason: vi.fn(),
  inspectAuthoritativeWeekSchedule: vi.fn(),
  previewAuthoritativeSimulationSave: vi.fn(),
  proposeAuthoritativeWeekSchedule: vi.fn(),
  previewAuthoritativeWeekSchedule: vi.fn(),
  adoptAuthoritativeWeekSchedule: vi.fn(),
  adoptAuthoritativeWeekScheduleProposal: vi.fn(),
  simulateAuthoritativeNextMatch: vi.fn(),
  simulateAuthoritativeNextSlot: vi.fn(),
  previewAuthoritativeNextMatchDay: vi.fn(),
  simulateAuthoritativeNextMatchDay: vi.fn(),
  previewAuthoritativeNextRound: vi.fn(),
  simulateAuthoritativeNextRound: vi.fn(),
  previewAuthoritativeNextTournament: vi.fn(),
  simulateAuthoritativeNextTournament: vi.fn(),
  previewAuthoritativeNextWeek: vi.fn(),
  simulateAuthoritativeNextWeek: vi.fn(),
  previewAuthoritativeNextSeason: vi.fn(),
  simulateAuthoritativeNextSeason: vi.fn(),
  previewAuthoritativeFullSimulation: vi.fn(),
  simulateAuthoritativeFullSimulation: vi.fn(),
  getPendingAuthoritativeFullSimulations: vi.fn(),
  inspectAuthoritativeMatchReconstruction: vi.fn(),
  previewAuthoritativeMatchReconstruction: vi.fn(),
  commitAuthoritativeMatchReconstruction: vi.fn(),
  saveAuthoritativeSimulation: vi.fn(),
  previewDerivedAuthoritativeWeekTransition: vi.fn(),
  confirmAuthoritativeWeekTransition: vi.fn(),
  previewRankingSave: vi.fn(),
  saveRankingPreparation: vi.fn(),
  previewDerivedRankingTransitionAuthority: vi.fn(),
  confirmDerivedRankingTransitionAuthority: vi.fn()
}))

vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/client')>()),
  ...api
}))

const week = { season_index: 2, week: 17 }
const position = {
  run_id: 'run-a',
  branch_id: 'branch-a',
  current_week: week,
  current_slot_kind: 'match' as const,
  current_slot_id: 'slot-1',
  slot_ordinal: 1,
  unresolved_group_ids: ['g1', 'g2', 'g3'],
  eligible_match_ids: ['g1', 'g2'],
  blocked_match_ids: ['g3'],
  current_slot_complete: false,
  supported_tournament_complete: false,
  week_ready_for_transition: false,
  transition_blockers: ['pending_authoritative_groups'],
  terminal_sporting_fingerprint: null,
  position_fingerprint: 'a'.repeat(64)
}

const scheduleInspection = {
  run_id: 'run-a',
  branch_id: 'branch-a',
  week,
  required: true,
  event_ids: ['event-a', 'event-b'],
  group_ids: ['g1', 'g2', 'g3'],
  schedule: null,
  schedule_fingerprint: null,
  expected_position_fingerprint: 'b'.repeat(64)
}

const proposal = {
  schedule: {
    schema_version: 'week_simulation_schedule.v2' as const,
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    slots: [
      {
        ordinal: 1,
        group_ids: ['g1'],
        match_day_ordinal: 1,
        match_order: 1,
        event_id: 'event-a',
        draw_phase: 'main' as const,
        round_number: 1
      },
      {
        ordinal: 2,
        group_ids: ['g2'],
        match_day_ordinal: 1,
        match_order: 2,
        event_id: 'event-b',
        draw_phase: 'main' as const,
        round_number: 1
      },
      {
        ordinal: 3,
        group_ids: ['g3'],
        match_day_ordinal: 2,
        match_order: 1,
        event_id: 'event-a',
        draw_phase: 'main' as const,
        round_number: 2
      }
    ]
  },
  schedule_fingerprint: 'c'.repeat(64),
  position_fingerprint: 'd'.repeat(64),
  provenance: 'match_day_schedule_hard_constraints.v1; one competitive match per global Simulation Slot',
  persisted: false as const
}

const matchDayPreview = {
  schema_version: 'authoritative_match_day_preview.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  week,
  match_day_ordinal: 1,
  schedule_fingerprint: 'c'.repeat(64),
  target_slot_ordinals: [1, 2],
  target_group_ids: ['g1', 'g2'],
  expected_position_fingerprint: 'a'.repeat(64),
  expected_revision_id: 'revision-7',
  preview_fingerprint: '7'.repeat(64)
}

const matchDayResult = {
  schema_version: 'authoritative_match_day_result.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  week,
  match_day_ordinal: 1,
  schedule_fingerprint: 'c'.repeat(64),
  target_slot_ordinals: [1, 2],
  target_group_ids: ['g1', 'g2'],
  child_command_ids: ['match-day-slot:one', 'match-day-slot:two'],
  completed_slot_count: 2,
  position: {
    ...position,
    current_slot_id: 'slot-3',
    slot_ordinal: 3,
    eligible_match_ids: ['g3'],
    unresolved_group_ids: ['g3'],
    blocked_match_ids: [],
    position_fingerprint: '1'.repeat(64)
  },
  adoption: 'committed' as const
}

const roundPreview = {
  schema_version: 'authoritative_round_preview.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  week,
  round_identity: {
    event_id: 'event-a',
    draw_phase: 'main' as const,
    round_number: 1
  },
  schedule_fingerprint: 'c'.repeat(64),
  target_slot_ordinals: [1, 3],
  target_group_ids: ['g1', 'g3'],
  horizon_slot_ordinals: [1, 2, 3],
  transit_slot_ordinals: [2],
  transit_group_ids: ['g2'],
  expected_position_fingerprint: 'a'.repeat(64),
  expected_revision_id: 'revision-7',
  preview_fingerprint: '8'.repeat(64)
}

const roundResult = {
  schema_version: 'authoritative_round_result.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  week,
  round_identity: roundPreview.round_identity,
  schedule_fingerprint: 'c'.repeat(64),
  target_slot_ordinals: [1, 3],
  target_group_ids: ['g1', 'g3'],
  horizon_slot_ordinals: [1, 2, 3],
  transit_slot_ordinals: [2],
  transit_group_ids: ['g2'],
  child_command_ids: ['round-slot:one', 'round-slot:two', 'round-slot:three'],
  completed_slot_count: 3,
  position: {
    ...position,
    current_slot_id: 'slot-4',
    slot_ordinal: 4,
    eligible_match_ids: ['g4'],
    unresolved_group_ids: ['g4'],
    blocked_match_ids: [],
    position_fingerprint: '2'.repeat(64)
  },
  adoption: 'committed' as const
}

const tournamentPreview = {
  schema_version: 'authoritative_tournament_preview.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  week,
  event_id: 'event-a',
  schedule_fingerprint: 'c'.repeat(64),
  target_slot_ordinals: [1, 3],
  target_group_ids: ['g1', 'g3'],
  horizon_slot_ordinals: [1, 2, 3],
  transit_slot_ordinals: [2],
  transit_group_ids: ['g2'],
  expected_position_fingerprint: 'a'.repeat(64),
  expected_revision_id: 'revision-7',
  preview_fingerprint: '9'.repeat(64)
}

const tournamentResult = {
  schema_version: 'authoritative_tournament_result.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  week,
  event_id: 'event-a',
  schedule_fingerprint: 'c'.repeat(64),
  target_slot_ordinals: [1, 3],
  target_group_ids: ['g1', 'g3'],
  horizon_slot_ordinals: [1, 2, 3],
  transit_slot_ordinals: [2],
  transit_group_ids: ['g2'],
  child_command_ids: [
    'tournament-slot:one',
    'tournament-slot:two',
    'tournament-slot:three'
  ],
  completed_slot_count: 3,
  owned_tournament_source_fingerprint: 'f'.repeat(64),
  position: {
    ...position,
    current_slot_id: 'slot-4',
    slot_ordinal: 4,
    eligible_match_ids: ['g4'],
    unresolved_group_ids: ['g4'],
    blocked_match_ids: [],
    position_fingerprint: '3'.repeat(64)
  },
  adoption: 'committed' as const
}

const weekPreview = {
  schema_version: 'authoritative_week_preview.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  week,
  target_week: { season_index: 2, week: 18 },
  schedule_fingerprint: 'c'.repeat(64),
  target_slot_ordinals: [1, 2, 3],
  target_group_ids: ['g1', 'g2', 'g3'],
  ranking_authority_mode: 'derived' as const,
  ranking_authority_command_id: 'week-authority:preview',
  ranking_authority_fingerprint: '5'.repeat(64),
  expected_position_fingerprint: 'a'.repeat(64),
  expected_revision_id: 'revision-7',
  initial_transition_blockers: [
    'pending_authoritative_groups',
    'ranking_transition_authority_missing'
  ],
  preview_fingerprint: '6'.repeat(64)
}

const weekProgress = {
  schema_version: 'authoritative_week_progress.v1' as const,
  status: 'blocked' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  completed_week: week,
  target_week: { season_index: 2, week: 18 },
  target_slot_ordinals: [1, 2, 3],
  completed_slot_count: 3,
  transition_blockers: ['working_draft_dirty'],
  position: {
    ...position,
    current_slot_kind: null,
    current_slot_id: null,
    slot_ordinal: null,
    unresolved_group_ids: [],
    eligible_match_ids: [],
    blocked_match_ids: [],
    current_slot_complete: true,
    supported_tournament_complete: true,
    week_ready_for_transition: false,
    transition_blockers: ['working_draft_dirty'],
    terminal_sporting_fingerprint: '7'.repeat(64),
    position_fingerprint: '8'.repeat(64)
  }
}

const weekResult = {
  schema_version: 'authoritative_week_result.v1' as const,
  status: 'complete' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  completed_week: week,
  target_week: { season_index: 2, week: 18 },
  schedule_fingerprint: 'c'.repeat(64),
  target_slot_ordinals: [1, 2, 3],
  target_group_ids: ['g1', 'g2', 'g3'],
  child_command_ids: ['week-slot:one', 'week-slot:two', 'week-slot:three'],
  completed_slot_count: 3,
  ranking_authority_mode: 'derived' as const,
  ranking_authority_command_id: 'week-authority:preview',
  ranking_authority_fingerprint: '5'.repeat(64),
  week_transition_command_id: 'week-transition:one',
  week_transition_request_fingerprint: '9'.repeat(64),
  official_ranking_fingerprint: 'a'.repeat(64),
  player_lifecycle_fingerprint: 'b'.repeat(64),
  player_sporting_fingerprint: 'd'.repeat(64),
  world_event_kind: 'week_transition_completed' as const,
  adoption: 'committed' as const
}

const seasonCompletedWeeks = Array.from(
  { length: 45 },
  (_, index) => ({ season_index: 2, week: 17 + index })
)

const seasonPreview = {
  schema_version: 'authoritative_season_preview.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  start_week: week,
  target_week: { season_index: 3, week: 1 },
  weeks_including_current: 45,
  initial_action: 'next_week',
  initial_transition_blockers: ['pending_authoritative_groups'],
  auto_empty_week_policy: 'calendar_proven_audited_child_only' as const,
  season_transition_mode: 'explicit_save_and_review_checkpoint' as const,
  expected_position_fingerprint: 'a'.repeat(64),
  expected_revision_id: 'revision-7',
  preview_fingerprint: '4'.repeat(64)
}

const seasonBoundaryPosition = {
  ...position,
  current_week: { season_index: 2, week: 61 },
  current_slot_kind: null,
  current_slot_id: null,
  slot_ordinal: null,
  unresolved_group_ids: [],
  eligible_match_ids: [],
  blocked_match_ids: [],
  current_slot_complete: true,
  supported_tournament_complete: true,
  week_ready_for_transition: false,
  transition_blockers: ['season_transition_required'],
  terminal_sporting_fingerprint: 'e'.repeat(64),
  position_fingerprint: 'f'.repeat(64)
}

const seasonSaveProgress = {
  schema_version: 'authoritative_season_progress.v1' as const,
  status: 'blocked' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  start_week: week,
  current_week: { season_index: 2, week: 61 },
  target_week: { season_index: 3, week: 1 },
  completed_weeks: seasonCompletedWeeks,
  completed_week_count: 45,
  checkpoint: 'season_transition_save_required' as const,
  blockers: ['season_transition_save_required'],
  detail: 'Save the current canonical world explicitly.',
  position: seasonBoundaryPosition
}

const seasonReviewProgress = {
  ...seasonSaveProgress,
  checkpoint: 'season_transition_review_required' as const,
  blockers: ['season_transition_review_required'],
  detail: 'Review and commit canonical Season Transition.'
}

const seasonResult = {
  schema_version: 'authoritative_season_result.v1' as const,
  status: 'complete' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  start_week: week,
  target_week: { season_index: 3, week: 1 },
  completed_weeks: seasonCompletedWeeks,
  completed_week_count: 45,
  week_child_command_ids: ['season-week:one'],
  empty_week_child_command_ids: ['season-empty:one'],
  week61_slot_child_command_ids: [],
  season_transition_observed: true as const,
  saved_revision_id: 'revision-season-3',
  position: {
    ...seasonBoundaryPosition,
    current_week: { season_index: 3, week: 1 },
    transition_blockers: [],
    terminal_sporting_fingerprint: null,
    position_fingerprint: '1'.repeat(64)
  },
  adoption: 'committed' as const
}

const fullSimulationPreview = {
  schema_version: 'authoritative_full_simulation_preview.v1' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  start_week: week,
  final_week: { season_index: 49, week: 61 },
  remaining_weeks_including_current: 2912,
  remaining_seasons_including_current: 48,
  initial_action: 'next_season' as const,
  initial_transition_blockers: ['pending_authoritative_groups'],
  season_child_mode: 'canonical_next_season' as const,
  final_season_mode: 'canonical_final_run_closure' as const,
  explicit_boundary_policy:
    'save_and_review_required_at_every_season_boundary' as const,
  expected_position_fingerprint: 'a'.repeat(64),
  expected_revision_id: 'revision-7',
  preview_fingerprint: '2'.repeat(64)
}

const fullSimulationSaveProgress = {
  schema_version: 'authoritative_full_simulation_progress.v1' as const,
  status: 'blocked' as const,
  run_id: 'run-a',
  branch_id: 'branch-a',
  start_week: week,
  current_week: { season_index: 2, week: 61 },
  final_week: { season_index: 49, week: 61 },
  completed_seasons: [],
  completed_season_count: 0,
  final_completed_weeks: [],
  final_completed_week_count: 0,
  checkpoint: 'season_transition_save_required' as const,
  blockers: ['season_transition_save_required'],
  detail: 'Save the current canonical world explicitly.',
  position: seasonBoundaryPosition,
  child_progress: seasonSaveProgress
}

const fullSimulationReviewProgress = {
  ...fullSimulationSaveProgress,
  checkpoint: 'season_transition_review_required' as const,
  blockers: ['season_transition_review_required'],
  detail: 'Review and commit the existing canonical Season Transition.',
  child_progress: seasonReviewProgress
}

const editedSchedule = {
  ...proposal.schedule,
  slots: [
    {
      ...proposal.schedule.slots[0],
      ordinal: 1,
      match_day_ordinal: 1,
      match_order: 1
    },
    {
      ...proposal.schedule.slots[1],
      ordinal: 2,
      match_day_ordinal: 2,
      match_order: 1
    },
    {
      ...proposal.schedule.slots[2],
      ordinal: 3,
      match_day_ordinal: 3,
      match_order: 1
    }
  ]
}

const transitionPreview = {
  request_fingerprint: '7'.repeat(64),
  command: {
    kind: 'authoritative_week_transition.v1' as const,
    command_id: 'transition-command',
    run_id: 'run-a',
    branch_id: 'branch-a',
    base_revision_id: 'revision-7',
    completed_week: week,
    target_week: { season_index: 2, week: 18 },
    authority_fingerprint: '8'.repeat(64),
    tournaments: [{
      run_id: 'run-a',
      branch_id: 'branch-a',
      edition_id: 'event-a',
      event_id: 'event-a',
      completed_week: week,
      first_publication_week: { season_index: 2, week: 18 },
      validity_weeks: 52,
      ranking_status: 'ranked' as const,
      expected_result_fingerprint: '9'.repeat(64),
      expected_award_fingerprint: 'a'.repeat(64)
    }],
    corrections: [],
    zero_versions: [],
    audit: { actor_label: 'Admin', reason: 'Reviewed canonical transition' }
  },
  result: {
    run_id: 'run-a',
    branch_id: 'branch-a',
    command_id: 'transition-command',
    completed_week: week,
    target_week: { season_index: 2, week: 18 },
    official_ranking_fingerprint: 'b'.repeat(64),
    player_lifecycle_fingerprint: 'c'.repeat(64),
    player_sporting_fingerprint: 'd'.repeat(64),
    world_event_kind: 'week_transition_completed' as const
  }
}

const rankingAuthorityPreview = {
  authority_fingerprint: '6'.repeat(64),
  authority: {
    schema_version: 'ranking_transition_authority.v1' as const,
    run_id: 'run-a',
    branch_id: 'branch-a',
    base_revision_id: 'revision-7',
    completed_week: week,
    target_week: { season_index: 2, week: 18 },
    players: [
      {
        player_id: 'P001',
        tie_break_token: 'token-P001',
        tour_entry_week: { season_index: 0, week: 1 },
        retired: false
      },
      {
        player_id: 'P002',
        tie_break_token: 'token-P002',
        tour_entry_week: { season_index: 0, week: 1 },
        retired: false
      }
    ],
    policy: {
      policy_id: 'season-3-policy',
      best_n: 15,
      tie_break_version: 'result_profile_age_previous_token.v1' as const
    },
    provenance: 'Derived from canonical target-week player lifecycle and predecessor Official Ranking policy',
    adopted_by_command_id: 'authority-command',
    audit: {
      actor_label: 'Admin operator',
      reason: 'Review canonical ranking boundary'
    }
  }
}

function renderPanel(props: Partial<ComponentProps<typeof AuthoritativeSimulationPanel>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AuthoritativeSimulationPanel
        runId="run-a"
        branchId="branch-a"
        savedRevisionId="revision-7"
        blockedReason={null}
        {...props}
      />
    </QueryClientProvider>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  api.getAuthoritativeSimulationPosition.mockResolvedValue(position)
  api.getPendingAuthoritativeFullSimulations.mockResolvedValue({
    schema_version: 'authoritative_full_simulation_pending_collection.v1',
    run_id: 'run-a',
    branch_id: 'branch-a',
    operations: [],
    legacy_pending_count: 0
  })
  api.inspectAuthoritativeEntryDecisionSlot.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    decision_slot_ordinal: 1,
    slot_fingerprint: '4'.repeat(64),
    authority: {
      schema_version: 'run_entry_decision_slot_authority.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      week,
      decision_slot_ordinal: 1,
      source_entry_batch_fingerprint: '1'.repeat(64),
      source_application_decisions_fingerprint: '2'.repeat(64),
      source_active_players_fingerprint: '3'.repeat(64),
      decisions: [
        {
          event_id: 'event-a',
          player_id: 'P001',
          target: 'MAIN',
          source_decision_fingerprint: '5'.repeat(64)
        },
        {
          event_id: 'event-b',
          player_id: 'P002',
          target: 'QUALIFICATION',
          source_decision_fingerprint: '6'.repeat(64)
        }
      ]
    },
    identity_tokens: {
      P001: 'token-P001',
      P002: 'token-P002'
    },
    validation_resolved: false,
    validation_fingerprint: null
  })
  api.reviewAuthoritativeEntryDecisionSlot.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    decision_slot_ordinal: 1,
    entry_slot_fingerprint: '4'.repeat(64),
    validation_fingerprint: '7'.repeat(64),
    validation_mode: 'explicit_admin_review.v1',
    validation_policy_id: 'explicit_admin_application_validation.v1',
    validation_policy_fingerprint: '8'.repeat(64),
    valid_submission_count: 1,
    submission_batch_fingerprint: '9'.repeat(64),
    first_tour_entry_trigger_fingerprints: ['a'.repeat(64)]
  })
  api.inspectWeekTournamentLock.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    expected_revision_id: 'revision-7',
    position_fingerprint: 'a'.repeat(64),
    event_ids: ['event-a', 'event-b'],
    event_evidence: [],
    conflicts: [],
    lock_status: 'not_required',
    authority: null,
    authority_fingerprint: null,
    selection_policy_id: 'explicit_admin_week_tournament_lock.v1',
    final_commitment_deadline_policy: 'intentionally_unresolved'
  })
  api.previewWeekTournamentLock.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    event_ids: ['event-a', 'event-b'],
    authority: {
      schema_version: 'week_tournament_lock_authority.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      week,
      resolved_by_command_id: 'lock-command',
      selection_policy_id: 'explicit_admin_week_tournament_lock.v1',
      operator_label: 'Commissioner',
      audit_reason: 'Resolve overlapping accepted fields',
      event_evidence: [
        {
          event_id: 'event-a',
          entry_field_fingerprint: '1'.repeat(64),
          accepted_player_ids: ['P001']
        },
        {
          event_id: 'event-b',
          entry_field_fingerprint: '2'.repeat(64),
          accepted_player_ids: ['P001']
        }
      ],
      player_locks: [
        {
          player_id: 'P001',
          eligible_event_ids: ['event-a', 'event-b'],
          selected_event_id: 'event-a'
        }
      ]
    },
    authority_fingerprint: '3'.repeat(64),
    position_fingerprint: 'a'.repeat(64),
    persisted: false
  })
  api.commitWeekTournamentLock.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    authority: {
      schema_version: 'week_tournament_lock_authority.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      week,
      resolved_by_command_id: 'lock-command',
      selection_policy_id: 'explicit_admin_week_tournament_lock.v1',
      operator_label: 'Commissioner',
      audit_reason: 'Resolve overlapping accepted fields',
      event_evidence: [
        {
          event_id: 'event-a',
          entry_field_fingerprint: '1'.repeat(64),
          accepted_player_ids: ['P001']
        },
        {
          event_id: 'event-b',
          entry_field_fingerprint: '2'.repeat(64),
          accepted_player_ids: ['P001']
        }
      ],
      player_locks: [
        {
          player_id: 'P001',
          eligible_event_ids: ['event-a', 'event-b'],
          selected_event_id: 'event-a'
        }
      ]
    },
    authority_fingerprint: '3'.repeat(64),
    field_repairs: [
      {
        event_id: 'event-b',
        withdrawn_player_ids: ['P001'],
        field_fingerprint: '4'.repeat(64)
      }
    ],
    adoption: 'committed'
  })
  api.getAdminVisibleProspects.mockResolvedValue({
    schema_version: 'visible_pre_tour_prospects.v1',
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    lifecycle_fingerprint: '9'.repeat(64),
    total: 1,
    limit: 10,
    offset: 0,
    prospects: [
      {
        player_id: 'prospect-one',
        display_name: 'CZE Prospect 0001',
        short_name: 'CZE P.',
        country_code: 'CZE',
        country_name: 'Czechia',
        age: 15,
        birth_year: 1987,
        birth_year_week: 53,
        lifecycle_status: 'active',
        tour_status: 'pre_tour',
        visible_since_week: week
      }
    ]
  })
  api.getAuthoritativeSeasonTransitionPreflight.mockResolvedValue({
    schema_version: 'authoritative_season_transition_preflight.v1',
    run_id: 'run-a',
    branch_id: 'branch-a',
    completed_week: { season_index: 2, week: 61 },
    target_week: { season_index: 3, week: 1 },
    final_season: false,
    saved_revision_id: 'revision-7',
    draft_version: 4,
    default_configuration_fingerprint: '6'.repeat(64),
    default_closing_ranking_fingerprint: 'a'.repeat(64),
    default_sporting_fingerprint: '7'.repeat(64),
    default_lifecycle_fingerprint: '8'.repeat(64),
    default_ranking_fingerprint: '9'.repeat(64),
    position_fingerprint: '4'.repeat(64),
    state_blockers: [],
    implementation_gaps: [],
    ready_for_execution: true,
    preflight_fingerprint: '5'.repeat(64)
  })
  api.inspectAuthoritativeWeekSchedule.mockResolvedValue(scheduleInspection)
  api.previewAuthoritativeSimulationSave.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    saved_head_revision_id: 'revision-7',
    draft_version: 4,
    has_unsaved_changes: false,
    can_save: false,
    simulation_fingerprint: 'e'.repeat(64)
  })
  api.proposeAuthoritativeWeekSchedule.mockResolvedValue(proposal)
  api.previewAuthoritativeWeekSchedule.mockResolvedValue({
    schedule: editedSchedule,
    schedule_fingerprint: 'e'.repeat(64),
    position_fingerprint: 'f'.repeat(64)
  })
  api.adoptAuthoritativeWeekSchedule.mockResolvedValue({
    ...scheduleInspection,
    schedule: editedSchedule,
    schedule_fingerprint: 'e'.repeat(64)
  })
  api.adoptAuthoritativeWeekScheduleProposal.mockResolvedValue({
    ...scheduleInspection,
    schedule: proposal.schedule,
    schedule_fingerprint: proposal.schedule_fingerprint,
    adoption: 'adopted_topological_proposal'
  })
  api.inspectAuthoritativeMatchReconstruction.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    expected_revision_id: 'revision-7',
    position_fingerprint: 'a'.repeat(64),
    slot_id: 'slot-1',
    slot_start_fingerprint: '2'.repeat(64),
    group_id: 'g1',
    event_id: 'event-a',
    match_id: 'match-g1',
    player_a_id: 'P001',
    player_b_id: 'P002'
  })
  api.previewAuthoritativeMatchReconstruction.mockResolvedValue({
    schema_version: 'authoritative_match_reconstruction_preview.v1',
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    slot_id: 'slot-1',
    slot_start_fingerprint: '2'.repeat(64),
    group_id: 'g1',
    event_id: 'event-a',
    match_id: 'match-g1',
    player_a_id: 'P001',
    player_b_id: 'P002',
    candidate_count_requested: 2,
    candidate_count_found: 1,
    attempted_scenarios: 3,
    search_complete: false,
    constraints: { winner_player_id: 'P001' },
    candidates: [{
      candidate_fingerprint: '3'.repeat(64),
      attempt_ordinal: 3,
      seed: 123,
      result_fingerprint: '4'.repeat(64),
      authoritative_input_fingerprint: '5'.repeat(64),
      winner_player_id: 'P001',
      player_a_id: 'P001',
      player_b_id: 'P002',
      sets_won: { P001: 3, P002: 1 },
      game_scores: [
        { player_a_points: 11, player_b_points: 7 },
        { player_a_points: 8, player_b_points: 11 },
        { player_a_points: 11, player_b_points: 9 },
        { player_a_points: 11, player_b_points: 6 }
      ],
      match_elapsed_seconds: 2100,
      detail: {
        match_id: 'match-g1',
        winner_player_id: 'P001',
        loser_player_id: 'P002',
        player_a_id: 'P001',
        player_b_id: 'P002',
        best_of: 5,
        games_to: 11,
        win_by: 2,
        sets: [],
        sets_won: { P001: 3, P002: 1 },
        termination_reason: 'COMPLETED',
        retired_player_id: null,
        retired_at_set_start: null
      }
    }],
    warnings: ['Natural deterministic search returned one candidate.'],
    preview_fingerprint: '6'.repeat(64)
  })
  api.commitAuthoritativeMatchReconstruction.mockResolvedValue({
    schema_version: 'authoritative_match_reconstruction_commit.v1',
    run_id: 'run-a',
    branch_id: 'branch-a',
    group_id: 'g1',
    match_id: 'match-g1',
    candidate_fingerprint: '3'.repeat(64),
    result_fingerprint: '4'.repeat(64),
    preview_fingerprint: '6'.repeat(64),
    operator_label: 'Commissioner',
    audit_reason: 'Reviewed historical result',
    authority_fingerprint: '7'.repeat(64),
    position: {
      ...position,
      eligible_match_ids: ['g2'],
      unresolved_group_ids: ['g2', 'g3'],
      position_fingerprint: 'f'.repeat(64)
    },
    adoption: 'committed'
  })
  api.simulateAuthoritativeNextMatch.mockResolvedValue({
    ...position,
    eligible_match_ids: ['g2'],
    unresolved_group_ids: ['g2', 'g3'],
    position_fingerprint: 'f'.repeat(64)
  })
  api.simulateAuthoritativeNextSlot.mockResolvedValue({
    ...position,
    current_slot_id: 'slot-2',
    slot_ordinal: 2,
    eligible_match_ids: ['g3'],
    unresolved_group_ids: ['g3'],
    blocked_match_ids: [],
    position_fingerprint: '1'.repeat(64)
  })
  api.previewAuthoritativeNextMatchDay.mockResolvedValue(matchDayPreview)
  api.simulateAuthoritativeNextMatchDay.mockResolvedValue(matchDayResult)
  api.previewAuthoritativeNextRound.mockResolvedValue(roundPreview)
  api.simulateAuthoritativeNextRound.mockResolvedValue(roundResult)
  api.previewAuthoritativeNextTournament.mockResolvedValue(tournamentPreview)
  api.simulateAuthoritativeNextTournament.mockResolvedValue(tournamentResult)
  api.previewAuthoritativeNextWeek.mockResolvedValue(weekPreview)
  api.simulateAuthoritativeNextWeek.mockResolvedValue(weekResult)
  api.previewAuthoritativeNextSeason.mockResolvedValue(seasonPreview)
  api.simulateAuthoritativeNextSeason.mockResolvedValue(seasonResult)
  api.previewAuthoritativeFullSimulation.mockResolvedValue(fullSimulationPreview)
  api.simulateAuthoritativeFullSimulation.mockResolvedValue(fullSimulationReviewProgress)
  api.saveAuthoritativeSimulation.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    previous_viewer_branch_id: 'branch-a',
    viewer_branch_id: 'branch-a',
    saved_revision: {
      revision_id: 'revision-8',
      sequence: 8,
      parent_revision_id: 'revision-7',
      kind: 'manual_save',
      payload_schema_version: '1',
      content_hash_algorithm: 'sha256',
      content_hash: '2'.repeat(64),
      change_summary: {}
    },
    working_draft: {
      run_id: 'run-a',
      branch_id: 'branch-a',
      draft_id: 'draft-a',
      base_saved_revision_id: 'revision-8',
      saved_viewer_branch_id: 'branch-a',
      proposed_viewer_branch_id: 'branch-a',
      current_viewer_branch_id: 'branch-a',
      status: 'clean',
      change_count: 0,
      draft_version: 5,
      can_save: false
    },
    audit_event_id: 'audit-8'
  })
  api.previewDerivedAuthoritativeWeekTransition.mockResolvedValue(transitionPreview)
  api.confirmAuthoritativeWeekTransition.mockResolvedValue(transitionPreview)
  api.previewRankingSave.mockResolvedValue({
    run_id: 'run-a',
    branch_id: 'branch-a',
    ranking_fingerprint: 'e'.repeat(64),
    saved_head_revision_id: 'revision-7',
    draft_version: 12,
    has_unsaved_changes: true,
    can_save: true
  })
  api.saveRankingPreparation.mockResolvedValue({ ok: true })
  api.previewDerivedRankingTransitionAuthority.mockResolvedValue(rankingAuthorityPreview)
  api.confirmDerivedRankingTransitionAuthority.mockResolvedValue(rankingAuthorityPreview.authority)
  api.previewAuthoritativeSeasonTransitionConfiguration.mockResolvedValue({
    configuration: {
      schema_version: 'season_transition_configuration.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      base_revision_id: 'revision-7',
      completed_week: { season_index: 2, week: 61 },
      target_week: { season_index: 3, week: 1 },
      predecessor_official_fingerprint: '1'.repeat(64),
      predecessor_sporting_fingerprint: '2'.repeat(64),
      outgoing_ranking_policy_fingerprint: '3'.repeat(64),
      target_ranking_policy: { policy_id: 'incoming-ranking', best_n: 15 },
      outgoing_development_policy_fingerprint: '4'.repeat(64),
      target_development_policy: { policy_id: 'incoming-development' },
      reset_catalog: {
        schema_version: 'season_scoped_reset_catalog.v1',
        registry_version: 'season_scoped_reset_registry.v1',
        component_ids: []
      },
      provenance: 'test'
    },
    configuration_fingerprint: '6'.repeat(64),
    ranking_policy_inherited: true,
    development_policy_inherited: true,
    reset_component_ids: []
  })
  api.advanceAuthoritativeOrdinarySeason.mockResolvedValue({
    schema_version: 'ordinary_season_transition_result.v1',
    run_id: 'run-a',
    branch_id: 'branch-a',
    completed_week: { season_index: 2, week: 61 },
    target_week: { season_index: 3, week: 1 },
    saved_revision_id: 'revision-season-3',
    configuration_fingerprint: '6'.repeat(64),
    closing_ranking_fingerprint: 'a'.repeat(64),
    season_summary_fingerprint: 'b'.repeat(64),
    closure_marker_fingerprint: 'c'.repeat(64),
    player_sporting_fingerprint: 'd'.repeat(64),
    player_lifecycle_fingerprint: 'e'.repeat(64),
    official_ranking_fingerprint: 'f'.repeat(64),
    world_event_kind: 'season_transition_completed',
    draft_version: 5
  })
})

describe('AuthoritativeSimulationPanel', () => {
  it('reviews and commits an explicit Week Tournament Lock before schedule adoption', async () => {
    api.inspectWeekTournamentLock
      .mockResolvedValueOnce({
        run_id: 'run-a',
        branch_id: 'branch-a',
        week,
        expected_revision_id: 'revision-7',
        position_fingerprint: 'a'.repeat(64),
        event_ids: ['event-a', 'event-b'],
        event_evidence: [
          {
            event_id: 'event-a',
            entry_field_fingerprint: '1'.repeat(64),
            accepted_player_ids: ['P001']
          },
          {
            event_id: 'event-b',
            entry_field_fingerprint: '2'.repeat(64),
            accepted_player_ids: ['P001']
          }
        ],
        conflicts: [
          {
            player_id: 'P001',
            eligible_event_ids: ['event-a', 'event-b']
          }
        ],
        lock_status: 'required',
        authority: null,
        authority_fingerprint: null,
        selection_policy_id: 'explicit_admin_week_tournament_lock.v1',
        final_commitment_deadline_policy: 'intentionally_unresolved'
      })
      .mockResolvedValue({
        run_id: 'run-a',
        branch_id: 'branch-a',
        week,
        expected_revision_id: 'revision-7',
        position_fingerprint: 'f'.repeat(64),
        event_ids: ['event-a', 'event-b'],
        event_evidence: [],
        conflicts: [],
        lock_status: 'locked',
        authority: {
          schema_version: 'week_tournament_lock_authority.v1',
          run_id: 'run-a',
          branch_id: 'branch-a',
          week,
          resolved_by_command_id: 'lock-command',
          selection_policy_id: 'explicit_admin_week_tournament_lock.v1',
          operator_label: 'Commissioner',
          audit_reason: 'Resolve overlapping accepted fields',
          event_evidence: [],
          player_locks: [
            {
              player_id: 'P001',
              eligible_event_ids: ['event-a', 'event-b'],
              selected_event_id: 'event-a'
            }
          ]
        },
        authority_fingerprint: '3'.repeat(64),
        selection_policy_id: 'explicit_admin_week_tournament_lock.v1',
        final_commitment_deadline_policy: 'intentionally_unresolved'
      })

    renderPanel()

    expect(await screen.findByRole('heading', { name: 'Week Tournament Lock' }))
      .toBeInTheDocument()
    await userEvent.selectOptions(
      screen.getByLabelText('Week Tournament Lock event for P001'),
      'event-a'
    )
    await userEvent.type(
      screen.getByLabelText('Week Tournament Lock operator'),
      'Commissioner'
    )
    await userEvent.type(
      screen.getByLabelText('Week Tournament Lock audit reason'),
      'Resolve overlapping accepted fields'
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Review Week Tournament Lock' })
    )

    await waitFor(() =>
      expect(api.previewWeekTournamentLock).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          command_id: expect.any(String),
          expected_week: week,
          expected_position_fingerprint: 'a'.repeat(64),
          expected_revision_id: 'revision-7',
          operator_label: 'Commissioner',
          audit_reason: 'Resolve overlapping accepted fields',
          selections: [
            { player_id: 'P001', selected_event_id: 'event-a' }
          ]
        })
      )
    )

    expect(await screen.findByText('Reviewed fingerprint')).toBeInTheDocument()
    await userEvent.click(
      screen.getByRole('button', { name: 'Commit Week Tournament Lock' })
    )
    await waitFor(() =>
      expect(api.commitWeekTournamentLock).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          expected_authority_fingerprint: '3'.repeat(64)
        })
      )
    )
  })

  it('shows lifecycle-visible pre-Tour prospects read-only for the current branch', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      required: false,
      schedule: null
    })

    renderPanel()

    expect(
      await screen.findByRole('heading', {
        name: 'Historically visible pre-Tour prospects',
      })
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('list', {
        name: 'Canonical visible pre-Tour prospects',
      })
    ).toHaveTextContent('CZE Prospect 0001 · CZE · age 15')
    expect(api.getAdminVisibleProspects).toHaveBeenCalledWith(
      'run-a',
      'branch-a',
      { limit: 10, offset: 0 }
    )
  })


  it('reviews and adopts the exact dependency-safe topological schedule proposal', async () => {
    renderPanel()

    expect(await screen.findByText('Week Simulation Schedule')).toBeInTheDocument()
    expect(api.getAuthoritativeSimulationPosition).not.toHaveBeenCalled()
    expect(screen.getByText('Canonical Position and match execution stay locked until this immutable Match Day / global-slot schedule is adopted.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Build Match Day schedule proposal' }))

    expect(await screen.findByRole('list', { name: 'Proposed authoritative week schedule' })).toHaveTextContent('Day 1 · #1 · global slot 1 · event-a · main R1: g1')
    await userEvent.click(screen.getByRole('button', { name: 'Adopt reviewed Match Day schedule' }))

    await waitFor(() =>
      expect(api.adoptAuthoritativeWeekScheduleProposal).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          request_id: expect.any(String),
          expected_week: week,
          expected_schedule_fingerprint: 'c'.repeat(64),
          expected_position_fingerprint: 'd'.repeat(64)
        })
      )
    )
  })

  it('reviews and adopts an exact manually edited Match Day schedule', async () => {
    renderPanel()

    await userEvent.click(
      await screen.findByRole('button', {
        name: 'Build Match Day schedule proposal'
      })
    )

    const g2Day = await screen.findByLabelText('Match Day g2')
    await userEvent.clear(g2Day)
    await userEvent.type(g2Day, '2')

    const g3Day = screen.getByLabelText('Match Day g3')
    await userEvent.clear(g3Day)
    await userEvent.type(g3Day, '3')

    await userEvent.click(
      screen.getByRole('button', {
        name: 'Review edited Match Day schedule'
      })
    )

    await waitFor(() =>
      expect(api.previewAuthoritativeWeekSchedule).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        {
          schedule: editedSchedule
        }
      )
    )
    expect(
      await screen.findByText('Reviewed schedule fingerprint')
    ).toBeInTheDocument()
    expect(
      screen.getByRole('list', {
        name: 'Reviewed edited Match Day schedule'
      })
    ).toHaveTextContent(
      'Day 2 · #1 · global slot 2 · event-b · main R1: g2'
    )

    await userEvent.click(
      screen.getByRole('button', {
        name: 'Adopt reviewed edited Match Day schedule'
      })
    )

    await waitFor(() =>
      expect(api.adoptAuthoritativeWeekSchedule).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          request_id: expect.any(String),
          schedule: editedSchedule,
          expected_position_fingerprint: 'f'.repeat(64)
        })
      )
    )
  })

  it('simulates one explicitly reviewed eligible match against exact canonical position and Saved Revision head', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    renderPanel()

    const selector = await screen.findByLabelText('Eligible authoritative match group')
    await userEvent.selectOptions(selector, 'g2')
    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    await userEvent.click(screen.getByRole('button', { name: 'Simulate authoritative Next Match' }))

    await waitFor(() =>
      expect(api.simulateAuthoritativeNextMatch).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          command_id: expect.any(String),
          run_id: 'run-a',
          branch_id: 'branch-a',
          expected_week: week,
          expected_position_fingerprint: 'a'.repeat(64),
          expected_revision_id: 'revision-7',
          group_id: 'g2'
        })
      )
    )
  })

  it('previews hard-constrained Match Reconstruction candidates and commits only the selected one', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    renderPanel()

    await screen.findByText('Minimum Match Reconstruction')
    await waitFor(() =>
      expect(api.inspectAuthoritativeMatchReconstruction).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        'g1'
      )
    )

    await userEvent.clear(screen.getByLabelText('Reconstruction candidate count'))
    await userEvent.type(screen.getByLabelText('Reconstruction candidate count'), '2')
    await userEvent.type(screen.getByLabelText('Reconstruction winner player ID'), 'P001')
    await userEvent.click(screen.getByRole('button', { name: 'Generate matching scenarios' }))

    await waitFor(() =>
      expect(api.previewAuthoritativeMatchReconstruction).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        {
          expected_week: week,
          expected_position_fingerprint: 'a'.repeat(64),
          expected_revision_id: 'revision-7',
          group_id: 'g1',
          candidate_count: 2,
          constraints: { winner_player_id: 'P001' }
        }
      )
    )

    expect(await screen.findByRole('list', { name: 'Match Reconstruction candidates' }))
      .toHaveTextContent('Candidate 1: P001 · 3-1 · 11-7, 8-11, 11-9, 11-6')
    await userEvent.type(screen.getByLabelText('Reconstruction operator'), 'Commissioner')
    await userEvent.type(
      screen.getByLabelText('Reconstruction audit reason'),
      'Reviewed historical result'
    )
    await userEvent.click(screen.getByRole('button', { name: 'Select this reconstruction' }))

    await waitFor(() =>
      expect(api.commitAuthoritativeMatchReconstruction).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          command_id: expect.any(String),
          expected_week: week,
          expected_position_fingerprint: 'a'.repeat(64),
          expected_revision_id: 'revision-7',
          group_id: 'g1',
          candidate_count: 2,
          constraints: { winner_player_id: 'P001' },
          expected_preview_fingerprint: '6'.repeat(64),
          selected_candidate_fingerprint: '3'.repeat(64),
          operator_label: 'Commissioner',
          audit_reason: 'Reviewed historical result'
        })
      )
    )
  })

  it('reuses the frozen command id when a Next Match response is lost and the user retries', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.simulateAuthoritativeNextMatch
      .mockRejectedValueOnce(new Error('network response lost'))
      .mockResolvedValueOnce({
        ...position,
        eligible_match_ids: ['g2'],
        unresolved_group_ids: ['g2', 'g3'],
        position_fingerprint: 'f'.repeat(64)
      })
    renderPanel()

    await screen.findByLabelText('Eligible authoritative match group')
    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    const button = screen.getByRole('button', { name: 'Simulate authoritative Next Match' })
    await userEvent.click(button)

    expect(await screen.findByText('Authoritative Next Match failed: network response lost')).toBeInTheDocument()
    const firstCommandId = api.simulateAuthoritativeNextMatch.mock.calls[0][2].command_id

    await userEvent.click(button)
    await waitFor(() => expect(api.simulateAuthoritativeNextMatch).toHaveBeenCalledTimes(2))
    expect(api.simulateAuthoritativeNextMatch.mock.calls[1][2].command_id).toBe(firstCommandId)
  })

  it('simulates the whole current slot without smuggling a group id into the command', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    renderPanel()

    await screen.findByText('Execute current canonical position')
    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    await userEvent.click(screen.getByRole('button', { name: 'Simulate authoritative Next Slot' }))

    await waitFor(() => expect(api.simulateAuthoritativeNextSlot).toHaveBeenCalled())
    const payload = api.simulateAuthoritativeNextSlot.mock.calls[0][2]
    expect(payload).toMatchObject({
      run_id: 'run-a',
      branch_id: 'branch-a',
      expected_week: week,
      expected_position_fingerprint: 'a'.repeat(64),
      expected_revision_id: 'revision-7'
    })
    expect(payload).not.toHaveProperty('group_id')
  })

  it('reviews and safely retries the exact canonical Next Match Day command', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.simulateAuthoritativeNextMatchDay
      .mockRejectedValueOnce(new Error('network response lost'))
      .mockResolvedValueOnce(matchDayResult)
    renderPanel()

    await screen.findByText('Execute current canonical position')
    await userEvent.click(
      screen.getByRole('button', { name: 'Review authoritative Next Match Day' })
    )

    await waitFor(() =>
      expect(api.previewAuthoritativeNextMatchDay).toHaveBeenCalledWith(
        'run-a',
        'branch-a'
      )
    )
    expect(
      await screen.findByRole('heading', { name: 'Reviewed canonical Match Day 1' })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('list', { name: 'Reviewed authoritative Match Day' })
    ).toHaveTextContent('Global slot 1: g1')
    expect(
      screen.getByRole('list', { name: 'Reviewed authoritative Match Day' })
    ).toHaveTextContent('Global slot 2: g2')

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    const commit = screen.getByRole('button', {
      name: 'Simulate reviewed authoritative Match Day'
    })
    await userEvent.click(commit)

    expect(
      await screen.findByText(
        'Authoritative Next Match Day failed: network response lost'
      )
    ).toBeInTheDocument()
    const firstCommand =
      api.simulateAuthoritativeNextMatchDay.mock.calls[0][2]
    expect(firstCommand).toMatchObject({
      expected_week: week,
      expected_position_fingerprint: 'a'.repeat(64),
      expected_revision_id: 'revision-7'
    })
    expect(firstCommand).not.toHaveProperty('run_id')
    expect(firstCommand).not.toHaveProperty('branch_id')

    await userEvent.click(commit)
    await waitFor(() =>
      expect(api.simulateAuthoritativeNextMatchDay).toHaveBeenCalledTimes(2)
    )
    expect(
      api.simulateAuthoritativeNextMatchDay.mock.calls[1][2].command_id
    ).toBe(firstCommand.command_id)
  })

  it('reviews transit chronology and safely retries the exact canonical Next Round command', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.simulateAuthoritativeNextRound
      .mockRejectedValueOnce(new Error('network response lost'))
      .mockResolvedValueOnce(roundResult)
    renderPanel()

    await screen.findByText('Execute current canonical position')
    await userEvent.click(
      screen.getByRole('button', { name: 'Review authoritative Next Round' })
    )

    await waitFor(() =>
      expect(api.previewAuthoritativeNextRound).toHaveBeenCalledWith(
        'run-a',
        'branch-a'
      )
    )
    expect(
      await screen.findByRole('heading', { name: /Reviewed canonical Round/ })
    ).toHaveTextContent('event-a')
    expect(
      screen.getByRole('list', {
        name: 'Reviewed authoritative Round target matches'
      })
    ).toHaveTextContent('Target slot 1: g1')
    expect(
      screen.getByRole('list', {
        name: 'Reviewed authoritative Round target matches'
      })
    ).toHaveTextContent('Target slot 3: g3')
    expect(
      screen.getByRole('list', {
        name: 'Reviewed authoritative Round transit matches'
      })
    ).toHaveTextContent('Transit slot 2: g2')

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    const commit = screen.getByRole('button', {
      name: 'Simulate reviewed authoritative Next Round'
    })
    await userEvent.click(commit)

    expect(
      await screen.findByText(
        'Authoritative Next Round failed: network response lost'
      )
    ).toBeInTheDocument()
    const firstCommand = api.simulateAuthoritativeNextRound.mock.calls[0][2]
    expect(firstCommand).toMatchObject({
      expected_week: week,
      expected_position_fingerprint: 'a'.repeat(64),
      expected_revision_id: 'revision-7'
    })
    expect(firstCommand).not.toHaveProperty('run_id')
    expect(firstCommand).not.toHaveProperty('branch_id')

    await userEvent.click(commit)
    await waitFor(() =>
      expect(api.simulateAuthoritativeNextRound).toHaveBeenCalledTimes(2)
    )
    expect(
      api.simulateAuthoritativeNextRound.mock.calls[1][2].command_id
    ).toBe(firstCommand.command_id)
  })

  it('reviews tournament transit chronology and retries the same canonical command', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.simulateAuthoritativeNextTournament
      .mockRejectedValueOnce(new Error('network response lost'))
      .mockResolvedValueOnce(tournamentResult)
    renderPanel()

    await screen.findByText('Execute current canonical position')
    await userEvent.click(
      screen.getByRole('button', { name: 'Review authoritative Next Tournament' })
    )

    await waitFor(() =>
      expect(api.previewAuthoritativeNextTournament).toHaveBeenCalledWith(
        'run-a',
        'branch-a'
      )
    )
    expect(
      await screen.findByRole('heading', {
        name: 'Reviewed canonical Tournament · event-a'
      })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('list', {
        name: 'Reviewed authoritative Tournament target matches'
      })
    ).toHaveTextContent('Target slot 1: g1')
    expect(
      screen.getByRole('list', {
        name: 'Reviewed authoritative Tournament target matches'
      })
    ).toHaveTextContent('Target slot 3: g3')
    expect(
      screen.getByRole('list', {
        name: 'Reviewed authoritative Tournament transit matches'
      })
    ).toHaveTextContent('Transit slot 2: g2')

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    const commit = screen.getByRole('button', {
      name: 'Simulate reviewed authoritative Next Tournament'
    })
    await userEvent.click(commit)

    expect(
      await screen.findByText(
        'Authoritative Next Tournament failed: network response lost'
      )
    ).toBeInTheDocument()
    const firstCommand =
      api.simulateAuthoritativeNextTournament.mock.calls[0][2]
    expect(firstCommand).toMatchObject({
      expected_week: week,
      expected_position_fingerprint: 'a'.repeat(64),
      expected_revision_id: 'revision-7'
    })
    expect(firstCommand).not.toHaveProperty('run_id')
    expect(firstCommand).not.toHaveProperty('branch_id')

    await userEvent.click(commit)
    await waitFor(() =>
      expect(api.simulateAuthoritativeNextTournament).toHaveBeenCalledTimes(2)
    )
    expect(
      api.simulateAuthoritativeNextTournament.mock.calls[1][2].command_id
    ).toBe(firstCommand.command_id)
  })

  it('keeps one reviewed Next Week command across a blocked checkpoint retry', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.simulateAuthoritativeNextWeek
      .mockResolvedValueOnce(weekProgress)
      .mockResolvedValueOnce(weekResult)
    renderPanel()

    await screen.findByText('Execute current canonical position')
    await userEvent.type(
      screen.getByLabelText('Next Week operator'),
      'Commissioner'
    )
    await userEvent.type(
      screen.getByLabelText('Next Week audit reason'),
      'Advance reviewed week'
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Review authoritative Next Week' })
    )

    await waitFor(() =>
      expect(api.previewAuthoritativeNextWeek).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        {
          command_id: expect.any(String),
          operator_label: 'Commissioner',
          audit_reason: 'Advance reviewed week'
        }
      )
    )
    expect(
      await screen.findByRole('heading', { name: /Reviewed canonical Week/ })
    ).toHaveTextContent('W17')
    expect(screen.getByText(/Frozen remaining global slots: 1, 2, 3/)).toBeInTheDocument()

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    const commit = screen.getByRole('button', {
      name: 'Simulate reviewed authoritative Next Week'
    })
    await userEvent.click(commit)

    expect(
      await screen.findByText(/Next Week paused after 3 sporting slot/)
    ).toHaveTextContent('working_draft_dirty')
    const firstCommand = api.simulateAuthoritativeNextWeek.mock.calls[0][2]
    expect(firstCommand).toMatchObject({
      command_id: expect.any(String),
      operator_label: 'Commissioner',
      audit_reason: 'Advance reviewed week',
      expected_week: week,
      expected_position_fingerprint: 'a'.repeat(64),
      expected_revision_id: 'revision-7',
      expected_preview_fingerprint: '6'.repeat(64)
    })

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    const retry = screen.getByRole('button', {
      name: 'Retry reviewed authoritative Next Week'
    })
    await userEvent.click(retry)

    await waitFor(() =>
      expect(api.simulateAuthoritativeNextWeek).toHaveBeenCalledTimes(2)
    )
    expect(api.simulateAuthoritativeNextWeek.mock.calls[1][2].command_id).toBe(
      firstCommand.command_id
    )
  })

  it('keeps one reviewed Next Season parent across explicit boundary checkpoints', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.simulateAuthoritativeNextSeason
      .mockResolvedValueOnce(seasonSaveProgress)
      .mockResolvedValueOnce(seasonReviewProgress)
      .mockResolvedValueOnce(seasonResult)
    renderPanel()

    await screen.findByText('Execute current canonical position')
    await userEvent.type(
      screen.getByLabelText('Next Season operator'),
      'Commissioner'
    )
    await userEvent.type(
      screen.getByLabelText('Next Season audit reason'),
      'Advance reviewed season'
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Review authoritative Next Season' })
    )

    await waitFor(() =>
      expect(api.previewAuthoritativeNextSeason).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        {
          command_id: expect.any(String),
          operator_label: 'Commissioner',
          audit_reason: 'Advance reviewed season'
        }
      )
    )
    expect(
      await screen.findByRole('heading', { name: /Reviewed canonical Season/ })
    ).toHaveTextContent('S2 W17')
    expect(screen.getByText('calendar_proven_audited_child_only')).toBeInTheDocument()

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    const commit = screen.getByRole('button', {
      name: 'Simulate reviewed authoritative Next Season'
    })
    await userEvent.click(commit)

    expect(
      await screen.findByText(/Next Season paused at season_transition_save_required/)
    ).toHaveTextContent('45 completed week')
    expect(
      screen.getByRole('button', { name: 'Save authoritative simulation' })
    ).toBeInTheDocument()
    const firstCommand = api.simulateAuthoritativeNextSeason.mock.calls[0][2]
    expect(firstCommand).toMatchObject({
      command_id: expect.any(String),
      operator_label: 'Commissioner',
      audit_reason: 'Advance reviewed season',
      expected_start_week: week,
      expected_position_fingerprint: 'a'.repeat(64),
      expected_revision_id: 'revision-7',
      expected_preview_fingerprint: '4'.repeat(64)
    })

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    await userEvent.click(
      screen.getByRole('button', {
        name: 'Retry reviewed authoritative Next Season'
      })
    )
    expect(
      await screen.findByText(/Next Season paused at season_transition_review_required/)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Review and commit the existing canonical Season Transition/)
    ).toBeInTheDocument()

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    await userEvent.click(
      screen.getByRole('button', {
        name: 'Retry reviewed authoritative Next Season'
      })
    )
    await waitFor(() =>
      expect(api.simulateAuthoritativeNextSeason).toHaveBeenCalledTimes(3)
    )
    expect(api.simulateAuthoritativeNextSeason.mock.calls[1][2].command_id).toBe(
      firstCommand.command_id
    )
    expect(api.simulateAuthoritativeNextSeason.mock.calls[2][2].command_id).toBe(
      firstCommand.command_id
    )
  })

  it('keeps one reviewed Full Simulation parent across season checkpoints', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.simulateAuthoritativeFullSimulation
      .mockResolvedValueOnce(fullSimulationSaveProgress)
      .mockResolvedValueOnce(fullSimulationReviewProgress)
    renderPanel()

    await screen.findByText('Execute current canonical position')
    await userEvent.type(
      screen.getByLabelText('Full Simulation operator'),
      'Commissioner'
    )
    await userEvent.type(
      screen.getByLabelText('Full Simulation audit reason'),
      'Advance the reviewed complete Run'
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Review authoritative Full Simulation' })
    )

    await waitFor(() =>
      expect(api.previewAuthoritativeFullSimulation).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        {
          command_id: expect.any(String),
          operator_label: 'Commissioner',
          audit_reason: 'Advance the reviewed complete Run'
        }
      )
    )
    expect(
      await screen.findByRole('heading', {
        name: /Reviewed canonical Full Simulation/
      })
    ).toHaveTextContent('S2 W17')
    expect(screen.getByText('canonical_next_season')).toBeInTheDocument()
    expect(screen.getByText('canonical_final_run_closure')).toBeInTheDocument()

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    await userEvent.click(
      screen.getByRole('button', {
        name: 'Simulate reviewed authoritative Full Simulation'
      })
    )

    expect(
      await screen.findByText(
        /Full Simulation paused at season_transition_save_required/
      )
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Save authoritative simulation' })
    ).toBeInTheDocument()
    expect(
      screen.getByText('Full Simulation parent Command ID')
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Save authoritative simulation below, then retry this exact reviewed Full Simulation parent/)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Do not discard this Full Simulation review/)
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText('Full Simulation completed season boundaries')
    ).toHaveAttribute('max', String(fullSimulationPreview.remaining_seasons_including_current))
    const firstCommand = api.simulateAuthoritativeFullSimulation.mock.calls[0][2]
    expect(firstCommand).toMatchObject({
      command_id: expect.any(String),
      operator_label: 'Commissioner',
      audit_reason: 'Advance the reviewed complete Run',
      expected_start_week: week,
      expected_position_fingerprint: 'a'.repeat(64),
      expected_revision_id: 'revision-7',
      expected_preview_fingerprint: '2'.repeat(64)
    })

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    await userEvent.click(
      screen.getByRole('button', {
        name: 'Retry reviewed authoritative Full Simulation'
      })
    )
    expect(
      await screen.findByText(
        /Full Simulation paused at season_transition_review_required/
      )
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        /Review and commit the canonical Season Transition below/
      )
    ).toBeInTheDocument()

    await waitFor(() =>
      expect(api.simulateAuthoritativeFullSimulation).toHaveBeenCalledTimes(2)
    )
    expect(
      api.simulateAuthoritativeFullSimulation.mock.calls[1][2].command_id
    ).toBe(firstCommand.command_id)
  })

  it('restores a durable pending Full Simulation parent after page state loss', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getPendingAuthoritativeFullSimulations.mockResolvedValue({
      schema_version: 'authoritative_full_simulation_pending_collection.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      operations: [
        {
          command: {
            command_id: 'full-parent-reload',
            operator_label: 'Commissioner',
            audit_reason: 'Resume complete Run',
            expected_start_week: fullSimulationPreview.start_week,
            expected_position_fingerprint:
              fullSimulationPreview.expected_position_fingerprint,
            expected_revision_id: fullSimulationPreview.expected_revision_id,
            expected_preview_fingerprint:
              fullSimulationPreview.preview_fingerprint
          },
          review: fullSimulationPreview,
          completed_seasons: [2, 3, 4],
          completed_season_count: 3,
          final_completed_weeks: [],
          final_completed_week_count: 0
        }
      ],
      legacy_pending_count: 0
    })
    api.simulateAuthoritativeFullSimulation.mockResolvedValue(
      fullSimulationReviewProgress
    )

    renderPanel()

    expect(
      await screen.findByRole('list', {
        name: 'Resumable Full Simulation parents'
      })
    ).toHaveTextContent('full-parent-reload')
    expect(
      screen.getByRole('button', {
        name: 'Review authoritative Full Simulation'
      })
    ).toBeDisabled()
    expect(
      screen.getByRole('list', {
        name: 'Resumable Full Simulation parents'
      })
    ).toHaveTextContent('3 completed season(s)')

    await userEvent.click(
      screen.getByRole('button', { name: 'Resume this Full Simulation' })
    )
    expect(screen.getByLabelText('Full Simulation operator')).toHaveValue(
      'Commissioner'
    )
    expect(screen.getByLabelText('Full Simulation audit reason')).toHaveValue(
      'Resume complete Run'
    )
    expect(
      await screen.findByRole('heading', {
        name: /Reviewed canonical Full Simulation/
      })
    ).toBeInTheDocument()

    await userEvent.click(screen.getByLabelText('Confirm authoritative simulation'))
    await userEvent.click(
      screen.getByRole('button', {
        name: 'Simulate reviewed authoritative Full Simulation'
      })
    )

    await waitFor(() =>
      expect(api.simulateAuthoritativeFullSimulation).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          command_id: 'full-parent-reload',
          operator_label: 'Commissioner',
          audit_reason: 'Resume complete Run',
          expected_preview_fingerprint:
            fullSimulationPreview.preview_fingerprint
        })
      )
    )
  })

  it('reviews the current Entry slot with minimal explicit Admin verdicts', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_slot_kind: 'entry',
      current_slot_id: 'entry-slot-1',
      slot_ordinal: 1,
      unresolved_group_ids: [],
      eligible_match_ids: [],
      blocked_match_ids: ['g1', 'g2', 'g3'],
      current_slot_complete: false,
      position_fingerprint: 'a'.repeat(64)
    })
    renderPanel()

    expect(
      await screen.findByRole('heading', { name: 'Entry application validation' })
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('list', { name: 'Frozen Entry application decisions' })
    ).toHaveTextContent('event-a · P001 · MAIN')

    await userEvent.selectOptions(
      screen.getByLabelText('Validation outcome event-a/P001'),
      'valid'
    )
    await userEvent.selectOptions(
      screen.getByLabelText('Validation outcome event-b/P002'),
      'invalid'
    )
    await userEvent.type(
      screen.getByLabelText('Validation rejection reason event-b/P002'),
      'explicit eligibility review rejected'
    )
    await userEvent.type(
      screen.getByLabelText('Entry validation operator'),
      'Admin operator'
    )
    await userEvent.type(
      screen.getByLabelText('Entry validation audit reason'),
      'Reviewed frozen application evidence'
    )

    const commit = screen.getByRole('button', {
      name: 'Commit explicit application validation'
    })
    expect(commit).toBeEnabled()
    await userEvent.click(commit)

    await waitFor(() =>
      expect(api.reviewAuthoritativeEntryDecisionSlot).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        {
          command_id: expect.any(String),
          expected_week: week,
          expected_revision_id: 'revision-7',
          expected_position_fingerprint: 'a'.repeat(64),
          decision_slot_ordinal: 1,
          expected_entry_slot_fingerprint: '4'.repeat(64),
          operator_label: 'Admin operator',
          reason: 'Reviewed frozen application evidence',
          reviews: [
            {
              event_id: 'event-a',
              player_id: 'P001',
              outcome: 'valid',
              reasons: []
            },
            {
              event_id: 'event-b',
              player_id: 'P002',
              outcome: 'invalid',
              reasons: ['explicit eligibility review rejected']
            }
          ]
        }
      )
    )

    expect(api.simulateAuthoritativeNextMatch).not.toHaveBeenCalled()
    expect(api.simulateAuthoritativeNextSlot).not.toHaveBeenCalled()
  })

  it('saves only the exact reviewed authoritative simulation draft preview', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.previewAuthoritativeSimulationSave.mockResolvedValue({
      run_id: 'run-a',
      branch_id: 'branch-a',
      saved_head_revision_id: 'revision-7',
      draft_version: 9,
      has_unsaved_changes: true,
      can_save: true,
      simulation_fingerprint: '9'.repeat(64)
    })
    renderPanel()

    const save = await screen.findByRole('button', { name: 'Save authoritative simulation' })
    expect(save).toBeEnabled()
    await userEvent.click(save)

    await waitFor(() =>
      expect(api.saveAuthoritativeSimulation).toHaveBeenCalledWith('run-a', 'branch-a', {
        expected_draft_version: 9,
        expected_simulation_fingerprint: '9'.repeat(64)
      })
    )
    expect(await screen.findByText('Saved as revision revision-8.')).toBeInTheDocument()
  })

  it('derives, confirms and saves the missing Ranking Transition Authority from canonical state', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_slot_kind: null,
      current_slot_id: null,
      slot_ordinal: null,
      unresolved_group_ids: [],
      eligible_match_ids: [],
      blocked_match_ids: [],
      current_slot_complete: true,
      supported_tournament_complete: true,
      week_ready_for_transition: false,
      transition_blockers: ['ranking_transition_authority_missing'],
      terminal_sporting_fingerprint: 'f'.repeat(64),
      position_fingerprint: '2'.repeat(64)
    })
    renderPanel()

    await screen.findByText('Ranking Transition Authority')
    await userEvent.type(screen.getByLabelText('Operator label'), 'Admin operator')
    await userEvent.type(
      screen.getByLabelText('Authority reason'),
      'Review canonical ranking boundary'
    )
    await userEvent.click(
      screen.getByRole('button', { name: 'Review derived Ranking Transition Authority' })
    )

    await waitFor(() =>
      expect(api.previewDerivedRankingTransitionAuthority).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          command_id: expect.any(String),
          audit: {
            actor_label: 'Admin operator',
            reason: 'Review canonical ranking boundary'
          }
        })
      )
    )
    expect(await screen.findByText('season-3-policy')).toBeInTheDocument()
    expect(screen.getByText('6'.repeat(64))).toBeInTheDocument()

    await userEvent.click(
      screen.getByRole('button', { name: 'Confirm reviewed Ranking Transition Authority' })
    )
    await waitFor(() =>
      expect(api.confirmDerivedRankingTransitionAuthority).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          audit: {
            actor_label: 'Admin operator',
            reason: 'Review canonical ranking boundary'
          }
        }),
        rankingAuthorityPreview
      )
    )

    const save = await screen.findByRole('button', { name: 'Save Ranking Transition Authority' })
    expect(save).toBeEnabled()
    await userEvent.click(save)
    await waitFor(() =>
      expect(api.saveRankingPreparation).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          draft_version: 12,
          ranking_fingerprint: 'e'.repeat(64),
          can_save: true
        })
      )
    )
  })

  it('does not derive Ranking Transition Authority while another transition blocker remains', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_slot_kind: null,
      current_slot_id: null,
      slot_ordinal: null,
      unresolved_group_ids: [],
      eligible_match_ids: [],
      blocked_match_ids: [],
      current_slot_complete: true,
      supported_tournament_complete: true,
      week_ready_for_transition: false,
      transition_blockers: [
        'ranking_transition_authority_missing',
        'working_draft_dirty'
      ],
      terminal_sporting_fingerprint: 'f'.repeat(64),
      position_fingerprint: '3'.repeat(64)
    })
    renderPanel()

    expect(await screen.findByText(
      'Ranking Transition Authority is missing, but other canonical blockers must be resolved first.'
    )).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Review derived Ranking Transition Authority' })
    ).not.toBeInTheDocument()
    expect(api.previewDerivedRankingTransitionAuthority).not.toHaveBeenCalled()
  })

  it('shows read-only Season Transition preflight at Week 61 and hides ordinary Week Transition actions', async () => {
    const week61 = { season_index: 2, week: 61 }
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      week: week61,
      schedule: {
        ...proposal.schedule,
        week: week61
      },
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_week: week61,
      current_slot_kind: null,
      current_slot_id: null,
      slot_ordinal: null,
      unresolved_group_ids: [],
      eligible_match_ids: [],
      blocked_match_ids: [],
      current_slot_complete: true,
      supported_tournament_complete: true,
      week_ready_for_transition: false,
      transition_blockers: ['season_transition_required'],
      terminal_sporting_fingerprint: '3'.repeat(64),
      position_fingerprint: '4'.repeat(64)
    })
    renderPanel()

    expect(await screen.findByText('Canonical Season Transition preflight')).toBeInTheDocument()
    await waitFor(() =>
      expect(api.getAuthoritativeSeasonTransitionPreflight).toHaveBeenCalledWith(
        'run-a',
        'branch-a'
      )
    )
    expect(screen.getByText('Season index 3 · Week 1')).toBeInTheDocument()
    expect(
      screen.queryByRole('list', { name: 'Season Transition implementation gaps' })
    ).not.toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Review Season Transition' })).toBeInTheDocument()
    expect(screen.queryByText('Canonical Week Transition')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Review derived Week Transition' })
    ).not.toBeInTheDocument()
  })

  it('requires review before committing a ready ordinary Season Transition', async () => {
    const week61 = { season_index: 2, week: 61 }
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      week: week61,
      schedule: { ...proposal.schedule, week: week61 },
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_week: week61,
      current_slot_kind: null,
      current_slot_id: null,
      slot_ordinal: null,
      unresolved_group_ids: [],
      eligible_match_ids: [],
      blocked_match_ids: [],
      current_slot_complete: true,
      supported_tournament_complete: true,
      week_ready_for_transition: true,
      transition_blockers: ['season_transition_required'],
      terminal_sporting_fingerprint: '3'.repeat(64),
      position_fingerprint: '4'.repeat(64)
    })
    api.getAuthoritativeSeasonTransitionPreflight.mockResolvedValue({
      schema_version: 'authoritative_season_transition_preflight.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      completed_week: week61,
      target_week: { season_index: 3, week: 1 },
      final_season: false,
      saved_revision_id: 'revision-7',
      draft_version: 4,
      default_configuration_fingerprint: '6'.repeat(64),
      default_closing_ranking_fingerprint: 'a'.repeat(64),
      default_sporting_fingerprint: '7'.repeat(64),
      default_lifecycle_fingerprint: '8'.repeat(64),
      default_ranking_fingerprint: '9'.repeat(64),
      position_fingerprint: '4'.repeat(64),
      state_blockers: [],
      implementation_gaps: [],
      ready_for_execution: true,
      preflight_fingerprint: '5'.repeat(64)
    })

    renderPanel()

    const review = await screen.findByRole('button', { name: 'Review Season Transition' })
    expect(screen.queryByRole('button', { name: 'Advance to next season' })).not.toBeInTheDocument()
    await userEvent.click(review)
    await userEvent.click(await screen.findByRole('button', { name: 'Advance to next season' }))

    await waitFor(() =>
      expect(api.previewAuthoritativeSeasonTransitionConfiguration).toHaveBeenCalledWith(
        'run-a',
        'branch-a'
      )
    )
    await waitFor(() =>
      expect(api.advanceAuthoritativeOrdinarySeason).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          expected_preflight_fingerprint: '5'.repeat(64),
          expected_saved_revision_id: 'revision-7',
          expected_draft_version: 4
        })
      )
    )
    expect(await screen.findByText('revision-season-3')).toBeInTheDocument()
    expect(screen.getByText('f'.repeat(64))).toBeInTheDocument()
  })

  it('requires explicit confirmation before finalizing 2049/50', async () => {
    const finalWeek = { season_index: 49, week: 61 }
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      week: finalWeek,
      schedule: { ...proposal.schedule, week: finalWeek },
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_week: finalWeek,
      current_slot_kind: null,
      current_slot_id: null,
      slot_ordinal: null,
      unresolved_group_ids: [],
      eligible_match_ids: [],
      blocked_match_ids: [],
      current_slot_complete: true,
      supported_tournament_complete: true,
      week_ready_for_transition: true,
      transition_blockers: ['season_transition_required'],
      terminal_sporting_fingerprint: '3'.repeat(64),
      position_fingerprint: '4'.repeat(64)
    })
    api.getAuthoritativeSeasonTransitionPreflight.mockResolvedValue({
      schema_version: 'authoritative_season_transition_preflight.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      completed_week: finalWeek,
      target_week: null,
      final_season: true,
      saved_revision_id: 'revision-7',
      draft_version: 4,
      default_configuration_fingerprint: null,
      default_closing_ranking_fingerprint: null,
      default_sporting_fingerprint: null,
      default_lifecycle_fingerprint: null,
      default_ranking_fingerprint: null,
      position_fingerprint: '4'.repeat(64),
      state_blockers: [],
      implementation_gaps: [],
      ready_for_execution: true,
      preflight_fingerprint: '5'.repeat(64)
    })
    api.finalizeAuthoritativeFinalSeason.mockResolvedValue({
      schema_version: 'final_season_transition_result.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      completed_week: { season_index: 49, week: 61 },
      saved_revision_id: 'revision-final',
      closing_ranking_fingerprint: '6'.repeat(64),
      season_summary_fingerprint: '7'.repeat(64),
      closure_marker_fingerprint: '8'.repeat(64),
      draft_version: 5,
      run_status: 'completed'
    })

    renderPanel()

    const review = await screen.findByRole('button', { name: 'Review final Run closure' })
    expect(screen.queryByRole('button', { name: 'Finalize 2049/50' })).not.toBeInTheDocument()
    await userEvent.click(review)
    const finalize = await screen.findByRole('button', { name: 'Finalize 2049/50' })
    await userEvent.click(finalize)

    await waitFor(() => expect(api.finalizeAuthoritativeFinalSeason).toHaveBeenCalledTimes(1))
    expect(api.finalizeAuthoritativeFinalSeason).toHaveBeenCalledWith(
      'run-a',
      'branch-a',
      expect.objectContaining({
        expected_preflight_fingerprint: '5'.repeat(64),
        expected_saved_revision_id: 'revision-7',
        expected_draft_version: 4
      })
    )
    expect(await screen.findByText('completed')).toBeInTheDocument()
    expect(screen.getByText('revision-final')).toBeInTheDocument()
  })

  it('reviews, confirms and saves one server-derived canonical Week Transition', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_slot_kind: null,
      current_slot_id: null,
      slot_ordinal: null,
      unresolved_group_ids: [],
      eligible_match_ids: [],
      blocked_match_ids: [],
      current_slot_complete: true,
      supported_tournament_complete: true,
      week_ready_for_transition: true,
      transition_blockers: [],
      terminal_sporting_fingerprint: 'f'.repeat(64),
      position_fingerprint: '1'.repeat(64)
    })
    renderPanel()

    const reviewButton = await screen.findByRole('button', { name: 'Review derived Week Transition' })
    await userEvent.click(reviewButton)

    await waitFor(() =>
      expect(api.previewDerivedAuthoritativeWeekTransition).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.any(String)
      )
    )
    expect(await screen.findByText('7'.repeat(64))).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Confirm reviewed Week Transition' }))
    await waitFor(() =>
      expect(api.confirmAuthoritativeWeekTransition).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        transitionPreview
      )
    )

    const save = await screen.findByRole('button', { name: 'Save transitioned week' })
    expect(save).toBeEnabled()
    await userEvent.click(save)
    await waitFor(() =>
      expect(api.saveRankingPreparation).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        expect.objectContaining({
          draft_version: 12,
          ranking_fingerprint: 'e'.repeat(64),
          can_save: true
        })
      )
    )
  })

  it('keeps Week Transition unavailable while canonical position reports blockers', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    renderPanel()

    expect(await screen.findByText('Week Transition is not ready. Resolve the canonical blockers shown above before advancing world time.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Review derived Week Transition' })).not.toBeInTheDocument()
    expect(api.previewDerivedAuthoritativeWeekTransition).not.toHaveBeenCalled()
  })

  it('does not query or mutate canonical simulation when the target Branch is blocked', async () => {
    renderPanel({ blockedReason: 'Branch is read-only.' })

    expect(screen.getByText('Canonical simulation blocked: Branch is read-only.')).toBeInTheDocument()
    await Promise.resolve()
    expect(api.getAuthoritativeSimulationPosition).not.toHaveBeenCalled()
    expect(api.inspectAuthoritativeWeekSchedule).not.toHaveBeenCalled()
    expect(api.previewAuthoritativeSimulationSave).not.toHaveBeenCalled()
    expect(api.simulateAuthoritativeNextMatch).not.toHaveBeenCalled()
  })
})

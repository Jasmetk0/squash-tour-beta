import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ComponentProps } from 'react'

import { AuthoritativeSimulationPanel } from './AuthoritativeSimulationPanel'

const api = vi.hoisted(() => ({
  getAuthoritativeSimulationPosition: vi.fn(),
  getAuthoritativeSeasonTransitionPreflight: vi.fn(),
  previewAuthoritativeSeasonTransitionConfiguration: vi.fn(),
  advanceAuthoritativeOrdinarySeason: vi.fn(),
  finalizeAuthoritativeFinalSeason: vi.fn(),
  getProspectBridgeInspection: vi.fn(),
  inspectAuthoritativeWeekSchedule: vi.fn(),
  previewAuthoritativeSimulationSave: vi.fn(),
  proposeAuthoritativeWeekSchedule: vi.fn(),
  adoptAuthoritativeWeekScheduleProposal: vi.fn(),
  simulateAuthoritativeNextMatch: vi.fn(),
  simulateAuthoritativeNextSlot: vi.fn(),
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
    schema_version: 'week_simulation_schedule.v1' as const,
    run_id: 'run-a',
    branch_id: 'branch-a',
    week,
    slots: [
      { ordinal: 1, group_ids: ['g1', 'g2'] },
      { ordinal: 2, group_ids: ['g3'] }
    ]
  },
  schedule_fingerprint: 'c'.repeat(64),
  position_fingerprint: 'd'.repeat(64),
  provenance: 'earliest_dependency_safe_topological_proposal_v1; not Match Day timing or Final Commitment authority',
  persisted: false as const
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
    implementation_gaps: [
      'season_prospect_creation_bridge_not_implemented'
    ],
    ready_for_execution: false,
    preflight_fingerprint: '5'.repeat(64)
  })
  api.getProspectBridgeInspection.mockResolvedValue({
    schema_version: 'prospect_bridge_inspection.v1',
    run_id: 'run-a',
    branch_id: 'branch-a',
    completed_week: week,
    target_week: { season_index: 2, week: 18 },
    season_start_year: 2002,
    calendar_year: 2003,
    year_week: 1,
    run_scoped_source: true,
    bridge_supported: false,
    blocking_code: 'prospect_bridge_missing',
    unresolved_contracts: ['canonical_sporting_profile'],
    prospects: [{
      prospect_id: 'prospect-1',
      display_name: 'CZE Prospect 0001',
      country_code: 'CZE',
      age: 15,
      status: 'prospect',
      source_type: 'weekly_15yo_cohort',
      cohort_policy_version: 'weekly_15yo_cohort_v1',
      profile_version: 'prospect_profile_v1',
      profile_placeholder: true,
      development_placeholder: true,
      potential_placeholder: true,
      trait_placeholder: true
    }],
    inspection_fingerprint: '5'.repeat(64)
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
  api.adoptAuthoritativeWeekScheduleProposal.mockResolvedValue({
    ...scheduleInspection,
    schedule: proposal.schedule,
    schedule_fingerprint: proposal.schedule_fingerprint,
    adoption: 'adopted_topological_proposal'
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
  it('reviews and adopts the exact dependency-safe topological schedule proposal', async () => {
    renderPanel()

    expect(await screen.findByText('Week Simulation Schedule')).toBeInTheDocument()
    expect(api.getAuthoritativeSimulationPosition).not.toHaveBeenCalled()
    expect(screen.getByText('Canonical Position and match execution stay locked until this required immutable Week Schedule is adopted.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Build topological schedule proposal' }))

    expect(await screen.findByRole('list', { name: 'Proposed authoritative week schedule' })).toHaveTextContent('Slot 1: g1, g2')
    await userEvent.click(screen.getByRole('button', { name: 'Adopt reviewed topological schedule' }))

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

  it('shows exact read-only Prospect Bridge blockers without offering activation', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_slot_id: null,
      slot_ordinal: null,
      unresolved_group_ids: [],
      eligible_match_ids: [],
      blocked_match_ids: [],
      current_slot_complete: true,
      supported_tournament_complete: true,
      week_ready_for_transition: false,
      transition_blockers: ['prospect_bridge_missing'],
      terminal_sporting_fingerprint: 'f'.repeat(64),
      position_fingerprint: '4'.repeat(64)
    })
    renderPanel()

    expect(api.getProspectBridgeInspection).not.toHaveBeenCalled()
    expect(screen.getByText('CZE Prospect 0001', { exact: false })).toHaveTextContent(
      'placeholders attributes, development, potential, traits'
    )
    expect(
      screen.getByText('Unresolved contracts: canonical_sporting_profile')
    ).toBeInTheDocument()
    expect(screen.getByText('5'.repeat(64))).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /prospect/i })).not.toBeInTheDocument()
  })

  it('does not derive Ranking Transition Authority while another transition blocker remains', async () => {
    api.inspectAuthoritativeWeekSchedule.mockResolvedValue({
      ...scheduleInspection,
      schedule: proposal.schedule,
      schedule_fingerprint: proposal.schedule_fingerprint
    })
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
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
        'prospect_bridge_missing'
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
      screen.getByRole('list', { name: 'Season Transition implementation gaps' })
    ).toHaveTextContent('season_prospect_creation_bridge_not_implemented')
    expect(await screen.findByText('Prospect Bridge inspection')).toBeInTheDocument()
    await waitFor(() =>
      expect(api.getProspectBridgeInspection).toHaveBeenCalledWith('run-a', 'branch-a')
    )
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
    expect(api.getProspectBridgeInspection).not.toHaveBeenCalled()
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
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...position,
      current_week: { season_index: 49, week: 61 },
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
      completed_week: { season_index: 49, week: 61 },
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

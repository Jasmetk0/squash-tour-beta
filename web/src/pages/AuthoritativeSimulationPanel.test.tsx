import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ComponentProps } from 'react'

import { AuthoritativeSimulationPanel } from './AuthoritativeSimulationPanel'

const api = vi.hoisted(() => ({
  getAuthoritativeSimulationPosition: vi.fn(),
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
  saveRankingPreparation: vi.fn()
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
    expect(await screen.findByText('event-a', { exact: false })).toBeInTheDocument()

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

import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunTournamentEntryReviewPanel } from './RunTournamentEntryReviewPanel'
import { buildReviewedEntryValidation, decisionKey, verifiedFrozenEntrySlot } from '../api/runTournamentEntryReview'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunContainer: vi.fn(),
  listRunBranches: vi.fn(),
  getBranchWorkingDraft: vi.fn(),
  getAuthoritativeSimulationPosition: vi.fn(),
  inspectAuthoritativeEntryDecisionSlot: vi.fn(),
  reviewAuthoritativeEntryDecisionSlot: vi.fn()
}))
vi.mock('../api/client', () => api)
const hash = (symbol: string) => symbol.repeat(64)
const position = {
  run_id: 'run-one', branch_id: 'branch-one',
  current_week: { season_index: 0, week: 1 },
  current_slot_kind: 'entry' as const,
  current_slot_id: 'entry-slot-1', slot_ordinal: 1,
  unresolved_group_ids: [], eligible_match_ids: [], blocked_match_ids: [],
  current_slot_complete: false, supported_tournament_complete: false,
  week_ready_for_transition: false, transition_blockers: [],
  terminal_sporting_fingerprint: null, position_fingerprint: hash('a')
}
const decisions = [
  { event_id: 'event-one', player_id: 'player-one', target: 'MAIN' as const,
    source_decision_fingerprint: hash('b') },
  { event_id: 'event-two', player_id: 'player-two', target: 'QUALIFICATION' as const,
    source_decision_fingerprint: hash('c') }
]
const inspection = {
  run_id: 'run-one', branch_id: 'branch-one',
  week: { season_index: 0, week: 1 }, decision_slot_ordinal: 1,
  slot_fingerprint: hash('d'),
  authority: {
    schema_version: 'run_entry_decision_slot_authority.v1' as const,
    run_id: 'run-one', branch_id: 'branch-one',
    week: { season_index: 0, week: 1 }, decision_slot_ordinal: 1,
    source_entry_batch_fingerprint: hash('e'),
    source_application_decisions_fingerprint: hash('f'),
    source_active_players_fingerprint: hash('0'),
    decisions
  },
  identity_tokens: { 'player-one': hash('1'), 'player-two': hash('2') },
  validation_resolved: false, validation_fingerprint: null
}
beforeEach(() => {
  vi.clearAllMocks()
  api.getRunContainer.mockResolvedValue({
    run_id: 'run-one', storage_kind: 'custom_local', read_only: false,
    status: 'working'
  })
  api.listRunBranches.mockResolvedValue({run_branches:[{
    run_id:'run-one',branch_id:'branch-one',status:'active',read_only:false,
    saved_head_revision_id:'rev-a'
  }]})
  api.getBranchWorkingDraft.mockResolvedValue({
    run_id:'run-one',branch_id:'branch-one',base_saved_revision_id:'rev-a',
    status:'clean',draft_version:0
  })
  api.getAuthoritativeSimulationPosition.mockResolvedValue(position)
  api.inspectAuthoritativeEntryDecisionSlot.mockResolvedValue(inspection)
  api.reviewAuthoritativeEntryDecisionSlot.mockResolvedValue({
    run_id:'run-one', branch_id:'branch-one', week:position.current_week,
    decision_slot_ordinal:1, entry_slot_fingerprint:hash('d'),
    validation_fingerprint:hash('3'), validation_mode:'explicit_admin_review.v1',
    validation_policy_id:'manual-test-policy', validation_policy_fingerprint:hash('4'),
    valid_submission_count:1, submission_batch_fingerprint:hash('5'),
    first_tour_entry_trigger_fingerprints:[]
  })
})
function show(eventId='event-one') {
  return renderWithRoute(<RunTournamentEntryReviewPanel runId="run-one" branchId="branch-one" eventId={eventId}/>, '/admin/runs/run-one/calendar/event-one')
}
describe('Actual Run-owned frozen Entry decisions', () => {
  it('never assumes applications are valid and only commits after review of every simultaneous event', async () => {
    show()
    expect(await screen.findByText(/2 frozen decisions across 2 simultaneous event/)).toBeInTheDocument()
    expect(api.reviewAuthoritativeEntryDecisionSlot).not.toHaveBeenCalled()
    const submit = screen.getByRole('button', { name: 'Review entire application batch' })
    expect(submit).toBeDisabled()
    const outcome1 = screen.getByRole('combobox', { name: `Entry outcome ${decisionKey('event-one', 'player-one')}` })
    const outcome2 = screen.getByRole('combobox', { name: `Entry outcome ${decisionKey('event-two', 'player-two')}` })
    await userEvent.selectOptions(outcome1,'valid')
    expect(submit).toBeDisabled()
    await userEvent.selectOptions(outcome2,'invalid')
    await userEvent.type(screen.getByRole('textbox',{name:`Entry rejection ${decisionKey('event-two','player-two')}`}), 'Missed deadline — reviewed operator evidence')
    await userEvent.type(screen.getByRole('textbox',{name:'Entry review operator'}), 'Tournament Admin')
    await userEvent.type(screen.getByRole('textbox',{name:'Entry review audit reason'}), 'Manual review of shared frozen slot')
    await userEvent.click(submit)
    expect(await screen.findByText(/Approve 1 valid and 1 invalid decisions/)).toBeInTheDocument()
    expect(api.reviewAuthoritativeEntryDecisionSlot).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Confirm reviewed application batch'}))
    await userEvent.click(screen.getByRole('button',{name:'Commit reviewed applications'}))
    await waitFor(()=>expect(api.reviewAuthoritativeEntryDecisionSlot).toHaveBeenCalledWith(
      'run-one','branch-one',expect.objectContaining({
        expected_revision_id:'rev-a', expected_position_fingerprint:hash('a'),
        expected_entry_slot_fingerprint:hash('d'),decision_slot_ordinal:1,
        reviews:[
          {event_id:'event-one',player_id:'player-one',outcome:'valid',reasons:[]},
          {event_id:'event-two',player_id:'player-two',outcome:'invalid',
            reasons:['Missed deadline — reviewed operator evidence']}
        ]
      })
    ))
    expect(await screen.findByText(/Persisted 1 explicitly valid tournament submissions/)).toBeInTheDocument()
  })

  it('refuses when selected event has no source decisions', async () => {
    show('foreign-event')
    expect(await screen.findByText(/has no decisions for this event/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Review entire application batch'})).not.toBeInTheDocument()
    expect(api.reviewAuthoritativeEntryDecisionSlot).not.toHaveBeenCalled()
  })

  it('refuses an unsaved or protected Branch before reading sporting position', async () => {
    api.getBranchWorkingDraft.mockResolvedValueOnce({
      run_id:'run-one',branch_id:'branch-one',base_saved_revision_id:'rev-a',
      status:'dirty',draft_version:1
    })
    show()
    expect(await screen.findByText(/clean Working Draft and verified Saved Revision/)).toBeInTheDocument()
    expect(api.getAuthoritativeSimulationPosition).not.toHaveBeenCalled()
  })

  it('prevents review from wrong Run, stale slot or duplicated decision evidence', () => {
    expect(verifiedFrozenEntrySlot(position,inspection,'run-one','branch-one','event-one')).toBe(true)
    expect(verifiedFrozenEntrySlot(position,inspection,'run-one','different','event-one')).toBe(false)
    expect(verifiedFrozenEntrySlot(position,{...inspection,slot_fingerprint:'bad'},'run-one','branch-one','event-one')).toBe(false)
    expect(verifiedFrozenEntrySlot(position,{
      ...inspection,authority:{...inspection.authority,decisions:[decisions[0],decisions[0]]}
    },'run-one','branch-one','event-one')).toBe(false)
    const outcomes = {
      [decisionKey('event-one','player-one')]:{outcome:'valid' as const,reason:''},
      [decisionKey('event-two','player-two')]:{outcome:'' as const,reason:''}
    }
    expect(()=>buildReviewedEntryValidation(position,inspection,'run-one','branch-one',
      'event-one','rev-a',outcomes,'Operator','Audit','cmd-one')).toThrow(/Every frozen decision/)
  })

  it('blocks further review of an already resolved immutable slot', async () => {
    api.inspectAuthoritativeEntryDecisionSlot.mockResolvedValueOnce({
      ...inspection,validation_resolved:true,validation_fingerprint:hash('f')
    })
    show()
    expect(await screen.findByText(/already resolved/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Commit reviewed applications'})).not.toBeInTheDocument()
  })
})

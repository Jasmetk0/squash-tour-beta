import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunCurrentEntryFreezePanel } from './RunCurrentEntryFreezePanel'
import { verifiedCurrentEntryApply, verifiedCurrentEntryPreview } from '../api/runCurrentEntryFreeze'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunContainer: vi.fn(),
  listRunBranches: vi.fn(),
  getBranchWorkingDraft: vi.fn(),
  getAuthoritativeSimulationPosition: vi.fn(),
  previewRunCurrentEntryDecisions: vi.fn(),
  applyRunCurrentEntryDecisions: vi.fn()
}))
vi.mock('../api/client', () => api)
const sha = (letter: string) => letter.repeat(64)
const position = {
  run_id: 'run-one', branch_id: 'branch-one',
  current_week: { season_index: 0, week: 1 },
  current_slot_kind: 'entry' as const,
  current_slot_id: 'entry-one', slot_ordinal: 1,
  unresolved_group_ids: [], eligible_match_ids: [], blocked_match_ids: [],
  current_slot_complete: false, supported_tournament_complete: false,
  week_ready_for_transition: false, transition_blockers: [],
  terminal_sporting_fingerprint: null, position_fingerprint: sha('a')
}
const preview = {
  schema_version: 'pre_alpha_fax_current_entry_decision_preview.v1' as const,
  run_id: 'run-one', branch_id: 'branch-one',
  current_week: { season_index: 0, week: 1 },
  decision_slot_ordinal: 1, event_ids: ['event-a', 'event-b'],
  seed: 12345, expected_revision_id: 'rev-1',
  expected_position_fingerprint: sha('a'), entry_batch_fingerprint: sha('b'),
  application_decisions_fingerprint: sha('c'), slot_fingerprint: sha('d'),
  decision_count: 15, persisted: false, preview_fingerprint: sha('e')
}
const applied = {
  schema_version: 'pre_alpha_fax_current_entry_decision_apply.v1' as const,
  run_id:'run-one', branch_id:'branch-one',
  current_week:{season_index:0,week:1},
  decision_slot_ordinal:1,event_ids:['event-a','event-b'],
  decision_count:15,slot_fingerprint:sha('d'),
  adoption:'committed' as const,validation_required:true as const,
  validation_policy_status:'automatic_policy_unresolved' as const,
  application_fingerprint:sha('f')
}

beforeEach(() => {
  vi.clearAllMocks()
  api.getRunContainer.mockResolvedValue({
    run_id:'run-one',storage_kind:'custom_local',read_only:false,status:'working'
  })
  api.listRunBranches.mockResolvedValue({run_branches:[{
    run_id:'run-one',branch_id:'branch-one',status:'active',read_only:false,
    saved_head_revision_id:'rev-1'
  }]})
  api.getBranchWorkingDraft.mockResolvedValue({
    run_id:'run-one',branch_id:'branch-one',
    status:'clean',base_saved_revision_id:'rev-1',draft_version:0
  })
  api.getAuthoritativeSimulationPosition.mockResolvedValue(position)
  api.previewRunCurrentEntryDecisions.mockResolvedValue(preview)
  api.applyRunCurrentEntryDecisions.mockResolvedValue(applied)
})
function show(eventId='event-a') {
  return renderWithRoute(
    <RunCurrentEntryFreezePanel runId="run-one" branchId="branch-one" eventId={eventId} />,
    '/admin/runs/run-one/calendar/event-a'
  )
}
describe('Production Run-owned Entry AI freeze', () => {
  it('reviews shared real events and requires distinct confirmation before freezing', async () => {
    show()
    const button=await screen.findByRole('button',{name:'Preview real Entry decisions'})
    await waitFor(()=>expect(button).toBeEnabled())
    await userEvent.click(button)
    expect(await screen.findByText(/15 generated player decisions, 2 World Tour event/)).toBeInTheDocument()
    expect(screen.getByText(/event-a, event-b/)).toBeInTheDocument()
    expect(api.applyRunCurrentEntryDecisions).not.toHaveBeenCalled()
    const apply=screen.getByRole('button',{name:'Confirm and freeze Entry decisions'})
    expect(apply).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve frozen Entry generation'}))
    await userEvent.click(apply)
    await waitFor(()=>expect(api.applyRunCurrentEntryDecisions).toHaveBeenCalledWith(
      'run-one','branch-one',preview,expect.stringMatching(/^admin-entry-freeze-/)
    ))
    expect(await screen.findByText(/Frozen 15 real Entry decisions/)).toBeInTheDocument()
  })

  it('rejects generated event list that excludes the requested tournament', async () => {
    show('another-event')
    await userEvent.click(await screen.findByRole('button',{name:'Preview real Entry decisions'}))
    expect(await screen.findByText(/does not match this Run, Branch, current Week/)).toBeInTheDocument()
    expect(api.applyRunCurrentEntryDecisions).not.toHaveBeenCalled()
  })

  it('refuses unsaved Working Draft before any Entry generator call', async () => {
    api.getBranchWorkingDraft.mockResolvedValueOnce({
      run_id:'run-one',branch_id:'branch-one',base_saved_revision_id:'rev-1',
      status:'dirty',draft_version:1
    })
    show()
    expect(await screen.findByText(/clean saved Working Draft/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Preview real Entry decisions'})).toBeDisabled()
    expect(api.previewRunCurrentEntryDecisions).not.toHaveBeenCalled()
  })

  it('rejects stale Position, wrong Saved Revision or already persisted slot', () => {
    expect(verifiedCurrentEntryPreview(preview,position,'run-one','branch-one','event-b','rev-1')).toBe(true)
    expect(verifiedCurrentEntryPreview(preview,position,'run-one','branch-one','event-b','rev-other')).toBe(false)
    expect(verifiedCurrentEntryPreview({...preview,persisted:true},position,'run-one','branch-one','event-b','rev-1')).toBe(true)
    expect(verifiedCurrentEntryPreview({...preview,expected_position_fingerprint:sha('0')},position,'run-one','branch-one','event-b','rev-1')).toBe(false)
    expect(verifiedCurrentEntryPreview({...preview,event_ids:['event-b','event-a']},position,'run-one','branch-one','event-b','rev-1')).toBe(false)
    expect(verifiedCurrentEntryApply(applied,preview)).toBe(true)
    expect(verifiedCurrentEntryApply({...applied,slot_fingerprint:sha('0')},preview)).toBe(false)
  })

  it('does not freeze empty proposals or existing frozen slots', async () => {
    api.previewRunCurrentEntryDecisions.mockResolvedValueOnce({...preview,decision_count:0})
    show()
    await userEvent.click(await screen.findByRole('button',{name:'Preview real Entry decisions'}))
    expect(await screen.findByText(/proposed no applications/)).toBeInTheDocument()
    expect(api.applyRunCurrentEntryDecisions).not.toHaveBeenCalled()
  })
})

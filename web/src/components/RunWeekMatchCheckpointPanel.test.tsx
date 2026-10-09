import {screen,waitFor} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {RunWeekMatchCheckpointPanel} from './RunWeekMatchCheckpointPanel'
import {
  validFirstWeekScheduleProposal,validPersistedWeekSchedule,validCheckpointPreview,
  validSavedCheckpoint,verifiedTournamentMatchRows
} from '../api/runWeekMatchCheckpoint'
import {renderWithRoute} from '../test/testUtils'

const api=vi.hoisted(()=>({
  ApiError:class ApiError extends Error{constructor(message:string,public status=409){super(message)}},
  getRunContainer:vi.fn(),listRunBranches:vi.fn(),getBranchWorkingDraft:vi.fn(),
  inspectAuthoritativeWeekSchedulePreflight:vi.fn(),inspectAuthoritativeWeekSchedule:vi.fn(),
  listAuthoritativeMatchReplays:vi.fn(),previewAuthoritativeSimulationSave:vi.fn(),
  proposeAuthoritativeWeekSchedule:vi.fn(),adoptAuthoritativeWeekScheduleProposal:vi.fn(),
  saveAuthoritativeSimulation:vi.fn()
}))
vi.mock('../api/client',()=>api)
const fp=(s:string)=>s.repeat(64)
const week={season_index:0,week:1}
const schedule={
  schema_version:'week_simulation_schedule.v2' as const,
  run_id:'run-one',branch_id:'branch-one',week,
  slots:[
    {ordinal:1,group_ids:['M1'],event_id:'E1',draw_phase:'main' as const,
      round_number:1,match_day_ordinal:1,match_order:1},
    {ordinal:2,group_ids:['M2'],event_id:'E2',draw_phase:'main' as const,
      round_number:1,match_day_ordinal:1,match_order:2}
  ]
}
const preflight={
  schema_version:'authoritative_week_schedule_preflight.v1' as const,
  run_id:'run-one',branch_id:'branch-one',week,
  event_ids:['E1','E2'],group_ids:['M1','M2'],schedule_required:true,
  schedule_already_adopted:false,canonical_preparation:null,
  canonical_preparation_ready:true,blockers:[],can_propose_schedule:true,
  expected_position_fingerprint:fp('a'),preflight_fingerprint:fp('b'),read_only:true as const
}
const proposal={schedule,schedule_fingerprint:fp('c'),position_fingerprint:fp('d'),
  provenance:'canonical_week_topological_proposal.v1',persisted:false as const}
const stored={run_id:'run-one',branch_id:'branch-one',week,required:true,
  event_ids:['E1','E2'],group_ids:['M1','M2'],schedule,
  schedule_fingerprint:fp('c'),expected_position_fingerprint:fp('a')}
const list={schema_version:'authoritative_match_replay_list.v1' as const,
  run_id:'run-one',branch_id:'branch-one',read_only:true,
  matches:[{
    week_ordinal:1,slot_id:'week-1:slot:1',group_id:'M1',match_id:'match-1',
    result_fingerprint:fp('e'),winner_player_id:'P1',loser_player_id:'P2',
    total_rallies:45,match_log_hash:fp('f'),replay_available:true
  },{
    week_ordinal:1,slot_id:'week-1:slot:2',group_id:'M2',match_id:'match-2',
    result_fingerprint:fp('g'.replace('g','0')),winner_player_id:'P3',
    loser_player_id:'P4',total_rallies:41,match_log_hash:fp('1'),replay_available:true
  }]
}
let adopted:boolean
let head:string
let draftVersion:number
let dirty:boolean
let saved:boolean
beforeEach(()=>{
  vi.clearAllMocks()
  adopted=false;head='rev-1';draftVersion=0;dirty=false;saved=false
  api.getRunContainer.mockResolvedValue({
    run_id:'run-one',storage_kind:'custom_local',read_only:false,status:'working'
  })
  api.listRunBranches.mockImplementation(async()=>({run_branches:[{
    run_id:'run-one',branch_id:'branch-one',status:'active',read_only:false,
    saved_head_revision_id:head
  }]}))
  api.getBranchWorkingDraft.mockImplementation(async()=>({
    run_id:'run-one',branch_id:'branch-one',base_saved_revision_id:head,
    status:dirty?'dirty':'clean',draft_version:draftVersion,
    can_save:dirty
  }))
  api.inspectAuthoritativeWeekSchedulePreflight.mockImplementation(async()=>({
    ...preflight,schedule_already_adopted:adopted,can_propose_schedule:!adopted
  }))
  api.inspectAuthoritativeWeekSchedule.mockResolvedValue(stored)
  api.proposeAuthoritativeWeekSchedule.mockResolvedValue(proposal)
  api.adoptAuthoritativeWeekScheduleProposal.mockImplementation(async()=>{
    adopted=true;dirty=true;draftVersion=1
    return {schedule,schedule_fingerprint:fp('c'),adoption:'adopted_topological_proposal'}
  })
  api.listAuthoritativeMatchReplays.mockResolvedValue(list)
  api.previewAuthoritativeSimulationSave.mockImplementation(async()=>({
    run_id:'run-one',branch_id:'branch-one',
    saved_head_revision_id:head,draft_version:draftVersion,
    can_save:dirty,has_unsaved_changes:dirty,
    simulation_fingerprint:fp('9')
  }))
  api.saveAuthoritativeSimulation.mockImplementation(async()=>{
    const previous=head
    head='rev-2';dirty=false;saved=true;draftVersion=2
    return {run_id:'run-one',branch_id:'branch-one',
      previous_viewer_branch_id:'viewer-1',viewer_branch_id:'viewer-1',
      saved_revision:{revision_id:head,parent_revision_id:previous,
        sequence:2,kind:'simulation',payload_schema_version:'v1',
        content_hash_algorithm:'sha256',content_hash:fp('8'),change_summary:{}},
      working_draft:{run_id:'run-one',branch_id:'branch-one',
        draft_id:'draft-1',base_saved_revision_id:head,
        saved_viewer_branch_id:'viewer-1',proposed_viewer_branch_id:'viewer-1',
        current_viewer_branch_id:'viewer-1',status:'clean',change_count:0,
        draft_version:2,can_save:false},
      audit_event_id:'audit-2'
    }
  })
})
const show=(eventId='E1')=>renderWithRoute(
  <RunWeekMatchCheckpointPanel runId="run-one" branchId="branch-one" eventId={eventId}/>,
  '/admin/runs/run-one/calendar/E1')

describe('Canonical Week schedule / real match / Saved Revision handoff',()=>{
  it('reviews *all* events, adopts once and reopens the persisted full Week schedule',async()=>{
    show()
    const preview=await screen.findByRole('button',{name:'Preview complete Week Schedule'})
    await waitFor(()=>expect(preview).toBeEnabled())
    await userEvent.click(preview)
    expect(await screen.findByText(/2 process\/match slots/)).toBeInTheDocument()
    expect(screen.getByText(/E2 · M2/)).toBeInTheDocument()
    const adopt=screen.getByRole('button',{name:'Commit reviewed Week Schedule'})
    expect(adopt).toBeDisabled()
    expect(api.adoptAuthoritativeWeekScheduleProposal).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve full Week Schedule'}))
    await userEvent.click(adopt)
    await waitFor(()=>expect(api.adoptAuthoritativeWeekScheduleProposal).toHaveBeenCalledWith(
      'run-one','branch-one',expect.objectContaining({
        expected_schedule_fingerprint:fp('c'),
        expected_position_fingerprint:fp('d'),expected_week:week
      })
    ))
    expect(await screen.findByText(/Adopted Week Schedule/)).toBeInTheDocument()
    expect(screen.getByText(/1 verified stored tournament match/)).toBeInTheDocument()
    expect(screen.getByText('P1')).toBeInTheDocument()
    expect(screen.queryByText('P3')).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Preview complete Week Schedule'})).not.toBeInTheDocument()
  })
  it('reviews dirty sporting changes, commits CAS Save and reloads new immutable revision',async()=>{
    adopted=true;dirty=true;draftVersion=1
    show()
    const review=await screen.findByRole('button',{name:'Review sporting Saved Revision'})
    await waitFor(()=>expect(review).toBeEnabled())
    await userEvent.click(review)
    expect(await screen.findByText(/simulation fingerprint/)).toBeInTheDocument()
    const save=screen.getByRole('button',{name:'Commit and verify Saved Revision'})
    expect(save).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve Run sporting Save'}))
    await userEvent.click(save)
    await waitFor(()=>expect(api.saveAuthoritativeSimulation).toHaveBeenCalledWith(
      'run-one','branch-one',expect.objectContaining({
        expected_draft_version:1,expected_simulation_fingerprint:fp('9')
      })
    ))
    expect(await screen.findByText(/Verified new Saved Revision:/)).toBeInTheDocument()
    expect(saved).toBe(true)
    expect(screen.getByText('rev-2')).toBeInTheDocument()
  })
  it('never proposes schedule with unresolved Week blockers',async()=>{
    api.inspectAuthoritativeWeekSchedulePreflight.mockResolvedValueOnce({
      ...preflight,blockers:['entry_validation_policy_unresolved'],
      can_propose_schedule:false
    })
    show()
    const button=await screen.findByRole('button',{name:'Preview complete Week Schedule'})
    expect(button).toBeDisabled()
    expect(api.proposeAuthoritativeWeekSchedule).not.toHaveBeenCalled()
  })
  it('rejects a stale full-Week proposal, altered source and forged replay outcomes',()=>{
    expect(validFirstWeekScheduleProposal(preflight,proposal,'run-one','branch-one','E1')).toBe(true)
    expect(validFirstWeekScheduleProposal(preflight,{
      ...proposal,schedule:{...schedule,slots:schedule.slots.slice(0,1)}
    },'run-one','branch-one','E1')).toBe(false)
    expect(validPersistedWeekSchedule(stored,proposal,'run-one','branch-one')).toBe(true)
    expect(validPersistedWeekSchedule({...stored,schedule_fingerprint:fp('0')},
      proposal,'run-one','branch-one')).toBe(false)
    expect(verifiedTournamentMatchRows(list,stored,'run-one','branch-one','E1')
      .map(x=>x.winnerId)).toEqual(['P1'])
    expect(verifiedTournamentMatchRows({...list,matches:[{
      ...list.matches[0],result_fingerprint:'bad',winner_player_id:'ghost'
    }]},stored,'run-one','branch-one','E1')).toEqual([])
  })
  it('refuses an unreviewable Save or a forged Saved Revision receipt',()=>{
    expect(validCheckpointPreview({
      run_id:'run-one',branch_id:'branch-one',
      saved_head_revision_id:'rev-1',draft_version:1,
      has_unsaved_changes:true,can_save:true,simulation_fingerprint:fp('7')
    },'rev-1')).toBe(true)
    expect(validCheckpointPreview({
      saved_head_revision_id:'rev-1',draft_version:1,
      has_unsaved_changes:false,can_save:true,simulation_fingerprint:fp('7')
    },'rev-1')).toBe(false)
    const receipt={
      run_id:'run-one',branch_id:'branch-one',
      previous_viewer_branch_id:'v',viewer_branch_id:'v',
      saved_revision:{revision_id:'rev-2',parent_revision_id:'rev-1',
        sequence:2,kind:'simulation',payload_schema_version:'v1',
        content_hash_algorithm:'sha256',content_hash:fp('8'),change_summary:{}},
      working_draft:{run_id:'run-one',branch_id:'branch-one',
        draft_id:'draft',base_saved_revision_id:'rev-2',
        saved_viewer_branch_id:'v',proposed_viewer_branch_id:'v',current_viewer_branch_id:'v',
        status:'clean' as const,change_count:0,draft_version:2,can_save:false},
      audit_event_id:'a'
    }
    expect(validSavedCheckpoint(receipt,'run-one','branch-one','rev-1')).toBe(true)
    expect(validSavedCheckpoint({...receipt,saved_revision:{
      ...receipt.saved_revision,parent_revision_id:'foreign'
    }},'run-one','branch-one','rev-1')).toBe(false)
  })
})

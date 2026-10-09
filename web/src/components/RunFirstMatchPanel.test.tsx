import { screen,waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach,describe,expect,it,vi } from 'vitest'

import { RunFirstMatchPanel } from './RunFirstMatchPanel'
import {
  verifiedMatchReplay,verifiedScheduledMatch,type ReviewedFirstMatchEvidence
} from '../api/runFirstMatchReview'
import { renderWithRoute } from '../test/testUtils'

const api=vi.hoisted(()=>({
  getRunContainer:vi.fn(),listRunBranches:vi.fn(),getBranchWorkingDraft:vi.fn(),
  getCanonicalTournamentPreparation:vi.fn(),
  getCanonicalTournamentEntryFieldState:vi.fn(),
  getCanonicalTournamentDrawState:vi.fn(),
  getCanonicalTournamentDrawAuthority:vi.fn(),
  inspectAuthoritativeWeekSchedulePreflight:vi.fn(),
  inspectAuthoritativeWeekSchedule:vi.fn(),
  getAuthoritativeSimulationPosition:vi.fn(),
  inspectAuthoritativeMatchReconstruction:vi.fn(),
  simulateAuthoritativeNextMatch:vi.fn(),
  listAuthoritativeMatchReplays:vi.fn(),
  getAuthoritativeMatchReplayContext:vi.fn()
}))
vi.mock('../api/client',()=>api)
const h=(x:string)=>x.repeat(64)
const week={season_index:0,week:1}
const field={
  schema_version:'canonical_tournament_entry_field_state.v2' as const,
  run_id:'run-first',branch_id:'branch-first',event_id:'event-first',
  field_sequence:1,field_fingerprint:h('a'),mode:'initial' as const,
  direct_main_player_ids:['A','B'],qualification_player_ids:[],
  below_qualification_cut_player_ids:[],withdrawn_player_ids:[],
  main_draw_capacity:4,active_main_entrant_count:2,
  effective_main_bye_count:2,main_diagnostics:[],
  draw_input_committed:true,pre_draw_repair_locked_by_draw_input:true
}
const draw={
  schema_version:'canonical_tournament_draw_state.v1' as const,
  run_id:'run-first',branch_id:'branch-first',event_id:'event-first',
  field_sequence:1,field_fingerprint:h('a'),
  main_draw_capacity:4,active_main_entrant_count:2,effective_main_bye_count:2,
  draw_input_committed:true,draw_input_fingerprint:h('b'),draw_seed:12345,
  main_seed_count:2,qualification_seed_count:0,
  initial_draw_generated:true,draw_authority_fingerprint:h('c'),
  draw_algorithm_version:'idealized_seed_tiers.v2',
  main_slot_count:4,main_node_count:3,main_bye_count:2,
  qualification_section_count:0,qualification_section_sizes:[],main_diagnostics:[]
}
const authority={
  schema_version:'tournament_draw_authority.v2' as const,
  algorithm_version:'idealized_seed_tiers.v2' as const,
  run_id:'run-first',branch_id:'branch-first',event_id:'event-first',
  generated_by_command_id:'draw-generated',draw_input_fingerprint:h('b'),
  main:{
    draw_type:'main' as const,bracket_size:4,
    seed_positions:[[1,1],[2,4]] as Array<[number,number]>,
    slots:[
      {slot_index:1,entrant_kind:'player' as const,player_id:'A',
        placeholder_id:null,seed_number:1,is_seed_protected:true},
      {slot_index:2,entrant_kind:'bye' as const,player_id:null,
        placeholder_id:null,seed_number:null,is_seed_protected:false},
      {slot_index:3,entrant_kind:'bye' as const,player_id:null,
        placeholder_id:null,seed_number:null,is_seed_protected:false},
      {slot_index:4,entrant_kind:'player' as const,player_id:'B',
        placeholder_id:null,seed_number:2,is_seed_protected:true}
    ],
    nodes:[],bye_slot_indexes:[1,2],
    qualifier_placeholder_slots:[]
  },
  qualification:null,qualification_sections:[]
}
const schedule={
  run_id:'run-first',branch_id:'branch-first',
  week,schedule_fingerprint:h('d'),
  required:true,event_ids:['event-first'],group_ids:['match-first'],
  expected_position_fingerprint:h('e'),
  schedule:{
    schema_version:'week_simulation_schedule.v2' as const,
    run_id:'run-first',branch_id:'branch-first',week,
    slots:[{ordinal:1,group_ids:['match-first'],event_id:'event-first',
      draw_phase:'main' as const,round_number:1,match_day_ordinal:1,match_order:1}]
  }
}
const position={
  run_id:'run-first',branch_id:'branch-first',current_week:week,
  current_slot_kind:'match' as const,current_slot_id:'week-1:slot:1',
  slot_ordinal:1,unresolved_group_ids:['match-first'],
  eligible_match_ids:['match-first'],blocked_match_ids:[],
  current_slot_complete:false,supported_tournament_complete:false,
  week_ready_for_transition:false,transition_blockers:[],
  terminal_sporting_fingerprint:null,position_fingerprint:h('e')
}
const match={
  run_id:'run-first',branch_id:'branch-first',week,
  expected_revision_id:'revision-one',position_fingerprint:h('e'),
  slot_id:'week-1:slot:1',slot_start_fingerprint:h('f'),
  group_id:'match-first',event_id:'event-first',match_id:'match-first',
  player_a_id:'A',player_b_id:'B'
}
const advanced={
  ...position,position_fingerprint:h('1'),current_slot_kind:null,
  current_slot_id:null,slot_ordinal:null,unresolved_group_ids:[],
  eligible_match_ids:[],current_slot_complete:true
}
const replayList={
  schema_version:'authoritative_match_replay_list.v1' as const,
  run_id:'run-first',branch_id:'branch-first',read_only:true,
  matches:[{
    week_ordinal:1,slot_id:'week-1:slot:1',group_id:'match-first',
    match_id:'match-first',result_fingerprint:h('2'),
    winner_player_id:'A',loser_player_id:'B',
    total_rallies:53,match_log_hash:h('3'),replay_available:true
  }]
}
const replay={
  schema_version:'authoritative_match_replay_context.v1' as const,
  run_id:'run-first',branch_id:'branch-first',event_id:'event-first',
  week_ordinal:1,slot_id:'week-1:slot:1',group_id:'match-first',
  match_id:'match-first',result_fingerprint:h('2'),
  match_input_fingerprint:h('4'),snapshot_hash:h('5'),
  simulation_seed:42,match_engine_version:'match-engine',
  context:{},effective_match_format:{},effective_match_timing:null,
  effective_match_gameplans:null,effective_rally_rules:null,
  rally_calibration_profile:null,unsupported_future_inputs:[],
  player_projections:[],
  summary:{
    player_a_id:'A',player_a_name:'Player A',
    player_b_id:'B',player_b_name:'Player B',
    best_of:5,games_to:11,win_by:2,
    ruleset_version:null,resolver_version:null,
    rules_calibration_version:null,rules_unsupported_components:[]
  },
  replay_source:'stored_authoritative_events' as const,
  rng_rerun:false as const,read_only:true as const,verified:true as const
}
let nowPosition:typeof position|typeof advanced
let scheduleAdopted:boolean
let dirty:boolean
let currentEvent:string
beforeEach(()=>{
  vi.clearAllMocks()
  nowPosition=position
  scheduleAdopted=true
  dirty=false
  currentEvent='event-first'
  api.getRunContainer.mockResolvedValue({
    run_id:'run-first',storage_kind:'custom_local',
    read_only:false,status:'working'
  })
  api.listRunBranches.mockResolvedValue({run_branches:[{
    run_id:'run-first',branch_id:'branch-first',status:'active',
    read_only:false,saved_head_revision_id:'revision-one'
  }]})
  api.getBranchWorkingDraft.mockImplementation(async()=>({
    run_id:'run-first',branch_id:'branch-first',
    base_saved_revision_id:'revision-one',status:dirty?'dirty':'clean',
    draft_version:1
  }))
  api.getCanonicalTournamentPreparation.mockResolvedValue({
    schema_version:'canonical_tournament_preparation_state.v1',
    run_id:'run-first',branch_id:'branch-first',event_id:'event-first',
    phase:'draw_ready',next_required_action:'none',
    authority_source:'run_owned_db_authorities.v1',
    blockers:[],ready_for_match_schedule:true,effective_draw_fingerprint:h('c')
  })
  api.getCanonicalTournamentEntryFieldState.mockResolvedValue(field)
  api.getCanonicalTournamentDrawState.mockResolvedValue(draw)
  api.getCanonicalTournamentDrawAuthority.mockResolvedValue(authority)
  api.inspectAuthoritativeWeekSchedulePreflight.mockImplementation(async()=>({
    schema_version:'authoritative_week_schedule_preflight.v1',
    run_id:'run-first',branch_id:'branch-first',week,
    schedule_required:true,schedule_already_adopted:scheduleAdopted,
    canonical_preparation:null,canonical_preparation_ready:true,
    blockers:scheduleAdopted?[]:['week_schedule_not_adopted'],
    can_propose_schedule:!scheduleAdopted,
    expected_position_fingerprint:h('e'),preflight_fingerprint:h('6'),
    read_only:true
  }))
  api.inspectAuthoritativeWeekSchedule.mockResolvedValue(schedule)
  api.getAuthoritativeSimulationPosition.mockImplementation(async()=>nowPosition)
  api.inspectAuthoritativeMatchReconstruction.mockImplementation(async()=>({
    ...match,event_id:currentEvent
  }))
  api.simulateAuthoritativeNextMatch.mockImplementation(async()=>{
    nowPosition=advanced
    return advanced
  })
  api.listAuthoritativeMatchReplays.mockResolvedValue(replayList)
  api.getAuthoritativeMatchReplayContext.mockResolvedValue(replay)
})
const show=()=>renderWithRoute(
  <RunFirstMatchPanel runId="run-first" branchId="branch-first" eventId="event-first"/>,
  '/admin/runs/run-first/calendar/event-first'
)

describe('First canonical Run-owned match execution',()=>{
  it('confirms real scheduled players, executes once and verifies persisted winner from replay',async()=>{
    show()
    const button=await screen.findByRole('button',{name:'Review first real match'})
    await waitFor(()=>expect(button).toBeEnabled())
    expect(screen.getByText(/Event event-first · Week 1/)).toBeInTheDocument()
    expect(api.simulateAuthoritativeNextMatch).not.toHaveBeenCalled()
    await userEvent.click(button)
    const play=screen.getByRole('button',{name:'Simulate reviewed first match'})
    expect(play).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve first real match'}))
    await userEvent.click(play)
    await waitFor(()=>expect(api.simulateAuthoritativeNextMatch).toHaveBeenCalledWith(
      'run-first','branch-first',expect.objectContaining({
        expected_position_fingerprint:h('e'),
        expected_revision_id:'revision-one',
        expected_week:week,group_id:'match-first'
      })
    ))
    expect(await screen.findByText(/Real stored match result/)).toBeInTheDocument()
    expect(screen.getByText(/53 persisted rallies/)).toBeInTheDocument()
    expect(screen.getByText('A',{exact:true})).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Simulate reviewed first match'})).not.toBeInTheDocument()
  })

  it('requires adopted Week Schedule instead of simulating directly from a Draw',async()=>{
    scheduleAdopted=false
    show()
    expect(await screen.findByText(/A verified adopted Week Simulation Schedule v2 is required/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Review first real match'})).not.toBeInTheDocument()
    expect(api.getAuthoritativeSimulationPosition).not.toHaveBeenCalled()
  })

  it('refuses running a match belonging to another current tournament',async()=>{
    currentEvent='other-event'
    show()
    expect(await screen.findByText(/does not belong to the selected event/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Review first real match'})).not.toBeInTheDocument()
  })

  it('refuses an unsaved Run Draft before position or match inspection',async()=>{
    dirty=true
    show()
    expect(await screen.findByText(/active writable Product Run Branch/)).toBeInTheDocument()
    expect(api.getAuthoritativeSimulationPosition).not.toHaveBeenCalled()
    expect(api.simulateAuthoritativeNextMatch).not.toHaveBeenCalled()
  })

  it('rechecks fresh position and rejects stale match before sending sporting command',async()=>{
    show()
    const button=await screen.findByRole('button',{name:'Review first real match'})
    await waitFor(()=>expect(button).toBeEnabled())
    await userEvent.click(button)
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve first real match'}))
    // Fresh backend state changes without first notifying the cached UI.
    nowPosition={...position,position_fingerprint:h('7')}
    await userEvent.click(screen.getByRole('button',{name:'Simulate reviewed first match'}))
    expect(await screen.findByText(/Match or timetable changed/)).toBeInTheDocument()
    expect(api.simulateAuthoritativeNextMatch).not.toHaveBeenCalled()
  })

  it('rejects wrong Week/Slot and non-authoritative winner evidence',()=>{
    expect(verifiedScheduledMatch(position,match,schedule,
      'run-first','branch-first','event-first','revision-one')).toBe(true)
    expect(verifiedScheduledMatch(position,{...match,player_b_id:'A'},schedule,
      'run-first','branch-first','event-first','revision-one')).toBe(false)
    expect(verifiedScheduledMatch(position,match,{...schedule,schedule_fingerprint:'stale'},
      'run-first','branch-first','event-first','revision-one')).toBe(false)
    const evidence:ReviewedFirstMatchEvidence={
      runId:'run-first',branchId:'branch-first',eventId:'event-first',
      head:'revision-one',draftVersion:1,
      positionFingerprint:h('e'),week,
      groupId:'match-first',matchId:'match-first',
      slotId:'week-1:slot:1',slotOrdinal:1,slotStartFingerprint:h('f'),
      playerAId:'A',playerBId:'B',drawFingerprint:h('c'),
      scheduleFingerprint:h('d'),commandId:'commit-first'
    }
    expect(verifiedMatchReplay(replayList,replay,evidence)?.winnerId).toBe('A')
    expect(verifiedMatchReplay({
      ...replayList,matches:[{...replayList.matches[0],winner_player_id:'ghost'}]
    },replay,evidence)).toBeNull()
    expect(verifiedMatchReplay(replayList,{...replay,result_fingerprint:h('9')},
      evidence)).toBeNull()
  })
})

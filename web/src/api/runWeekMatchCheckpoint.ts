import type {
  AuthoritativeWeekSchedulePreflight, AuthoritativeWeekScheduleProposal,
  AuthoritativeWeekScheduleInspection, AuthoritativeSimulationSavePreview,
  AuthoritativeSimulationSaveResponse, AuthoritativeMatchReplayList
} from './types'

const sha=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v)
const equalWeek=(a:{season_index:number;week:number},b:{season_index:number;week:number})=>
  a.season_index===b.season_index&&a.week===b.week

/** Review *the entire Week*, including simultaneous tournaments, not one Event. */
export function validFirstWeekScheduleProposal(
  preflight:AuthoritativeWeekSchedulePreflight|undefined,
  proposal:AuthoritativeWeekScheduleProposal|undefined,
  runId:string,branchId:string,eventId:string
):proposal is AuthoritativeWeekScheduleProposal {
  if(!preflight||!proposal||
    preflight.schema_version!=='authoritative_week_schedule_preflight.v1'||
    preflight.run_id!==runId||preflight.branch_id!==branchId||
    !preflight.read_only||!preflight.schedule_required||
    preflight.schedule_already_adopted||!preflight.can_propose_schedule||
    !preflight.canonical_preparation_ready||preflight.blockers.length>0||
    !preflight.event_ids.includes(eventId)||
    !sha(preflight.expected_position_fingerprint)||!sha(preflight.preflight_fingerprint)||
    proposal.persisted!==false||
    proposal.schedule.schema_version!=='week_simulation_schedule.v2'||
    proposal.schedule.run_id!==runId||proposal.schedule.branch_id!==branchId||
    !equalWeek(proposal.schedule.week,preflight.week)||
    !sha(proposal.schedule_fingerprint)||!sha(proposal.position_fingerprint)||
    proposal.schedule.slots.length===0) return false
  const ids=new Set<number>()
  const scheduled=new Set<string>()
  for(const slot of proposal.schedule.slots){
    if(!Number.isInteger(slot.ordinal)||slot.ordinal<1||ids.has(slot.ordinal)||
      slot.group_ids.length===0||new Set(slot.group_ids).size!==slot.group_ids.length)
      return false
    ids.add(slot.ordinal)
    for(const id of slot.group_ids){
      if(!id||scheduled.has(id))return false
      scheduled.add(id)
    }
    if(slot.event_id && !preflight.event_ids.includes(slot.event_id))return false
  }
  return preflight.group_ids.every(id=>scheduled.has(id))&&
    scheduled.size===preflight.group_ids.length
}

export function validPersistedWeekSchedule(
  saved:AuthoritativeWeekScheduleInspection|undefined,
  proposal:AuthoritativeWeekScheduleProposal,runId:string,branchId:string
):boolean {
  return Boolean(saved&&saved.run_id===runId&&saved.branch_id===branchId&&
    saved.schedule?.schema_version==='week_simulation_schedule.v2'&&
    saved.schedule.run_id===runId&&saved.schedule.branch_id===branchId&&
    equalWeek(saved.week,proposal.schedule.week)&&
    saved.schedule_fingerprint===proposal.schedule_fingerprint&&
    saved.schedule.slots.length===proposal.schedule.slots.length&&
    saved.schedule.slots.every((v,i)=>{
      const source=proposal.schedule.slots[i]
      return source&&v.ordinal===source.ordinal&&
        v.event_id===source.event_id&&v.draw_phase===source.draw_phase&&
        v.round_number===source.round_number&&
        v.match_day_ordinal===source.match_day_ordinal&&
        v.match_order===source.match_order&&
        v.group_ids.length===source.group_ids.length&&
        v.group_ids.every((id,j)=>id===source.group_ids[j])
    }))
}

export function validCheckpointPreview(
  preview:AuthoritativeSimulationSavePreview|undefined,head:string
):boolean {
  return Boolean(preview&&head&&preview.saved_head_revision_id===head&&
    Number.isInteger(preview.draft_version)&&preview.draft_version>=0&&
    preview.can_save===true&&preview.has_unsaved_changes===true&&
    sha(preview.simulation_fingerprint))
}

export function validSavedCheckpoint(
  result:AuthoritativeSimulationSaveResponse|undefined,
  runId:string,branchId:string,previousHead:string
):boolean {
  return Boolean(result&&result.run_id===runId&&result.branch_id===branchId&&
    result.saved_revision.revision_id&&
    result.saved_revision.revision_id!==previousHead&&
    result.saved_revision.parent_revision_id===previousHead&&
    result.working_draft.run_id===runId&&
    result.working_draft.branch_id===branchId&&
    result.working_draft.status==='clean'&&
    result.working_draft.base_saved_revision_id===result.saved_revision.revision_id&&
    result.working_draft.can_save===false)
}

export type WeekMatchRow={
  matchId:string;groupId:string;winnerId:string;loserId:string;
  resultFingerprint:string;totalRallies:number
}
export function verifiedTournamentMatchRows(
  replays:AuthoritativeMatchReplayList|undefined,
  schedule:AuthoritativeWeekScheduleInspection|undefined,
  runId:string,branchId:string,eventId:string
):WeekMatchRow[]{
  if(!replays||!schedule||replays.schema_version!=='authoritative_match_replay_list.v1'||
    replays.run_id!==runId||replays.branch_id!==branchId||!replays.read_only||
    schedule.run_id!==runId||schedule.branch_id!==branchId||
    schedule.schedule?.schema_version!=='week_simulation_schedule.v2'||!sha(schedule.schedule_fingerprint))
    return []
  const groups=new Set(schedule.schedule.slots.filter(s=>s.event_id===eventId)
    .flatMap(s=>s.group_ids))
  const found=new Set<string>()
  return replays.matches.filter(row=>{
    if(!groups.has(row.group_id)||!row.replay_available||
      !row.match_id||!sha(row.result_fingerprint)||
      !row.winner_player_id||!row.loser_player_id||
      row.winner_player_id===row.loser_player_id||
      !Number.isInteger(row.total_rallies)||row.total_rallies<1||
      found.has(row.group_id))return false
    found.add(row.group_id)
    return true
  }).map(row=>({
    matchId:row.match_id,groupId:row.group_id,winnerId:row.winner_player_id,
    loserId:row.loser_player_id,resultFingerprint:row.result_fingerprint,
    totalRallies:row.total_rallies
  }))
}

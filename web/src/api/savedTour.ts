/** Read-only Saved Revision Run Tour contracts from the canonical backend. */
export type SavedTourEvent = {
  event_id:string;season:string;season_week:number;event_name:string
  template_id:string;category:string;tour_level:string|null
  host_country:string;host_city:string|null;region:string
  main_draw_size:number;qualification_draw_size:number
  seeds_count:number;qualifier_spots:number;wild_cards:number;byes:number
  ranking_status:string;result_published:boolean
  champion_player_id:string|null;finalist_player_id:string|null
}
export type SavedTourCalendar = {
  schema_version:'run_saved_tour_calendar.v1';source:'reachable_saved_revision'
  run_id:string;branch_id:string;revision_branch_id:string
  saved_revision_id:string;season_index:number;season:string;week_count:61
  calendar_status:'empty'|'ready';edition_count:number;editions:SavedTourEvent[]
}
export type SavedTourResult = {
  schema_version:'viewer_tournament_result.v1'
  product_run_id:string;viewer_branch_id:string;event_id:string
  completed_season_index:number;completed_week:number
  champion_player_id:string;finalist_player_id:string
  qualification_winner_ids:string[]
  players:Array<{player_id:string;draw_type:string;reached_stage:string;wins:number;losses:number}>
  matches:Array<{match_id:string;draw_type:string;round_number:number;bracket_position:number;winner_player_id:string;loser_player_id:string|null;scoreline:string}>
}
export type SavedTourEntryField = {
  schema_version:'viewer_tournament_entry_field.v1'
  product_run_id:string;viewer_branch_id:string;event_id:string
  field_sequence:number;mode:'initial'|'pre_draw_repair'
  main_draw_capacity:number;active_main_entrant_count:number;effective_main_bye_count:number
  direct_main_player_ids:string[];qualification_player_ids:string[]
  alternate_player_ids:string[];withdrawn_player_ids:string[]
}
export type SavedTourDrawSlot = {
  slot_index:number;entrant_kind:'player'|'qualifier_placeholder'|'lucky_loser_placeholder'|'bye'
  player_id:string|null;placeholder_id:string|null;seed_number:number|null
  entry_status:'wild_card'|'lucky_loser'|null
}
export type SavedTourDrawBracket = {
  draw_type:'main'|'qualification';section_id:string|null;bracket_size:number;slots:SavedTourDrawSlot[]
}
export type SavedTourDraw = {
  schema_version:'viewer_tournament_draw.v1'
  product_run_id:string;viewer_branch_id:string;event_id:string;revision_count:number
  main:SavedTourDrawBracket;qualification_sections:SavedTourDrawBracket[]
}
export type SavedTourScheduledMatch = {
  global_slot_ordinal:number;match_day_ordinal:number;match_order:number
  draw_phase:'qualification'|'main'|'group';round_number:number
  group_id:string;match_id:string|null
}
export type SavedTourMatchSchedule = {
  schema_version:'run_saved_tour_match_schedule.v1'
  source:'saved_week_simulation_schedule.v2'
  run_id:string;revision_branch_id:string;event_id:string
  season_index:number;season_week:number;week_schedule_fingerprint:string
  slots:SavedTourScheduledMatch[]
}
export type SavedTourGroupMatch = {
  match_id:string;group_index:number;match_day_ordinal:number;match_order:number
  top_player_id:string;bottom_player_id:string;best_of:3|5
}
export type SavedTourGroupSchedule = {
  schema_version:'run_saved_tour_group_schedule.v1'
  source:'saved_tournament_group_match_schedule_authority.v1'
  run_id:string;revision_branch_id:string;event_id:string;authority_fingerprint:string
  group_count:number;group_size:number;match_day_count:number
  matches:SavedTourGroupMatch[]
}
export type SavedTourGroupTableRow = {
  position:number;player_id:string;wins:number;losses:number;group_points:number
  played_matches:number;walkovers_received:number;walkovers_conceded:number
  games_won:number;games_lost:number;points_won:number;points_lost:number
}
export type SavedTourGroupStandings = {
  schema_version:'run_saved_tour_group_standings.v1'
  source:'saved_tournament_group_standings_authority'
  run_id:string;revision_branch_id:string;event_id:string
  authority_fingerprint:string;group_schedule_fingerprint:string
  groups:Array<{group_index:number;rows:SavedTourGroupTableRow[]}>
  tie_decisions:Array<{group_index:number;case_fingerprint:string;ordered_player_ids:string[];admin_reason:string}>
}
export type SavedTourPendingTieDecision = {
  group_index:number;case_fingerprint:string;ordered_player_ids:string[];admin_reason:string
}
export type SavedTourEdition = {
  schema_version:'run_saved_tour_edition.v1';source:'reachable_saved_revision'
  run_id:string;branch_id:string;revision_branch_id:string
  saved_revision_id:string;season_index:number
  edition:SavedTourEvent;published_result:SavedTourResult|null
  entry_field?:SavedTourEntryField|null;draw?:SavedTourDraw|null
  match_schedule?:SavedTourMatchSchedule|null
  group_schedule?:SavedTourGroupSchedule|null
  group_standings?:SavedTourGroupStandings|null
  pending_group_tie_decisions?:SavedTourPendingTieDecision[]
  lifecycle_status:'unavailable'
}

export type SavedTourRallyFrame = {
  rally_index:number;set_number:number;server_player_id:string;winner_player_id:string|null
  score_a_before:number;score_b_before:number;score_a_after:number;score_b_after:number
  sets_a_after:number;sets_b_after:number;set_complete:boolean;match_complete:boolean
}
export type SavedTourMatchDetail = {
  schema_version:'run_saved_tour_match_detail.v1'
  source:'reachable_saved_revision'
  run_id:string;branch_id:string;revision_branch_id:string
  saved_revision_id:string;season_index:number;event_id:string;match_id:string
  match:SavedTourResult['matches'][number]
  replay_status:'available'|'unavailable';player_a_id:string|null;player_b_id:string|null
  offset:number;limit:number;total_rallies:number;has_more:boolean
  rallies:SavedTourRallyFrame[]
}
/** Confirm two successive, already independently validated archive events form
 * one sporting timeline. Also usable at the 25/26 page boundary, but only
 * when both real Saved pages have already been read: no guessed neighbors. */
export function validSavedTourRallyTransition(
  previous:SavedTourRallyFrame,next:SavedTourRallyFrame
):boolean{
  if(previous.match_complete||next.rally_index!==previous.rally_index+1)return false
  // The new rally's post-score may award exactly one Game/set on completion.
  // A later rally can never erase an earned set, even across page boundaries.
  const gamesA=next.sets_a_after-previous.sets_a_after
  const gamesB=next.sets_b_after-previous.sets_b_after
  if(gamesA<0||gamesB<0||gamesA+gamesB!==Number(next.set_complete))return false
  if(next.set_number===previous.set_number)
    return !previous.set_complete
      &&next.score_a_before===previous.score_a_after
      &&next.score_b_before===previous.score_b_after
  return previous.set_complete&&next.set_number===previous.set_number+1
    &&next.score_a_before===0&&next.score_b_before===0
}

/** Compare independently validated adjacent Saved archive pages. A matching
 * URL scope alone is not proof: revision-owner, match summary and archive
 * length must also agree before reading their connecting rally events. */
export function validSavedTourRallyPagePair(
  previous:SavedTourMatchDetail,next:SavedTourMatchDetail
):boolean{
  const same=['run_id','branch_id','revision_branch_id','saved_revision_id',
    'season_index','event_id','match_id','replay_status','player_a_id',
    'player_b_id','total_rallies','limit'] as const
  const sameMatch=['match_id','draw_type','round_number','bracket_position',
    'winner_player_id','loser_player_id','scoreline'] as const
  return previous.replay_status==='available'&&next.replay_status==='available'
    &&previous.offset+previous.limit===next.offset
    &&same.every(key=>previous[key]===next[key])
    &&sameMatch.every(key=>previous.match[key]===next.match[key])
    &&previous.rallies.length>0&&next.rallies.length>0
    &&validSavedTourRallyTransition(
      previous.rallies[previous.rallies.length-1],next.rallies[0])
}

/** Exact selected branch and original revision-owner validation for historical match pages. */
export function validSavedTourMatchDetail(
  data:SavedTourMatchDetail,runId:string,branchId:string,revisionId:string,
  seasonIndex:number,eventId:string,matchId:string,offset:number,limit:number
):boolean{
  if(!data||data.schema_version!=='run_saved_tour_match_detail.v1'
    ||data.source!=='reachable_saved_revision'
    ||data.run_id!==runId||data.branch_id!==branchId
    ||!data.revision_branch_id||data.saved_revision_id!==revisionId
    ||data.season_index!==seasonIndex||data.event_id!==eventId
    ||data.match_id!==matchId||data.match?.match_id!==matchId
    ||!['main','qualification','group','knockout'].includes(data.match.draw_type)
    ||!Number.isSafeInteger(data.match.round_number)||data.match.round_number<1
    ||!Number.isSafeInteger(data.match.bracket_position)||data.match.bracket_position<1
    ||typeof data.match.scoreline!=='string'||!data.match.scoreline.trim()
    ||typeof data.match.winner_player_id!=='string'||!data.match.winner_player_id.trim()
    ||typeof data.match.loser_player_id!=='string'||!data.match.loser_player_id.trim()
    ||data.match.winner_player_id===data.match.loser_player_id
    ||data.offset!==offset||data.limit!==limit
    ||!Number.isSafeInteger(data.total_rallies)||data.total_rallies<0
    ||!Array.isArray(data.rallies)||data.rallies.length>limit
    ||!['available','unavailable'].includes(data.replay_status)
    ||data.has_more!==(data.replay_status==='available'&&offset+limit<data.total_rallies))
    return false
  if(data.replay_status==='unavailable')
    return data.total_rallies===0&&data.rallies.length===0&&!data.player_a_id&&!data.player_b_id
  if(!data.player_a_id||!data.player_b_id||data.player_a_id===data.player_b_id
    ||new Set([data.player_a_id,data.player_b_id,data.match.winner_player_id,data.match.loser_player_id]).size!==2
    ||data.total_rallies===0
    ||data.rallies.length!==Math.max(0,Math.min(limit,data.total_rallies-offset)))
    return false
  return data.rallies.every((frame,i)=>
    frame!=null&&frame.rally_index===offset+i+1
    &&Number.isSafeInteger(frame.set_number)&&frame.set_number>=1
    &&(['score_a_before','score_b_before','score_a_after','score_b_after',
      'sets_a_after','sets_b_after'] as const).every(key=>
      Number.isSafeInteger(frame[key])&&frame[key]>=0)
    &&typeof frame.set_complete==='boolean'&&typeof frame.match_complete==='boolean'
    // The archived MatchEngine may end by retirement after a rally, but a
    // documented "match complete" can only occur on its final scoring event.
    &&(!frame.match_complete||(frame.set_complete&&frame.rally_index===data.total_rallies))
    &&frame.score_a_after>=frame.score_a_before&&frame.score_b_after>=frame.score_b_before
    &&(frame.winner_player_id!==null
      ||(frame.score_a_before===frame.score_a_after
        &&frame.score_b_before===frame.score_b_after))
    &&(i===0||validSavedTourRallyTransition(data.rallies[i-1],frame))
    &&typeof frame.server_player_id==='string'
    &&[data.player_a_id,data.player_b_id].includes(frame.server_player_id)
    &&(frame.winner_player_id===null||typeof frame.winner_player_id==='string'
      &&[data.player_a_id,data.player_b_id].includes(frame.winner_player_id))
  )
}

/** The Calendar publication flag is authority, not a truthy display hint.
 * Validate raw JSON at the read boundary before granting result/player links. */
function validSavedTourOutcomeFields(event:SavedTourEvent):boolean{
  if(!event||typeof event.result_published!=='boolean')return false
  const winner=event.champion_player_id,runnerUp=event.finalist_player_id
  if(winner!==null&&(typeof winner!=='string'||!winner.trim()))return false
  if(runnerUp!==null&&(typeof runnerUp!=='string'||!runnerUp.trim()))return false
  // A published result is a completed sporting outcome, not merely a flag.
  // Missing champion/finalist IDs cannot authorize result links or player finishes.
  return !event.result_published||(Boolean(winner)&&Boolean(runnerUp)&&winner!==runnerUp)
}

/** Fail closed before displaying data from stale caches or cross-Branch responses. */
export function matchesSavedTourContext(
  payload:SavedTourCalendar|SavedTourEdition,
  runId:string,branchId:string,revisionId:string,seasonIndex:number
):boolean{
  return payload.source==='reachable_saved_revision'
    && payload.run_id===runId && payload.branch_id===branchId
    && payload.saved_revision_id===revisionId
    && payload.season_index===seasonIndex
    && typeof payload.revision_branch_id==='string'
    && payload.revision_branch_id.length>0
    && (payload.schema_version==='run_saved_tour_calendar.v1'
      || payload.schema_version==='run_saved_tour_edition.v1')
}
/** Both canonical calendar seasons (2000/2001) and stored edition seasons
 * (2000/01) identify the same sporting season, independent of World data years. */
function isSavedTourSeason(value:string,seasonIndex:number):boolean{
  if(!Number.isInteger(seasonIndex)||seasonIndex<0||seasonIndex>=50)return false
  const first=2000+seasonIndex,second=first+1
  return value===`${first}/${second}`
    ||value===`${first}/${String(second%100).padStart(2,'0')}`
}
export function validSavedTourCalendar(
  payload:SavedTourCalendar,runId:string,branchId:string,revisionId:string,seasonIndex:number
):boolean{
  if(!matchesSavedTourContext(payload,runId,branchId,revisionId,seasonIndex)
    ||payload.schema_version!=='run_saved_tour_calendar.v1'
    ||!isSavedTourSeason(payload.season,seasonIndex)
    ||payload.week_count!==61||!Array.isArray(payload.editions)
    ||payload.edition_count!==payload.editions.length
    ||!['ready','empty'].includes(payload.calendar_status)
    ||(payload.calendar_status==='empty'&&payload.editions.length>0))return false
  const seen=new Set<string>()
  return payload.editions.every(e=>{
    if(!validSavedTourOutcomeFields(e)||typeof e.event_id!=='string'||!e.event_id.trim()
      ||seen.has(e.event_id)
      ||!Number.isSafeInteger(e.season_week)||e.season_week<1||e.season_week>61
      ||!isSavedTourSeason(e.season,seasonIndex))return false
    seen.add(e.event_id)
    return true
  })
}
export function validSavedTourEdition(
  payload:SavedTourEdition,runId:string,branchId:string,revisionId:string,seasonIndex:number,eventId:string
):boolean{
  if(!matchesSavedTourContext(payload,runId,branchId,revisionId,seasonIndex)
    ||payload.schema_version!=='run_saved_tour_edition.v1'
    ||!validSavedTourOutcomeFields(payload.edition)
    ||typeof payload.edition.event_id!=='string'
    ||payload.edition.event_id!==eventId
    ||!isSavedTourSeason(payload.edition.season,seasonIndex)
    ||!Number.isSafeInteger(payload.edition.season_week)
    ||payload.edition.season_week<1||payload.edition.season_week>61
    ||payload.lifecycle_status!=='unavailable')return false
  const result=payload.published_result
  const published=result===null?!payload.edition.result_published:
    payload.edition.result_published &&
    result.schema_version==='viewer_tournament_result.v1'
    &&result.event_id===eventId&&result.product_run_id===runId
    &&result.viewer_branch_id===payload.revision_branch_id
    &&result.completed_season_index===seasonIndex
    &&result.completed_week===payload.edition.season_week
    &&result.champion_player_id===payload.edition.champion_player_id
    &&result.finalist_player_id===payload.edition.finalist_player_id
    &&result.champion_player_id!==result.finalist_player_id
    &&Array.isArray(result.players)&&Array.isArray(result.matches)
    &&Array.isArray(result.qualification_winner_ids)
    &&result.qualification_winner_ids.every(id=>typeof id==='string'&&!!id.trim())
    &&result.players.every(player=>player!=null
      &&typeof player.player_id==='string'&&!!player.player_id.trim()
      &&typeof player.reached_stage==='string'&&!!player.reached_stage.trim()
      &&Number.isSafeInteger(player.wins)&&player.wins>=0
      &&Number.isSafeInteger(player.losses)&&player.losses>=0)
    &&new Set(result.matches.map(match=>match?.match_id)).size===result.matches.length
    &&result.matches.every(match=>match!=null
      &&typeof match.match_id==='string'&&!!match.match_id.trim()
      &&['main','qualification','group','knockout'].includes(match.draw_type)
      &&Number.isSafeInteger(match.round_number)&&match.round_number>=1
      &&Number.isSafeInteger(match.bracket_position)&&match.bracket_position>=1
      &&typeof match.winner_player_id==='string'&&!!match.winner_player_id.trim()
      &&(match.loser_player_id===null||typeof match.loser_player_id==='string'
        &&!!match.loser_player_id.trim()&&match.loser_player_id!==match.winner_player_id)
      &&typeof match.scoreline==='string'&&!!match.scoreline.trim())
  if(!published)return false
  const entry=payload.entry_field,draw=payload.draw
  const owned=(value:{product_run_id:string;viewer_branch_id:string;event_id:string})=>
    value.product_run_id===runId&&value.viewer_branch_id===payload.revision_branch_id
      &&value.event_id===eventId
  if(entry){
    if(entry.schema_version!=='viewer_tournament_entry_field.v1'||!owned(entry)
      ||!Array.isArray(entry.direct_main_player_ids)
      ||!Array.isArray(entry.qualification_player_ids)
      ||!Array.isArray(entry.alternate_player_ids)
      ||!Array.isArray(entry.withdrawn_player_ids))return false
    const active=[...entry.direct_main_player_ids,...entry.qualification_player_ids,
      ...entry.alternate_player_ids]
    if(new Set(active).size!==active.length
      ||entry.withdrawn_player_ids.some(id=>active.includes(id)))return false
  }
  if(draw){
    if(!entry||draw.schema_version!=='viewer_tournament_draw.v1'||!owned(draw)
      ||!Array.isArray(draw.qualification_sections))return false
    const brackets=[draw.main,...draw.qualification_sections]
    for(const bracket of brackets){
      if(!Array.isArray(bracket.slots)||bracket.slots.length!==bracket.bracket_size
        ||new Set(bracket.slots.map(slot=>slot.slot_index)).size!==bracket.bracket_size
        ||bracket.slots.some(slot=>slot.slot_index<1||slot.slot_index>bracket.bracket_size
          ||(slot.entrant_kind==='player'?!slot.player_id:slot.player_id!==null)))
        return false
    }
  }
  const standings=payload.group_standings
  if(standings){
    if(!payload.group_schedule
      ||standings.schema_version!=='run_saved_tour_group_standings.v1'
      ||standings.source!=='saved_tournament_group_standings_authority'
      ||standings.run_id!==runId
      ||standings.revision_branch_id!==payload.revision_branch_id
      ||standings.event_id!==eventId
      ||!/^[0-9a-f]{64}$/.test(standings.authority_fingerprint)
      ||standings.group_schedule_fingerprint!==payload.group_schedule.authority_fingerprint
      ||!Array.isArray(standings.groups)
      ||standings.groups.length!==payload.group_schedule.group_count
      ||!Array.isArray(standings.tie_decisions))return false
    const members=new Set<string>()
    for(let i=0;i<standings.groups.length;i++){
      const group=standings.groups[i]
      if(group.group_index!==i+1||!Array.isArray(group.rows)
        ||group.rows.length!==payload.group_schedule.group_size)return false
      for(let j=0;j<group.rows.length;j++){
        const row=group.rows[j]
        if(row.position!==j+1||!row.player_id||members.has(row.player_id)
          ||(['wins','losses','group_points','played_matches','walkovers_received',
            'walkovers_conceded','games_won','games_lost','points_won','points_lost'] as const)
            .some(key=>{const n=row[key];return !Number.isInteger(n)||n<0}))
          return false
        members.add(row.player_id)
      }
    }
    const cases=new Set<string>()
    for(const decision of standings.tie_decisions){
      if(!Number.isInteger(decision.group_index)||decision.group_index<1
        ||decision.group_index>standings.groups.length
        ||!/^[0-9a-f]{64}$/.test(decision.case_fingerprint)
        ||cases.has(decision.case_fingerprint)
        ||!decision.admin_reason?.trim()
        ||!Array.isArray(decision.ordered_player_ids)
        ||decision.ordered_player_ids.length<2
        ||new Set(decision.ordered_player_ids).size!==decision.ordered_player_ids.length
        ||decision.ordered_player_ids.some(id=>
          !standings.groups[decision.group_index-1].rows.some(r=>r.player_id===id))
      )return false
      cases.add(decision.case_fingerprint)
    }
  }
  const groupsSchedule=payload.group_schedule
  if(groupsSchedule){
    if(groupsSchedule.schema_version!=='run_saved_tour_group_schedule.v1'
      ||groupsSchedule.source!=='saved_tournament_group_match_schedule_authority.v1'
      ||groupsSchedule.run_id!==runId
      ||groupsSchedule.revision_branch_id!==payload.revision_branch_id
      ||groupsSchedule.event_id!==eventId
      ||!/^[0-9a-f]{64}$/.test(groupsSchedule.authority_fingerprint)
      ||!Number.isInteger(groupsSchedule.group_count)||groupsSchedule.group_count<1
      ||!Number.isInteger(groupsSchedule.group_size)||groupsSchedule.group_size<2
      ||!Number.isInteger(groupsSchedule.match_day_count)||groupsSchedule.match_day_count<1
      ||!Array.isArray(groupsSchedule.matches)
      ||groupsSchedule.matches.length!==groupsSchedule.group_count
        *groupsSchedule.group_size*(groupsSchedule.group_size-1)/2)
      return false
    const matchIds=new Set<string>(),pairs=new Set<string>()
    for(const m of groupsSchedule.matches){
      const pair=m.group_index+':'+[m.top_player_id,m.bottom_player_id].sort().join('|')
      if(!m.match_id||matchIds.has(m.match_id)
        ||!Number.isInteger(m.group_index)||m.group_index<1||m.group_index>groupsSchedule.group_count
        ||!Number.isInteger(m.match_day_ordinal)||m.match_day_ordinal<1
        ||m.match_day_ordinal>groupsSchedule.match_day_count
        ||!Number.isInteger(m.match_order)||m.match_order<1
        ||!m.top_player_id||!m.bottom_player_id||m.top_player_id===m.bottom_player_id
        ||pairs.has(pair)||![3,5].includes(m.best_of))return false
      matchIds.add(m.match_id);pairs.add(pair)
    }
    const canonicalGroup=result?.matches.filter(m=>m.draw_type==='group')??[]
    if(canonicalGroup.some(m=>{
      const scheduled=groupsSchedule.matches.find(item=>item.match_id===m.match_id)
      return !scheduled||(m.loser_player_id!==null&&
        !((m.winner_player_id===scheduled.top_player_id&&m.loser_player_id===scheduled.bottom_player_id)
          ||(m.winner_player_id===scheduled.bottom_player_id&&m.loser_player_id===scheduled.top_player_id)))
    }))return false
  }
  // Audited intermediate decisions are not a final rank or a match result.
  // Read only if the original Saved Edition has a frozen group schedule and
  // does not already have completed canonical standings.
  const pending=payload.pending_group_tie_decisions
  if(pending!==undefined){
    if(!Array.isArray(pending)||
      (pending.length>0&&(!groupsSchedule||standings)))return false
    const cases=new Set<string>()
    for(const d of pending){
      if(!Number.isInteger(d.group_index)||!groupsSchedule
        ||d.group_index<1||d.group_index>groupsSchedule.group_count
        ||!/^[0-9a-f]{64}$/.test(d.case_fingerprint)
        ||cases.has(d.case_fingerprint)||!d.admin_reason?.trim()
        ||!Array.isArray(d.ordered_player_ids)||d.ordered_player_ids.length<2
        ||d.ordered_player_ids.length>groupsSchedule.group_size
        ||new Set(d.ordered_player_ids).size!==d.ordered_player_ids.length)
        return false
      const members=new Set(groupsSchedule.matches
        .filter(m=>m.group_index===d.group_index)
        .flatMap(m=>[m.top_player_id,m.bottom_player_id]))
      if(d.ordered_player_ids.some(id=>!id||!members.has(id)))return false
      cases.add(d.case_fingerprint)
    }
  }
  const schedule=payload.match_schedule
  if(schedule){
    if(schedule.schema_version!=='run_saved_tour_match_schedule.v1'
      ||schedule.source!=='saved_week_simulation_schedule.v2'
      ||schedule.run_id!==runId||schedule.revision_branch_id!==payload.revision_branch_id
      ||schedule.event_id!==eventId||schedule.season_index!==seasonIndex
      ||schedule.season_week!==payload.edition.season_week
      ||!Array.isArray(schedule.slots)
      ||!/^[0-9a-f]{64}$/.test(schedule.week_schedule_fingerprint))return false
    const groups=new Set<string>(),ordinals=new Set<number>()
    for(const slot of schedule.slots){
      if(!slot.group_id||groups.has(slot.group_id)||ordinals.has(slot.global_slot_ordinal)
        ||!Number.isInteger(slot.global_slot_ordinal)||slot.global_slot_ordinal<1
        ||!Number.isInteger(slot.match_day_ordinal)||slot.match_day_ordinal<1
        ||!Number.isInteger(slot.match_order)||slot.match_order<1
        ||!Number.isInteger(slot.round_number)||slot.round_number<1
        ||!['main','qualification','group'].includes(slot.draw_phase)
        ||(slot.match_id!==null&&!slot.match_id))return false
      groups.add(slot.group_id);ordinals.add(slot.global_slot_ordinal)
    }
  }
  return true
}

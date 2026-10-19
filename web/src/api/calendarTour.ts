import {tourWeekOffset} from './nativeTourCalendar'

export type TourWeek = {calendar:{schema_version:string;weeks_per_year:number;season_start_year_week:number;start_year:number;season_count:number};season_index:number;week:number}
export type TourResult = {edition_id:string;player_id:string;main_points:number;qualification_points:number;source_fingerprint:string;validity_weeks:number;completed_week:{season_index:number;week:number};first_publication_week:{season_index:number;week:number}}
export type TourContribution = TourResult & {status?:string}
export type TourSaveReceipt = {schema_version:'calendar_tour_save_receipt.v1';run_id:string;branch_id:string;saved_revision:{revision_id:string;run_id:string;branch_id:string;content_hash:string}}
export type TourPlayer = {run_id:string;branch_id:string;saved_head_revision_id:string;checkpoint_fingerprint:string;record:{player_id:string;attributes:[string,number][];current_form:number;match_sharpness:number;long_term_fatigue:number};lifecycle:null|{age:number;status:string}}
export type TourRanking = {week:{season_index:number;week:number};policy:{best_n:number;policy_id:string};rows:{rank:number;player_id:string;points:number;counted_results:TourResult[]}[]}
export type TourEdition = {
  edition:{edition_id:string;name:string;week:TourWeek;announcement_week:TourWeek;start_slot:number;main_entrant_count:number;point_table:Record<string,number>;validity_weeks:number}
  submissions:{application_id:string;player_id:string}[]
  field:{direct_main_player_ids:string[];below_qualification_cut_player_ids:string[]}|null
  draw:{main:{slots:{slot_index:number;player_id:string}[]}}|null
  tournament_fingerprint:string|null;result_confirmed:boolean
}
export type TourView = {schema_version:'calendar_tour_inspection.v1';run_id:string;branch_id:string;saved_head_revision_id:string;draft_version:number;run_calendar?:TourWeek['calendar'];checkpoint_fingerprint:string|null;tour_fingerprint:string|null;saved:boolean;can_initialize:boolean;players:{player_id:string;name:string;status?:string}[];transition_blockers:string[];season_transition_blockers:string[];saved_completed_seasons:number[];contributions?:Record<string,TourContribution[]>;edition_evidence:Record<string,{results:(TourResult&{stage:string})[];matches:{match_id:string;slot:number;player_a_id:string;player_b_id:string;winner_player_id:string;rally_count:number}[]}>;state:null|{week:TourWeek;editions:TourEdition[];rankings:TourRanking[];transitions:{public_event:Record<string,unknown>}[]}}
export type TourAction = 'initialize'|'create-edition'|'submit'|'approve'|'draw'|'play'|'confirm-result'|'policy'|'transition'|'season-transition'
export type TourCommand = {action:TourAction;command_id:string;expected_saved_head:string;expected_checkpoint_fingerprint:string;expected_tour_fingerprint:string|null;edition_id:string|null;seed:number;operator_label:string;audit_reason:string;data:Record<string,unknown>}
export type TourPreview = {schema_version:'calendar_tour_command_preview.v1';run_id:string;branch_id:string;command:TourCommand;preview_fingerprint:string;impact:{ranking?:TourRanking;sporting?:{changed_player_count:number;attribute_change_count:number;changes?:{player_id:string;changed_attributes:number;form_before:number;form_after:number;sharpness_before:number;sharpness_after:number;fatigue_before:number;fatigue_after:number}[]};target_week?:TourWeek;approved_field?:TourEdition['field'];draw?:TourEdition['draw'];results?:TourResult[];entrant_ids?:string[];point_table?:Record<string,number>}}

export function validateTourView(v:TourView,run:string,branch:string):TourView {
  if (v.schema_version!=='calendar_tour_inspection.v1'||v.run_id!==run||v.branch_id!==branch
    ||!v.saved_head_revision_id||!Array.isArray(v.players)||!Array.isArray(v.transition_blockers)||!Array.isArray(v.season_transition_blockers)||!Array.isArray(v.saved_completed_seasons)
    ||(v.state&&(!v.tour_fingerprint||!v.state.week||!Array.isArray(v.state.editions)||!Array.isArray(v.state.rankings)))) throw Error('Tour source scope is invalid')
  return v
}

export function validateTourPreview(v:TourPreview,c:TourCommand,run:string,branch:string):TourPreview {
  const same=Object.keys(c).every(k=>JSON.stringify(v.command?.[k as keyof TourCommand])===JSON.stringify(c[k as keyof TourCommand]))
  if (v.schema_version!=='calendar_tour_command_preview.v1'||v.run_id!==run||v.branch_id!==branch
    ||!same||!/^[0-9a-f]{64}$/.test(v.preview_fingerprint)) throw Error('Tour review does not match the requested inputs')
  return v
}

export type SignedSeasonCountry={country_code:string;titles:number;finals:number;semifinals:number;quarterfinals:number;awarded_points:number;distinct_players:number;edition_appearances:number}
export type SignedSeasonSummary={
  schema_version:'native_tour_signed_season_summary.v1';run_id:string;branch_id:string
  source_tour_fingerprint:string;season_index:number;season_label:string
  weeks_per_season:number;boundary_command_id:string;next_season_index:number
  completed_edition_count:number;countries:SignedSeasonCountry[]
  editions:{edition_id:string;name:string;week:number;champion_player_id:string;champion_name:string;champion_country:string;finalist_player_id:string;finalist_name:string;finalist_country:string;source_tournament_fingerprint:string}[]
  players:{player_id:string;name:string;country_code:string;titles:number;finals:number;awarded_points:number;edition_appearances:number}[]
  last_week_published_ranking:{week:number;source_fingerprint:string;top_players:{player_id:string;rank:number;points:number}[]}
}
export type TourSeasonComparison={
  schema_version:'calendar_tour_season_comparison.v1';run_id:string;branch_id:string;saved_head_revision_id:string
  selected:SignedSeasonSummary;comparison:SignedSeasonSummary|null
  country_deltas:{country_code:string;titles_delta:number;finals_delta:number;awarded_points_delta:number}[]
}
export function validateTourSeasonComparison(v:TourSeasonComparison,run:string,branch:string,head:string,season:number,compare:number|null):TourSeasonComparison{
  if(v.schema_version!=='calendar_tour_season_comparison.v1'||v.run_id!==run||v.branch_id!==branch
    ||v.saved_head_revision_id!==head||v.selected?.season_index!==season
    ||v.selected?.run_id!==run||v.selected?.branch_id!==branch
    ||!Array.isArray(v.selected.countries)||!Array.isArray(v.selected.editions)
    ||!Array.isArray(v.country_deltas)
    ||(compare===null?v.comparison!==null:v.comparison?.season_index!==compare))
    throw Error('Saved Season Summary source or requested comparison changed')
  return v
}

export type TourRecordMetric='titles'|'finals'|'awarded_points'
export type TourCareerRecords={
  schema_version:'calendar_tour_signed_records_response.v1';run_id:string;branch_id:string
  saved_head_revision_id:string;source_tour_fingerprint:string
  as_of_season_index:number;from_season_index:number
  country_code:string|null;leaderboard_limit:number
  completed_seasons:number[];completed_edition_count:number
  source_seasons:{season_index:number;season_label:string;boundary_command_id:string;completed_edition_count:number;source_tour_fingerprint:string;published_ranking_fingerprint:string}[]
  records:{
    record_id:string;scope:'player'|'country';metric:TourRecordMetric
    value:number
    holders:{entity_id:string;label:string;country_code:string;titles:number;finals:number;awarded_points:number}[]
    holder_history:{season_index:number;season_label:string;record_value:number;holder_ids:string[];holder_labels:string[];change:'established'|'improved'|'tied';boundary_command_id:string}[]
    leaderboard:{entity_id:string;label:string;country_code:string;titles:number;finals:number;awarded_points:number;rank:number}[]
    leaderboard_total:number
  }[]
}
export function validateTourCareerRecords(v:TourCareerRecords,run:string,branch:string,head:string,asOf:number,from:number,country:string|null):TourCareerRecords{
  if(v.schema_version!=='calendar_tour_signed_records_response.v1'
    ||v.run_id!==run||v.branch_id!==branch||v.saved_head_revision_id!==head
    ||v.as_of_season_index!==asOf||v.from_season_index!==from||v.country_code!==country
    ||!Array.isArray(v.completed_seasons)||!v.completed_seasons.includes(asOf)
    ||!Array.isArray(v.source_seasons)||!Array.isArray(v.records)
    ||v.records.length!==6
    ||v.records.some(r=>!Array.isArray(r.holders)||!Array.isArray(r.holder_history)||!Array.isArray(r.leaderboard)
      ||r.holder_history.some(h=>!Array.isArray(h.holder_labels)||h.holder_labels.length!==h.holder_ids.length
        ||h.holder_labels.some(name=>typeof name!=='string'||name.length===0))))
    throw Error('Signed Career Records source, request, or metric catalog changed')
  return v
}

export type NativeProspectIntakePreflight={
  schema_version:'native_tour_prospect_intake_preflight.v1'
  run_id:string;branch_id:string;saved_head_revision_id:string
  checkpoint_fingerprint:string;source_fingerprint:string|null;preflight_fingerprint:string
  target_week:{season_index:number;week:number}
  due:{player_id:string;display_name:string;country_code:string;profile_fingerprint:string}[]
  due_count:number;problems:{prospect_id:string;code:string}[]
  blocked:boolean;native_activation_supported:false
}
export function validateNativeProspectIntake(v:NativeProspectIntakePreflight,run:string,branch:string,head:string,checkpoint:string):NativeProspectIntakePreflight {
  if(v.schema_version!=='native_tour_prospect_intake_preflight.v1'
    ||v.run_id!==run||v.branch_id!==branch||v.saved_head_revision_id!==head
    ||v.checkpoint_fingerprint!==checkpoint||!/^[0-9a-f]{64}$/.test(v.preflight_fingerprint)
    ||v.native_activation_supported!==false||!Array.isArray(v.due)
    ||!Array.isArray(v.problems)||v.due_count!==v.due.length
    ||!v.target_week||!Number.isInteger(v.target_week.week)
    ||!Number.isInteger(v.target_week.season_index))
    throw Error('Native prospect intake source or Run Week changed')
  return v
}

/** Strong client check for the POST *read-only* native birth/Health/sporting review.
 * The server still owns proof of real Signed inputs and played matches. */
export type NativeSportingBirthPreviewRequest={
  expected_saved_head:string
  expected_checkpoint_fingerprint:string
  expected_tour_fingerprint:string
  seed:number
}
export type NativeSportingBirthPreflight=NativeProspectIntakePreflight&{
  sporting_week_projection:{
    schema_version:'native_tour_sporting_week_preflight.v1'
    seed:number
    source_saved_head:string
    played_player_count:number
    old_population_count:number
    new_population_count:number
    played_counts_fingerprint:string
    developed_players_fingerprint:string
    recovered_players_fingerprint:string
    target_players_fingerprint:string
    sporting_birth_advance_fingerprint:string
    signed_admission_week_fingerprint:string
    completed_week:TourWeek
    target_week:TourWeek
    signed_writer_supported:false
  }
}
export function validateNativeSportingBirthPreflight(
  value:NativeSportingBirthPreflight,
  run:string,branch:string,request:NativeSportingBirthPreviewRequest,current:TourWeek,
  targetCalendar:TourWeek['calendar']=current.calendar,
):NativeSportingBirthPreflight {
  const v=validateNativeProspectIntake(
    value,run,branch,request.expected_saved_head,request.expected_checkpoint_fingerprint,
  )
  const s=value.sporting_week_projection
  const target=tourWeekOffset({...current,calendar:targetCalendar},1)
  const sameWeek=(actual:TourWeek|undefined,expected:TourWeek|null)=>Boolean(
    actual&&expected&&actual.season_index===expected.season_index&&actual.week===expected.week
    &&actual.calendar&&(['schema_version','weeks_per_year','season_start_year_week','start_year','season_count'] as const)
      .every(key=>actual.calendar[key]===expected.calendar[key]),
  )
  const hash=(h:unknown)=>typeof h==='string'&&/^[0-9a-f]{64}$/.test(h)
  if(!s||s.schema_version!=='native_tour_sporting_week_preflight.v1'
    ||v.native_activation_supported!==false||v.blocked!==true
    ||v.problems.length!==0||v.due_count<1
    ||s.signed_writer_supported!==false
    ||s.source_saved_head!==request.expected_saved_head||s.seed!==request.seed
    ||!Number.isSafeInteger(s.seed)
    ||!Number.isSafeInteger(s.old_population_count)||s.old_population_count<1
    ||s.new_population_count!==s.old_population_count+v.due_count
    ||!Number.isSafeInteger(s.played_player_count)
    ||s.played_player_count<0||s.played_player_count>s.old_population_count
    ||!hash(s.played_counts_fingerprint)
    ||!hash(s.developed_players_fingerprint)
    ||!hash(s.recovered_players_fingerprint)
    ||!hash(s.target_players_fingerprint)
    ||!hash(s.sporting_birth_advance_fingerprint)
    ||!hash(s.signed_admission_week_fingerprint)
    ||!s.target_week||s.target_week.season_index!==v.target_week.season_index
    ||s.target_week.week!==v.target_week.week
    ||!sameWeek(s.completed_week,current)||!sameWeek(s.target_week,target))
    throw Error('Signed native sporting birth proposal differs from saved input or Run clock')
  return value
}

export type TourWeek = {calendar:{schema_version:string;weeks_per_year:number;season_start_year_week:number;start_year:number;season_count:number};season_index:number;week:number}
export type TourResult = {edition_id:string;player_id:string;main_points:number;qualification_points:number;source_fingerprint:string;validity_weeks:number;completed_week:{season_index:number;week:number};first_publication_week:{season_index:number;week:number}}
export type TourContribution = TourResult & {status?:string}
export type TourPlayer = {run_id:string;branch_id:string;saved_head_revision_id:string;checkpoint_fingerprint:string;record:{player_id:string;attributes:[string,number][];current_form:number;match_sharpness:number;long_term_fatigue:number};lifecycle:null|{age:number;status:string}}
export type TourRanking = {week:{season_index:number;week:number};policy:{best_n:number;policy_id:string};rows:{rank:number;player_id:string;points:number;counted_results:TourResult[]}[]}
export type TourEdition = {
  edition:{edition_id:string;name:string;week:TourWeek;announcement_week:TourWeek;start_slot:number;main_entrant_count:number;point_table:Record<string,number>;validity_weeks:number}
  submissions:{application_id:string;player_id:string}[]
  field:{direct_main_player_ids:string[];below_qualification_cut_player_ids:string[]}|null
  draw:{main:{slots:{slot_index:number;player_id:string}[]}}|null
  tournament_fingerprint:string|null;result_confirmed:boolean
}
export type TourView = {schema_version:'calendar_tour_inspection.v1';run_id:string;branch_id:string;saved_head_revision_id:string;draft_version:number;run_calendar?:TourWeek['calendar'];checkpoint_fingerprint:string|null;tour_fingerprint:string|null;saved:boolean;can_initialize:boolean;players:{player_id:string;name:string}[];transition_blockers:string[];contributions?:Record<string,TourContribution[]>;edition_evidence:Record<string,{results:(TourResult&{stage:string})[];matches:{match_id:string;slot:number;player_a_id:string;player_b_id:string;winner_player_id:string;rally_count:number}[]}>;state:null|{week:TourWeek;editions:TourEdition[];rankings:TourRanking[];transitions:{public_event:Record<string,unknown>}[]}}
export type TourAction = 'initialize'|'create-edition'|'submit'|'approve'|'draw'|'play'|'confirm-result'|'policy'|'transition'
export type TourCommand = {action:TourAction;command_id:string;expected_saved_head:string;expected_checkpoint_fingerprint:string;expected_tour_fingerprint:string|null;edition_id:string|null;seed:number;operator_label:string;audit_reason:string;data:Record<string,unknown>}
export type TourPreview = {schema_version:'calendar_tour_command_preview.v1';run_id:string;branch_id:string;command:TourCommand;preview_fingerprint:string;impact:{ranking?:TourRanking;sporting?:{changed_player_count:number;attribute_change_count:number;changes?:{player_id:string;changed_attributes:number;form_before:number;form_after:number;sharpness_before:number;sharpness_after:number;fatigue_before:number;fatigue_after:number}[]};target_week?:TourWeek;approved_field?:TourEdition['field'];draw?:TourEdition['draw'];results?:TourResult[];entrant_ids?:string[];point_table?:Record<string,number>}}

export function validateTourView(v:TourView,run:string,branch:string):TourView {
  if (v.schema_version!=='calendar_tour_inspection.v1'||v.run_id!==run||v.branch_id!==branch
    ||!v.saved_head_revision_id||!Array.isArray(v.players)||!Array.isArray(v.transition_blockers)
    ||(v.state&&(!v.tour_fingerprint||!v.state.week||!Array.isArray(v.state.editions)||!Array.isArray(v.state.rankings)))) throw Error('Tour source scope is invalid')
  return v
}

export function validateTourPreview(v:TourPreview,c:TourCommand,run:string,branch:string):TourPreview {
  const same=Object.keys(c).every(k=>JSON.stringify(v.command?.[k as keyof TourCommand])===JSON.stringify(c[k as keyof TourCommand]))
  if (v.schema_version!=='calendar_tour_command_preview.v1'||v.run_id!==run||v.branch_id!==branch
    ||!same||!/^[0-9a-f]{64}$/.test(v.preview_fingerprint)) throw Error('Tour review does not match the requested inputs')
  return v
}

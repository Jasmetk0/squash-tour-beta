import {clock,preview} from './calendarInitialPool.fixture'
import type {CalendarPopulation,CalendarPopulationRequest,CalendarPopulationReview} from './calendarPopulation'

export const population:CalendarPopulation={fingerprint:'c'.repeat(64),lifecycle_fingerprint:'d'.repeat(64),sporting_execution_supported:false,
  state:{schema_version:'initial_world_state.v2',run_id:'run-a',branch_id:'branch-a',run_calendar:clock,
    players:[{player_id:'p0',name:'Country 1',birth_year:2012,birth_year_week:1,
      age_years_at_season_start:18,age_weeks_at_season_start:970,active_status:'active'}]}}
export function reviewed(request:CalendarPopulationRequest):CalendarPopulationReview {
  return {schema_version:'calendar_initial_world_review.v2',preview_only:true,request,pool_preview:preview(),
    initial_world_fingerprint:population.fingerprint,lifecycle_fingerprint:population.lifecycle_fingerprint,
    player_count_before:0,player_count_after:1}
}
export const saveProof={run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'head-a',draft_version:2,
  initial_world_fingerprint:population.fingerprint,has_unsaved_changes:true,can_save:true}
export const saveReceipt={saved_revision:{revision_id:'saved-new',run_id:'run-a',branch_id:'branch-a',
  payload:{content:{initial_world:{fingerprint:population.fingerprint}}}},working_draft:{run_id:'run-a',branch_id:'branch-a',
    status:'clean',base_saved_revision_id:'saved-new'}}

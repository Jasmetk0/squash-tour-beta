import type { BoundaryOptions, BoundaryTarget } from './fullSimulationBoundaryTargets'
export const boundaryExample=(kind:BoundaryTarget['kind']='before_final'):BoundaryTarget=>({
 schema_version:'full_simulation_boundary_target.v1',kind,week:{season_index:0,week:1},schedule_fingerprint:'a'.repeat(64),
 slot_ordinal:kind==='after_tournament'?null:3,slot_id:kind==='after_tournament'?null:'week-0:slot:3',slot_kind:kind==='after_tournament'?null:'match',
 group_ids:kind==='after_tournament'?[]:['final-match'],event_id:kind==='before_slot'?null:'edition',edition_id:kind==='before_slot'?null:'edition',
 event_fingerprint:kind==='before_slot'?null:'b'.repeat(64),topology_fingerprint:kind==='before_final'?'c'.repeat(64):null,selector_fingerprint:'d'.repeat(64)
})
export const boundaryReview=():BoundaryOptions=>({schema_version:'full_simulation_boundary_options.v1',run_id:'run',branch_id:'branch',parent_command_id:'parent',week:{season_index:0,week:1},options:[boundaryExample()],unavailable:[{event_id:'unplanned',kind:'before_final',reason:'final_topology_not_frozen'}]})

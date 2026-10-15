export function taskExample(){return {schema_version:'full_simulation_task_view.v1',task_id:'task',run_id:'run',branch_id:'branch',parent_command_id:'parent',
 run_name:'World',branch_name:'Timeline 1',revision:1,desired_state:'queued',state:'recoverable',heartbeat_health:'inactive',heartbeat_unix:0,
 lease_expires_at_unix:null,checkpoint:null,progress:null,current_week:{season_index:0,week:1},error:null,needs_operator_action:true,
 original_command:{command_id:'parent',operator_label:'Operator',audit_reason:'Original intent',expected_start_week:{season_index:0,week:1},
 expected_position_fingerprint:'a'.repeat(64),expected_revision_id:'saved',expected_preview_fingerprint:'b'.repeat(64)},
 events:[{revision:1,previous:null as string|null,state:'queued',reason:'explicit_start',at_unix:1,fingerprint:'c'.repeat(64)}]}}

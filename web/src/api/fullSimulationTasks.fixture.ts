export function taskExample(){return {schema_version:'full_simulation_task_view.v1',task_id:'task',run_id:'run',branch_id:'branch',parent_command_id:'parent',
 run_name:'World',branch_name:'Timeline 1',revision:1,desired_state:'queued',state:'recoverable',heartbeat_health:'inactive',heartbeat_unix:0,
 lease_expires_at_unix:null,checkpoint:null,progress:null,current_week:{season_index:0,week:1},
 progress_evidence:{schema_version:'full_simulation_task_progress_evidence.v1',kind:'live_branch',week:{season_index:0,week:1},
  weeks_advanced_since_start:0,completed_slot_receipts_this_week:0,committed_group_receipts_this_week:0,receipt_scope:'branch_current_week'},
 error:null,needs_operator_action:true,
 original_command:{command_id:'parent',operator_label:'Operator',audit_reason:'Original intent',expected_start_week:{season_index:0,week:1},
 expected_position_fingerprint:'a'.repeat(64),expected_revision_id:'saved',expected_preview_fingerprint:'b'.repeat(64)},
 events:[{revision:1,previous:null as string|null,state:'queued',reason:'explicit_start',at_unix:1,fingerprint:'c'.repeat(64)}]}}

/** v2 read DTO; this does not claim that the legacy worker executes this clock. */
export function calendarTaskExample(calendar: import('./fullSimulationTasksCalendar').TaskCalendar) {
 const task=taskExample() as unknown as import('./fullSimulationTasks').ServerTask
 task.schema_version='full_simulation_task_view.v2'
 task.execution_calendar={...calendar}
 task.calendar_revision_id=task.original_command.expected_revision_id
 task.progress_evidence.schema_version='full_simulation_task_progress_evidence.v2'
 return task
}

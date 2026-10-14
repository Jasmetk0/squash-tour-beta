import { ApiError } from './client'
import type { AuthoritativeRankingWeek } from './types'

export type FullSimulationSummary = {
  schema_version: 'full_simulation_terminal_summary.v1'
  run_id: string; branch_id: string; command_id: string
  receipt_request_fingerprint: string; summary_fingerprint: string
  status: 'stopped' | 'target_reached'
  start_week: AuthoritativeRankingWeek; end_week: AuthoritativeRankingWeek
  original_final_week: AuthoritativeRankingWeek; effective_target_week: AuthoritativeRankingWeek
  target_revision: number; target_reached: boolean
  reason: 'operator_stop' | 'week_target_reached'
  terminal_control_command_id:string; terminal_operator_label:string; terminal_audit_reason:string
  initial_saved_revision_id: string; terminal_saved_revision_id: string
  persisted_child_command_count: number
  completed_tournaments: {event_id:string; edition_id:string; completed_week:AuthoritativeRankingWeek;
    champion_player_id:string|null; finalist_player_id:string|null;
    source_fingerprint:string; source_command_id:string}[]
  position: {run_id:string; branch_id:string; current_week:AuthoritativeRankingWeek; position_fingerprint:string}
  unavailable_sections: string[]
}
export type FullSimulationSummaryResponse = {
  schema_version: 'full_simulation_terminal_summary_response.v1'
  run_id:string; branch_id:string; command_id:string
  status:'pending'|'stopped'|'target_reached'|'abandoned'|'complete'
  available:boolean; summary:FullSimulationSummary|null
}

const hash = (value:unknown) => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)
const id = (value:unknown) => typeof value === 'string' && value.length > 0
const ordinal = (week:AuthoritativeRankingWeek) => week.season_index * 61 + week.week - 1
const validWeek = (week:AuthoritativeRankingWeek) => week &&
  Number.isInteger(week.season_index) && week.season_index >= 0 && week.season_index < 50 &&
  Number.isInteger(week.week) && week.week > 0 && week.week <= 61

export async function getFullSimulationSummary(runId:string, branchId:string, commandId:string):Promise<FullSimulationSummaryResponse> {
  const root = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
  const response = await fetch(`${root}/admin/runs/${encodeURIComponent(runId)}/branches/${encodeURIComponent(branchId)}/authoritative-simulation/full-simulation/parents/${encodeURIComponent(commandId)}/summary`)
  if (!response.ok) throw new ApiError(await response.text(), response.status)
  const data = await response.json() as FullSimulationSummaryResponse
  const scope = (v:{run_id:string;branch_id:string;command_id:string}) =>
    v.run_id === runId && v.branch_id === branchId && v.command_id === commandId
  if (!data || data.schema_version !== 'full_simulation_terminal_summary_response.v1' || !scope(data) ||
    !['pending','stopped','target_reached','abandoned','complete'].includes(data.status) ||
    typeof data.available !== 'boolean' || data.available !== (data.summary !== null)) {
    throw new Error('Full Simulation summary response is invalid.')
  }
  if (!data.available) return data
  const s = data.summary!
  if (!s || s.schema_version !== 'full_simulation_terminal_summary.v1' || !scope(s) ||
    s.status !== data.status || !['stopped','target_reached'].includes(s.status) ||
    !hash(s.summary_fingerprint) || !hash(s.receipt_request_fingerprint) ||
    ![s.start_week,s.end_week,s.original_final_week,s.effective_target_week].every(validWeek) ||
    s.original_final_week.season_index !== 49 || s.original_final_week.week !== 61 ||
    ordinal(s.end_week) < ordinal(s.start_week) || ordinal(s.effective_target_week) < ordinal(s.start_week) ||
    s.target_reached !== (s.status === 'target_reached') ||
    s.reason !== (s.target_reached ? 'week_target_reached' : 'operator_stop') ||
    (s.target_reached && ordinal(s.end_week) < ordinal(s.effective_target_week)) ||
    !Number.isInteger(s.target_revision) || s.target_revision < 0 ||
    !Number.isInteger(s.persisted_child_command_count) || s.persisted_child_command_count < 0 ||
    !id(s.initial_saved_revision_id) || !id(s.terminal_saved_revision_id) ||
    !id(s.terminal_control_command_id) || !id(s.terminal_operator_label) || !id(s.terminal_audit_reason) ||
    !s.position || s.position.run_id !== runId || s.position.branch_id !== branchId ||
    !validWeek(s.position.current_week) || ordinal(s.position.current_week) !== ordinal(s.end_week) ||
    !hash(s.position.position_fingerprint) || !Array.isArray(s.completed_tournaments) ||
    s.completed_tournaments.some(t => !id(t.event_id) || !id(t.edition_id) || !validWeek(t.completed_week) ||
      ordinal(t.completed_week) < ordinal(s.start_week) || ordinal(t.completed_week) > ordinal(s.end_week) ||
      !hash(t.source_fingerprint) || !id(t.source_command_id) ||
      !(t.champion_player_id === null || id(t.champion_player_id)) ||
      !(t.finalist_player_id === null || id(t.finalist_player_id))) ||
    new Set(s.completed_tournaments.map(t=>t.edition_id)).size !== s.completed_tournaments.length ||
    !Array.isArray(s.unavailable_sections) || s.unavailable_sections.some(v=>
      !['ranking_changes','watched_events','notifications'].includes(v))) {
    throw new Error('Full Simulation terminal summary is invalid.')
  }
  return data
}

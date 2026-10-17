/** Verified, read-only Run Home guidance. Does not authorize simulation. */
export type RunReadinessCode = 'world' | 'calendar_package' | 'population' | 'health'
  | 'official_ranking' | 'working_draft'
export type RunReadinessStatus = 'saved' | 'missing' | 'candidate_only' | 'unsaved' | 'optional'
export type RunReadinessItem = {
  code: RunReadinessCode
  status: RunReadinessStatus
  evidence_count: number
}
export type RunHomeReadiness = {
  schema_version: 'run_home_readiness.v1'
  run_id: string
  branch_id: string
  saved_revision_id: string
  saved_revision_content_hash: string
  draft_version: number
  run_status: string
  source: 'validated_selected_branch_saved_head'
  current_calendar: {
    schema_version: string; weeks_per_year: number; season_start_year_week: number
    start_year: number; season_count: number
  }
  phase: 'preparation' | 'sporting_history' | 'completed'
  items: RunReadinessItem[]
  saved_transition_count: number
  saved_published_ranking_count: number
  active_full_simulation_task_count: number
  historical_full_simulation_task_count: number
  sporting_calendar_supported_by_legacy_writers: boolean
  requires_operation_preflight: true
  simulation_started: false
}

const codes: RunReadinessCode[] = [
  'world', 'calendar_package', 'population', 'health', 'official_ranking', 'working_draft'
]
const statuses: RunReadinessStatus[] = ['saved', 'missing', 'candidate_only', 'unsaved', 'optional']

/** Reject partial/foreign/ambiguous responses rather than displaying false greens. */
export function validateRunHomeReadiness(raw: unknown, runId: string, branchId: string): RunHomeReadiness {
  const r = raw as RunHomeReadiness
  if (!r || r.schema_version !== 'run_home_readiness.v1'
    || r.run_id !== runId || r.branch_id !== branchId
    || r.source !== 'validated_selected_branch_saved_head'
    || !r.saved_revision_id || !/^[a-f0-9]{64}$/.test(r.saved_revision_content_hash)
    || !Number.isSafeInteger(r.draft_version) || r.draft_version < 0
    || !['preparation', 'sporting_history', 'completed'].includes(r.phase)
    || r.requires_operation_preflight !== true || r.simulation_started !== false
    || typeof r.sporting_calendar_supported_by_legacy_writers !== 'boolean'
    || !r.current_calendar || !Number.isSafeInteger(r.current_calendar.season_count)
    || !Number.isSafeInteger(r.current_calendar.weeks_per_year)
    || !Array.isArray(r.items) || r.items.length !== codes.length
    || r.items.some((item, i) => item?.code !== codes[i]
      || !statuses.includes(item.status)
      || !Number.isSafeInteger(item.evidence_count) || item.evidence_count < 0)
    || ![r.saved_transition_count, r.saved_published_ranking_count,
      r.active_full_simulation_task_count, r.historical_full_simulation_task_count]
      .every(x => Number.isSafeInteger(x) && x >= 0)
    || r.active_full_simulation_task_count > r.historical_full_simulation_task_count
  ) throw Error('Invalid Run Home readiness evidence')
  return r
}

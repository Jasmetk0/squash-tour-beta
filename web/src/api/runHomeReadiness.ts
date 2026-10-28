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
const countedSavedFoundations: RunReadinessCode[] = [
  'world', 'calendar_package', 'population', 'official_ranking'
]
const allowedStatus: Record<RunReadinessCode, readonly RunReadinessStatus[]> = {
  world: ['saved', 'missing'],
  calendar_package: ['saved', 'missing'],
  population: ['saved', 'missing'],
  health: ['saved', 'missing', 'optional'],
  official_ranking: ['saved', 'missing', 'candidate_only'],
  working_draft: ['saved', 'unsaved'],
}

/** Reject partial/foreign/ambiguous responses rather than displaying false greens. */
export function validateRunHomeReadiness(raw: unknown, runId: string, branchId: string): RunHomeReadiness {
  const r = raw as RunHomeReadiness
  if (!r || r.schema_version !== 'run_home_readiness.v1'
    || r.run_id !== runId || r.branch_id !== branchId
    || r.source !== 'validated_selected_branch_saved_head'
    || typeof r.saved_revision_id !== 'string' || !r.saved_revision_id.trim()
    || !/^[a-f0-9]{64}$/.test(r.saved_revision_content_hash)
    || !Number.isSafeInteger(r.draft_version) || r.draft_version < 0
    || !['preparation', 'sporting_history', 'completed'].includes(r.phase)
    || r.requires_operation_preflight !== true || r.simulation_started !== false
    || typeof r.sporting_calendar_supported_by_legacy_writers !== 'boolean'
    || !r.current_calendar || r.current_calendar.schema_version !== 'run_calendar.v1'
    || !Number.isSafeInteger(r.current_calendar.weeks_per_year) || r.current_calendar.weeks_per_year <= 0
    || !Number.isSafeInteger(r.current_calendar.season_start_year_week)
    || r.current_calendar.season_start_year_week < 1
    || r.current_calendar.season_start_year_week > r.current_calendar.weeks_per_year
    || !Number.isSafeInteger(r.current_calendar.start_year) || r.current_calendar.start_year < 0
    || !Number.isSafeInteger(r.current_calendar.season_count) || r.current_calendar.season_count <= 0
    || !Array.isArray(r.items) || r.items.length !== codes.length
    || r.items.some((item, i) => item?.code !== codes[i]
      || !statuses.includes(item.status) || !allowedStatus[item.code].includes(item.status)
      || !Number.isSafeInteger(item.evidence_count) || item.evidence_count < 0
      // The current Saved owner cannot publish or own a counted foundation
      // without a positive count. Reject contradictory 'saved' badges.
      || (countedSavedFoundations.includes(item.code)
        && item.status === 'saved' && item.evidence_count === 0)
      || (countedSavedFoundations.includes(item.code)
        && item.status !== 'saved' && item.evidence_count > 0))
    || ![r.saved_transition_count, r.saved_published_ranking_count,
      r.active_full_simulation_task_count, r.historical_full_simulation_task_count]
      .every(x => Number.isSafeInteger(x) && x >= 0)
    || r.active_full_simulation_task_count > r.historical_full_simulation_task_count
    // The backend derives both ranking counters from the same Saved
    // publication list. Divergence must never produce a false published badge.
    || r.saved_published_ranking_count !== r.items[4].evidence_count
    // The reference FAX writer is explicitly scoped to this exact clock.
    // The converse is intentionally not assumed for legacy read-time clocks.
    || (r.sporting_calendar_supported_by_legacy_writers && (
      r.current_calendar.weeks_per_year !== 61
      || r.current_calendar.season_start_year_week !== 37
      || r.current_calendar.start_year !== 2000
      || r.current_calendar.season_count !== 50))
  ) throw Error('Invalid Run Home readiness evidence')
  return r
}

import type { RunHomeReadiness } from '../api/runHomeReadiness'

/** Shared synthetic Saved-readiness contract for Run Home UI tests only.
 * Never used as runtime evidence or a fallback when the server cannot verify HEAD.
 */
export function runHomeReadinessFixture(
  runId = 'run-a', branchId = 'branch-a', overrides: Partial<RunHomeReadiness> = {}
): RunHomeReadiness {
  return {
    schema_version: 'run_home_readiness.v1',
    run_id: runId, branch_id: branchId, saved_revision_id: 'revision-a',
    saved_revision_content_hash: 'a'.repeat(64), draft_version: 1,
    source: 'validated_selected_branch_saved_head',
    run_status: 'working', phase: 'preparation',
    current_calendar: { schema_version: 'run_calendar.v1', weeks_per_year: 52,
      season_start_year_week: 35, start_year: 2030, season_count: 3 },
    items: [
      { code: 'world', status: 'saved', evidence_count: 250 },
      { code: 'calendar_package', status: 'missing', evidence_count: 0 },
      { code: 'population', status: 'saved', evidence_count: 1000 },
      { code: 'health', status: 'saved', evidence_count: 1 },
      { code: 'official_ranking', status: 'candidate_only', evidence_count: 0 },
      { code: 'working_draft', status: 'unsaved', evidence_count: 1 }
    ],
    saved_transition_count: 0,
    saved_published_ranking_count: 0,
    active_full_simulation_task_count: 0,
    historical_full_simulation_task_count: 0,
    sporting_calendar_supported_by_legacy_writers: false,
    requires_operation_preflight: true, simulation_started: false,
    ...overrides
  }
}

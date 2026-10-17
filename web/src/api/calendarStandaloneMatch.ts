/** Run-owned opening-week BO5 exhibition. Not a tournament or ranking publication. */
export type CalendarMatchView = {
  schema_version: 'calendar_standalone_match_inspection.v1'
  run_id: string
  branch_id: string
  run_calendar: { schema_version: string; weeks_per_year: number; season_start_year_week: number; start_year: number; season_count: number }
  saved_head_revision_id: string
  draft_version: number
  initial_world_fingerprint: string
  player_ids: string[]
  match: CalendarPlayedMatch | null
  match_fingerprint: string | null
  saved: boolean
}
export type CalendarPlayedMatch = {
  schema_version: 'calendar_standalone_match.v1'
  run_id: string; branch_id: string; match_id: string; command_id: string
  week: { season_index: number; week: number; calendar: CalendarMatchView['run_calendar'] }
  result: {
    winner_player_id: string; loser_player_id: string
    sets_won: Record<string, number>
    rally_log: { events: unknown[] }
    sets: { winner_games: number; loser_games: number; winner_player_id: string }[]
  }
}
export type CalendarMatchCommand = {
  command_id: string; match_id: string; expected_saved_head: string
  expected_initial_world_fingerprint: string
  player_a_id: string; player_b_id: string
  seed: number; operator_label: string; audit_reason: string
}
export type CalendarMatchReceipt = { match: CalendarPlayedMatch; fingerprint: string }
export type CalendarMatchSavePreview = {
  run_id: string; branch_id: string; calendar_match_fingerprint: string | null
  saved_head_revision_id: string; draft_version: number
  has_unsaved_changes: boolean; can_save: boolean
}
export type CalendarMatchReplay = {
  match_id: string; fingerprint: string
  exact_replay: boolean; rally_count: number
  result: CalendarPlayedMatch['result']
}

const hash = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{64}$/.test(v)

export function validateCalendarMatchView(value: unknown, runId: string, branchId: string, expectedHead: string): CalendarMatchView {
  const v = value as CalendarMatchView
  if (!v || v.schema_version !== 'calendar_standalone_match_inspection.v1'
    || v.run_id !== runId || v.branch_id !== branchId || v.saved_head_revision_id !== expectedHead
    || !Number.isSafeInteger(v.draft_version) || v.draft_version < 0
    || !hash(v.initial_world_fingerprint) || !Array.isArray(v.player_ids)
    || new Set(v.player_ids).size !== v.player_ids.length
    || !v.run_calendar || v.run_calendar.schema_version !== 'run_calendar.v1'
    || !Number.isSafeInteger(v.run_calendar.weeks_per_year)
    || v.run_calendar.weeks_per_year < 1
    || typeof v.saved !== 'boolean') throw Error('Calendar match response does not match the selected Saved Run/Branch/HEAD')
  if (v.match) {
    if (v.match.schema_version !== 'calendar_standalone_match.v1'
      || v.match.run_id !== runId || v.match.branch_id !== branchId
      || v.match.week.week !== 1 || v.match.week.season_index !== 0
      || v.match.week.calendar.weeks_per_year !== v.run_calendar.weeks_per_year
      || !hash(v.match_fingerprint)
      || !v.player_ids.includes(v.match.result.winner_player_id)
      || !v.player_ids.includes(v.match.result.loser_player_id)
      || !Array.isArray(v.match.result.rally_log?.events)) throw Error('Played calendar match source is inconsistent')
  } else if (v.match_fingerprint !== null || v.saved) throw Error('Unexpected saved calendar match without a played result')
  return v
}

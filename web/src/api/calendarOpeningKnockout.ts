/** A bounded real four-player knockout. Not a ranking/points/Week Transition. */
export type KnockoutMatch = {
  round: 'semifinal_1' | 'semifinal_2' | 'final'
  slot: 1 | 2
  seed: number
  result: { winner_player_id: string; loser_player_id: string; rally_log: { events: unknown[] }; sets_won: Record<string, number> }
  input_context: { match_id: string; player_a: { player: { player_id: string } }; player_b: { player: { player_id: string } } }
}
export type OpeningKnockout = {
  schema_version: 'calendar_opening_knockout.v1'
  run_id: string; branch_id: string; match_id: string
  week: { season_index: number; week: number; calendar: KnockoutInspection['run_calendar'] }
  entrant_ids: [string, string, string, string]
  matches: [KnockoutMatch, KnockoutMatch, KnockoutMatch]
}
export type KnockoutInspection = {
  schema_version: 'calendar_opening_knockout_inspection.v1'
  run_id: string; branch_id: string; saved_head_revision_id: string; draft_version: number
  run_calendar: { schema_version: string; weeks_per_year: number; season_start_year_week: number; start_year: number; season_count: number }
  initial_world_fingerprint: string
  player_ids: string[]
  knockout: OpeningKnockout | null
  knockout_fingerprint: string | null
  saved: boolean
  prepared_points: {
    policy: CalendarAwardPolicy
    awards: CalendarAwardEntry[]
    first_publication_week: { season_index: number; week: number; calendar: KnockoutInspection['run_calendar'] }
    publication_status: 'prepared_not_official'
    scored_fingerprint: string
  } | null
}
export type KnockoutCommand = {
  command_id: string; match_id: string; expected_saved_head: string
  expected_initial_world_fingerprint: string
  entrant_ids: [string, string, string, string]
  seed: number; operator_label: string; audit_reason: string
}
export type KnockoutReceipt = { knockout: OpeningKnockout; fingerprint: string }
export type KnockoutReplay = {
  match_id: string; fingerprint: string; exact_replay: boolean
  winner_player_id: string; rally_counts: number[]
}
export type KnockoutSavePreview = {
  run_id: string; branch_id: string; calendar_match_fingerprint: string | null
  saved_head_revision_id: string; draft_version: number
  has_unsaved_changes: boolean; can_save: boolean
}

const isHash = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{64}$/.test(v)

export function verifyKnockoutInspection(v: KnockoutInspection, runId: string, branchId: string, expectedHead: string): KnockoutInspection {
  if (!v || v.schema_version !== 'calendar_opening_knockout_inspection.v1'
    || v.run_id !== runId || v.branch_id !== branchId || v.saved_head_revision_id !== expectedHead
    || !isHash(v.initial_world_fingerprint)
    || !Array.isArray(v.player_ids) || new Set(v.player_ids).size !== v.player_ids.length
    || !Number.isSafeInteger(v.draft_version) || v.draft_version < 0
    || !v.run_calendar || v.run_calendar.schema_version !== 'run_calendar.v1'
    || !Number.isSafeInteger(v.run_calendar.weeks_per_year)
    || v.run_calendar.weeks_per_year < 1 || typeof v.saved !== 'boolean') {
    throw Error('Opening knockout response has changed Run/Branch/Saved HEAD')
  }
  if (v.knockout) {
    const k = v.knockout, [a, b, f] = k.matches ?? []
    if (k.schema_version !== 'calendar_opening_knockout.v1'
      || k.run_id !== runId || k.branch_id !== branchId
      || k.week.season_index !== 0 || k.week.week !== 1
      || k.week.calendar.weeks_per_year !== v.run_calendar.weeks_per_year
      || !isHash(v.knockout_fingerprint)
      || k.entrant_ids.length !== 4 || new Set(k.entrant_ids).size !== 4
      || k.entrant_ids.some(id => !v.player_ids.includes(id))
      || !a || !b || !f
      || a.round !== 'semifinal_1' || b.round !== 'semifinal_2' || f.round !== 'final'
      || a.slot !== 1 || b.slot !== 1 || f.slot !== 2
      || f.input_context.player_a.player.player_id !== a.result.winner_player_id
      || f.input_context.player_b.player.player_id !== b.result.winner_player_id
      || !k.matches.every(m => Array.isArray(m.result.rally_log?.events) && m.result.rally_log.events.length > 0)) {
      throw Error('Opening knockout is not a valid winner-fed three-match bracket')
    }
  } else if (v.saved || v.knockout_fingerprint !== null || v.prepared_points) {
    throw Error('Saved knockout component has no played result')
  }
  if (v.prepared_points) {
    const awards = v.prepared_points.awards
    if (!v.knockout || v.prepared_points.publication_status !== 'prepared_not_official'
      || v.prepared_points.scored_fingerprint !== v.knockout_fingerprint
      || !Array.isArray(awards) || awards.length !== 4
      || new Set(awards.map(a => a.player_id)).size !== 4
      || awards.some(a => !v.knockout!.entrant_ids.includes(a.player_id))
      || v.prepared_points.first_publication_week.week !== 2
      || v.prepared_points.first_publication_week.season_index !== 0) {
      throw Error('Knockout points are not authenticated prepared ranking facts')
    }
  }
  return v
}

export type CalendarAwardPolicy = {
  schema_version: 'calendar_knockout_point_policy.v1'
  source_kind: 'admin_explicit_reviewed'
  category_label: string
  champion: number
  finalist: number
  semifinal: number
  validity_weeks: number
}
export type CalendarAwardEntry = {
  player_id: string
  reached_stage: 'champion' | 'finalist' | 'semifinal'
  main_points: number
  source_knockout_fingerprint: string
  source_policy_fingerprint: string
}
export type CalendarAwardProposal = {
  expected_saved_head: string
  expected_knockout_fingerprint: string
  policy: CalendarAwardPolicy
  operator_label: string
  audit_reason: string
}
export type CalendarAwardReview = {
  schema_version: 'calendar_knockout_award_review.v1'
  run_id: string; branch_id: string; source_saved_head: string
  source_knockout_fingerprint: string
  first_publication_week: { season_index: number; week: number; calendar: KnockoutInspection['run_calendar'] }
  policy_fingerprint: string
  awards: CalendarAwardEntry[]
  preview_fingerprint: string
  publication_status: 'prepared_not_official'
}
export type CalendarAwardApplyCommand = {
  command_id: string
  proposal: CalendarAwardProposal
  expected_preview_fingerprint: string
  explicit_confirmation: true
}

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
  } else if (v.saved || v.knockout_fingerprint !== null) {
    throw Error('Saved knockout component has no played result')
  }
  return v
}

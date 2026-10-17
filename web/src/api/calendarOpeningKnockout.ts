/** A bounded real four-player knockout. Not a ranking/points/Week Transition. */
export type KnockoutHealthProfile = {
  player_id: string; highest_current_severity: number; highest_permanent_limitation: number
  numeric_effect_applied: false; numeric_calibration_required: boolean
  current_records: { record_id: string; condition_key: string; severity: number }[]
}
export type KnockoutHealthSource = {
  schema_version: 'calendar_knockout_health_source.v1'
  source_health_schema: string; source_health_fingerprint: string
  profiles: KnockoutHealthProfile[]; numeric_effect_applied: false
}
export type KnockoutMatch = {
  effective_health?: { numeric_effect_applied: false; player_profiles: KnockoutHealthProfile[] }
  round: 'semifinal_1' | 'semifinal_2' | 'final'
  slot: 1 | 2
  seed: number
  result: { winner_player_id: string; loser_player_id: string; rally_log: { events: unknown[] }; sets_won: Record<string, number> }
  input_context: { match_id: string; player_a: { player: { player_id: string } }; player_b: { player: { player_id: string } } }
}
export type KnockoutPlayerState = {
  player_id: string; current_form: number; match_sharpness: number; long_term_fatigue: number
}
export type KnockoutSportingState = {
  schema_version: 'calendar_knockout_sporting.v1'
  initial: KnockoutPlayerState[]; after_semifinals: KnockoutPlayerState[]; terminal: KnockoutPlayerState[]
  effects: { match_id: string; player_id: string; input_fingerprint: string; result_fingerprint: string; source_checkpoint_fingerprint: string }[]
  health_effects_applied: false; annual_development_applied: false
}
export type OpeningKnockout = {
  schema_version: 'calendar_opening_knockout.v1' | 'calendar_opening_knockout.v2' | 'calendar_opening_knockout.v3'
  run_id: string; branch_id: string; match_id: string
  week: { season_index: number; week: number; calendar: KnockoutInspection['run_calendar'] }
  entrant_ids: [string, string, string, string]
  matches: [KnockoutMatch, KnockoutMatch, KnockoutMatch]
  sporting?: KnockoutSportingState
  health_source?: KnockoutHealthSource
}
export type KnockoutInspection = {
  schema_version: 'calendar_opening_knockout_inspection.v1'
  run_id: string; branch_id: string; saved_head_revision_id: string; draft_version: number
  run_calendar: { schema_version: string; weeks_per_year: number; season_start_year_week: number; start_year: number; season_count: number }
  health_readiness?: {
    source_health_schema: string; source_health_fingerprint: string
    limited_player_ids: string[]; numeric_effect_applied: false
  } | null
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
    if (!['calendar_opening_knockout.v1', 'calendar_opening_knockout.v2', 'calendar_opening_knockout.v3'].includes(k.schema_version)
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
    if (k.schema_version !== 'calendar_opening_knockout.v1') {
      const state = k.sporting
      if (!state || state.schema_version !== 'calendar_knockout_sporting.v1'
        || state.health_effects_applied !== false || state.annual_development_applied !== false
        || ![state.initial, state.after_semifinals, state.terminal].every(stage =>
          Array.isArray(stage) && stage.length === 4 && new Set(stage.map(p => p.player_id)).size === 4
          && stage.every(p => k.entrant_ids.includes(p.player_id)
            && Number.isInteger(p.current_form) && p.current_form >= 0 && p.current_form <= 200
            && Number.isInteger(p.match_sharpness) && p.match_sharpness >= 0 && p.match_sharpness <= 100
            && Number.isInteger(p.long_term_fatigue) && p.long_term_fatigue >= 0 && p.long_term_fatigue <= 100))
        || !Array.isArray(state.effects) || state.effects.length !== 6
        || !state.effects.every(e => k.entrant_ids.includes(e.player_id)
          && isHash(e.input_fingerprint) && isHash(e.result_fingerprint) && isHash(e.source_checkpoint_fingerprint))) {
        throw Error('Knockout sporting checkpoints are incomplete or outside the entrant roster')
      }
    } else if (k.sporting !== undefined) {
      throw Error('Historical knockout cannot carry newer sporting checkpoints')
    }
    if (k.schema_version === 'calendar_opening_knockout.v3') {
      const source = k.health_source
      if (!source || source.schema_version !== 'calendar_knockout_health_source.v1'
        || !['calendar_initial_health_state.v1', 'player_health_calendar_state.v2'].includes(source.source_health_schema)
        || !isHash(source.source_health_fingerprint) || source.numeric_effect_applied !== false
        || !Array.isArray(source.profiles) || source.profiles.length !== 4
        || new Set(source.profiles.map(p => p.player_id)).size !== 4
        || !source.profiles.every(p => k.entrant_ids.includes(p.player_id)
          && p.numeric_effect_applied === false && typeof p.numeric_calibration_required === 'boolean'
          && Number.isInteger(p.highest_current_severity) && p.highest_current_severity >= 0 && p.highest_current_severity <= 100
          && Number.isInteger(p.highest_permanent_limitation) && p.highest_permanent_limitation >= 0 && p.highest_permanent_limitation <= 100
          && Array.isArray(p.current_records))
        || !k.matches.every(m => m.effective_health?.numeric_effect_applied === false
          && m.effective_health.player_profiles.length === 2
          && m.effective_health.player_profiles.every(p => p.numeric_effect_applied === false)
          && m.effective_health.player_profiles[0].player_id === m.input_context.player_a.player.player_id
          && m.effective_health.player_profiles[1].player_id === m.input_context.player_b.player.player_id)) {
        throw Error('Knockout Health does not match its Saved source and match participants')
      }
    } else if (k.health_source !== undefined || k.matches.some(m => m.effective_health !== undefined)) {
      throw Error('Historical knockout cannot acquire newer Health inputs')
    }
  } else if (v.saved || v.knockout_fingerprint !== null || v.prepared_points) {
    throw Error('Saved knockout component has no played result')
  }
  if (v.health_readiness && (!isHash(v.health_readiness.source_health_fingerprint)
    || v.health_readiness.numeric_effect_applied !== false
    || !Array.isArray(v.health_readiness.limited_player_ids)
    || v.health_readiness.limited_player_ids.some(id => !v.player_ids.includes(id)))) {
    throw Error('Knockout Health readiness has changed its population')
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

export type SignedKnockoutStandingsRow = {
  player_id: string
  player_name: string
  nationality: string
  tournament_place: number
  reached_stage: 'champion' | 'finalist' | 'semifinal'
  awarded_main_points: number
  as_of_counted_points: number
  points_rank: number | null
}
export type SignedKnockoutStandings = {
  schema_version: 'calendar_signed_knockout_standings.v1'
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  saved_head_content_hash: string
  source_knockout_fingerprint: string
  scored_evidence_fingerprint: string
  source_point_policy_fingerprint: string
  source_initial_world_fingerprint: string
  as_of: { calendar: KnockoutInspection['run_calendar']; season_index: number; week: number }
  source_completed_week: { calendar: KnockoutInspection['run_calendar']; season_index: number; week: number }
  proposed_first_publication_week: { calendar: KnockoutInspection['run_calendar']; season_index: number; week: number }
  expiration_week_exclusive: { season_index: number; week: number }
  validity_weeks: number
  rows: SignedKnockoutStandingsRow[]
  points_in_period: boolean
  publication_status: 'not_official_no_week_transition'
  official_ready: false
  blockers: string[]
  fingerprint: string
}

export function verifySignedKnockoutStandings(
  input: SignedKnockoutStandings,
  inspection: KnockoutInspection,
  seasonIndex: number, week: number,
): SignedKnockoutStandings {
  const players: string[] = inspection.knockout?.entrant_ids ?? []
  if (!input || input.schema_version !== 'calendar_signed_knockout_standings.v1'
    || input.run_id !== inspection.run_id
    || input.branch_id !== inspection.branch_id
    || input.saved_head_revision_id !== inspection.saved_head_revision_id
    || input.scored_evidence_fingerprint !== inspection.knockout_fingerprint
    || input.as_of.season_index !== seasonIndex || input.as_of.week !== week
    || input.as_of.calendar.weeks_per_year !== inspection.run_calendar.weeks_per_year
    || !inspection.saved || !inspection.prepared_points
    || input.publication_status !== 'not_official_no_week_transition'
    || input.official_ready !== false
    || !Array.isArray(input.blockers) || input.blockers.length < 3
    || !Array.isArray(input.rows) || input.rows.length !== 4
    || !/^[0-9a-f]{64}$/.test(input.fingerprint)
    || !/^[0-9a-f]{64}$/.test(input.saved_head_content_hash)
    || new Set(input.rows.map(r => r.player_id)).size !== 4
    || input.rows.some(r => !players.includes(r.player_id) || !Number.isSafeInteger(r.as_of_counted_points))
    || input.rows.some(r => r.as_of_counted_points !==
      (input.points_in_period ? r.awarded_main_points : 0))) {
    throw Error('Signed knockout standings do not match the selected Saved Run/Branch')
  }
  return input
}

export type ContinuationView = {
  schema_version: 'calendar_continuation_inspection.v1'; run_id: string; branch_id: string
  saved_head_revision_id: string; draft_version: number; checkpoint_fingerprint: string | null
  player_ids: string[]; saved: boolean; can_play: boolean; limited_player_ids: string[]
  sporting_week?: { calendar: { weeks_per_year: number; season_start_year_week: number; start_year: number; season_count: number }; season_index: number; week: number } | null
  weekly_advance_count?: number
  weekly_advances?: { command_id: string; fingerprint: string; completed_week: number; target_week: number; saved: boolean }[]
  health_numeric_effect_applied: false
  matches: { match_id: string; sequence: number; fingerprint: string; player_ids: [string, string]
    winner_player_id: string; rally_count: number; saved: boolean }[]
}
export type ContinuationCommand = {
  command_id: string; match_id: string; expected_saved_head: string; expected_checkpoint_fingerprint: string
  player_a_id: string; player_b_id: string; seed: number; operator_label: string; audit_reason: string
}
export type ContinuationReceipt = {
  fingerprint: string; checkpoint_fingerprint: string
  match: { match_id: string; sequence: number; source_saved_head: string; source_checkpoint_fingerprint: string
    result: { winner_player_id: string }; input_context: { player_a: { player: { player_id: string } }; player_b: { player: { player_id: string } } }
    canonical_projections: { player_id: string; current_form: number; match_sharpness: number; long_term_fatigue: number }[] }
}
export function verifyContinuation(v: ContinuationView, run: string, branch: string, head: string) {
  const hash = (s: unknown) => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s)
  if (!v || v.schema_version !== 'calendar_continuation_inspection.v1' || v.run_id !== run || v.branch_id !== branch
    || v.saved_head_revision_id !== head || !Number.isSafeInteger(v.draft_version) || v.draft_version < 0
    || !Array.isArray(v.player_ids) || new Set(v.player_ids).size !== v.player_ids.length
    || typeof v.saved !== 'boolean' || typeof v.can_play !== 'boolean' || (v.can_play && !v.saved)
    || (v.checkpoint_fingerprint !== null && !hash(v.checkpoint_fingerprint))
    || ((v.saved || v.can_play) && !v.checkpoint_fingerprint)
    || v.health_numeric_effect_applied !== false || !Array.isArray(v.limited_player_ids)
    || v.limited_player_ids.some(p => !v.player_ids.includes(p)) || !Array.isArray(v.matches)
    || new Set(v.matches.map(m => m.match_id)).size !== v.matches.length
    || v.matches.some((m, i) => m.sequence !== i + 1 || !hash(m.fingerprint)
      || m.player_ids.length !== 2 || new Set(m.player_ids).size !== 2
      || m.player_ids.some(p => !v.player_ids.includes(p)) || !m.player_ids.includes(m.winner_player_id)
      || !Number.isSafeInteger(m.rally_count) || m.rally_count < 1 || typeof m.saved !== 'boolean'
      || (v.saved && !m.saved))) throw Error('Continuation source/history changed')
  if (v.sporting_week) {
    const w = v.sporting_week
    if (!Number.isSafeInteger(w.week) || w.week < 1 || w.week > w.calendar.weeks_per_year
      || w.season_index !== 0 || !Number.isSafeInteger(v.weekly_advance_count) || v.weekly_advance_count! < 0
      || !Array.isArray(v.weekly_advances) || v.weekly_advances.length !== v.weekly_advance_count
      || v.weekly_advances.length !== w.week - 1
      || v.weekly_advances.some((a, i) => !hash(a.fingerprint) || a.completed_week !== i + 1 || a.target_week !== i + 2
        || typeof a.saved !== 'boolean' || (v.saved && !a.saved))) throw Error('Sporting week source/history changed')
  }
  return v
}

export type SportingWeekCommand = { command_id: string; expected_saved_head: string; expected_checkpoint_fingerprint: string
  seed: number; operator_label: string; audit_reason: string }
export type SportingWeekPreview = { schema_version: 'calendar_sporting_week_preview.v1'; preview_fingerprint: string
  advance_fingerprint: string; checkpoint_fingerprint: string; player_count: number; changed_player_count: number; attribute_change_count: number
  changes: { player_id: string; changed_attributes: number; form_before: number; form_after: number; sharpness_before: number; sharpness_after: number; fatigue_before: number; fatigue_after: number }[]
  advance: { run_id: string; branch_id: string; command_id: string; source_saved_head: string; source_checkpoint_fingerprint: string
    completed_week: NonNullable<ContinuationView['sporting_week']>; target_week: NonNullable<ContinuationView['sporting_week']>
    policy: { policy_id: string }; scope: 'sporting_only_exhibition_timeline' } }
export function verifySportingWeek(v: SportingWeekPreview, command: SportingWeekCommand, source: ContinuationView) {
  const a = v?.advance, w = source.sporting_week
  const hash = (s: unknown) => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s)
  if (!v || v.schema_version !== 'calendar_sporting_week_preview.v1' || !a || !w
    || !hash(v.preview_fingerprint) || !hash(v.advance_fingerprint) || !hash(v.checkpoint_fingerprint)
    || a.run_id !== source.run_id || a.branch_id !== source.branch_id || a.command_id !== command.command_id
    || a.source_saved_head !== source.saved_head_revision_id || a.source_checkpoint_fingerprint !== source.checkpoint_fingerprint
    || a.scope !== 'sporting_only_exhibition_timeline' || a.policy.policy_id !== 'calendar-annual-development.provisional.v1'
    || a.completed_week.week !== w.week || a.target_week.week !== w.week + 1
    || a.completed_week.season_index !== w.season_index || a.target_week.season_index !== w.season_index
    || Object.entries(w.calendar).some(([k, n]) => a.completed_week.calendar[k as keyof typeof w.calendar] !== n || a.target_week.calendar[k as keyof typeof w.calendar] !== n)
    || !Number.isSafeInteger(v.changed_player_count) || v.changed_player_count < 0 || v.changed_player_count > source.player_ids.length
    || v.player_count !== source.player_ids.length || !Array.isArray(v.changes) || v.changes.length !== v.changed_player_count
    || new Set(v.changes.map(c => c.player_id)).size !== v.changes.length || v.changes.some(c => !source.player_ids.includes(c.player_id))
    || !Number.isSafeInteger(v.attribute_change_count) || v.attribute_change_count < 0) throw Error('Weekly preview source changed')
  return v
}

export type ContinuationView = {
  schema_version: 'calendar_continuation_inspection.v1'; run_id: string; branch_id: string
  saved_head_revision_id: string; draft_version: number; checkpoint_fingerprint: string | null
  player_ids: string[]; saved: boolean; can_play: boolean; limited_player_ids: string[]
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
  return v
}

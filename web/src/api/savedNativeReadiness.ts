/** Read-only contracts for the Saved FAX Draw native-readiness inspections. */
export type SavedDrawPreflight = {
  saved_revision_id: string
  source_plan_fingerprint: string
  draw_fingerprint: string
  ranking_status: 'ranked' | 'unranked'
  point_table_status: 'complete' | 'incomplete' | 'not_required'
  required_point_stages: string[]
  missing_point_stages: string[]
  invalid_point_stages: string[]
  native_execution_status:
    | 'ranked_not_supported'
    | 'ranked_points_incomplete'
    | 'requires_adoption_preview'
}

export type SavedDrawFirstEntryTrigger = {
  schema_version: string
  run_id: string
  branch_id: string
  player_id: string
  event_id: string
  trigger_kind: 'valid_tournament_application' | 'definitive_wild_card_assignment'
  trigger_week: { season_index: number; week: number }
  decision_slot_ordinal: number
  source_evidence_id: string
  source_evidence_fingerprint: string
  provenance: string
}

export type SavedDrawEntrant = {
  player_id: string
  draw_role: 'direct_main' | 'qualification' | 'wild_card'
  first_entry: SavedDrawFirstEntryTrigger | null
}

export type SavedDrawEntryEvidence = {
  saved_revision_id: string
  source_plan_fingerprint: string
  event_id: string
  entrants: SavedDrawEntrant[]
}

const SHA = /^[0-9a-f]{64}$/
const ROLES = ['direct_main', 'qualification', 'wild_card']
/** The only first-entry trigger contracts the backend defines (`PlayerTourEntryTrigger`). */
const TRIGGER_SCHEMAS = ['player_tour_entry_trigger.v1', 'player_tour_entry_trigger.v2']
const KINDS = ['valid_tournament_application', 'definitive_wild_card_assignment']
const sha = (v: unknown): v is string => typeof v === 'string' && SHA.test(v)
const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0
const stages = (v: unknown): v is string[] =>
  Array.isArray(v) && v.every(text) && new Set(v).size === v.length

/** Reject any response that is not exactly the requested Saved owner. */
export function validSavedDrawPreflight(
  data: SavedDrawPreflight | null | undefined, revisionId: string
): data is SavedDrawPreflight {
  if (!data || data.saved_revision_id !== revisionId) return false
  if (!sha(data.source_plan_fingerprint) || !sha(data.draw_fingerprint)) return false
  if (!['ranked', 'unranked'].includes(data.ranking_status)) return false
  if (!['complete', 'incomplete', 'not_required'].includes(data.point_table_status)) return false
  if (![
    'ranked_not_supported', 'ranked_points_incomplete', 'requires_adoption_preview'
  ].includes(data.native_execution_status)) return false
  if (!stages(data.required_point_stages) || !stages(data.missing_point_stages) ||
    !stages(data.invalid_point_stages)) return false
  const required = new Set(data.required_point_stages)
  if (![...data.missing_point_stages, ...data.invalid_point_stages].every(s => required.has(s))) {
    return false
  }
  // An unranked Draw never needs a table; a ranked one is complete only without gaps.
  const gaps = data.missing_point_stages.length + data.invalid_point_stages.length
  if (data.ranking_status === 'unranked') {
    return data.point_table_status === 'not_required' && required.size === 0 &&
      data.native_execution_status === 'requires_adoption_preview'
  }
  // A Ranked Draw always has point stages to score; an empty list is not 'complete'.
  if (required.size === 0) return false
  if (data.point_table_status !== (gaps ? 'incomplete' : 'complete')) return false
  // Gaps can only be reported as unsupported or incomplete, never as ready for preview.
  return !(gaps && data.native_execution_status === 'requires_adoption_preview') &&
    !(!gaps && data.native_execution_status === 'ranked_points_incomplete')
}

export function validSavedDrawEntryEvidence(
  data: SavedDrawEntryEvidence | null | undefined, revisionId: string, eventId: string,
  scope: { runId: string; branchId: string }
): data is SavedDrawEntryEvidence {
  if (!data || data.saved_revision_id !== revisionId || data.event_id !== eventId) return false
  if (!sha(data.source_plan_fingerprint) || !Array.isArray(data.entrants)) return false
  const seen = new Set<string>()
  for (const row of data.entrants) {
    if (!row || !text(row.player_id) || seen.has(row.player_id)) return false
    seen.add(row.player_id)
    if (!ROLES.includes(row.draw_role)) return false
    const t = row.first_entry
    if (t === null) continue
    if (!t || !TRIGGER_SCHEMAS.includes(t.schema_version) || t.run_id !== scope.runId || t.branch_id !== scope.branchId ||
      t.player_id !== row.player_id || !text(t.event_id) ||
      !KINDS.includes(t.trigger_kind) || !sha(t.source_evidence_fingerprint) ||
      !text(t.source_evidence_id) || !t.trigger_week ||
      !Number.isInteger(t.trigger_week.season_index) || t.trigger_week.season_index < 0 ||
      !Number.isInteger(t.trigger_week.week) || t.trigger_week.week < 1 ||
      !Number.isInteger(t.decision_slot_ordinal) || t.decision_slot_ordinal < 1) return false
  }
  return true
}

/** The two inspections must describe the same authenticated Draw source. */
export function sameSavedDrawSource(
  preflight: SavedDrawPreflight, evidence: SavedDrawEntryEvidence
): boolean {
  return preflight.saved_revision_id === evidence.saved_revision_id &&
    preflight.source_plan_fingerprint === evidence.source_plan_fingerprint
}

/** Read-only contract of the native player career (milestones and timeline). */
export type CareerSource = { kind: string; fingerprint: string; [key: string]: unknown }
export type CareerWeek = { season_index: number; week: number }
export type CareerEvent = {
  kind: string
  effective_week: CareerWeek | null
  detail: Record<string, unknown>
  source: CareerSource
}
export type SavedPlayerCareer = {
  schema_version: 'native_player_career.v1'
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  source_tour_fingerprint: string
  as_of_ordinal: number
  player: { player_id: string; name: string; country_code: string }
  covered_period: { first_recorded_ranking_ordinal: number; note: string }
  overview: {
    status: 'professional' | 'not_professional' | 'retired'
    titles: number
    finals: number
    editions_played: number
    career_high_rank: number | null
    current_rank: number | null
  }
  milestones: CareerEvent[]
  timeline: CareerEvent[]
  /** Present only when the player retired at or before the viewed week. */
  retirement_summary?: RetirementSummary | null
  unsupported: string[]
}
export type RetirementSummary = {
  retired_week: CareerWeek; turn_pro_rule: boolean
  without_turn_pro: boolean | null; without_tour_entry: boolean | null
  opening_professional: boolean; entry_week: CareerWeek | null
  titles: number; finals: number; editions_played: number
  first_recorded_title_week: CareerWeek | null; career_high_rank: number | null
  source: CareerSource; note: string
}

/** Kinds that can appear in the timeline; a milestone may also be a first recorded title. */
export const CAREER_KINDS = [
  'turn_pro', 'first_top_rank', 'career_high_ranking', 'edition_result', 'retirement'
] as const
export const MILESTONE_KINDS = [...CAREER_KINDS, 'first_recorded_title'] as const
const STATUSES = ['professional', 'not_professional', 'retired']
const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0
const count = (v: unknown): v is number => Number.isInteger(v) && (v as number) >= 0
const rank = (v: unknown): boolean => v === null || (Number.isInteger(v) && (v as number) >= 1)

function validEvent(e: CareerEvent | null | undefined, kinds: readonly string[]): boolean {
  if (!e || !kinds.includes(e.kind) || !e.detail || typeof e.detail !== 'object') return false
  const w = e.effective_week
  // Only an opening professional has no week (its history precedes the Run).
  if (w === null) {
    if (e.kind !== 'turn_pro') return false
  } else if (!w || !count(w.season_index) || !Number.isInteger(w.week) || w.week < 1) return false
  return Boolean(e.source) && text(e.source.kind) && text(e.source.fingerprint)
}

/** Exact Run/Branch/Saved HEAD/player scope; anything else is never displayed. */
export function validSavedPlayerCareer(
  data: SavedPlayerCareer | null | undefined, scope: {
    runId: string; branchId: string; savedHead: string; playerId: string
  }
): data is SavedPlayerCareer {
  if (!data || data.schema_version !== 'native_player_career.v1') return false
  if (data.run_id !== scope.runId || data.branch_id !== scope.branchId ||
    data.saved_head_revision_id !== scope.savedHead ||
    data.player?.player_id !== scope.playerId) return false
  if (!count(data.as_of_ordinal) || !text(data.source_tour_fingerprint)) return false
  const o = data.overview
  if (!o || !STATUSES.includes(o.status) || !count(o.titles) || !count(o.finals) ||
    !count(o.editions_played) || !rank(o.career_high_rank) || !rank(o.current_rank)) return false
  if (!data.covered_period || !text(data.covered_period.note) ||
    !count(data.covered_period.first_recorded_ranking_ordinal)) return false
  if (!Array.isArray(data.timeline) || !Array.isArray(data.milestones) ||
    !Array.isArray(data.unsupported)) return false
  if (!data.timeline.every(e => validEvent(e, CAREER_KINDS))) return false
  const r = data.retirement_summary
  if (r !== undefined && r !== null) {
    // A summary exists exactly for a retired player and is backed by a retirement fact.
    if (o.status !== 'retired' || !count(r.titles) || !count(r.finals) || !count(r.editions_played) ||
      !rank(r.career_high_rank) || !text(r.source?.fingerprint) || !r.retired_week ||
      !data.timeline.some(t => t.kind === 'retirement' && t.source.fingerprint === r.source.fingerprint)) return false
  } else if (o.status === 'retired') return false
  // Milestones are a selection of recorded facts, never an independent source.
  return data.milestones.every(m => validEvent(m, MILESTONE_KINDS) &&
    data.timeline.some(t => t.source.fingerprint === m.source.fingerprint &&
      t.source.kind === m.source.kind &&
      (t.kind === m.kind || (m.kind === 'first_recorded_title' &&
        t.kind === 'edition_result' && t.detail.reached_stage === 'champion')) &&
      JSON.stringify(t.detail) === JSON.stringify(m.detail) &&
      JSON.stringify(t.effective_week) === JSON.stringify(m.effective_week)))
}

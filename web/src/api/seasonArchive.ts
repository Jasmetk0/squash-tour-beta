/** Read-only seasonal archive and presence-aware comparison (native Tour). */
export type SeasonRules = {
  ranking_policy_id: string; ranking_best_n: number
  development_policy_fingerprint: string; weeks_per_season: number
}
export type SeasonOverview = {
  completed_edition_count: number; players_with_results: number
  countries_represented: number; titles_awarded: number
  turned_pro: string[]; retired: string[]; no_completed_editions: boolean
  rankings: {
    week_w_published_fingerprint: string; season_closing_ranking_available: boolean
    next_season_week_1_fingerprint: string | null
  }
}
export type SeasonArchiveRow = {
  season_index: number; season_label: string; boundary_command_id: string
  source_tour_fingerprint: string; rules: SeasonRules; overview: SeasonOverview
  leading_player: { player_id: string; name: string; country_code: string; titles: number; awarded_points: number } | null
  leading_country: { country_code: string; titles: number; finals: number; awarded_points: number } | null
}
export type SeasonArchive = {
  schema_version: 'native_tour_season_archive.v1'; run_id: string; branch_id: string
  saved_head_revision_id: string; source_tour_fingerprint: string; seasons: SeasonArchiveRow[]
}
type Metrics = { titles: number; finals: number; awarded_points: number }
export type PresenceRow = {
  presence: 'both' | 'only_selected' | 'only_comparison'
  selected: Metrics | null; comparison: Metrics | null; delta: Metrics | null
  country_code?: string; player_id?: string
}
export type SeasonDetail = {
  schema_version: 'native_tour_season_comparison_detail.v1'
  selected_season_index: number; comparison_season_index: number
  selected_overview: SeasonOverview; comparison_overview: SeasonOverview
  comparability: {
    comparable: boolean; compared_fields: string[]; not_compared: string[]
    differences: { field: string; selected: unknown; comparison: unknown }[]
  }
  countries: PresenceRow[]; players: PresenceRow[]; note: string
}
export type SeasonDetailResponse = {
  schema_version: 'calendar_tour_season_comparison.v1'; run_id: string; branch_id: string
  saved_head_revision_id: string; overview: SeasonOverview; detail?: SeasonDetail
  selected: { season_index: number }
}

const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0
const count = (v: unknown): v is number => Number.isInteger(v) && (v as number) >= 0
const metrics = (m: Metrics | null) => m !== null && count(m.titles) && count(m.finals) && count(m.awarded_points)

function validOverview(o: SeasonOverview | undefined): boolean {
  return Boolean(o) && count(o!.completed_edition_count) && count(o!.players_with_results) &&
    count(o!.countries_represented) && count(o!.titles_awarded) &&
    Array.isArray(o!.turned_pro) && Array.isArray(o!.retired) &&
    typeof o!.no_completed_editions === 'boolean' &&
    o!.no_completed_editions === (o!.completed_edition_count === 0) && text(o!.rankings?.week_w_published_fingerprint)
}

export function validSeasonArchive(
  data: SeasonArchive | null | undefined, scope: { runId: string; branchId: string; savedHead: string }
): data is SeasonArchive {
  if (!data || data.schema_version !== 'native_tour_season_archive.v1' ||
    data.run_id !== scope.runId || data.branch_id !== scope.branchId ||
    data.saved_head_revision_id !== scope.savedHead || !Array.isArray(data.seasons)) return false
  let last = -1
  for (const s of data.seasons) {
    if (!s || !Number.isInteger(s.season_index) || s.season_index <= last) return false
    last = s.season_index
    if (!text(s.season_label) || !validOverview(s.overview) || !s.rules ||
      !count(s.rules.ranking_best_n) || !text(s.rules.ranking_policy_id)) return false
  }
  return true
}

/** A delta must exist exactly when both seasons contain the entity; absence is never zero. */
function validRows(rows: PresenceRow[], key: 'country_code' | 'player_id'): boolean {
  if (!Array.isArray(rows)) return false
  const seen = new Set<string>()
  for (const r of rows) {
    const id = r?.[key]
    if (!text(id) || seen.has(id)) return false
    seen.add(id)
    const both = r.presence === 'both'
    if (!['both', 'only_selected', 'only_comparison'].includes(r.presence)) return false
    if ((r.selected !== null) !== (r.presence !== 'only_comparison') ||
      (r.comparison !== null) !== (r.presence !== 'only_selected')) return false
    if (both !== (r.delta !== null)) return false
    if (r.selected !== null && !metrics(r.selected)) return false
    if (r.comparison !== null && !metrics(r.comparison)) return false
    if (r.delta !== null && (!Number.isInteger(r.delta.titles) || !Number.isInteger(r.delta.awarded_points))) return false
  }
  return true
}

export function validSeasonDetail(
  data: SeasonDetailResponse | null | undefined,
  scope: { runId: string; branchId: string; savedHead: string; season: number; compareTo: number }
): data is SeasonDetailResponse & { detail: SeasonDetail } {
  if (!data || data.schema_version !== 'calendar_tour_season_comparison.v1' ||
    data.run_id !== scope.runId || data.branch_id !== scope.branchId ||
    data.saved_head_revision_id !== scope.savedHead) return false
  const d = data.detail
  if (!d || d.schema_version !== 'native_tour_season_comparison_detail.v1' ||
    d.selected_season_index !== scope.season || d.comparison_season_index !== scope.compareTo) return false
  if (!validOverview(d.selected_overview) || !validOverview(d.comparison_overview)) return false
  const c = d.comparability
  if (!c || typeof c.comparable !== 'boolean' || !Array.isArray(c.differences) ||
    c.comparable !== (c.differences.length === 0)) return false
  return validRows(d.countries, 'country_code') && validRows(d.players, 'player_id')
}

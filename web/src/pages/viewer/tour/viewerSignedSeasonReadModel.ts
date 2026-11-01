import type { SignedSeasonSummary, TourCareerRecords, TourSeasonComparison } from '../../../api/calendarTour'

const positiveId = (v: unknown): v is string => typeof v === 'string' && v.trim().length > 0
const whole = (v: unknown, min = 0): v is number =>
  typeof v === 'number' && Number.isSafeInteger(v) && v >= min

export function verifiedSignedSeasonBranch(context: unknown, runId: string): string | null {
  if (!context || typeof context !== 'object' || !positiveId(runId)) return null
  const value = context as { product_run_id?: unknown; official_branch_id?: unknown }
  return value.product_run_id === runId && positiveId(value.official_branch_id) ?
    value.official_branch_id : null
}

/** Readable dates are ONLY from authenticated completed-season response, never predicted. */
export function verifiedSignedSeasonList(
  source: unknown, runId: string, branchId: string
): { savedHead: string; seasons: { index: number; label: string }[] } | null {
  if (!source || typeof source !== 'object') return null
  const v = source as TourCareerRecords
  if (v.schema_version !== 'calendar_tour_signed_records_response.v1' ||
    v.run_id !== runId || v.branch_id !== branchId ||
    !positiveId(v.saved_head_revision_id) || !positiveId(v.source_tour_fingerprint) ||
    !Array.isArray(v.completed_seasons) || !Array.isArray(v.source_seasons) ||
    v.completed_seasons.length === 0 ||
    v.source_seasons.length !== v.completed_seasons.length ||
    v.country_code !== null || v.from_season_index !== 0 ||
    v.leaderboard_limit !== 20 ||
    v.as_of_season_index !== v.completed_seasons[v.completed_seasons.length - 1]) return null

  const seasons: { index: number; label: string }[] = []
  let last = -1
  for (let i = 0; i < v.completed_seasons.length; i++) {
    const index = v.completed_seasons[i], sourceSeason = v.source_seasons[i]
    if (!whole(index) || index <= last || !sourceSeason ||
      sourceSeason.season_index !== index ||
      !positiveId(sourceSeason.season_label) || !positiveId(sourceSeason.boundary_command_id) ||
      !positiveId(sourceSeason.source_tour_fingerprint) ||
      !positiveId(sourceSeason.published_ranking_fingerprint) ||
      !whole(sourceSeason.completed_edition_count)) return null
    seasons.push({ index, label: sourceSeason.season_label })
    last = index
  }
  if (seasons[0].index !== 0) return null // public default from_season_index=0
  return { savedHead: v.saved_head_revision_id, seasons }
}

function validSummary(
  summary: SignedSeasonSummary, runId: string, branchId: string, seasonIndex: number
): boolean {
  if (!summary || (summary.schema_version !== 'native_tour_signed_season_summary.v1' &&
    summary.schema_version !== 'native_tour_signed_season_summary.v2') ||
    summary.run_id !== runId || summary.branch_id !== branchId ||
    summary.season_index !== seasonIndex || !positiveId(summary.season_label) ||
    !positiveId(summary.source_tour_fingerprint) || !positiveId(summary.boundary_command_id) ||
    !whole(summary.weeks_per_season, 1) || !whole(summary.completed_edition_count) ||
    !Array.isArray(summary.countries) || !Array.isArray(summary.players) ||
    !Array.isArray(summary.editions) ||
    summary.editions.length !== summary.completed_edition_count ||
    !summary.last_week_published_ranking ||
    summary.last_week_published_ranking.week !== summary.weeks_per_season ||
    !positiveId(summary.last_week_published_ranking.source_fingerprint) ||
    !Array.isArray(summary.last_week_published_ranking.top_players) ||
    summary.last_week_published_ranking.top_players.length > 10) return false

  const countryIds = new Set<string>(), playerIds = new Set<string>(), editionIds = new Set<string>()
  for (const c of summary.countries) {
    if (!c || !/^[A-Z]{3}$/.test(c.country_code) || countryIds.has(c.country_code) ||
      !whole(c.titles) || !whole(c.finals) || !whole(c.semifinals) ||
      !whole(c.quarterfinals) || !whole(c.awarded_points) ||
      !whole(c.distinct_players) || !whole(c.edition_appearances)) return false
    countryIds.add(c.country_code)
  }
  for (const p of summary.players) {
    if (!p || !positiveId(p.player_id) || playerIds.has(p.player_id) ||
      !positiveId(p.name) || !/^[A-Z]{3}$/.test(p.country_code) ||
      !whole(p.titles) || !whole(p.finals) || !whole(p.awarded_points) ||
      !whole(p.edition_appearances)) return false
    playerIds.add(p.player_id)
  }
  for (const e of summary.editions) {
    if (!e || !positiveId(e.edition_id) || editionIds.has(e.edition_id) ||
      !positiveId(e.name) || !whole(e.week, 1) || e.week > summary.weeks_per_season ||
      !positiveId(e.source_tournament_fingerprint) ||
      (e.champion_player_id !== null && !positiveId(e.champion_player_id)) ||
      (e.finalist_player_id !== null && !positiveId(e.finalist_player_id))) return false
    editionIds.add(e.edition_id)
  }
  for (const p of summary.last_week_published_ranking.top_players) {
    if (!p || !positiveId(p.player_id) || !whole(p.rank, 1) || !whole(p.points)) return false
  }
  return true
}

/** Match exact read scope, stable Saved HEAD and all country difference arithmetic. */
export function verifiedSignedSeasonComparison(
  source: unknown, runId: string, branchId: string, savedHead: string,
  seasonIndex: number, comparisonIndex: number | null,
  permitted: number[]
): TourSeasonComparison | null {
  if (!source || typeof source !== 'object' || !permitted.includes(seasonIndex) ||
    (comparisonIndex !== null && (!permitted.includes(comparisonIndex) || comparisonIndex === seasonIndex))) return null
  const v = source as TourSeasonComparison
  if (v.schema_version !== 'calendar_tour_season_comparison.v1' ||
    v.run_id !== runId || v.branch_id !== branchId ||
    v.saved_head_revision_id !== savedHead ||
    !validSummary(v.selected, runId, branchId, seasonIndex) ||
    (comparisonIndex === null
      ? v.comparison !== null
      : !validSummary(v.comparison as SignedSeasonSummary, runId, branchId, comparisonIndex)) ||
    !Array.isArray(v.country_deltas)) return null

  if (comparisonIndex === null) return v.country_deltas.length === 0 ? v : null
  const selected = v.selected, comparison = v.comparison
  if (!comparison ||
    comparison.source_tour_fingerprint !== selected.source_tour_fingerprint) return null

  const left = new Map(selected.countries.map(c => [c.country_code, c]))
  const right = new Map(comparison.countries.map(c => [c.country_code, c]))
  const expectedCodes = [...new Set([...left.keys(), ...right.keys()])].sort()
  if (v.country_deltas.length !== expectedCodes.length) return null
  for (const [i, code] of expectedCodes.entries()) {
    const row = v.country_deltas[i]
    const one = left.get(code), two = right.get(code)
    if (!row || row.country_code !== code ||
      !Number.isSafeInteger(row.titles_delta) ||
      !Number.isSafeInteger(row.finals_delta) ||
      !Number.isSafeInteger(row.awarded_points_delta) ||
      row.titles_delta !== (one?.titles ?? 0) - (two?.titles ?? 0) ||
      row.finals_delta !== (one?.finals ?? 0) - (two?.finals ?? 0) ||
      row.awarded_points_delta !== (one?.awarded_points ?? 0) - (two?.awarded_points ?? 0)) return null
  }
  return v
}

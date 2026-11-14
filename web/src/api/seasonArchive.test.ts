import { describe, expect, it } from 'vitest'
import { validSeasonArchive, validSeasonDetail } from './seasonArchive'

const f = 'f'.repeat(64)
const scope = { runId: 'run', branchId: 'branch', savedHead: 'rev-1' }
const overview = (editions = 2) => ({
  completed_edition_count: editions, players_with_results: 8, countries_represented: 3,
  titles_awarded: editions, turned_pro: [], retired: [], no_completed_editions: editions === 0,
  rankings: { week_w_published_fingerprint: f, season_closing_ranking_available: false, next_season_week_1_fingerprint: f }
})
const season = (i: number, patch = {}) => ({
  season_index: i, season_label: `S${i + 1}`, boundary_command_id: 'c', source_tour_fingerprint: f,
  rules: { ranking_policy_id: 'p', ranking_best_n: 15, development_policy_fingerprint: f, weeks_per_season: 4 },
  overview: overview(), leading_player: null, leading_country: null, ...patch
})
const archive = (seasons = [season(0), season(1)], patch = {}) => ({
  schema_version: 'native_tour_season_archive.v1', run_id: 'run', branch_id: 'branch',
  saved_head_revision_id: 'rev-1', source_tour_fingerprint: f, seasons, ...patch
}) as never
const m = (t: number, p: number) => ({ titles: t, finals: 0, awarded_points: p })
const row = (id: string, presence: string, a: unknown, b: unknown, d: unknown) =>
  ({ country_code: id, presence, selected: a, comparison: b, delta: d })
const detail = (countries: unknown[], comparable = true, differences: unknown[] = []) => ({
  schema_version: 'calendar_tour_season_comparison.v1', run_id: 'run', branch_id: 'branch',
  saved_head_revision_id: 'rev-1', overview: overview(), selected: { season_index: 1 },
  detail: {
    schema_version: 'native_tour_season_comparison_detail.v1',
    selected_season_index: 1, comparison_season_index: 0,
    selected_overview: overview(), comparison_overview: overview(),
    comparability: { comparable, compared_fields: ['ranking_best_n'], not_compared: ['point_tables'], differences },
    countries, players: [], note: 'n'
  }
}) as never
const dscope = { ...scope, season: 1, compareTo: 0 }

describe('season archive contract', () => {
  it('accepts an ordered archive, including a season without completed Editions', () => {
    expect(validSeasonArchive(archive(), scope)).toBe(true)
    expect(validSeasonArchive(archive([season(0, { overview: overview(0) })]), scope)).toBe(true)
  })
  it('rejects another Run, Branch, Saved HEAD, unordered seasons or a lying empty flag', () => {
    expect(validSeasonArchive(archive(undefined, { run_id: 'x' }), scope)).toBe(false)
    expect(validSeasonArchive(archive(undefined, { branch_id: 'sibling' }), scope)).toBe(false)
    expect(validSeasonArchive(archive(undefined, { saved_head_revision_id: 'rev-2' }), scope)).toBe(false)
    expect(validSeasonArchive(archive([season(1), season(0)]), scope)).toBe(false)
    expect(validSeasonArchive(archive([season(0, { overview: { ...overview(2), no_completed_editions: true } })]), scope)).toBe(false)
    expect(validSeasonArchive(null, scope)).toBe(false)
  })
})

describe('season comparison contract', () => {
  it('accepts a delta only when both seasons contain the entity', () => {
    expect(validSeasonDetail(detail([
      row('CZE', 'both', m(2, 100), m(1, 60), m(1, 40)),
      row('AUT', 'only_selected', m(1, 30), null, null),
      row('GER', 'only_comparison', null, m(1, 30), null)
    ]), dscope)).toBe(true)
  })
  it('rejects a zero-filled delta for a missing side and a missing delta for both sides', () => {
    expect(validSeasonDetail(detail([row('AUT', 'only_selected', m(1, 30), null, m(1, 30))]), dscope)).toBe(false)
    expect(validSeasonDetail(detail([row('CZE', 'both', m(2, 100), m(1, 60), null)]), dscope)).toBe(false)
    expect(validSeasonDetail(detail([row('AUT', 'only_selected', m(1, 30), m(0, 0), null)]), dscope)).toBe(false)
  })
  it('requires honest comparability and the requested seasons/scope', () => {
    expect(validSeasonDetail(detail([], false, []), dscope)).toBe(false)
    expect(validSeasonDetail(detail([], true, [{ field: 'ranking_best_n', selected: 1, comparison: 15 }]), dscope)).toBe(false)
    expect(validSeasonDetail(detail([], false, [{ field: 'ranking_best_n', selected: 1, comparison: 15 }]), dscope)).toBe(true)
    expect(validSeasonDetail(detail([]), { ...dscope, compareTo: 2 })).toBe(false)
    expect(validSeasonDetail(detail([]), { ...dscope, savedHead: 'rev-2' })).toBe(false)
    expect(validSeasonDetail(detail([row('CZE', 'both', m(1, 1), m(1, 1), m(0, 0)), row('CZE', 'both', m(1, 1), m(1, 1), m(0, 0))]), dscope)).toBe(false)
  })
  it('rejects missing comparison labels and incorrect deltas without crashing the panel', () => {
    const missingLabels = detail([]) as unknown as { detail: { comparability: { compared_fields?: string[] } } }
    delete missingLabels.detail.comparability.compared_fields
    expect(validSeasonDetail(missingLabels as never, dscope)).toBe(false)
    expect(validSeasonDetail(detail([
      row('CZE', 'both', m(2, 100), m(1, 60), m(1, 999))
    ]), dscope)).toBe(false)
    const missingMetrics = row('CZE', 'both', undefined as never, m(1, 60), m(1, 40))
    expect(validSeasonDetail(detail([missingMetrics]), dscope)).toBe(false)
  })

})

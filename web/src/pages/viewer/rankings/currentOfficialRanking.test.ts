import { describe, expect, it } from 'vitest'
import {
  currentRankingViewerBranch, legacyCurrentRankingSeason, validCurrentOfficialRanking
} from './currentOfficialRanking'

const player = (rank: number, playerId = 'player-' + rank, points = 0) => ({
  rank, player_id: playerId, points
})
function ranking(rows = [player(1)]) {
  return {
    schema_version: 'viewer_official_ranking.v1',
    product_run_id: 'run-a',
    viewer_branch_id: 'branch-a',
    season_index: 0,
    week: 2,
    week_ordinal: 1,
    policy_id: 'historic-best-12',
    best_n: 12,
    snapshot_fingerprint: 'a'.repeat(64),
    row_count: rows.length,
    rows
  }
}

describe('current published Official Ranking source validation (legacy v1)', () => {
  it('requires a matching nonempty canonical Viewer Branch context', () => {
    expect(currentRankingViewerBranch({ product_run_id: 'run-a', official_branch_id: 'branch-a' }, 'run-a')).toBe('branch-a')
    expect(currentRankingViewerBranch({ product_run_id: 'run-b', official_branch_id: 'branch-a' }, 'run-a')).toBeNull()
    expect(currentRankingViewerBranch({ product_run_id: 'run-a', official_branch_id: '' }, 'run-a')).toBeNull()
    expect(currentRankingViewerBranch({ product_run_id: 'run-a', official_branch_id: '  ' }, 'run-a')).toBeNull()
    expect(currentRankingViewerBranch(null, 'run-a')).toBeNull()
    expect(currentRankingViewerBranch({ product_run_id: 'run-a', official_branch_id: 'branch-a' }, '')).toBeNull()
  })

  it('accepts the actual zero-player and zero-point published ranks', () => {
    expect(validCurrentOfficialRanking(ranking([]), 'run-a', 'branch-a')).toBe(true)
    expect(validCurrentOfficialRanking(ranking([player(1, 'zero', 0)]), 'run-a', 'branch-a')).toBe(true)
    expect(legacyCurrentRankingSeason(0)).toBe('2000/01')
    expect(legacyCurrentRankingSeason(3)).toBe('2003/04')
  })

  it('rejects foreign and corrupt sources without fabricating results', () => {
    const ok = ranking([player(1, 'one', 70), player(2, 'two', 30)])
    expect(validCurrentOfficialRanking(ok, 'run-a', 'branch-a')).toBe(true)
    const invalid: unknown[] = [
      { ...ok, schema_version: 'calendar-ranking-v2' },
      { ...ok, product_run_id: 'run-b' },
      { ...ok, viewer_branch_id: 'other' },
      { ...ok, week: 3 },
      { ...ok, week_ordinal: 2 },
      { ...ok, season_index: 50 },
      { ...ok, snapshot_fingerprint: 'not-a-fingerprint' },
      { ...ok, policy_id: null },
      { ...ok, best_n: 0 },
      { ...ok, row_count: 3 },
      { ...ok, row_count: -1 },
      { ...ok, rows: [player(1, 'one'), player(2, 'one')] },
      { ...ok, rows: [player(1, 'one'), player(3, 'two')] },
      { ...ok, rows: [player(1, 'one'), player(2, 'two', -3)] },
      { ...ok, rows: [player(1, 'one', 30), player(2, 'two', 70)] },
      { ...ok, rows: [player(1, '  '), player(2, 'two')] },
      { ...ok, rows: null },
      null
    ]
    for (const value of invalid) expect(validCurrentOfficialRanking(value, 'run-a', 'branch-a')).toBe(false)
    expect(validCurrentOfficialRanking(ok, 'run-b', 'branch-a')).toBe(false)
    expect(validCurrentOfficialRanking(ok, 'run-a', 'other')).toBe(false)
  })
})

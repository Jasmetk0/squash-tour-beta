import { describe, expect, it } from 'vitest'

import {
  detailPages, legacySeasonLabel, parseDetailPage,
  parseLegacyRankingOrdinal, rankingRowsMatchingId, validViewerRankingDetail
} from './rankingSnapshotDetailBrowsing'

const row = (rank: number, playerId = 'player-' + rank, points = 0) => ({
  rank, player_id: playerId, points
})
function ranking(rows = [row(1)]) {
  return {
    schema_version: 'viewer_official_ranking.v1',
    product_run_id: 'run-a',
    viewer_branch_id: 'branch-a',
    season_index: 0,
    week: 2,
    week_ordinal: 1,
    snapshot_fingerprint: 'a'.repeat(64),
    policy_id: 'historic-policy',
    best_n: 15,
    row_count: rows.length,
    rows
  }
}

describe('legacy published ranking snapshot validation', () => {
  it('accepts a legitimate zero-player publication and zero ranking points', () => {
    expect(validViewerRankingDetail(ranking([]), 'run-a', 'branch-a', 1)).toBe(true)
    expect(validViewerRankingDetail(ranking([row(1, 'a', 0)]), 'run-a', 'branch-a', 1)).toBe(true)
  })

  it('does not reinterpret noncanonical ordinals or unsupported legacy range', () => {
    expect(parseLegacyRankingOrdinal('0')).toBe(0)
    expect(parseLegacyRankingOrdinal('3049')).toBe(3049)
    for (const invalid of ['', '01', '-1', '+2', '1.0', '1e2', '3050', 'NaN', '999999999999999999']) {
      expect(parseLegacyRankingOrdinal(invalid)).toBeNull()
    }
    expect(legacySeasonLabel(0)).toBe('2000/01')
    expect(legacySeasonLabel(1)).toBe('2001/02')
  })

  it('rejects foreign identity, wrong clock, missing/duplicate player evidence and invalid rows', () => {
    const original = ranking([row(1, 'one', 120), row(2, 'two', 0)])
    expect(validViewerRankingDetail(original, 'run-a', 'branch-a', 1)).toBe(true)
    const invalid = [
      { ...original, schema_version: 'other' },
      { ...original, product_run_id: 'run-b' },
      { ...original, viewer_branch_id: 'branch-b' },
      { ...original, week_ordinal: 2 },
      { ...original, week: 1 },
      { ...original, season_index: 1 },
      { ...original, best_n: 0 },
      { ...original, snapshot_fingerprint: 'invalid' },
      { ...original, policy_id: null },
      { ...original, row_count: 1 },
      { ...original, rows: [row(1, 'one'), row(2, 'one')] },
      { ...original, rows: [row(1, 'one'), row(3, 'two')] },
      { ...original, rows: [row(1, 'one'), row(2, 'two', -1)] },
      { ...original, rows: [row(1, 'one'), row(2, 'two', 1.2)] },
      { ...original, rows: [row(1, '   '), row(2, 'two')] }
    ]
    for (const bad of invalid) {
      expect(validViewerRankingDetail(bad, 'run-a', 'branch-a', 1)).toBe(false)
    }
    expect(validViewerRankingDetail(original, 'wrong', 'branch-a', 1)).toBe(false)
    expect(validViewerRankingDetail(original, 'run-a', 'wrong', 1)).toBe(false)
    expect(validViewerRankingDetail(original, 'run-a', 'branch-a', 0)).toBe(false)
  })

  it('searches only actual player IDs without changing authoritative rank/points', () => {
    const rows = [row(1, 'Alice-ID', 50), row(2, 'bob', 0), row(3, 'alice-other', 80)]
    const filtered = rankingRowsMatchingId(rows, ' ALICE ')
    expect(filtered).toEqual([rows[0], rows[2]])
    expect(filtered.map(x => x.rank)).toEqual([1, 3])
    expect(rankingRowsMatchingId(rows, '')).toHaveLength(3)
    expect(rankingRowsMatchingId(rows, 'unavailable')).toHaveLength(0)
    expect(rows).toHaveLength(3)
  })

  it('counts exact pages and rejects invalid numeric jumps', () => {
    expect(detailPages(0)).toBe(0)
    expect(detailPages(50)).toBe(1)
    expect(detailPages(51)).toBe(2)
    for (const invalid of ['', '0', '-2', '1.5', '3', '2x', '999999999999999999999']) {
      expect(parseDetailPage(invalid, 2)).toBeNull()
    }
    expect(parseDetailPage(' 2 ', 2)).toBe(2)
  })
})

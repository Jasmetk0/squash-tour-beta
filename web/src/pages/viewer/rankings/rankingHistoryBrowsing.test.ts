import { describe, expect, it } from 'vitest'
import {
  filterRankingHistory, legacyRankingSeasonLabel, rankingHistoryPageCount,
  rankingHistoryPageJump, validRankingHistory
} from './rankingHistoryBrowsing'

function item(n: number, policy = 'policy-1', best = 15, count = 0) {
  return {
    season_index: Math.floor(n / 61), week: n % 61 + 1,
    week_ordinal: n, snapshot_fingerprint: 'a'.repeat(64),
    policy_id: policy, best_n: best, row_count: count
  }
}
function payload(rows = [item(0)]) {
  return {
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'r', viewer_branch_id: 'b',
    public_head_ordinal: rows.length ? Math.max(...rows.map(row => row.week_ordinal)) : 0,
    publication_count: rows.length, publications: rows
  }
}

describe('legacy Viewer ranking history helpers', () => {
  it('accepts empty publication history and legitimately zero-player publications', () => {
    expect(validRankingHistory(payload([]), 'r', 'b')).toBe(true)
    expect(validRankingHistory(payload([item(0)]), 'r', 'b')).toBe(true)
  })
  it('rejects foreign identity, missing/duplicate evidence, incorrect ordinal and future rows', () => {
    const valid = payload([item(0), item(61)])
    expect(validRankingHistory(valid, 'r', 'b')).toBe(true)
    const bad = [
      { ...valid, product_run_id: 'foreign' },
      { ...valid, viewer_branch_id: 'foreign' },
      { ...valid, schema_version: 'v2' },
      { ...valid, publication_count: 1 },
      { ...valid, public_head_ordinal: 0 },
      { ...valid, publications: [item(0), item(0)] },
      { ...valid, publications: [item(0), { ...item(61), week: 1 }] },
      { ...valid, publications: [item(0), { ...item(61), best_n: 0 }] },
      { ...valid, publications: [item(0), { ...item(61), row_count: -1 }] },
      { ...valid, publications: [item(0), { ...item(61), snapshot_fingerprint: 'bad' }] },
      { ...valid, publications: [item(0), { ...item(61), week_ordinal: 3049 }] },
      { ...valid, publications: [item(0)] }
    ]
    for (const value of bad) expect(validRankingHistory(value, 'r', 'b')).toBe(false)
  })
  it('filters whole collection and sorts ordinal irrespective of server array order', () => {
    const rows = [item(62, 'Foo', 20), item(0, 'bar', 15), item(61, 'foo', 15)]
    expect(filterRankingHistory(rows, { season: '', bestN: '', search: '', order: 'newest' }).map(x => x.week_ordinal)).toEqual([62, 61, 0])
    expect(filterRankingHistory(rows, { season: '', bestN: '', search: '', order: 'oldest' }).map(x => x.week_ordinal)).toEqual([0, 61, 62])
    expect(filterRankingHistory(rows, { season: '1', bestN: '15', search: 'FOO', order: 'newest' }).map(x => x.week_ordinal)).toEqual([61])
    expect(filterRankingHistory(rows, { season: '', bestN: '', search: '#62', order: 'newest' }).map(x => x.week_ordinal)).toEqual([62])
    expect(rows[0].week_ordinal).toBe(62)
  })
  it('handles first/last/empty pages and blocks invalid numeric jumps', () => {
    expect(rankingHistoryPageCount(0)).toBe(0)
    expect(rankingHistoryPageCount(25)).toBe(1)
    expect(rankingHistoryPageCount(26)).toBe(2)
    for (const value of ['', '0', '-1', '1.5', '2x', '3', '999999999999999999999999999']) {
      expect(rankingHistoryPageJump(value, 2)).toBeNull()
    }
    expect(rankingHistoryPageJump(' 2 ', 2)).toBe(2)
    expect(legacyRankingSeasonLabel(0)).toBe('2000/01')
    expect(legacyRankingSeasonLabel(1)).toBe('2001/02')
  })
})

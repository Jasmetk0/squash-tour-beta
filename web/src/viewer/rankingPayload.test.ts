import { describe, expect, it } from 'vitest'

import { parseRankingPreviewPayload } from './rankingPayload'

function rows(payload: unknown) {
  return parseRankingPreviewPayload(payload).rows
}

describe('parseRankingPreviewPayload', () => {
  it('accepts supported safe ranking row containers and keeps explicit row fields', () => {
    const result = parseRankingPreviewPayload({
      rankings: [
        {
          rank: '2',
          player_id: 'p2',
          player_name: 'Safe Player Two',
          country_code: 'ENG',
          points: '12,500',
          tournaments_counted: '11',
          previous_rank: 3
        },
        {
          rank: 1,
          player: { id: 'p1', display_name: 'Safe Player One', country: 'EGY' },
          ranking_points: 13000,
          events_counted: 12,
          movement: '+1'
        }
      ]
    })

    expect(result.sourceKey).toBe('rankings')
    expect(result.unsupportedReason).toBeNull()
    expect(result.rows).toEqual([
      {
        rank: 1,
        playerId: 'p1',
        playerName: 'Safe Player One',
        country: 'EGY',
        points: 13000,
        tournamentsCounted: 12,
        movement: '+1',
        previousRank: null
      },
      {
        rank: 2,
        playerId: 'p2',
        playerName: 'Safe Player Two',
        country: 'ENG',
        points: 12500,
        tournamentsCounted: 11,
        movement: null,
        previousRank: 3
      }
    ])
  })

  it('accepts current known ranking table and nested rows containers', () => {
    expect(rows({ ranking_table: { rows: [{ current_rank: 1, playerId: 'p1', playerName: 'Known Shape', total_points: 100 }] } })).toHaveLength(1)
    expect(rows({ top_100: [{ place: 1, player_id: 'p2', player_name: 'Top 100 Shape', point_total: 90 }] })).toHaveLength(1)
  })

  it('returns rows only when player identity and standing values are explicit', () => {
    expect(rows({ rankings: [{ rank: 1, points: 100 }] })).toEqual([])
    expect(rows({ rankings: [{ player_id: 'p1', player_name: 'No Standing' }] })).toEqual([])
    expect(rows({ rankings: [{ player_id: 'p1', player_name: 'Has Rank', rank: 1 }] })).toHaveLength(1)
    expect(rows({ rankings: [{ player_id: 'p2', player_name: 'Has Points', points: 100 }] })).toHaveLength(1)
  })

  it('does not invent ranks, players, or points from row index or ambiguous fields', () => {
    expect(rows({ rankings: [{ seed: 1, athlete: 'Ambiguous Player', score: 1000 }] })).toEqual([])
    expect(rows({ rankings: [{ player_id: 'p1', player_name: 'No Index Rank' }, { player_id: 'p2', player_name: 'No Index Rank Two' }] })).toEqual([])
  })

  it('rejects malformed rows and nested object values for rank, player labels, and points', () => {
    expect(
      rows({
        rankings: [
          null,
          'not a row',
          { rank: { value: 1 }, player_id: 'p1', player_name: 'Nested Rank', points: 100 },
          { rank: 2, player_id: 'p2', player_name: { label: 'Nested Player' }, points: 90 },
          { rank: 3, player_id: 'p3', player_name: 'Nested Points', points: { value: 80 } },
          { rank: 4, player_id: 'p4', player_name: 'Non-numeric Points', points: 'many' }
        ]
      })
    ).toEqual([])
  })

  it('rejects missing player identifiers and labels instead of guessing display rows', () => {
    expect(rows({ rankings: [{ rank: 1, country: 'EGY', points: 1000 }] })).toEqual([])
    expect(rows({ rankings: [{ rank: 1, player: {}, points: 1000 }] })).toEqual([])
  })

  it('returns empty rows for empty, null, undefined, unknown, and weird payloads without throwing', () => {
    const weirdPayloads = [null, undefined, [], {}, { rankings: [] }, { rankings: [[], {}, { rank: [], player_name: [], points: [] }] }, { rows: { value: [] } }]

    weirdPayloads.forEach((payload) => {
      expect(() => parseRankingPreviewPayload(payload)).not.toThrow()
      expect(rows(payload)).toEqual([])
    })
  })

  it('does not produce object-like row labels', () => {
    const renderedValues = rows({ rankings: [{ rank: 1, player_id: 'p1', player_name: { toString: () => 'Bad Object' }, points: 100 }] })
      .flatMap((row) => Object.values(row))
      .map(String)

    expect(renderedValues).not.toContain('[object Object]')
    expect(renderedValues).not.toContain('Bad Object')
  })
})

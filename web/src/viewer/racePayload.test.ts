import { describe, expect, it } from 'vitest'

import { parseRacePreviewPayload } from './racePayload'

function rows(payload: unknown) {
  return parseRacePreviewPayload(payload).rows
}

describe('parseRacePreviewPayload', () => {
  it('accepts supported safe race row containers and keeps explicit row fields', () => {
    const result = parseRacePreviewPayload({
      race_to_finals: {
        rows: [
          {
            position: '2',
            player_id: 'r2',
            player_name: 'Safe Race Player Two',
            country: 'NZL',
            race_points: '8,500',
            tournaments_counted: '7',
            qualification_status: 'Chasing',
            next_max_points_possible: '900'
          },
          {
            race_rank: 1,
            player: { id: 'r1', displayName: 'Safe Race Player One', country_code: 'EGY' },
            racePoints: 9000,
            eventsCounted: 8,
            qualified: true,
            nextMaxPoints: 1200
          }
        ]
      }
    })

    expect(result.sourceKey).toBe('race_to_finals.rows')
    expect(result.unsupportedReason).toBeNull()
    expect(result.rows).toEqual([
      {
        rank: 1,
        playerId: 'r1',
        playerName: 'Safe Race Player One',
        country: 'EGY',
        racePoints: 9000,
        tournamentsCounted: 8,
        qualificationStatus: 'Qualified',
        nextMaxPoints: 1200
      },
      {
        rank: 2,
        playerId: 'r2',
        playerName: 'Safe Race Player Two',
        country: 'NZL',
        racePoints: 8500,
        tournamentsCounted: 7,
        qualificationStatus: 'Chasing',
        nextMaxPoints: 900
      }
    ])
  })

  it('accepts current known race containers without broadening to unsafe shapes', () => {
    expect(rows({ race: [{ position: 1, player_id: 'r1', player_name: 'Race Shape', points: 100 }] })).toHaveLength(1)
    expect(rows({ race_table: { rows: [{ raceRank: 1, playerId: 'r2', playerName: 'Race Table Shape', totalPoints: 90 }] } })).toHaveLength(1)
  })

  it('rejects ranking-only generic rows unless they carry a race-specific signal', () => {
    expect(rows({ rows: [{ rank: 1, player_id: 'p1', player_name: 'Ranking Only', points: 1000 }] })).toEqual([])
    expect(rows({ standings: [{ rank: 1, player_id: 'p1', player_name: 'Ranking Only', points: 1000 }] })).toEqual([])
    expect(rows({ rows: [{ position: 1, player_id: 'r1', player_name: 'Race Position', points: 1000 }] })).toHaveLength(1)
    expect(rows({ rows: [{ rank: 1, player_id: 'r2', player_name: 'Race Points', race_points: 1000 }] })).toHaveLength(1)
  })

  it('returns rows only when player identity and race standing values are explicit', () => {
    expect(rows({ race_to_finals: { rows: [{ position: 1, race_points: 100 }] } })).toEqual([])
    expect(rows({ race_to_finals: { rows: [{ player_id: 'r1', player_name: 'No Standing' }] } })).toEqual([])
    expect(rows({ race_to_finals: { rows: [{ player_id: 'r1', player_name: 'Has Position', position: 1 }] } })).toHaveLength(1)
    expect(rows({ race_to_finals: { rows: [{ player_id: 'r2', player_name: 'Has Points', race_points: 100 }] } })).toHaveLength(1)
  })

  it('does not invent race positions, players, or points from row index or ambiguous fields', () => {
    expect(rows({ race_to_finals: { rows: [{ seed: 1, athlete: 'Ambiguous Race Player', score: 1000 }] } })).toEqual([])
    expect(rows({ race_to_finals: { rows: [{ player_id: 'r1', player_name: 'No Index Rank' }, { player_id: 'r2', player_name: 'No Index Rank Two' }] } })).toEqual([])
  })

  it('rejects malformed rows and nested object values for race position, player labels, and points', () => {
    expect(
      rows({
        race_to_finals: {
          rows: [
            null,
            'not a row',
            { position: { value: 1 }, player_id: 'r1', player_name: 'Nested Rank', race_points: 100 },
            { position: 2, player_id: 'r2', player_name: { label: 'Nested Player' }, race_points: 90 },
            { position: 3, player_id: 'r3', player_name: 'Nested Points', race_points: { value: 80 } },
            { position: 4, player_id: 'r4', player_name: 'Non-numeric Points', race_points: 'many' }
          ]
        }
      })
    ).toEqual([])
  })

  it('rejects missing player identifiers and labels instead of guessing display rows', () => {
    expect(rows({ race_to_finals: { rows: [{ position: 1, country: 'EGY', race_points: 1000 }] } })).toEqual([])
    expect(rows({ race_to_finals: { rows: [{ position: 1, player: {}, race_points: 1000 }] } })).toEqual([])
  })

  it('returns empty rows for empty, null, undefined, unknown, and weird payloads without throwing', () => {
    const weirdPayloads = [null, undefined, [], {}, { race_to_finals: { rows: [] } }, { race_to_finals: { rows: [[], {}, { position: [], player_name: [], race_points: [] }] } }, { rows: { value: [] } }]

    weirdPayloads.forEach((payload) => {
      expect(() => parseRacePreviewPayload(payload)).not.toThrow()
      expect(rows(payload)).toEqual([])
    })
  })

  it('does not produce object-like row labels', () => {
    const renderedValues = rows({ race_to_finals: { rows: [{ position: 1, player_id: 'r1', player_name: { toString: () => 'Bad Object' }, race_points: 100 }] } })
      .flatMap((row) => Object.values(row))
      .map(String)

    expect(renderedValues).not.toContain('[object Object]')
    expect(renderedValues).not.toContain('Bad Object')
  })
})

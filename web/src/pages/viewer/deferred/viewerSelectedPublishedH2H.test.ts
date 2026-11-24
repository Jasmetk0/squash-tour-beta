import { describe, expect, it } from 'vitest'

import type { ViewerTournamentResult, ViewerTournamentResultPlayer } from '../../../api/types'
import { calendarEvent, historyEvent } from '../../../test/viewerCalendarFixtures'
import type { SavedTournamentEntry } from '../tour/viewerTournamentCatalog'
import {
  MAX_SELECTED_H2H_EVENTS, selectedPublishedH2H,
} from './viewerSelectedPublishedH2H'

const runId = 'run alpha'
const branchId = 'viewer-branch'
const player = (player_id: string): ViewerTournamentResultPlayer => ({
  player_id, draw_type: 'main', seed_number: null, qualifier: false,
  main_entry_status: null, reached_stage: 'semifinal',
  final_round_number: null, eliminated_by_player_id: null, last_match_id: null,
  wins: 0, losses: 0, byes_received: 0, walkovers_received: 0,
  retired_or_walkover_loss: false, group_index: null, group_position: null,
  played_group_wins: null, group_walkovers_received: null, knockout_reached_stage: null,
})
function fixture(n = 1, overrides: Partial<ViewerTournamentResult> = {}) {
  const event = calendarEvent({
    event_id: 'event/' + n, event_name: 'Open ' + n, season_week: n,
    start_season_week: n, end_season_week: n,
  })
  const entry: SavedTournamentEntry = {
    event,
    publication: historyEvent(event, {
      result_published: true, champion_player_id: 'A', finalist_player_id: 'B',
    }),
  }
  const data: ViewerTournamentResult = {
    schema_version: 'viewer_tournament_result.v1', product_run_id: runId,
    viewer_branch_id: branchId, event_id: event.event_id,
    completed_season_index: 28, completed_week: event.season_week,
    champion_player_id: 'A', finalist_player_id: 'B',
    qualification_winner_ids: [], players: [player('A'), player('B'), player('C')],
    matches: [
      { match_id: 'semi/' + n, draw_type: 'main', round_number: 1,
        bracket_position: 1, winner_player_id: 'A', loser_player_id: 'C', scoreline: '3-0' },
      { match_id: 'final/' + n, draw_type: 'main', round_number: 2,
        bracket_position: 1, winner_player_id: 'A', loser_player_id: 'B', scoreline: '3-2' },
    ],
    ...overrides,
  }
  return { entry, data }
}

describe('bounded source-complete public Saved H2H derivation', () => {
  it('counts only exact two-player outcomes from verified explicitly selected publications', () => {
    const report = selectedPublishedH2H([fixture(1), fixture(2)], runId, branchId, ' A ', 'B')
    expect(report).toMatchObject({
      playerA: 'A', playerB: 'B', eventCount: 2, publicationMatchCount: 4,
      winsA: 2, winsB: 0,
    })
    expect(report?.encounters.map(e => [e.eventId, e.matchId, e.scoreline]))
      .toEqual([
        ['event/1', 'final/1', '3-2'], ['event/2', 'final/2', '3-2'],
      ])
  })

  it('is directional for B victories without assigning unrelated player matches to H2H', () => {
    const x = fixture(2, {
      matches: [
        { match_id: 'final/2', draw_type: 'main', round_number: 2,
          bracket_position: 1, winner_player_id: 'B', loser_player_id: 'A',
          scoreline: '3-1' },
      ],
    })
    x.entry.publication.champion_player_id = 'B'
    x.entry.publication.finalist_player_id = 'A'
    x.data.champion_player_id = 'B'
    x.data.finalist_player_id = 'A'
    const report = selectedPublishedH2H([fixture(1), x], runId, branchId, 'A', 'B')
    expect(report).toMatchObject({ winsA: 1, winsB: 1, publicationMatchCount: 3 })
    expect(report?.encounters.map(e => e.winnerId)).toEqual(['A', 'B'])
  })

  it('reports a source-scoped zero rather than inventing a global career record', () => {
    const report = selectedPublishedH2H([fixture()], runId, branchId, 'A', 'C')
    expect(report).toMatchObject({ eventCount: 1, publicationMatchCount: 2, winsA: 1, winsB: 0 })
    const zero = selectedPublishedH2H([fixture()], runId, branchId, 'B', 'C')
    expect(zero).toMatchObject({ eventCount: 1, winsA: 0, winsB: 0, encounters: [] })
  })

  it('derives source-scoped per-player outcomes against all named opponents without inflating H2H', () => {
    const report = selectedPublishedH2H([fixture(1), fixture(2)], runId, branchId, 'A', 'B')
    expect(report?.playerAStats).toMatchObject({
      playerId: 'A', listedInEvents: 2,
      winsAgainstNamedOpponents: 4, lossesAgainstNamedOpponents: 0,
      noOpponentOutcomes: 0, uniqueNamedOpponents: 2,
    })
    expect(report?.playerBStats).toMatchObject({
      playerId: 'B', listedInEvents: 2,
      winsAgainstNamedOpponents: 0, lossesAgainstNamedOpponents: 2,
      uniqueNamedOpponents: 1,
    })
    expect(report?.winsA).toBe(2)
    expect(report?.playerAStats.byDraw).toEqual([
      { draw: 'qualification', wins: 0, losses: 0 },
      { draw: 'group', wins: 0, losses: 0 },
      { draw: 'main', wins: 4, losses: 0 },
      { draw: 'knockout', wins: 0, losses: 0 },
    ])
    expect(report?.playerBStats.byEvent.map(row =>
      [row.eventId, row.listedAsParticipant, row.wins, row.losses]))
      .toEqual([['event/1', true, 0, 1], ['event/2', true, 0, 1]])
  })

  it('keeps outcome counts independent per player when winners change across published sources', () => {
    const reversed = fixture(2, {
      champion_player_id: 'B', finalist_player_id: 'A',
      matches: [
        { match_id: 'final/2', draw_type: 'main', round_number: 2,
          bracket_position: 1, winner_player_id: 'B', loser_player_id: 'A', scoreline: '3-1' },
      ],
    })
    reversed.entry.publication.champion_player_id = 'B'
    reversed.entry.publication.finalist_player_id = 'A'
    const report = selectedPublishedH2H([fixture(1), reversed], runId, branchId, 'A', 'B')
    expect(report).toMatchObject({
      winsA: 1, winsB: 1,
      playerAStats: { winsAgainstNamedOpponents: 2, lossesAgainstNamedOpponents: 1 },
      playerBStats: { winsAgainstNamedOpponents: 1, lossesAgainstNamedOpponents: 1 },
    })
  })

  it('does not count a source BYE as a win over an opponent', () => {
    const x = fixture(1, {
      matches: [
        { match_id: 'bye', draw_type: 'qualification', round_number: 1,
          bracket_position: 1, winner_player_id: 'A', loser_player_id: null, scoreline: 'BYE' },
      ],
    })
    const report = selectedPublishedH2H([x], runId, branchId, 'A', 'B')
    expect(report).toMatchObject({
      winsA: 0, winsB: 0, publicationMatchCount: 1,
      playerAStats: {
        winsAgainstNamedOpponents: 0, lossesAgainstNamedOpponents: 0,
        noOpponentOutcomes: 1, uniqueNamedOpponents: 0,
      },
    })
    expect(report?.playerAStats.byEvent[0].noOpponentOutcomes).toBe(1)
  })

  it('distinguishes a stable player ID absent from selected player lists from a demonstrated 0-0', () => {
    const report = selectedPublishedH2H([fixture(1)], runId, branchId, 'NOT-IN-SOURCE', 'A')
    expect(report).toMatchObject({
      winsA: 0, winsB: 0,
      playerAStats: { listedInEvents: 0, winsAgainstNamedOpponents: 0, lossesAgainstNamedOpponents: 0 },
      playerBStats: { listedInEvents: 1, winsAgainstNamedOpponents: 2 },
    })
    expect(report?.playerAStats.byEvent[0].listedAsParticipant).toBe(false)
  })

  it('does not count outcome records lacking a losing player as H2H', () => {
    const x = fixture(1, {
      matches: [
        { match_id: 'bye', draw_type: 'main', round_number: 1,
          bracket_position: 1, winner_player_id: 'A', loser_player_id: null,
          scoreline: 'BYE' },
      ],
    })
    expect(selectedPublishedH2H([x], runId, branchId, 'A', 'B'))
      .toMatchObject({ eventCount: 1, publicationMatchCount: 1, encounters: [] })
  })

  it('rejects a foreign Viewer Branch, different Run or event ID, without partial totals', () => {
    for (const wrong of [
      { viewer_branch_id: 'other' }, { product_run_id: 'other' }, { event_id: 'event/other' },
    ]) {
      expect(selectedPublishedH2H([
        fixture(1), fixture(2, wrong),
      ], runId, branchId, 'A', 'B')).toBeNull()
    }
  })

  it('rejects private match fields and corrupted champion identity', () => {
    const x = fixture()
    expect(selectedPublishedH2H([fixture(2), {
      entry: x.entry, data: {
        ...x.data, matches: [{ ...x.data.matches[0], private_performance: 96 }],
      },
    }], runId, branchId, 'A', 'B')).toBeNull()
    expect(selectedPublishedH2H([fixture(2), fixture(1, {
      champion_player_id: 'C',
    })], runId, branchId, 'A', 'B')).toBeNull()
  })

  it('rejects repeated event identities and limits the amount of explicit reads', () => {
    expect(selectedPublishedH2H([fixture(1), fixture(1)], runId, branchId, 'A', 'B')).toBeNull()
    const nine = Array.from({ length: MAX_SELECTED_H2H_EVENTS + 1 }, (_, i) => fixture(i + 1))
    expect(selectedPublishedH2H(nine, runId, branchId, 'A', 'B')).toBeNull()
    expect(selectedPublishedH2H(nine.slice(0, MAX_SELECTED_H2H_EVENTS), runId, branchId, 'A', 'B'))
      .not.toBeNull()
  })

  it('accepts a genuine multi-week tournament completion inside the Saved calendar span but not outside', () => {
    const inside = fixture(5, { completed_week: 7 })
    inside.entry.event.end_season_week = 7
    inside.entry.event.duration_in_season_weeks = 3
    const report = selectedPublishedH2H([inside], runId, branchId, 'A', 'B')
    expect(report).toMatchObject({
      eventCount: 1, publicationMatchCount: 2, winsA: 1, winsB: 0,
    })

    const outside = fixture(5, { completed_week: 8 })
    outside.entry.event.end_season_week = 7
    outside.entry.event.duration_in_season_weeks = 3
    expect(selectedPublishedH2H([outside], runId, branchId, 'A', 'B')).toBeNull()

    const beforeStart = fixture(5, { completed_week: 4 })
    beforeStart.entry.event.end_season_week = 7
    beforeStart.entry.event.duration_in_season_weeks = 3
    expect(selectedPublishedH2H([beforeStart], runId, branchId, 'A', 'B')).toBeNull()
  })

  it('fails closed on empty, identical or case-different player IDs rather than guessing identity', () => {
    for (const [a, b] of [['', 'B'], ['A', 'A'], [' A ', 'A'], ['A', '']]) {
      expect(selectedPublishedH2H([fixture()], runId, branchId, a, b)).toBeNull()
    }
    // Published IDs are case sensitive, no implicit player identity matching.
    expect(selectedPublishedH2H([fixture()], runId, branchId, 'a', 'B'))
      .toMatchObject({ winsA: 0, winsB: 0 })
  })

  it('rejects impossible BYE/opponent combinations, missing scores and opponentless walkovers', () => {
    const good = fixture()
    const match = good.data.matches[0]
    for (const overrides of [
      { scoreline: 'BYE' },
      { loser_player_id: null, scoreline: 'W/O' },
      { loser_player_id: null, scoreline: '3-0' },
      { scoreline: '' },
      { scoreline: '   ' },
    ]) {
      const wrong = fixture(2, { matches: [{ ...match, ...overrides }] })
      expect(selectedPublishedH2H([good, wrong], runId, branchId, 'A', 'B')).toBeNull()
    }
  })

  it('retains canonical named-opponent walkovers as published outcome records, not inferred on-court play', () => {
    const data = fixture(1, {
      matches: [{
        match_id: 'withdrawal', draw_type: 'main', round_number: 1,
        bracket_position: 1, winner_player_id: 'A', loser_player_id: 'B', scoreline: 'W/O',
      }],
    })
    expect(selectedPublishedH2H([data], runId, branchId, 'A', 'B'))
      .toMatchObject({ winsA: 1, winsB: 0, encounters: [{ scoreline: 'W/O' }] })
  })

})

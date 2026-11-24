import type { ViewerTournamentResultMatch } from '../../../api/types'
import type { SavedTournamentEntry } from '../tour/viewerTournamentCatalog'
import { verifiedSavedMatchResult } from './viewerSavedMatchCenter'

export const MAX_SELECTED_H2H_EVENTS = 8

export type SelectedH2HSource = { entry: SavedTournamentEntry; data: unknown }

export type PublishedH2HEncounter = {
  eventId: string
  eventName: string
  season: string
  week: number
  matchId: string
  draw: ViewerTournamentResultMatch['draw_type']
  round: number
  bracketPosition: number
  winnerId: string
  loserId: string
  scoreline: string
}

export type SelectedPlayerDrawRecord = {
  draw: ViewerTournamentResultMatch['draw_type']
  wins: number
  losses: number
}

export type SelectedPlayerEventRecord = {
  eventId: string
  eventName: string
  season: string
  week: number
  listedAsParticipant: boolean
  wins: number
  losses: number
  noOpponentOutcomes: number
}

export type SelectedPlayerPublishedStats = {
  playerId: string
  listedInEvents: number
  winsAgainstNamedOpponents: number
  lossesAgainstNamedOpponents: number
  noOpponentOutcomes: number
  uniqueNamedOpponents: number
  byDraw: SelectedPlayerDrawRecord[]
  byEvent: SelectedPlayerEventRecord[]
}

export type SelectedPublishedH2H = {
  playerA: string
  playerB: string
  eventCount: number
  publicationMatchCount: number
  winsA: number
  winsB: number
  encounters: PublishedH2HEncounter[]
  playerAStats: SelectedPlayerPublishedStats
  playerBStats: SelectedPlayerPublishedStats
}

/**
 * A deliberately bounded H2H over only explicitly selected, fully verified
 * Saved tournament publications. Every selected event must be valid; a broken
 * one fails the *entire* result closed, not a silently reduced denominator.
 *
 * Walkovers, if present, remain published outcome records, not an assertion
 * of on-court play. A zero means zero encounters *in these chosen sources*
 * only, never a career-wide zero.
 */
export function selectedPublishedH2H(
  sources: readonly SelectedH2HSource[],
  runId: string,
  branchId: string,
  playerA: string,
  playerB: string,
): SelectedPublishedH2H | null {
  const a = playerA.trim()
  const b = playerB.trim()
  if (!a || !b || a === b || !runId.trim() || !branchId.trim() ||
      sources.length === 0 || sources.length > MAX_SELECTED_H2H_EVENTS ||
      new Set(sources.map(source => source.entry.event.event_id)).size !== sources.length) {
    return null
  }

  const encounters: PublishedH2HEncounter[] = []
  let publicationMatchCount = 0
  const drawOrder: ViewerTournamentResultMatch['draw_type'][] =
    ['qualification', 'group', 'main', 'knockout']
  function startStats(playerId: string): SelectedPlayerPublishedStats {
    return {
      playerId, listedInEvents: 0, winsAgainstNamedOpponents: 0,
      lossesAgainstNamedOpponents: 0, noOpponentOutcomes: 0,
      uniqueNamedOpponents: 0,
      byDraw: drawOrder.map(draw => ({ draw, wins: 0, losses: 0 })),
      byEvent: [],
    }
  }
  const playerAStats = startStats(a)
  const playerBStats = startStats(b)
  const opponentsA = new Set<string>()
  const opponentsB = new Set<string>()
  for (const source of sources) {
    const verified = verifiedSavedMatchResult(
      source.data, source.entry, runId, branchId,
    )
    if (!verified) return null
    publicationMatchCount += verified.matches.length

    const eventRows: SelectedPlayerEventRecord[] = [a, b].map(playerId => ({
      eventId: source.entry.event.event_id,
      eventName: source.entry.event.event_name,
      season: String(source.entry.event.season),
      week: source.entry.event.season_week,
      listedAsParticipant: verified.players.some(player => player.player_id === playerId),
      wins: 0, losses: 0, noOpponentOutcomes: 0,
    }))
    const playerStats = [playerAStats, playerBStats]
    const opponents = [opponentsA, opponentsB]
    playerStats.forEach((stats, index) => {
      if (eventRows[index].listedAsParticipant) stats.listedInEvents++
      stats.byEvent.push(eventRows[index])
    })

    for (const match of verified.matches) {
      playerStats.forEach((stats, index) => {
        const row = eventRows[index]
        const playerId = stats.playerId
        if (match.winner_player_id === playerId && match.loser_player_id === null) {
          // A BYE/unopposed result must never inflate recorded wins vs rivals.
          stats.noOpponentOutcomes++
          row.noOpponentOutcomes++
        } else if (match.winner_player_id === playerId && match.loser_player_id) {
          stats.winsAgainstNamedOpponents++
          stats.byDraw.find(x => x.draw === match.draw_type)!.wins++
          row.wins++
          opponents[index].add(match.loser_player_id)
        } else if (match.loser_player_id === playerId) {
          stats.lossesAgainstNamedOpponents++
          stats.byDraw.find(x => x.draw === match.draw_type)!.losses++
          row.losses++
          opponents[index].add(match.winner_player_id)
        }
      })

      if (!match.loser_player_id || !(
        (match.winner_player_id === a && match.loser_player_id === b) ||
        (match.winner_player_id === b && match.loser_player_id === a)
      )) continue
      encounters.push({
        eventId: source.entry.event.event_id,
        eventName: source.entry.event.event_name,
        season: String(source.entry.event.season),
        week: source.entry.event.season_week,
        matchId: match.match_id,
        draw: match.draw_type,
        round: match.round_number,
        bracketPosition: match.bracket_position,
        winnerId: match.winner_player_id,
        loserId: match.loser_player_id,
        scoreline: match.scoreline,
      })
    }
  }
  playerAStats.uniqueNamedOpponents = opponentsA.size
  playerBStats.uniqueNamedOpponents = opponentsB.size
  for (const stats of [playerAStats, playerBStats]) {
    stats.byEvent.sort((x, y) =>
      x.season.localeCompare(y.season, undefined, { numeric: true }) ||
      x.week - y.week || x.eventId.localeCompare(y.eventId)
    )
  }
  encounters.sort((x, y) =>
    x.season.localeCompare(y.season, undefined, { numeric: true }) ||
    x.week - y.week || x.eventId.localeCompare(y.eventId) ||
    x.round - y.round || x.bracketPosition - y.bracketPosition ||
    x.matchId.localeCompare(y.matchId)
  )
  return {
    playerA: a, playerB: b,
    eventCount: sources.length, publicationMatchCount,
    winsA: encounters.filter(item => item.winnerId === a).length,
    winsB: encounters.filter(item => item.winnerId === b).length,
    encounters,
    playerAStats, playerBStats,
  }
}

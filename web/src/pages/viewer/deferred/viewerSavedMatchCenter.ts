import type {
  ViewerTournamentResult, ViewerTournamentResultMatch,
} from '../../../api/types'
import type { SavedTournamentEntry } from '../tour/viewerTournamentCatalog'

const resultFields = new Set([
  'schema_version', 'product_run_id', 'viewer_branch_id', 'event_id',
  'completed_season_index', 'completed_week', 'champion_player_id',
  'finalist_player_id', 'qualification_winner_ids', 'players', 'matches',
])
const matchFields = new Set([
  'match_id', 'draw_type', 'round_number', 'bracket_position',
  'winner_player_id', 'loser_player_id', 'scoreline',
])
const playerFields = new Set([
  'player_id', 'draw_type', 'seed_number', 'qualifier', 'main_entry_status',
  'reached_stage', 'final_round_number', 'eliminated_by_player_id',
  'last_match_id', 'wins', 'losses', 'byes_received', 'walkovers_received',
  'retired_or_walkover_loss', 'group_index', 'group_position',
  'played_group_wins', 'group_walkovers_received', 'knockout_reached_stage',
])
const validDraws = new Set(['qualification', 'main', 'group', 'knockout'])
const validPlayerDraws = new Set(['qualification', 'main', 'both', 'hybrid', 'group'])
const validEntryStatuses = new Set(['direct', 'wild_card', 'lucky_loser'])
const whole = (n: unknown, min = 0, max = Number.MAX_SAFE_INTEGER): n is number =>
  typeof n === 'number' && Number.isSafeInteger(n) && n >= min && n <= max
const nonblank = (n: unknown): n is string =>
  typeof n === 'string' && n.trim().length > 0 && n.length <= 500
const optionalString = (n: unknown): n is string | null =>
  n === null || nonblank(n)
const record = (n: unknown): n is Record<string, unknown> =>
  Boolean(n) && typeof n === 'object' && !Array.isArray(n)
const exactFields = (n: Record<string, unknown>, allowed: Set<string>): boolean =>
  Object.keys(n).every(key => allowed.has(key)) &&
  [...allowed].every(key => Object.prototype.hasOwnProperty.call(n, key))

/**
 * Public provenance gate: the tournament must be *published* in the separately
 * verified Calendar+History catalog, and the result must describe precisely
 * that event, branch, winner and finalist. All returned records are restricted
 * to the v1 public fields — never forward unexpected private metadata.
 *
 * We do not infer chronology, rally detail, ranking shifts or live scores from
 * this static published Tournament Result read model (legacy W61 only).
 */
export function verifiedSavedMatchResult(
  raw: unknown, entry: SavedTournamentEntry, runId: string, branchId: string,
): ViewerTournamentResult | null {
  if (!entry.publication.result_published || !record(raw) ||
      !nonblank(runId) || !nonblank(branchId) ||
      !exactFields(raw, resultFields) ||
      raw.schema_version !== 'viewer_tournament_result.v1' ||
      raw.product_run_id !== runId || raw.viewer_branch_id !== branchId ||
      raw.event_id !== entry.event.event_id ||
      !whole(raw.completed_season_index) ||
      // Results can be published after a multi-week event finishes; the
      // scheduled occurrence week is not necessarily its completion week.
      !whole(entry.event.start_season_week, 1, 61) ||
      !whole(entry.event.end_season_week, entry.event.start_season_week, 61) ||
      !whole(entry.event.season_week,
        entry.event.start_season_week, entry.event.end_season_week) ||
      !whole(raw.completed_week,
        entry.event.start_season_week, entry.event.end_season_week) ||
      raw.champion_player_id !== entry.publication.champion_player_id ||
      raw.finalist_player_id !== entry.publication.finalist_player_id ||
      !Array.isArray(raw.players) || !Array.isArray(raw.matches) ||
      !Array.isArray(raw.qualification_winner_ids) ||
      !raw.qualification_winner_ids.every(nonblank)) return null

  const ids = new Set<string>()
  for (const item of raw.players) {
    if (!record(item) || !exactFields(item, playerFields) ||
        !nonblank(item.player_id) || ids.has(item.player_id) ||
        !validPlayerDraws.has(item.draw_type as string) ||
        !whole(item.wins) || !whole(item.losses) ||
        !whole(item.byes_received) || !whole(item.walkovers_received) ||
        typeof item.qualifier !== 'boolean' ||
        typeof item.retired_or_walkover_loss !== 'boolean' ||
        !nonblank(item.reached_stage) ||
        !optionalString(item.eliminated_by_player_id) ||
        !optionalString(item.last_match_id) ||
        !optionalString(item.knockout_reached_stage) ||
        (item.seed_number !== null && !whole(item.seed_number, 1)) ||
        (item.final_round_number !== null && !whole(item.final_round_number, 1)) ||
        (item.group_index !== null && !whole(item.group_index)) ||
        (item.group_position !== null && !whole(item.group_position, 1)) ||
        (item.played_group_wins !== null && !whole(item.played_group_wins)) ||
        (item.group_walkovers_received !== null && !whole(item.group_walkovers_received)) ||
        (item.main_entry_status !== null && !validEntryStatuses.has(item.main_entry_status as string))
    ) return null
    ids.add(item.player_id as string)
  }
  if (!ids.has(raw.champion_player_id as string) ||
      !ids.has(raw.finalist_player_id as string) ||
      raw.champion_player_id === raw.finalist_player_id ||
      new Set(raw.qualification_winner_ids).size !== raw.qualification_winner_ids.length ||
      !raw.qualification_winner_ids.every((id: string) => ids.has(id))) return null

  const matches = new Set<string>()
  for (const item of raw.matches) {
    if (!record(item) || !exactFields(item, matchFields) ||
        !nonblank(item.match_id) || matches.has(item.match_id) ||
        !validDraws.has(item.draw_type as string) ||
        !whole(item.round_number, 1) || !whole(item.bracket_position, 1) ||
        !nonblank(item.winner_player_id) ||
        !ids.has(item.winner_player_id as string) ||
        !optionalString(item.loser_player_id) ||
        (item.loser_player_id !== null &&
          (!ids.has(item.loser_player_id as string) ||
           item.loser_player_id === item.winner_player_id)) ||
        typeof item.scoreline !== 'string' || item.scoreline.length > 100
    ) return null
    matches.add(item.match_id as string)
  }
  return raw as ViewerTournamentResult
}

export type PublicMatchDraw = 'all' | ViewerTournamentResultMatch['draw_type']
const drawOrder: Record<ViewerTournamentResultMatch['draw_type'], number> = {
  qualification: 0, group: 1, main: 2, knockout: 3,
}

export function filterPublishedMatches(
  matches: readonly ViewerTournamentResultMatch[],
  search: string, draw: PublicMatchDraw,
): ViewerTournamentResultMatch[] {
  const term = search.trim().toLocaleLowerCase()
  return matches.filter(item =>
    (draw === 'all' || item.draw_type === draw) &&
    (!term || [
      item.match_id, item.winner_player_id, item.loser_player_id ?? '', item.scoreline,
    ].some(value => value.toLocaleLowerCase().includes(term)))
  ).sort((a, b) =>
    drawOrder[a.draw_type] - drawOrder[b.draw_type] ||
    a.round_number - b.round_number ||
    a.bracket_position - b.bracket_position ||
    a.match_id.localeCompare(b.match_id)
  )
}

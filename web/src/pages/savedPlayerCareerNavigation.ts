/** Read-only URL and page guards for current-HEAD player career/replay. */
import type { SavedPlayerMatch, SavedPlayerMatchDetail } from '../api/types'

export const CAREER_PAGE_SIZE = 20
export const REPLAY_PAGE_SIZE = 25
// Limit untrusted URL inputs before they can trigger a large server offset.
export const MAX_CAREER_PAGE = 10000
export const MAX_REPLAY_RALLY = 100000

/** Reject duplicate URL keys instead of trusting URLSearchParams.get's first value. */
export function hasAmbiguousPlayerLinkParams(params: URLSearchParams, keys: readonly string[]): boolean {
  return keys.some(key => params.getAll(key).length > 1)
}

export function parseCareerSeason(raw: string | null): string | null {
  return raw === null ? 'all' : /^(0|[1-9]\d*)$/.test(raw) && Number(raw) <= 49 ? raw : null
}
export function parseCareerPage(raw: string | null): number | null {
  if (raw === null) return 0
  if (!/^(0|[1-9]\d*)$/.test(raw)) return null
  const value = Number(raw)
  return Number.isSafeInteger(value) && value <= MAX_CAREER_PAGE ? value : null
}
export function parseCareerOutcome(raw: string | null): 'all' | 'win' | 'loss' | null {
  return raw === null ? 'all' : raw === 'all' || raw === 'win' || raw === 'loss' ? raw : null
}
export function parseCareerCompletion(raw: string | null): 'all' | 'played' | 'walkover' | null {
  return raw === null ? 'all' : raw === 'all' || raw === 'played' || raw === 'walkover' ? raw : null
}
export function totalCareerPages(total: number): number {
  return Number.isSafeInteger(total) && total >= 0 ? Math.ceil(total / CAREER_PAGE_SIZE) : 0
}
/** Do not present an omitted/duplicated result window as an empty filter.
 * The backend guarantees stable event+match keys within a saved career. */
export function validCareerResultWindow(
  total: number, offset: number, limit: number,
  matches: readonly Pick<SavedPlayerMatch, 'event_id' | 'match_id'>[],
  identityUnavailable: boolean,
): boolean {
  if (!Number.isSafeInteger(total) || total < 0 ||
    !Number.isSafeInteger(offset) || offset < 0 ||
    !Number.isSafeInteger(limit) || limit !== CAREER_PAGE_SIZE ||
    !Array.isArray(matches) || matches.length > limit) return false
  if (identityUnavailable) return total === 0 && matches.length === 0
  const expected = Math.max(0, Math.min(limit, total - offset))
  if ((expected > 0 && matches.length === 0) ||
    (expected === 0 && matches.length !== 0) ||
    new Set(matches.map(m => JSON.stringify([m.event_id, m.match_id]))).size !== matches.length)
    return false
  return true
}

export function parsePageInput(raw: string, totalPages: number): number | null {
  if (!/^[1-9]\d*$/.test(raw)) return null
  const oneBased = Number(raw)
  return Number.isSafeInteger(oneBased) && oneBased <= Math.min(MAX_CAREER_PAGE + 1, totalPages)
    ? oneBased - 1 : null
}
export function matchLoadedCareer(
  match: SavedPlayerMatch, names: Record<string, string>,
  search: string, outcome: 'all' | 'win' | 'loss',
  completion: 'all' | 'played' | 'walkover',
): boolean {
  if (outcome !== 'all' && match.outcome !== outcome) return false
  if (completion !== 'all' && match.completion !== completion) return false
  const query = search.trim().toLocaleLowerCase()
  if (!query) return true
  return [match.event_name, match.event_id, match.match_id,
    match.opponent_player_id, names[match.opponent_player_id] ?? '', match.scoreline]
    .some(value => value.toLocaleLowerCase().includes(query))
}
export function parsePlayerRally(raw: string | null): number | null {
  if (raw === null) return 1
  if (!/^[1-9]\d*$/.test(raw)) return null
  const value = Number(raw)
  return Number.isSafeInteger(value) && value <= MAX_REPLAY_RALLY ? value : null
}
export function validPlayerReplayPagePair(
  previous: SavedPlayerMatchDetail, next: SavedPlayerMatchDetail,
): boolean {
  const identity = ['schema_version', 'source', 'run_id', 'branch_id',
    'saved_revision_id', 'player_id', 'winner_player_id', 'loser_player_id',
    'replay_status', 'player_a_id', 'player_b_id', 'total_rallies', 'limit'] as const
  const matchIdentity = ['event_id', 'event_name', 'match_id', 'season_index',
    'season', 'week', 'draw_type', 'round_number', 'opponent_player_id',
    'outcome', 'completion', 'scoreline'] as const
  if (previous.replay_status !== 'available' || next.replay_status !== 'available' ||
    !identity.every(key => previous[key] === next[key]) ||
    !matchIdentity.every(key => previous.match[key] === next.match[key]) ||
    previous.offset + previous.limit !== next.offset ||
    previous.limit !== REPLAY_PAGE_SIZE ||
    previous.offset >= previous.total_rallies || next.offset >= next.total_rallies ||
    !previous.has_more ||
    previous.rallies.length === 0 || next.rallies.length === 0) return false
  const a = previous.rallies[previous.rallies.length - 1]
  const b = next.rallies[0]
  if (a.rally_index + 1 !== b.rally_index || a.match_complete) return false
  const setsA = b.sets_a_after - a.sets_a_after
  const setsB = b.sets_b_after - a.sets_b_after
  // A new rally either awards one completed game or none; earned games
  // cannot disappear when crossing a saved 25-rally page boundary.
  if (setsA < 0 || setsB < 0 || setsA + setsB !== Number(b.set_complete)) return false
  // The first rally after a completed game begins at 0:0; otherwise the
  // exact score and set number must continue.
  return a.set_complete
    ? b.set_number === a.set_number + 1 && b.score_a_before === 0 && b.score_b_before === 0
    : b.set_number === a.set_number &&
      a.score_a_after === b.score_a_before && a.score_b_after === b.score_b_before
}

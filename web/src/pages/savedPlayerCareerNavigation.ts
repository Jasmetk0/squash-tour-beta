/** Read-only URL and page guards for current-HEAD player career/replay. */
import type { SavedPlayerMatch, SavedPlayerMatchDetail } from '../api/types'

export const CAREER_PAGE_SIZE = 20
export const REPLAY_PAGE_SIZE = 25
// Limit untrusted URL inputs before they can trigger a large server offset.
export const MAX_CAREER_PAGE = 10000
export const MAX_REPLAY_RALLY = 100000

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
  if (previous.replay_status !== 'available' || next.replay_status !== 'available' ||
    previous.total_rallies !== next.total_rallies ||
    previous.run_id !== next.run_id || previous.branch_id !== next.branch_id ||
    previous.saved_revision_id !== next.saved_revision_id ||
    previous.player_id !== next.player_id ||
    previous.match.event_id !== next.match.event_id ||
    previous.match.match_id !== next.match.match_id ||
    previous.player_a_id !== next.player_a_id || previous.player_b_id !== next.player_b_id ||
    previous.offset + REPLAY_PAGE_SIZE !== next.offset ||
    previous.offset >= previous.total_rallies || next.offset >= next.total_rallies ||
    previous.rallies.length === 0 || next.rallies.length === 0) return false
  const a = previous.rallies[previous.rallies.length - 1]
  const b = next.rallies[0]
  if (a.rally_index + 1 !== b.rally_index || a.match_complete) return false
  // The first rally after a completed game begins at 0:0; within the game
  // scores must carry over exactly. The API still owns complete replay proof.
  return a.set_complete
    ? b.set_number === a.set_number + 1 && b.score_a_before === 0 && b.score_b_before === 0
    : b.set_number === a.set_number &&
      a.score_a_after === b.score_a_before && a.score_b_after === b.score_b_before
}

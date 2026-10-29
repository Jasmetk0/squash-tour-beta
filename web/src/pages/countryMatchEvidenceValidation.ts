/** Exact read-only Country match record evidence guard; API remains the authority. */
import type { CountryMatchRecordHighlights, CountryMatchRecordKey } from '../api/types'
import { calendarSeasonIndex } from './runWorldCountryTournaments'

export const COUNTRY_EVIDENCE_PAGE_SIZE = 25
export type CountryEvidenceScope = {
  runId: string
  branchId: string
  countryCode: string
  revision: string
  fromSeason: number
  fromWeek: number
  toSeason: number
  toWeek: number
  selected: CountryMatchRecordKey | null
  offset: number
}
const keys: readonly CountryMatchRecordKey[] = ['played_wins', 'played_matches']
const count = (n: number): boolean => Number.isSafeInteger(n) && n >= 0

export function validCountryMatchEvidence(
  data: CountryMatchRecordHighlights | undefined, scope: CountryEvidenceScope,
): data is CountryMatchRecordHighlights {
  if (!data || data.schema_version !== 'country_match_record_highlights.v1' ||
    data.source !== 'reachable_saved_revision' ||
    data.run_id !== scope.runId || data.branch_id !== scope.branchId ||
    data.country_code !== scope.countryCode || data.saved_revision_id !== scope.revision ||
    !data.revision_branch_id?.trim() ||
    data.from_season !== scope.fromSeason || data.from_week !== scope.fromWeek ||
    data.to_season !== scope.toSeason || data.to_week !== scope.toWeek ||
    data.selected_record !== scope.selected ||
    data.offset !== scope.offset || data.limit !== COUNTRY_EVIDENCE_PAGE_SIZE ||
    !count(data.period_country_matches) || !count(data.period_played_matches) ||
    !count(data.period_walkovers) || !count(data.evidence_count) ||
    data.period_country_matches !== data.period_played_matches + data.period_walkovers ||
    !Array.isArray(data.records) || data.records.length !== keys.length ||
    !Array.isArray(data.evidence) || typeof data.has_more !== 'boolean') return false

  const summaries = new Map(data.records.map(r => [r?.key, r]))
  if (summaries.size !== keys.length || !keys.every(key => summaries.has(key))) return false
  for (const key of keys) {
    const record = summaries.get(key)
    if (!record || !count(record.value) || !Array.isArray(record.holders) ||
      (record.value === 0) !== (record.holders.length === 0)) return false
    const holders = new Set<string>()
    for (const h of record.holders) {
      if (!h || !h.player_id?.trim() || !h.player_name?.trim() ||
        h.value !== record.value || holders.has(h.player_id)) return false
      holders.add(h.player_id)
    }
  }

  if (scope.selected === null) {
    return data.offset === 0 && data.evidence_count === 0 &&
      data.evidence.length === 0 && data.has_more === false
  }
  const summary = summaries.get(scope.selected)!
  const holderIds = new Set(summary.holders.map(h => h.player_id))
  const expected = Math.max(0, Math.min(COUNTRY_EVIDENCE_PAGE_SIZE,
    data.evidence_count - scope.offset))
  if (data.evidence.length !== expected ||
    data.has_more !== (scope.offset + COUNTRY_EVIDENCE_PAGE_SIZE < data.evidence_count) ||
    data.evidence_count > data.period_played_matches) return false
  if (data.evidence_count === 0 && summary.value !== 0) return false
  const uniqueMatches = new Set<string>()
  const from = scope.fromSeason * 61 + scope.fromWeek
  const to = scope.toSeason * 61 + scope.toWeek
  for (const match of data.evidence) {
    if (!match || match.completion !== 'played' ||
      !match.event_id?.trim() || !match.match_id?.trim() ||
      !match.event_name?.trim() || !match.scoreline?.trim() ||
      !match.winner_player_id?.trim() || !match.loser_player_id?.trim() ||
      match.winner_player_id === match.loser_player_id) return false
    const id = JSON.stringify([match.event_id, match.match_id])
    if (uniqueMatches.has(id)) return false
    uniqueMatches.add(id)
    const season = calendarSeasonIndex(match.season)
    if (season === null || !Number.isSafeInteger(match.season_week) ||
      match.season_week < 1 || match.season_week > 61 ||
      season * 61 + match.season_week < from ||
      season * 61 + match.season_week > to) return false
    const winner = match.winner_country === scope.countryCode &&
      holderIds.has(match.winner_player_id)
    const loser = match.loser_country === scope.countryCode &&
      holderIds.has(match.loser_player_id)
    if (scope.selected === 'played_wins' ? !winner : !(winner || loser)) return false
  }
  return true
}

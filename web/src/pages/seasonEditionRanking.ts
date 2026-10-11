import type { SeasonCalendarEvent } from '../api/types'

type RankingFields = 'ranking_status' | 'ranking_points_table' | 'ranking_configuration_legacy' |
  'required_ranking_point_stages' | 'missing_required_point_stages' | 'points_table_complete'
type LegacySeasonCalendarEvent = Omit<SeasonCalendarEvent, RankingFields> & Partial<Pick<SeasonCalendarEvent, RankingFields>>

export function normalizeEditionRanking(event: LegacySeasonCalendarEvent): SeasonCalendarEvent {
  return {
    ...event,
    ranking_status: event.ranking_status ?? 'ranked',
    ranking_points_table: event.ranking_points_table ?? {},
    ranking_configuration_legacy: event.ranking_configuration_legacy ?? true,
    required_ranking_point_stages: event.required_ranking_point_stages ?? [],
    missing_required_point_stages: event.missing_required_point_stages ?? [],
    points_table_complete: event.points_table_complete ?? true
  }
}

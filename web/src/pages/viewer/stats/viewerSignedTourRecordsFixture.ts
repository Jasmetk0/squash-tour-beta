import type { TourCareerRecords } from '../../../api/calendarTour'

export function signedRecordFixture(): TourCareerRecords {
  const metrics = ['titles', 'finals', 'awarded_points'] as const
  const scopes = ['player', 'country'] as const
  return {
    schema_version: 'calendar_tour_signed_records_response.v1',
    run_id: 'record run', branch_id: 'viewer-a', saved_head_revision_id: 'revision-7',
    source_tour_fingerprint: 'a'.repeat(64),
    as_of_season_index: 1, from_season_index: 0, country_code: null,
    leaderboard_limit: 20, completed_seasons: [0, 1], completed_edition_count: 2,
    source_seasons: [
      { season_index: 0, season_label: '2000/01', boundary_command_id: 'closed-0',
        completed_edition_count: 0, source_tour_fingerprint: 'b'.repeat(64),
        published_ranking_fingerprint: 'c'.repeat(64) },
      { season_index: 1, season_label: '2001/02', boundary_command_id: 'closed-1',
        completed_edition_count: 2, source_tour_fingerprint: 'd'.repeat(64),
        published_ranking_fingerprint: 'e'.repeat(64) }
    ],
    records: scopes.flatMap(scope => metrics.map(metric => {
      const row = { entity_id: scope === 'player' ? 'p-1' : 'CZE',
        label: scope === 'player' ? 'Player One' : 'CZE', country_code: 'CZE',
        titles: 1, finals: 2, awarded_points: 150 }
      return {
        record_id: 'native_tour.' + scope + '.' + metric + '.v1',
        scope, metric, value: row[metric], holders: [row],
        holder_history: [{ season_index: 1, season_label: '2001/02',
          record_value: row[metric], holder_ids: [row.entity_id],
          holder_labels: [row.label], change: 'established' as const,
          boundary_command_id: 'closed-1' }],
        leaderboard: [{ ...row, rank: 1 }], leaderboard_total: 1
      }
    }))
  }
}


import type { SignedSeasonSummary, TourCareerRecords, TourSeasonComparison } from '../../../api/calendarTour'

export function signedSeasonListFixture(): TourCareerRecords {
  return {
    schema_version: 'calendar_tour_signed_records_response.v1',
    run_id: 'run alpha', branch_id: 'branch-tour', saved_head_revision_id: 'rev-20',
    source_tour_fingerprint: 'a'.repeat(64),
    from_season_index: 0, as_of_season_index: 1, country_code: null,
    leaderboard_limit: 20, completed_seasons: [0, 1],
    completed_edition_count: 3, records: [],
    source_seasons: [
      { season_index: 0, season_label: '2000/01', boundary_command_id: 'end-0',
        completed_edition_count: 1, source_tour_fingerprint: 'a'.repeat(64),
        published_ranking_fingerprint: 'b'.repeat(64) },
      { season_index: 1, season_label: '2001/02', boundary_command_id: 'end-1',
        completed_edition_count: 2, source_tour_fingerprint: 'a'.repeat(64),
        published_ranking_fingerprint: 'c'.repeat(64) }
    ]
  }
}

export function signedSeasonFixture(index: number): SignedSeasonSummary {
  return {
    schema_version: 'native_tour_signed_season_summary.v1',
    run_id: 'run alpha', branch_id: 'branch-tour',
    source_tour_fingerprint: 'a'.repeat(64),
    season_index: index, season_label: index === 0 ? '2000/01' : '2001/02',
    weeks_per_season: 52, boundary_command_id: 'end-' + index,
    next_season_index: index === 0 ? 1 : null,
    completed_edition_count: 1,
    countries: [{ country_code: 'CZE', titles: index === 0 ? 1 : 0,
      finals: 1, semifinals: 0, quarterfinals: 0,
      awarded_points: index === 0 ? 100 : 60,
      distinct_players: 2, edition_appearances: 1 }],
    editions: [{ edition_id: 'open-' + index, name: 'Open ' + index,
      week: 25, champion_player_id: 'p1', champion_name: 'Player One', champion_country: 'CZE',
      finalist_player_id: 'p2', finalist_name: 'Player Two', finalist_country: 'CZE',
      source_tournament_fingerprint: 'd'.repeat(64) }],
    players: [
      { player_id: 'p1', name: 'Player One', country_code: 'CZE',
        titles: index === 0 ? 1 : 0, finals: 0,
        awarded_points: index === 0 ? 100 : 60, edition_appearances: 1 }
    ],
    last_week_published_ranking: { week: 52, source_fingerprint: 'e'.repeat(64),
      top_players: [{ player_id: 'p1', rank: 1, points: 300 }] }
  }
}

export function signedSeasonComparisonFixture(compare = false): TourSeasonComparison {
  return {
    schema_version: 'calendar_tour_season_comparison.v1',
    run_id: 'run alpha', branch_id: 'branch-tour', saved_head_revision_id: 'rev-20',
    selected: signedSeasonFixture(1),
    comparison: compare ? signedSeasonFixture(0) : null,
    country_deltas: compare ?
      [{ country_code: 'CZE', titles_delta: -1, finals_delta: 0, awarded_points_delta: -40 }] : []
  }
}

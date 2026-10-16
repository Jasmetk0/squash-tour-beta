import type {CalendarPoolPreview} from './calendarInitialPool'

export const clock = {schema_version: 'run_calendar.v1' as const, weeks_per_year: 52,
  season_start_year_week: 35, start_year: 2030, season_count: 3}
export const input = {world_package_id: 'earth', seed: 802, target_pool_size: 1, min_age: 15, max_age: 45}
export function preview(count = 1): CalendarPoolPreview {
  return {schema_version: 'run_calendar_initial_pool_preview.v2', run_id: 'run-a', branch_id: 'branch-a',
    calendar_saved_revision_id: 'head-a', run_calendar: clock, run_package_state_fingerprint: 'a'.repeat(64),
    preview_fingerprint: 'b'.repeat(64), request: {...input, target_pool_size: count},
    preview_only: true, adoption_supported: false, limitations: ['preview_only'],
    result: {players: Array.from({length: count}, (_,i) => ({player_id: 'p'+i, name: 'Country '+(i+1), country_code: 'CZE',
      birth_year: 2012, birth_year_week: 1, age_at_generation: 18, current_age_years: 18,
      current_ability: 50, potential_ability: 70, created_for_season: '2030/2031',
      schema_version: 'initial_pool_player.v2', time_basis: {schema_version: 'initial_pool_calendar.v1',
        weeks_per_year: 52, season_start_year_week: 35, start_year: 2030}}))}}
}

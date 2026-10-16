import type { RunCalendarMetadata } from './runCalendarCreation'

export type CalendarPoolInput = {
  world_package_id: string; seed: number; target_pool_size: number; min_age: number; max_age: number
}
export type CalendarPoolPlayer = {
  player_id: string; name: string; country_code: string; birth_year: number; birth_year_week: number
  age_at_generation: number; current_age_years: number; current_ability: number; potential_ability: number
  created_for_season: string; schema_version: 'initial_pool_player.v2'
  time_basis: {schema_version: 'initial_pool_calendar.v1'; weeks_per_year: number; season_start_year_week: number; start_year: number}
}
export type CalendarPoolPreview = {
  schema_version: 'run_calendar_initial_pool_preview.v2'; run_id: string; branch_id: string
  calendar_saved_revision_id: string; run_calendar: RunCalendarMetadata
  run_package_state_fingerprint: string; preview_fingerprint: string
  request: CalendarPoolInput; preview_only: true; adoption_supported: false
  limitations: string[]; result: { players: CalendarPoolPlayer[] }
}

export function validateCalendarPoolPreview(value: unknown, runId: string, branchId: string,
  head: string, packageFingerprint: string, clock: RunCalendarMetadata, input: CalendarPoolInput): CalendarPoolPreview {
  const p = value as CalendarPoolPreview
  const hash = (v: unknown): boolean => typeof v === 'string' && /^[0-9a-f]{64}$/.test(v)
  const integer = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v)
  if (!p || p.schema_version !== 'run_calendar_initial_pool_preview.v2'
    || p.run_id !== runId || p.branch_id !== branchId || p.calendar_saved_revision_id !== head
    || p.preview_only !== true || p.adoption_supported !== false
    || p.run_package_state_fingerprint !== packageFingerprint || !hash(p.preview_fingerprint)
    || !p.run_calendar || Object.entries(clock).some(([k,v]) => p.run_calendar[k as keyof RunCalendarMetadata] !== v)
    || !p.request || Object.entries(input).some(([k,v]) =>
      JSON.stringify(p.request[k as keyof CalendarPoolInput]) !== JSON.stringify(v))
    || !Array.isArray(p.limitations) || !p.limitations.length || p.limitations.some(v => typeof v !== 'string')
    || !Array.isArray(p.result?.players) || p.result.players.length !== input.target_pool_size) {
    throw Error('Calendar player preview does not match the selected Run, Branch or source')
  }
  const ids = new Set<string>()
  for (const player of p.result.players) {
    const basis = player.time_basis
    const elapsed = (clock.start_year - player.birth_year) * clock.weeks_per_year
      + clock.season_start_year_week - player.birth_year_week
    if (player.schema_version !== 'initial_pool_player.v2' || !basis || basis.schema_version !== 'initial_pool_calendar.v1'
      || basis.weeks_per_year !== clock.weeks_per_year || basis.season_start_year_week !== clock.season_start_year_week
      || basis.start_year !== clock.start_year || typeof player.player_id !== 'string' || !player.player_id
      || ids.has(player.player_id) || typeof player.name !== 'string' || !player.name
      || typeof player.country_code !== 'string' || !/^[A-Z]{3}$/.test(player.country_code)
      || !integer(player.birth_year) || !integer(player.birth_year_week)
      || player.birth_year_week < 1 || player.birth_year_week > clock.weeks_per_year
      || !integer(player.current_age_years) || player.current_age_years !== Math.floor(elapsed / clock.weeks_per_year)
      || player.age_at_generation !== player.current_age_years || elapsed <= 15 * clock.weeks_per_year
      || player.current_age_years < input.min_age || player.current_age_years > input.max_age
      || player.created_for_season !== (clock.season_start_year_week === 1 ? String(clock.start_year) : `${clock.start_year}/${clock.start_year + 1}`)
      || !integer(player.current_ability) || player.current_ability < 1 || player.current_ability > 99
      || !integer(player.potential_ability) || player.potential_ability < 1 || player.potential_ability > 99) {
      throw Error('Invalid calendar player identity in preview')
    }
    ids.add(player.player_id)
  }
  return p
}

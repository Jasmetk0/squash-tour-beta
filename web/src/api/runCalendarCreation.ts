/** Calendar planning DTOs. These do not grant sporting execution authority. */
export type RunCalendarCreationInput = {
  weeks_per_year: number
  season_start_year_week: number
  start_year: number
} & ({ season_count: number; last_season_start_year?: never }
  | { last_season_start_year: number; season_count?: never })

export type RunCalendarMetadata = {
  schema_version: 'run_calendar.v1'
  weeks_per_year: number
  season_start_year_week: number
  start_year: number
  season_count: number
}

type PlannedWeek = {
  season_index: number; season_week: number; calendar_year: number
  year_week: number; season_label: string; week_ordinal: number
}

export type RunCalendarCreationPreview = {
  schema_version: 'run_calendar_configuration_preview.v1'
  read_only: true; run_created: false
  run_calendar: RunCalendarMetadata
  first_week: PlannedWeek; last_week: PlannedWeek
  sporting_calendar_supported: boolean
  limitations: string[]
}

export function expectedCreationCalendar(input: RunCalendarCreationInput): RunCalendarMetadata {
  return {
    schema_version: 'run_calendar.v1', weeks_per_year: input.weeks_per_year,
    season_start_year_week: input.season_start_year_week, start_year: input.start_year,
    season_count: input.season_count ?? (input.last_season_start_year! - input.start_year + 1)
  }
}

export function sameCreationCalendar(value: unknown, expected: RunCalendarMetadata): boolean {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  return Object.entries(expected).every(([key, item]) => record[key] === item)
}

export function validateCalendarCreationPreview(
  value: unknown, input: RunCalendarCreationInput
): RunCalendarCreationPreview {
  const v = value as RunCalendarCreationPreview
  const calendar = expectedCreationCalendar(input)
  if (!v || v.schema_version !== 'run_calendar_configuration_preview.v1'
    || v.read_only !== true || v.run_created !== false
    || !sameCreationCalendar(v.run_calendar, calendar)
    || typeof v.sporting_calendar_supported !== 'boolean'
    || !Array.isArray(v.limitations) || v.limitations.some(item => typeof item !== 'string')
    || (!v.sporting_calendar_supported && !v.limitations.length)) {
    throw Error('Invalid calendar creation preview')
  }
  const { weeks_per_year: w, season_start_year_week: offset, start_year: year, season_count: count } = calendar
  const validWeek = (actual: PlannedWeek, index: number, week: number): boolean => {
    const elapsed = offset - 1 + week - 1
    const seasonYear = year + index
    return !!actual && actual.season_index === index && actual.season_week === week
      && actual.calendar_year === seasonYear + Math.floor(elapsed / w)
      && actual.year_week === elapsed % w + 1 && actual.week_ordinal === index * w + week - 1
      && actual.season_label === (offset === 1 ? String(seasonYear) : `${seasonYear}/${seasonYear + 1}`)
  }
  if (!validWeek(v.first_week, 0, 1) || !validWeek(v.last_week, count - 1, w)) {
    throw Error('Calendar preview endpoints do not match the requested calendar')
  }
  return v
}

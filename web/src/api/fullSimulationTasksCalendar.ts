/** Read-only task clock. v2 is anchored to the original Saved Revision;
 * v1 is the explicitly legacy FAX API, never a fallback for broken v2 data. */
export type TaskCalendar = {
  schema_version: 'run_calendar.v1' | 'legacy_fax_calendar.v0'
  weeks_per_year: number
  season_start_year_week: number
  start_year: number
  season_count: number
}
export type TaskWeek = { season_index: number; week: number }

type ClockSource = {
  schema_version: string
  execution_calendar?: TaskCalendar
  calendar_revision_id?: string
  original_command?: { expected_revision_id: string }
}

const legacyCalendar: TaskCalendar = {
  schema_version: 'legacy_fax_calendar.v0', weeks_per_year: 61,
  season_start_year_week: 37, start_year: 2000, season_count: 50,
}

export function serverTaskCalendar(source: ClockSource): TaskCalendar {
  if (source.schema_version === 'full_simulation_task_view.v1') {
    if ('execution_calendar' in source || 'calendar_revision_id' in source) {
      throw Error('Invalid legacy server task calendar fields')
    }
    return {...legacyCalendar}
  }
  const c = source.execution_calendar
  const keys = ['schema_version', 'weeks_per_year', 'season_start_year_week', 'start_year', 'season_count']
  if (source.schema_version !== 'full_simulation_task_view.v2' || !c
    || typeof c !== 'object' || Array.isArray(c)
    || Object.keys(c).length !== keys.length || !keys.every(key => key in c)
    || !['run_calendar.v1', 'legacy_fax_calendar.v0'].includes(c.schema_version)
    || !Number.isSafeInteger(c.weeks_per_year) || c.weeks_per_year < 1
    || !Number.isSafeInteger(c.season_start_year_week)
    || c.season_start_year_week < 1 || c.season_start_year_week > c.weeks_per_year
    || !Number.isSafeInteger(c.start_year) || c.start_year < 0
    || !Number.isSafeInteger(c.season_count) || c.season_count < 1
    || c.start_year + c.season_count - 1 > 2147483647
    || !Number.isSafeInteger(c.weeks_per_year * c.season_count)
    || typeof source.calendar_revision_id !== 'string' || !source.calendar_revision_id
    || source.calendar_revision_id !== source.original_command?.expected_revision_id) {
    throw Error('Invalid Saved server task calendar')
  }
  if (c.schema_version === 'legacy_fax_calendar.v0'
    && keys.some(key => c[key as keyof TaskCalendar] !== legacyCalendar[key as keyof TaskCalendar])) {
    throw Error('Invalid legacy server task calendar values')
  }
  return c
}

export function validTaskWeek(value: unknown, calendar: TaskCalendar): value is TaskWeek {
  const w = value as TaskWeek
  return !!w && Number.isSafeInteger(w.season_index) && w.season_index >= 0
    && w.season_index < calendar.season_count && Number.isSafeInteger(w.week)
    && w.week >= 1 && w.week <= calendar.weeks_per_year
}

export function taskWeekOrdinal(value: TaskWeek, calendar: TaskCalendar): number {
  if (!validTaskWeek(value, calendar)) throw Error('Invalid server task week')
  return value.season_index * calendar.weeks_per_year + value.week - 1
}

export function taskCalendarPosition(source: ClockSource, week: TaskWeek) {
  const calendar = serverTaskCalendar(source)
  taskWeekOrdinal(week, calendar)
  const year = calendar.start_year + week.season_index
  // Avoid adding two individually exact but potentially near-MAX_SAFE values.
  const weeksBeforeNextYear = calendar.weeks_per_year - calendar.season_start_year_week + 1
  const nextYear = week.week > weeksBeforeNextYear
  return {
    seasonStartYear: year,
    seasonLabel: calendar.season_start_year_week === 1 ? String(year) : `${year}/${year + 1}`,
    calendarYear: year + (nextYear ? 1 : 0),
    yearWeek: nextYear ? week.week - weeksBeforeNextYear : calendar.season_start_year_week - 1 + week.week,
  }
}

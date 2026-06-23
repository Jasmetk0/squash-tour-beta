export type CalendarEventDraftStatus = 'draft' | 'canonical' | 'template'

export interface CalendarEventDraft {
  id: string
  name: string
  categoryCode: string
  weeks: number[]
  qualificationWeeks: number[]
  locked: boolean
  countryCode?: string
  city?: string
  venue?: string
  notes?: string
  status?: CalendarEventDraftStatus
}

const MIN_SEASON_WEEK = 1
const MAX_SEASON_WEEK = 61

/**
 * Returns sorted unique season weeks. Empty arrays are valid here to represent
 * draft events that are not scheduled yet; editor/business rules can require
 * main weeks later when a draft is applied to a real calendar.
 */
export function normalizeSeasonWeeks(weeks: number[]): number[] {
  return [...new Set(weeks)].sort((a, b) => a - b)
}

export function formatSeasonWeeks(weeks: number[]): string {
  const normalizedWeeks = normalizeSeasonWeeks(weeks)

  if (!normalizedWeeks.length) {
    return '—'
  }

  const ranges: string[] = []
  let rangeStart = normalizedWeeks[0]
  let previousWeek = normalizedWeeks[0]

  for (const week of normalizedWeeks.slice(1)) {
    if (week === previousWeek + 1) {
      previousWeek = week
      continue
    }

    ranges.push(formatWeekRange(rangeStart, previousWeek))
    rangeStart = week
    previousWeek = week
  }

  ranges.push(formatWeekRange(rangeStart, previousWeek))
  return ranges.join(', ')
}

/**
 * Validates basic season-week shape only. Empty arrays are valid here as
 * "not scheduled yet" placeholders for future admin draft templates.
 */
export function validateSeasonWeeks(weeks: number[]): string[] {
  const errors: string[] = []
  const seen = new Set<number>()

  weeks.forEach((week, index) => {
    if (!Number.isInteger(week)) {
      errors.push(`Week at position ${index + 1} must be an integer.`)
      return
    }

    if (week < MIN_SEASON_WEEK || week > MAX_SEASON_WEEK) {
      errors.push(`Week ${week} must be between ${MIN_SEASON_WEEK} and ${MAX_SEASON_WEEK}.`)
    }

    if (seen.has(week)) {
      errors.push(`Week ${week} is duplicated.`)
    }
    seen.add(week)
  })

  return errors
}

export function describeCalendarEventTiming(event: CalendarEventDraft): string {
  const parts: string[] = []

  if (event.qualificationWeeks.length) {
    parts.push(`Qualifying ${formatSeasonWeeks(event.qualificationWeeks)}`)
  }

  parts.push(`Main ${formatSeasonWeeks(event.weeks)}`)
  return parts.join(' · ')
}

function formatWeekRange(startWeek: number, endWeek: number): string {
  return startWeek === endWeek ? `W${startWeek}` : `W${startWeek}–W${endWeek}`
}

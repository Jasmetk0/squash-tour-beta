import { describe, expect, it } from 'vitest'
import { describeCalendarEventTiming, formatSeasonWeeks, normalizeSeasonWeeks, validateSeasonWeeks } from './calendarEventModel'
import type { CalendarEventDraft } from './calendarEventModel'

describe('calendarEventModel', () => {
  it('formats empty, single-week, contiguous, and split season week ranges', () => {
    expect(formatSeasonWeeks([])).toBe('—')
    expect(formatSeasonWeeks([6])).toBe('W6')
    expect(formatSeasonWeeks([6, 7])).toBe('W6–W7')
    expect(formatSeasonWeeks([5, 7])).toBe('W5, W7')
    expect(formatSeasonWeeks([5, 6, 7])).toBe('W5–W7')
    expect(formatSeasonWeeks([5, 6, 8])).toBe('W5–W6, W8')
  })

  it('normalizes season weeks by sorting ascending and removing duplicates', () => {
    expect(normalizeSeasonWeeks([7, 5, 5])).toEqual([5, 7])
  })

  it('validates season week bounds, integer shape, and duplicates', () => {
    expect(validateSeasonWeeks([])).toEqual([])
    expect(validateSeasonWeeks([0])).toContain('Week 0 must be between 1 and 61.')
    expect(validateSeasonWeeks([62])).toContain('Week 62 must be between 1 and 61.')
    expect(validateSeasonWeeks([5.5])).toContain('Week at position 1 must be an integer.')
    expect(validateSeasonWeeks([5, 5])).toContain('Week 5 is duplicated.')
  })

  it('describes calendar event timing with qualification and main weeks', () => {
    const event: CalendarEventDraft = {
      id: 'nemarque-open-example',
      name: 'Némarque Open',
      categoryCode: 'DIAMOND',
      qualificationWeeks: [5],
      weeks: [6, 7],
      locked: true,
      status: 'template'
    }

    expect(describeCalendarEventTiming(event)).toBe('Qualifying W5 · Main W6–W7')
  })

  it('describes calendar event timing without qualification and with unscheduled main weeks', () => {
    expect(describeCalendarEventTiming({
      id: 'world-tour-finals-example',
      name: 'World Tour Finals',
      categoryCode: 'WORLD_TOUR_FINALS',
      qualificationWeeks: [],
      weeks: [55],
      locked: true,
      status: 'template'
    })).toBe('Main W55')

    expect(describeCalendarEventTiming({
      id: 'draft-placeholder-example',
      name: 'Draft Placeholder',
      categoryCode: 'GOLD',
      qualificationWeeks: [],
      weeks: [],
      locked: false,
      status: 'draft'
    })).toBe('Main —')
  })
})

import { describe, expect, it } from 'vitest'

import { buildViewerContextSummaryItems, formatViewerContextButtonLabel, formatViewerWeekLabel, normalizeViewerWeekInput } from './viewerContextDisplay'

describe('viewerContextDisplay', () => {
  it('formats the existing Viewer season/week button and jump labels', () => {
    expect(formatViewerContextButtonLabel({ selectedSeason: '2004/05', selectedWeek: 10 })).toBe('Season 2004/05 · W10')
    expect(formatViewerWeekLabel(24)).toBe('W24')
  })

  it('builds the existing Viewer context metadata text values', () => {
    expect(
      buildViewerContextSummaryItems({
        selectedSeason: '2004/05',
        selectedWeek: 10,
        seasonWeekCount: 61,
        calendarYear: 2004,
        yearWeek: 46
      })
    ).toEqual([
      { label: 'Season Week', value: '10 / 61' },
      { label: 'Calendar Year', value: '2004' },
      { label: 'Year Week', value: '46' },
      { label: 'Status', value: 'selected viewer context; stored locally in this browser.' }
    ])
  })

  it('normalizes Viewer week input with the same Number conversion used by the selector', () => {
    expect(normalizeViewerWeekInput('24')).toBe(24)
    expect(normalizeViewerWeekInput('')).toBe(0)
    expect(Number.isNaN(normalizeViewerWeekInput('not-a-week'))).toBe(true)
  })
})

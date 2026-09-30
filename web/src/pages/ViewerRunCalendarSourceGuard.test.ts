import calendarSource from './ViewerRunCalendarPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('ViewerRunCalendarPage canonical source guard', () => {
  it('uses Saved Calendar authority and canonical Viewer publication readers', () => {
    expect(calendarSource).toContain('getViewerRunCalendar')
    expect(calendarSource).toContain('getViewerTournamentHistory')
    expect(calendarSource).toContain('listViewerOfficialRankingHistory')
  })

  it('does not reintroduce legacy run/event calendar readers', () => {
    expect(calendarSource).not.toContain('getRun(')
    expect(calendarSource).not.toContain('listEvents(')
    expect(calendarSource).not.toContain('listRankingSnapshots(')
  })

  it('keeps legacy compatibility explicit only for Race snapshots', () => {
    expect(calendarSource).toContain('listRaceSnapshots')
    expect(calendarSource).toContain('viewerRaceSnapshotPath')
  })
})

import currentWeekSource from './ViewerTourCurrentWeekPage.tsx?raw'
import seasonHubSource from './ViewerSeasonHubPage.tsx?raw'
import tournamentsSource from './ViewerTournamentsPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('Viewer canonical Tour hub source guard', () => {
  it('uses Product Run canonical authorities', () => {
    expect(seasonHubSource).toContain('getViewerRunCalendar')
    expect(seasonHubSource).toContain('getViewerTournamentHistory')
    expect(seasonHubSource).toContain('getViewerFinalsRace')
    expect(tournamentsSource).toContain('getViewerRunCalendar')
    expect(tournamentsSource).toContain('getViewerTournamentHistory')
    expect(currentWeekSource).toContain('getViewerRunCalendar')
    for (const source of [seasonHubSource, tournamentsSource, currentWeekSource]) {
      expect(source).toContain('useActiveViewerProductRunId')
    }
  })

  it('does not use legacy Viewer run/event/finals readers', () => {
    for (const source of [seasonHubSource, tournamentsSource, currentWeekSource]) {
      for (const legacyReader of [
        'useActiveViewerRunId',
        'getRun(',
        'getRunStatusSummary(',
        'listEvents(',
        'getFinalsSummary(',
      ]) {
        expect(source).not.toContain(legacyReader)
      }
    }
  })
})

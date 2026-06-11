import { describe, expect, it } from 'vitest'

import viewerHomeSource from './ViewerHomePage.tsx?raw'

describe('ViewerHomePage source guard', () => {
  it('normalizes activeRunId before Viewer Home active-run runtime behavior', () => {
    expect(viewerHomeSource).toContain('normalizeViewerHomeActiveRunId(activeRunId)')

    for (const forbiddenRawActiveRunUse of [
      'getRun(activeRunId',
      'getRunStatusSummary(activeRunId',
      'listEvents(activeRunId',
      'listRankingSnapshots(activeRunId',
      'listRaceSnapshots(activeRunId',
      'getRunActivity(activeRunId',
      'getFinalsSummary(activeRunId',
      'viewerRankingsPath(activeRunId',
      'viewerRacePath(activeRunId',
      'viewerTournamentsPath(activeRunId',
      'viewerSeasonCalendarPath(activeRunId',
      'viewerHistoryPath(activeRunId',
      'renderLinkedEventId(activeRunId',
      'renderLinkedWeek(activeRunId',
      'renderActivityItem(latestActivityItem, activeRunId'
    ]) {
      expect(viewerHomeSource).not.toContain(forbiddenRawActiveRunUse)
    }
  })
})

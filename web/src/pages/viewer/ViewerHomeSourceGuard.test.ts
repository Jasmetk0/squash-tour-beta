import { describe, expect, it } from 'vitest'

import viewerHomeSource from './ViewerHomePage.tsx?raw'

const strippedViewerHomeSource = viewerHomeSource
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/(^|\n)\s*\/\/.*(?=\n|$)/g, '$1')

describe('ViewerHomePage source guard', () => {
  it('normalizes activeRunId before Viewer Home active-run runtime behavior', () => {
    expect(strippedViewerHomeSource).toContain('normalizeViewerHomeActiveRunId(activeRunId)')
  })

  it('does not pass raw activeRunId into active-run API calls', () => {
    for (const forbiddenRawActiveRunUse of [
      'getRun(activeRunId',
      'getRunStatusSummary(activeRunId',
      'listEvents(activeRunId',
      'listRankingSnapshots(activeRunId',
      'listRaceSnapshots(activeRunId',
      'getRunActivity(activeRunId',
      'getFinalsSummary(activeRunId'
    ]) {
      expect(strippedViewerHomeSource).not.toContain(forbiddenRawActiveRunUse)
    }
  })

  it('does not pass raw activeRunId into active-run route helper calls', () => {
    for (const forbiddenRawActiveRunUse of [
      'viewerRankingsPath(activeRunId',
      'viewerRacePath(activeRunId',
      'viewerTournamentsPath(activeRunId',
      'viewerSeasonCalendarPath(activeRunId',
      'viewerHistoryPath(activeRunId',
      'viewerRankingSnapshotPath(activeRunId',
      'viewerRaceSnapshotPath(activeRunId',
      'viewerTournamentDetailPath(activeRunId',
      'viewerWeekDetailPath(activeRunId',
      'viewerPlannedEventPath(activeRunId',
      'renderLinkedEventId(activeRunId',
      'renderLinkedWeek(activeRunId',
      'renderActivityItem(latestActivityItem, activeRunId'
    ]) {
      expect(strippedViewerHomeSource).not.toContain(forbiddenRawActiveRunUse)
    }
  })

  it('does not reintroduce stale broad Home headings', () => {
    expect(strippedViewerHomeSource).not.toContain('Top 10 Rankings')
    expect(strippedViewerHomeSource).not.toContain('Race to Finals')
  })
})

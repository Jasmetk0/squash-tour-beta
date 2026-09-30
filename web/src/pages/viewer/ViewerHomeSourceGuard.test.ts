import { describe, expect, it } from 'vitest'

import viewerHomeSource from './ViewerHomePage.tsx?raw'

const strippedViewerHomeSource = viewerHomeSource
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/(^|\n)\s*\/\/.*(?=\n|$)/g, '$1')

describe('ViewerHomePage source guard', () => {
  it('normalizes activeRunId before Viewer Home active-run runtime behavior', () => {
    expect(strippedViewerHomeSource).toContain('normalizeViewerHomeActiveRunId(activeRunId)')
  })

  it('uses only canonical Viewer Home readers for active-run summaries', () => {
    for (const canonicalReader of [
      'getViewerOfficialRunContext',
      'getViewerTournamentHistory',
      'listViewerOfficialRankingHistory',
      'getViewerFinalsRace'
    ]) {
      expect(strippedViewerHomeSource).toContain(canonicalReader)
    }

    for (const legacyReader of [
      'getRun(',
      'getRunStatusSummary(',
      'listEvents(',
      'listRankingSnapshots(',
      'listRaceSnapshots(',
      'getRunActivity(',
      'getFinalsSummary('
    ]) {
      expect(strippedViewerHomeSource).not.toContain(legacyReader)
    }
  })

  it('does not pass raw activeRunId into active-run route helper calls', () => {
    for (const forbiddenRawActiveRunUse of [
      'viewerRankingsPath(activeRunId',
      'viewerRacePath(activeRunId',
      'viewerTournamentsPath(activeRunId',
      'viewerSeasonCalendarPath(activeRunId',
      'viewerHistoryPath(activeRunId',
      'viewerTournamentDetailPath(activeRunId'
    ]) {
      expect(strippedViewerHomeSource).not.toContain(forbiddenRawActiveRunUse)
    }
  })

  it('does not reintroduce stale snapshot/activity Home compatibility surfaces', () => {
    expect(strippedViewerHomeSource).not.toContain('Top 10 Rankings')
    expect(strippedViewerHomeSource).not.toContain('Ranking snapshots')
    expect(strippedViewerHomeSource).not.toContain('Race snapshots')
    expect(strippedViewerHomeSource).not.toContain('activity items')
    expect(strippedViewerHomeSource).not.toContain('snapshot_sequence')
  })
})

import hookSource from './useViewerDeferredSourceQueries.ts?raw'
import predictionSource from './ViewerPredictionDeferredPage.tsx?raw'
import rankingSource from './ViewerRankingDeferredPage.tsx?raw'
import statsSource from './ViewerStatsDeferredPage.tsx?raw'
import recordsStatsSource from '../stats/ViewerRecordsStatsLandingPage.tsx?raw'
import tourSource from './ViewerTourDeferredPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('Viewer deferred canonical source guard', () => {
  it('uses only Saved-Revision/publication readers in the shared deferred hook', () => {
    for (const canonicalReader of [
      'getViewerRunCalendar',
      'getViewerTournamentHistory',
      'listViewerOfficialRankingHistory',
      'getViewerFinalsRace',
    ]) {
      expect(hookSource).toContain(canonicalReader)
    }

    for (const legacyReader of [
      'getRun(',
      'getRunStatusSummary(',
      'listEvents(',
      'listRankingSnapshots(',
      'listRaceSnapshots(',
      'getFinalsSummary(',
    ]) {
      expect(hookSource).not.toContain(legacyReader)
    }
  })

  it('uses Product Run identity on all shared deferred pages', () => {
    for (const source of [predictionSource, rankingSource, statsSource, tourSource, recordsStatsSource]) {
      expect(source).toContain('useActiveViewerProductRunId')
      expect(source).not.toContain('useActiveViewerRunId')
    }
  })
})

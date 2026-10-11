import source from './ViewerH2HSubroutePage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('Viewer H2H canonical metadata source guard', () => {
  it('uses the shared canonical Saved-Revision metadata hook', () => {
    expect(source).toContain('useViewerDeferredSourceQueries')
    expect(source).toContain('useActiveViewerProductRunId')
  })

  it('keeps listRunPlayers as the only explicit legacy reader', () => {
    expect(source).toContain('listRunPlayers')
    for (const forbiddenLegacyReader of [
      'getRunStatusSummary(',
      'listEvents(',
      'listRankingSnapshots(',
      'listRaceSnapshots(',
      'getFinalsSummary(',
      'getRun(',
    ]) {
      expect(source).not.toContain(forbiddenLegacyReader)
    }
  })
})

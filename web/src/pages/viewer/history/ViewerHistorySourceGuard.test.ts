import source from './ViewerHistoryPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('ViewerHistoryPage canonical source guard', () => {
  it('uses only canonical Saved-Revision history readers', () => {
    expect(source).toContain('getViewerTournamentHistory')
    expect(source).toContain('listViewerOfficialRankingHistory')
    expect(source).toContain('getViewerFinalsRace')
    for (const legacyReader of [
      'getRun(',
      'getRunActivity(',
      'getRunStatusSummary(',
      'listEvents(',
      'listRankingSnapshots(',
      'listRaceSnapshots('
    ]) {
      expect(source).not.toContain(legacyReader)
    }
  })
})

import source from '../../ViewerRunSnapshotsPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('Viewer Race snapshot compatibility source context', () => {
  it('keeps legacy identity only for Race snapshot lookup/navigation', () => {
    expect(source).toContain('getRaceSnapshot')
    expect(source).toContain('listRaceSnapshots')
    expect(source).toContain('legacySimulationRunId')
  })

  it('uses canonical Saved-Revision authorities for source event context', () => {
    expect(source).toContain('getViewerRunCalendar')
    expect(source).toContain('getViewerTournamentHistory')
    expect(source).not.toContain('getRun(')
    expect(source).not.toContain('listEvents(')
  })
})

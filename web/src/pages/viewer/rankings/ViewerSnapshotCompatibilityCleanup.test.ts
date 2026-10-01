import rankingsIndexSource from './index.ts?raw'
import runSnapshotsSource from '../../ViewerRunSnapshotsPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('Viewer snapshot compatibility cleanup', () => {
  it('does not export the retired generic snapshot landing', () => {
    expect(rankingsIndexSource).not.toContain('ViewerSnapshotLandingPage')
    expect(rankingsIndexSource).not.toContain('ViewerSnapshotLandingConfig')
  })

  it('keeps only the actually routed legacy Race snapshot detail compatibility surface', () => {
    expect(runSnapshotsSource).not.toContain('export function ViewerRunSnapshotListPage')
    expect(runSnapshotsSource).toContain('export function ViewerRunSnapshotDetailPage')
    expect(runSnapshotsSource).toContain('legacySimulationRunId')
  })
})

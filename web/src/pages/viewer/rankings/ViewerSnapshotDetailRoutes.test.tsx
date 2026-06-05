import { describe, expect, it } from 'vitest'

import appSource from '../../../App.tsx?raw'
import rankingsIndexSource from './index.ts?raw'

describe('Viewer snapshot detail route wiring', () => {
  it('keeps ranking and race detail routes on dedicated Viewer wrappers', () => {
    expect(appSource).toContain('<Route path="viewer/runs/:runId/rankings/:snapshotSequence" element={<ViewerRankingSnapshotDetailPage />} />')
    expect(appSource).toContain('<Route path="viewer/runs/:runId/race/:snapshotSequence" element={<ViewerRaceSnapshotDetailPage />} />')
    expect(appSource).not.toMatch(/ViewerRunSnapshotDetailPage/)
  })

  it('exports both snapshot detail wrappers from the rankings barrel', () => {
    expect(rankingsIndexSource).toContain("export { ViewerRankingSnapshotDetailPage } from './ViewerRankingSnapshotDetailPage'")
    expect(rankingsIndexSource).toContain("export { ViewerRaceSnapshotDetailPage } from './ViewerRaceSnapshotDetailPage'")
  })
})

import { describe, expect, it } from 'vitest'

import rankingPreviewSource from '../../viewer/RankingPreviewTable.tsx?raw'
import racePreviewSource from '../../viewer/RacePreviewTable.tsx?raw'
import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'

const forbiddenMutationLabelText = />\s*(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)\s*</i

describe('Player/country preview route source guard', () => {
  it('keeps Ranking and Race preview tables on Viewer route helpers without Admin or mutation controls', () => {
    for (const source of [rankingPreviewSource, racePreviewSource]) {
      expect(source).toContain("from './viewerRoutes'")
      expect(source).toContain('viewerPlayerProfilePath')
      expect(source).toContain('viewerCountryProfilePath')
      expect(source).not.toContain('/admin')
      expect(source).not.toMatch(forbiddenMutationLabelText)
    }
  })

  it('keeps player/country Viewer route helper names exported from viewerRoutes', () => {
    expect(viewerRoutesSource).toContain('export function viewerPlayerProfilePath')
    expect(viewerRoutesSource).toContain('export function viewerCountryProfilePath')
  })
})

import { describe, expect, it } from 'vitest'

import rankingPreviewSource from '../../viewer/RankingPreviewTable.tsx?raw'
import racePreviewSource from '../../viewer/RacePreviewTable.tsx?raw'
import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import viewerRunPlayersCountriesSource from '../ViewerRunPlayersCountriesPage.tsx?raw'

const forbiddenMutationLabelText = />\s*(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)\s*</i
const forbiddenTargetPageMutationSource = /<button|type=\"submit\"|\b(?:post|put|patch|delete)[A-Z][A-Za-z]*\(|\b(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rebuild|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)\b/

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


  it('keeps player/country list and target page source read-only without Admin or fake profile fixtures', () => {
    expect(viewerRunPlayersCountriesSource).toContain('export function ViewerRunPlayersPage')
    expect(viewerRunPlayersCountriesSource).toContain('export function ViewerRunCountriesPage')
    expect(viewerRunPlayersCountriesSource).toContain('export function ViewerRunPlayerCareerPage')
    expect(viewerRunPlayersCountriesSource).toContain('export function ViewerRunCountryDetailPage')
    expect(viewerRunPlayersCountriesSource).not.toContain('/admin')
    expect(viewerRunPlayersCountriesSource).not.toMatch(forbiddenTargetPageMutationSource)
    expect(viewerRunPlayersCountriesSource).not.toMatch(/world champion|grand slam|career high no\. 1|Team Championship|medals?|Top 100/i)
  })

  it('keeps player/country list links backed by encoded Viewer route helpers', () => {
    expect(viewerRunPlayersCountriesSource).toContain('viewerPlayerProfilePath')
    expect(viewerRunPlayersCountriesSource).toContain('viewerCountryProfilePath')
    expect(viewerRunPlayersCountriesSource).toContain('viewerPlayersPath')
    expect(viewerRunPlayersCountriesSource).toContain('viewerCountriesPath')
    expect(viewerRunPlayersCountriesSource).not.toMatch(/to=\{`\/viewer\/runs\/\$\{runId\}\/players/)
    expect(viewerRunPlayersCountriesSource).not.toMatch(/to=\{`\/viewer\/runs\/\$\{runId\}\/countries/)
  })

  it('keeps player/country Viewer route helper names exported from viewerRoutes', () => {
    expect(viewerRoutesSource).toContain('export function viewerPlayerProfilePath')
    expect(viewerRoutesSource).toContain('export function viewerCountryProfilePath')
  })
})

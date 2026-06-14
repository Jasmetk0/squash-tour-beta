import { describe, expect, it } from 'vitest'

import rankingPreviewSource from '../../viewer/RankingPreviewTable.tsx?raw'
import racePreviewSource from '../../viewer/RacePreviewTable.tsx?raw'
import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import viewerRunPlayersCountriesSource from '../ViewerRunPlayersCountriesPage.tsx?raw'

const forbiddenMutationLabelText = />\s*(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)\s*</i
const forbiddenClientMutationCall = /\b(?:post|put|patch|delete)[A-Z][A-Za-z]*\(|\.(?:post|put|patch|delete)\s*\(/i
const forbiddenTargetPageControlSource = /<button|type=\"submit\"/i
const forbiddenVisibleMutationLabel = />\s*(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)\s*</i
const forbiddenFakeClaim = /world champion|grand slam|career high no\. 1|Team Championship|medals?|Top 100|fake profile|fixture profile/i

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


  it('keeps all player/country module target and list pages exported', () => {
    expect(viewerRunPlayersCountriesSource).toContain('export function ViewerRunPlayersPage')
    expect(viewerRunPlayersCountriesSource).toContain('export function ViewerRunPlayerCareerPage')
    expect(viewerRunPlayersCountriesSource).toContain('export function ViewerRunCountriesPage')
    expect(viewerRunPlayersCountriesSource).toContain('export function ViewerRunCountryDetailPage')
  })

  it('keeps scalar-safe normalization helpers present before player/country rendering', () => {
    for (const helperName of [
      'normalizePlayerListEntries',
      'normalizeNationListEntries',
      'normalizeCareerEntries',
      'normalizePerformanceEntries',
      'normalizeTournamentResultEntries',
      'normalizeTopPlayers',
      'normalizeCountMap',
      'normalizeDistribution',
      'scalarText',
      'optionalNumber'
    ]) {
      expect(viewerRunPlayersCountriesSource).toContain(helperName)
    }
  })

  it('keeps player/country list and target page source read-only without Admin controls or mutation calls', () => {
    expect(viewerRunPlayersCountriesSource).not.toContain('/admin')
    expect(viewerRunPlayersCountriesSource).not.toMatch(forbiddenTargetPageControlSource)
    expect(viewerRunPlayersCountriesSource).not.toMatch(forbiddenClientMutationCall)
    expect(viewerRunPlayersCountriesSource).not.toMatch(forbiddenVisibleMutationLabel)
  })

  it('keeps player/country list and target page source free of fake profile and source claims', () => {
    expect(viewerRunPlayersCountriesSource).not.toMatch(forbiddenFakeClaim)
  })

  it('keeps player/country list links backed by encoded Viewer route helpers', () => {
    for (const helperName of [
      'viewerPlayerProfilePath',
      'viewerCountryProfilePath',
      'viewerTournamentDetailPath',
      'viewerWeekDetailPath',
      'viewerPlayersPath',
      'viewerCountriesPath'
    ]) {
      expect(viewerRunPlayersCountriesSource).toContain(helperName)
    }
    expect(viewerRunPlayersCountriesSource).not.toMatch(/`\/viewer\/runs\/\$\{runId\}\/players(?:`|\/|\?)/)
    expect(viewerRunPlayersCountriesSource).not.toMatch(/`\/viewer\/runs\/\$\{runId\}\/countries(?:`|\/|\?)/)
    expect(viewerRunPlayersCountriesSource).not.toMatch(/`\/viewer\/runs\/\$\{runId\}\/tournaments(?:`|\/|\?)/)
    expect(viewerRunPlayersCountriesSource).not.toMatch(/`\/viewer\/runs\/\$\{runId\}\/weeks(?:`|\/|\?)/)
  })

  it('keeps player/country Viewer route helper names exported from viewerRoutes', () => {
    expect(viewerRoutesSource).toContain('export function viewerPlayerProfilePath')
    expect(viewerRoutesSource).toContain('export function viewerCountryProfilePath')
  })
})

import h2hSource from '../deferred/ViewerH2HSubroutePage.tsx?raw'
import searchSource from '../explore/ViewerSearchPage.tsx?raw'
import countriesHubSource from './ViewerCountriesPage.tsx?raw'
import playersHubSource from './ViewerPlayersPage.tsx?raw'
import runPeopleSource from '../../ViewerRunPlayersCountriesPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('Viewer canonical people UI source guard', () => {
  it('uses Product Run canonical people readers on migrated Viewer surfaces', () => {
    for (const source of [h2hSource, searchSource, countriesHubSource, playersHubSource, runPeopleSource]) {
      expect(source).toMatch(/getViewerPlayers|getViewerCountries/)
    }
  })

  it('does not reintroduce legacy list people readers on migrated list/search/H2H surfaces', () => {
    for (const source of [h2hSource, searchSource, countriesHubSource, playersHubSource]) {
      expect(source).not.toContain('listRunPlayers(')
      expect(source).not.toContain('listRunNations(')
    }
    const runListSection = runPeopleSource.slice(
      runPeopleSource.indexOf('export function ViewerRunPlayersPage'),
      runPeopleSource.indexOf('export function ViewerRunPlayerCareerPage'),
    ) + runPeopleSource.slice(
      runPeopleSource.indexOf('export function ViewerRunCountriesPage'),
      runPeopleSource.indexOf('export function ViewerRunCountryDetailPage'),
    )
    expect(runListSection).not.toContain('listRunPlayers(')
    expect(runListSection).not.toContain('listRunNations(')
  })
})

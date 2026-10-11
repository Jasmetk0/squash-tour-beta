import source from '../../ViewerRunPlayersCountriesPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('Viewer canonical people detail source guard', () => {
  it('uses canonical people readers for current Player/Country profiles', () => {
    expect(source).toContain('getViewerPlayers')
    expect(source).toContain('getViewerCountries')
  })

  it('does not use legacy Player/Country detail or career readers', () => {
    for (const legacyReader of [
      'getRunPlayerDetail(',
      'getRunPlayerCareerHistory(',
      'getRunPlayerCareerPerformance(',
      'getRunPlayerTournamentResults(',
      'getRunNationDetail(',
    ]) {
      expect(source).not.toContain(legacyReader)
    }
  })
})

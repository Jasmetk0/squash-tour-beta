import calendarSource from '../../ViewerRunCalendarPage.tsx?raw'
import tournamentSource from '../../ViewerRunTournamentsPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('Viewer canonical Tournament/Week detail source guard', () => {
  it('uses only canonical Product Run authorities for Tournament Detail context', () => {
    for (const reader of [
      'getViewerRunCalendar',
      'getViewerTournamentHistory',
      'listViewerOfficialRankingHistory',
      'getViewerFinalsRace',
      'getViewerTournamentEntryField',
      'getViewerTournamentDraw',
      'getViewerTournamentWildCards',
      'getViewerTournamentResult',
    ]) {
      expect(tournamentSource).toContain(reader)
    }

    for (const legacyReader of [
      'getEvent(',
      'getRun(',
      'listEvents(',
      'listRankingSnapshots(',
      'listRaceSnapshots(',
      'legacySimulationRunId',
    ]) {
      expect(tournamentSource).not.toContain(legacyReader)
    }
  })

  it('uses canonical Finals Race history on Week Detail', () => {
    expect(calendarSource).toContain('getViewerFinalsRace')
    expect(calendarSource).not.toContain('listRaceSnapshots(')
    expect(calendarSource).not.toContain('legacySimulationRunId')
  })
})

import { describe, expect, it } from 'vitest'

import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import viewerRunCalendarSource from '../ViewerRunCalendarPage.tsx?raw'
import viewerRunPlayersCountriesSource from '../ViewerRunPlayersCountriesPage.tsx?raw'
import viewerRunSnapshotsSource from '../ViewerRunSnapshotsPage.tsx?raw'
import viewerRunTournamentsSource from '../ViewerRunTournamentsPage.tsx?raw'

const viewerCalendarTournamentSources = [
  viewerRunCalendarSource,
  viewerRunPlayersCountriesSource,
  viewerRunSnapshotsSource,
  viewerRunTournamentsSource
]

const unsafeTemplateRoutePatterns = [
  /`\/viewer\/runs\/\$\{runId\}\/calendar(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/tournaments(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/weeks(?:`|\/|\?)/
]
const forbiddenMutationLabelText = />\s*(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)\s*</i

function expectNoUnsafeRouteTemplates(source: string): void {
  for (const pattern of unsafeTemplateRoutePatterns) {
    expect(source).not.toMatch(pattern)
  }
}

describe('Calendar/tournament Viewer route source guard', () => {
  it('keeps calendar, week, and tournament route helpers exported from viewerRoutes', () => {
    for (const helperName of [
      'viewerSeasonCalendarPath',
      'viewerPlannedEventPath',
      'viewerWeekDetailPath',
      'viewerTournamentsPath',
      'viewerTournamentDetailPath'
    ]) {
      expect(viewerRoutesSource).toContain(`export function ${helperName}`)
    }
  })

  it('keeps snapshot and player/country modules on Viewer route helpers for event/week/tournament links', () => {
    expect(viewerRunSnapshotsSource).toContain('viewerSeasonCalendarPath')
    expect(viewerRunSnapshotsSource).toContain('viewerPlannedEventPath')
    expect(viewerRunSnapshotsSource).toContain('viewerTournamentDetailPath')
    expect(viewerRunSnapshotsSource).toContain('viewerWeekDetailPath')

    expect(viewerRunPlayersCountriesSource).toContain('viewerTournamentDetailPath')
    expect(viewerRunPlayersCountriesSource).toContain('viewerWeekDetailPath')
  })

  it('keeps calendar/tournament Viewer sources free of unsafe templates, Admin links, and mutation labels', () => {
    for (const source of viewerCalendarTournamentSources) {
      expectNoUnsafeRouteTemplates(source)
      expect(source).not.toContain('/admin')
      expect(source).not.toMatch(forbiddenMutationLabelText)
    }
  })
})

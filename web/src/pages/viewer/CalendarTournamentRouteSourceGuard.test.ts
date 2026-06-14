import { describe, expect, it } from 'vitest'

import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import viewerRunCalendarSource from '../ViewerRunCalendarPage.tsx?raw'
import viewerRunPlayersCountriesSource from '../ViewerRunPlayersCountriesPage.tsx?raw'
import viewerRunSnapshotsSource from '../ViewerRunSnapshotsPage.tsx?raw'
import viewerRunTournamentsSource from '../ViewerRunTournamentsPage.tsx?raw'

const calendarTournamentTargetSources = [viewerRunCalendarSource, viewerRunTournamentsSource]

const unsafeTemplateRoutePatterns = [
  /`\/viewer\/runs\/\$\{runId\}\/calendar(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/tournaments(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/weeks(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/rankings(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/race(?:`|\/|\?)/
]
const forbiddenMutationLabelText = />\s*(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)\s*</i
const forbiddenMutationCalls = /\b(?:useMutation|mutate\s*\(|fetch\s*\([\s\S]{0,160}method\s*:\s*['\"](?:POST|PUT|PATCH|DELETE)['\"]|axios\.[a-z]+\s*\([\s\S]{0,160}['\"](?:POST|PUT|PATCH|DELETE)['\"])/i
const forbiddenFakeClaims = /(?:fake winner|fake champion|invented winner|invented standings|final score|match result|fixture tournament|fake tournament|standings table)/i

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
    for (const source of calendarTournamentTargetSources) {
      expectNoUnsafeRouteTemplates(source)
      expect(source).not.toContain('/admin')
      expect(source).not.toContain('<button')
      expect(source).not.toContain('type="submit"')
      expect(source).not.toMatch(forbiddenMutationCalls)
      expect(source).not.toMatch(forbiddenMutationLabelText)
    }
  })

  it('keeps actual calendar/tournament targets exported', () => {
    for (const componentName of ['ViewerRunCalendarPage', 'ViewerRunPlannedEventPage', 'ViewerRunWeekPage']) {
      expect(viewerRunCalendarSource).toContain(`export function ${componentName}`)
    }
    for (const componentName of ['ViewerRunTournamentsPage', 'ViewerRunTournamentDetailPage']) {
      expect(viewerRunTournamentsSource).toContain(`export function ${componentName}`)
    }

  })

  it('keeps calendar scalar-safe helpers present', () => {
    for (const helperName of [
      'safeText',
      'safeWeekLabel',
      'safeOrderedEvents',
      'safeCompletedEventIds',
      'safeEventRecords',
      'safeSnapshotRecords',
      'parseViewerWeekParam'
    ]) {
      expect(viewerRunCalendarSource).toContain(helperName)
    }
  })

  it('keeps tournament scalar-safe helpers present', () => {
    for (const helperName of [
      'buildPlannedContext',
      'safeText',
      'safeNumber',
      'safeEventRecords',
      'safeCompletedEventIds',
      'safeSnapshotRecords',
      'eventWeek',
      'eventSeason',
      'displayWeekDetailLink'
    ]) {
      expect(viewerRunTournamentsSource).toContain(helperName)
    }
  })

  it('keeps calendar/tournament links backed by Viewer route helpers', () => {
    for (const helperName of [
      'viewerSeasonCalendarPath',
      'viewerPlannedEventPath',
      'viewerWeekDetailPath',
      'viewerTournamentDetailPath',
      'viewerRankingSnapshotPath',
      'viewerRaceSnapshotPath'
    ]) {
      expect(viewerRunCalendarSource).toContain(helperName)
    }

    for (const helperName of ['viewerPlannedEventPath', 'viewerTournamentsPath', 'viewerTournamentDetailPath', 'viewerWeekDetailPath']) {
      expect(viewerRunTournamentsSource).toContain(helperName)
    }
  })

  it('keeps calendar/tournament target sources free of fake claims', () => {
    for (const source of calendarTournamentTargetSources) {
      expect(source).not.toMatch(forbiddenFakeClaims)
    }
  })
})

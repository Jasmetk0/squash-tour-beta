import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import viewerRunCalendarSource from '../ViewerRunCalendarPage.tsx?raw'
import viewerRunHistoryFinalsSource from '../ViewerRunHistoryFinalsPage.tsx?raw'
import viewerRunPlayersCountriesSource from '../ViewerRunPlayersCountriesPage.tsx?raw'
import viewerRunSnapshotsSource from '../ViewerRunSnapshotsPage.tsx?raw'
import viewerRunTournamentsSource from '../ViewerRunTournamentsPage.tsx?raw'

const completedRunScopedSources = [
  viewerRunSnapshotsSource,
  viewerRunPlayersCountriesSource,
  viewerRunCalendarSource,
  viewerRunTournamentsSource,
  viewerRunHistoryFinalsSource
]

const expectedRunScopedRoutePatterns = [
  '/viewer/runs/:runId/calendar',
  '/viewer/runs/:runId/calendar/:eventId',
  '/viewer/runs/:runId/weeks/:week',
  '/viewer/runs/:runId/tournaments',
  '/viewer/runs/:runId/tournaments/:eventId',
  '/viewer/runs/:runId/rankings',
  '/viewer/runs/:runId/rankings/:snapshotSequence',
  '/viewer/runs/:runId/race',
  '/viewer/runs/:runId/race/:snapshotSequence',
  '/viewer/runs/:runId/players',
  '/viewer/runs/:runId/players/:playerId/career',
  '/viewer/runs/:runId/countries',
  '/viewer/runs/:runId/countries/:countryCode',
  '/viewer/runs/:runId/history',
  '/viewer/runs/:runId/finals',
  '/viewer/runs/:runId/finals/qualification',
  '/viewer/runs/:runId/finals/result'
]

const expectedRouteHelperExports = [
  'viewerSeasonCalendarPath',
  'viewerPlannedEventPath',
  'viewerWeekDetailPath',
  'viewerTournamentsPath',
  'viewerTournamentDetailPath',
  'viewerRankingsPath',
  'viewerRankingSnapshotPath',
  'viewerRacePath',
  'viewerRaceSnapshotPath',
  'viewerPlayersPath',
  'viewerPlayerProfilePath',
  'viewerCountriesPath',
  'viewerCountryProfilePath',
  'viewerHistoryPath',
  'viewerFinalsPath',
  'viewerFinalsQualificationPath',
  'viewerFinalsResultPath'
]

const forbiddenMutationLabelText = />\s*(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)\s*</i
const forbiddenMutationCalls = /\b(?:useMutation|mutate\s*\(|fetch\s*\([\s\S]{0,160}method\s*:\s*['"](?:POST|PUT|PATCH|DELETE)['"]|axios\.[a-z]+\s*\([\s\S]{0,160}['"](?:POST|PUT|PATCH|DELETE)['"])/i

const unsafeRunScopedRouteTemplates = [
  /`\/viewer\/runs\/\$\{runId\}\/calendar(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/tournaments(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/weeks(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/rankings(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/race(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/players(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/countries(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/history(?:`|\/|\?)/,
  /`\/viewer\/runs\/\$\{runId\}\/finals(?:`|\/|\?)/
]

const forbiddenFakeClaimLanguage = /(?:fake champion|fake winner|invented champion|invented winner|invented standings|fake standings|fake profile|fixture profile|fake tournament|fixture tournament|fake history|invented history|fake finals|invented finals|fake finalist|invented finalist|world champion|grand slam|career high no\. 1|Team Championship|medals|Top 100|standings table)/i

function appRoutePaths(): Set<string> {
  return new Set([...appSource.matchAll(/<Route\s+path="([^"]+)"/g)].map((match) => `/${match[1]}`))
}

describe('Viewer run-scoped module final source guard', () => {
  it('keeps all expected run-scoped route patterns registered in App', () => {
    const routes = appRoutePaths()

    for (const routePattern of expectedRunScopedRoutePatterns) {
      expect(routes).toContain(routePattern)
    }
  })

  it('keeps all expected run-scoped route helper exports available', () => {
    for (const helperName of expectedRouteHelperExports) {
      expect(viewerRoutesSource).toContain(`export function ${helperName}`)
    }
  })

  it('keeps completed run-scoped Viewer sources Viewer-only and read-only', () => {
    for (const source of completedRunScopedSources) {
      expect(source).not.toContain('/admin')
      expect(source).not.toContain('<button')
      expect(source).not.toContain('type="submit"')
      expect(source).not.toMatch(forbiddenMutationCalls)
      expect(source).not.toMatch(forbiddenMutationLabelText)
    }
  })

  it('keeps completed run-scoped Viewer sources free of unsafe hardcoded route templates', () => {
    for (const source of completedRunScopedSources) {
      for (const unsafeTemplate of unsafeRunScopedRouteTemplates) {
        expect(source).not.toMatch(unsafeTemplate)
      }
    }
  })

  it('keeps completed run-scoped Viewer production sources free of fake or invented claim language', () => {
    for (const source of completedRunScopedSources) {
      expect(source).not.toMatch(forbiddenFakeClaimLanguage)
    }
  })
})

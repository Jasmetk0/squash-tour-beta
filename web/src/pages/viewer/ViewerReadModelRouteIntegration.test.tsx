import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import { buildRunBrowserContextLinks, buildRunBrowserPrimaryLinks } from '../../viewer/runBrowserDisplay'
import { buildViewerHomeActiveRunLinks, buildViewerHomePrimaryHubLinks } from '../../viewer/viewerHomeDisplay'
import { viewerTopLevelHubLinks } from '../../viewer/viewerHubLinks'
import {
  viewerCountriesPath,
  viewerCountryProfilePath,
  viewerFinalsPath,
  viewerFinalsQualificationPath,
  viewerFinalsResultPath,
  viewerHistoryPath,
  viewerPlannedEventPath,
  viewerPlayerProfilePath,
  viewerPlayersPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath,
  viewerWeekDetailPath
} from '../../viewer/viewerRoutes'
import viewerHomeSource from './ViewerHomePage.tsx?raw'

const viewerOnlyPathPattern = /^\/viewer(?:\/|$)/
const adminPathPattern = /^\/admin(?:\/|$)/
const viewerDeferredPageSources = import.meta.glob('./deferred/*.tsx', { query: '?raw', import: 'default', eager: true }) as Record<string, string>

const expectedViewerRoutePatterns = [
  '/viewer',
  '/viewer/runs',
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
  '/viewer/runs/:runId/finals/result',
  '/viewer/predictions',
  '/viewer/predictions/match-predictor',
  '/viewer/predictions/match-odds',
  '/viewer/predictions/tournament-odds',
  '/viewer/predictions/finals-qualification',
  '/viewer/predictions/season-end-no1',
  '/viewer/predictions/upset-watch',
  '/viewer/predictions/futures',
  '/viewer/rankings',
  '/viewer/rankings/race',
  '/viewer/rankings/next-gen',
  '/viewer/rankings/elo',
  '/viewer/rankings/power',
  '/viewer/rankings/form',
  '/viewer/rankings/no1-history',
  '/viewer/tour',
  '/viewer/tour/calendar',
  '/viewer/tour/current-week',
  '/viewer/tour/tournaments',
  '/viewer/tour/matches',
  '/viewer/tour/categories',
  '/viewer/tour/champions'
]

function appRoutePaths(): Set<string> {
  return new Set([...appSource.matchAll(/<Route\s+path="([^"]+)"/g)].map((match) => `/${match[1]}`))
}

function routePattern(path: string): RegExp {
  return new RegExp(`^${path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/:[^/]+/g, '[^/]+')}$`)
}

function viewerRouteExists(to: string): boolean {
  const routes = appRoutePaths()
  return [...routes].some((route) => routePattern(route).test(to))
}

function expectViewerOnlyPath(destination: string): void {
  expect(destination).toMatch(viewerOnlyPathPattern)
  expect(destination).not.toMatch(adminPathPattern)
}

describe('Viewer read-model route integration', () => {
  it('keeps expected App Viewer route patterns registered', () => {
    const routes = appRoutePaths()

    for (const route of expectedViewerRoutePatterns) {
      expect(routes).toContain(route)
    }
  })

  it('keeps top-level Viewer hub routes registered and Viewer-only', () => {
    const routes = [...appRoutePaths()]
    const topLevelViewerRoutes = routes.filter((route) => route.startsWith('/viewer') && !route.startsWith('/viewer/runs/:'))
    const expectedTopLevelViewerRoutes = [
      '/viewer',
      '/viewer/rankings',
      '/viewer/rankings/race',
      '/viewer/rankings/next-gen',
      '/viewer/rankings/elo',
      '/viewer/rankings/power',
      '/viewer/rankings/form',
      '/viewer/rankings/no1-history',
      '/viewer/tour',
      '/viewer/tour/calendar',
      '/viewer/tour/current-week',
      '/viewer/tour/tournaments',
      '/viewer/tour/matches',
      '/viewer/tour/categories',
      '/viewer/tour/champions',
      '/viewer/tournaments',
      '/viewer/players',
      '/viewer/players/all',
      '/viewer/players/active',
      '/viewer/players/next-gen',
      '/viewer/players/retired',
      '/viewer/players/compare',
      '/viewer/countries',
      '/viewer/countries/ranking',
      '/viewer/countries/all',
      '/viewer/countries/hosting',
      '/viewer/countries/talent-pipeline',
      '/viewer/countries/records',
      '/viewer/h2h',
      '/viewer/h2h/rivalries',
      '/viewer/h2h/most-played',
      '/viewer/h2h/finals-rivalries',
      '/viewer/stats',
      '/viewer/stats/title-leaders',
      '/viewer/stats/no1-weeks',
      '/viewer/stats/streaks',
      '/viewer/stats/upsets',
      '/viewer/stats/best-seasons',
      '/viewer/stats/player-stats',
      '/viewer/stats/tournament-stats',
      '/viewer/stats/country-stats',
      '/viewer/stats/awards',
      '/viewer/stats/hall-of-fame',
      '/viewer/stats/era-rankings',
      '/viewer/records',
      '/viewer/predictions',
      '/viewer/predictions/match-predictor',
      '/viewer/predictions/match-odds',
      '/viewer/predictions/tournament-odds',
      '/viewer/predictions/finals-qualification',
      '/viewer/predictions/season-end-no1',
      '/viewer/predictions/upset-watch',
      '/viewer/predictions/futures',
      '/viewer/search',
      '/viewer/history',
      '/viewer/runs'
    ]

    expect(topLevelViewerRoutes).toEqual(expect.arrayContaining(expectedTopLevelViewerRoutes))
    expect(new Set(topLevelViewerRoutes).size).toBe(topLevelViewerRoutes.length)

    for (const route of topLevelViewerRoutes) {
      expect(route).toMatch(viewerOnlyPathPattern)
      expect(route).not.toMatch(adminPathPattern)
    }
  })

  it('keeps player/country route helpers Viewer-only, registered, and encoded', () => {
    const runId = 'run/alpha #1'
    const playerId = 'P/1 #A'
    const countryCode = 'CO/DE #1'
    const encodedRunSegment = 'run%2Falpha%20%231'
    const encodedPlayerSegment = 'P%2F1%20%23A'
    const encodedCountrySegment = 'CO%2FDE%20%231'
    const listDestinations = [viewerPlayersPath(runId), viewerCountriesPath(runId)]
    const detailDestinations = [
      {
        destination: viewerPlayerProfilePath(runId, playerId),
        encodedSegment: encodedPlayerSegment,
        rawSegment: playerId,
        routeTail: `/players/${encodedPlayerSegment}/career`
      },
      {
        destination: viewerCountryProfilePath(runId, countryCode),
        encodedSegment: encodedCountrySegment,
        rawSegment: countryCode,
        routeTail: `/countries/${encodedCountrySegment}`
      }
    ]

    for (const destination of listDestinations) {
      expectViewerOnlyPath(destination)
      expect(destination).toContain(`/viewer/runs/${encodedRunSegment}`)
      expect(destination).not.toContain(runId)
      expect(destination).not.toContain('#')
      expect(viewerRouteExists(destination)).toBe(true)
    }

    for (const { destination, encodedSegment, rawSegment, routeTail } of detailDestinations) {
      expectViewerOnlyPath(destination)
      expect(destination).not.toMatch(adminPathPattern)
      expect(destination).toContain(`/viewer/runs/${encodedRunSegment}`)
      expect(destination).toContain(encodedSegment)
      expect(destination).toContain(routeTail)
      expect(destination).not.toContain(runId)
      expect(destination).not.toContain(rawSegment)
      expect(destination).not.toContain('#')
      expect(viewerRouteExists(destination)).toBe(true)
    }
  })

  it('keeps snapshot list/detail route helpers Viewer-only, registered, and encoded', () => {
    const runId = 'run/alpha #1'
    const eventId = 'EVT/1 #A'
    const encodedRunSegment = 'run%2Falpha%20%231'
    const encodedEventSegment = 'EVT%2F1%20%23A'
    const snapshotDestinations = [
      viewerRankingsPath(runId),
      viewerRankingSnapshotPath(runId, 4),
      viewerRacePath(runId),
      viewerRaceSnapshotPath(runId, 5)
    ]

    for (const destination of snapshotDestinations) {
      expectViewerOnlyPath(destination)
      expect(destination).toContain(`/viewer/runs/${encodedRunSegment}`)
      expect(destination).not.toContain(runId)
      expect(viewerRouteExists(destination)).toBe(true)
    }

    expect(viewerPlannedEventPath(runId, eventId)).toContain(encodedEventSegment)
    expect(viewerTournamentDetailPath(runId, eventId)).toContain(encodedEventSegment)
  })

  it('keeps history/finals route helpers Viewer-only, registered, and encoded', () => {
    const runId = 'run/alpha #1'
    const encodedRunSegment = 'run%2Falpha%20%231'
    const destinations = [
      viewerHistoryPath(runId),
      viewerFinalsPath(runId),
      viewerFinalsQualificationPath(runId),
      viewerFinalsResultPath(runId)
    ]

    for (const destination of destinations) {
      expectViewerOnlyPath(destination)
      expect(destination).not.toMatch(adminPathPattern)
      expect(destination).toContain(`/viewer/runs/${encodedRunSegment}`)
      expect(destination).not.toContain(runId)
      expect(destination).not.toContain('#')
      expect(viewerRouteExists(destination)).toBe(true)
    }
  })

  it('keeps calendar/week/tournament route helpers Viewer-only, registered, and encoded', () => {
    const runId = 'run/alpha #1'
    const eventId = 'EVT/1 #A'
    const week = 7
    const encodedRunSegment = 'run%2Falpha%20%231'
    const encodedEventSegment = 'EVT%2F1%20%23A'
    const calendarTournamentDestinations = [
      { destination: viewerSeasonCalendarPath(runId), routeTail: '/calendar' },
      { destination: viewerPlannedEventPath(runId, eventId), routeTail: `/calendar/${encodedEventSegment}`, encodedEventSegment },
      { destination: viewerWeekDetailPath(runId, week), routeTail: '/weeks/7' },
      { destination: viewerTournamentsPath(runId), routeTail: '/tournaments' },
      { destination: viewerTournamentDetailPath(runId, eventId), routeTail: `/tournaments/${encodedEventSegment}`, encodedEventSegment }
    ]

    for (const { destination, routeTail, encodedEventSegment: destinationEventSegment } of calendarTournamentDestinations) {
      expectViewerOnlyPath(destination)
      expect(destination).not.toMatch(adminPathPattern)
      expect(destination).toContain(`/viewer/runs/${encodedRunSegment}`)
      expect(destination).toContain(routeTail)
      expect(destination).not.toContain(runId)
      expect(destination).not.toContain('#')
      expect(destination).not.toContain(eventId)
      if (destinationEventSegment) {
        expect(destination).toContain(destinationEventSegment)
      }
      expect(viewerRouteExists(destination)).toBe(true)
    }
  })

  it('keeps run-scoped route helpers Viewer-only and safely encoded', () => {
    const runId = 'run/alpha #1'
    const eventId = 'EVT/1 #A'
    const encodedRunSegment = 'run%2Falpha%20%231'
    const encodedEventSegment = 'EVT%2F1%20%23A'
    const destinations = [
      viewerSeasonCalendarPath(runId),
      viewerPlannedEventPath(runId, eventId),
      viewerWeekDetailPath(runId, 7),
      viewerTournamentDetailPath(runId, eventId),
      viewerRankingsPath(runId),
      viewerRankingSnapshotPath(runId, 4),
      viewerRacePath(runId),
      viewerRaceSnapshotPath(runId, 5),
      viewerHistoryPath(runId)
    ]

    for (const destination of destinations) {
      expectViewerOnlyPath(destination)
      expect(destination).toContain(`/viewer/runs/${encodedRunSegment}`)
      expect(destination).not.toContain(runId)
      expect(viewerRouteExists(destination)).toBe(true)
    }

    expect(viewerPlannedEventPath(runId, eventId)).toContain(encodedEventSegment)
    expect(viewerTournamentDetailPath(runId, eventId)).toContain(encodedEventSegment)
    expect(viewerPlannedEventPath(runId, eventId)).not.toContain(eventId)
    expect(viewerTournamentDetailPath(runId, eventId)).not.toContain(eventId)
  })

  it('keeps Home and Run Browser link builders Viewer-only with intentional active-run overlap', () => {
    const runId = 'run/alpha #1'
    const homeLinks = buildViewerHomeActiveRunLinks(runId)
    const primaryLinks = buildRunBrowserPrimaryLinks(runId)
    const contextLinks = buildRunBrowserContextLinks(runId)
    const homeDestinations = homeLinks.map((link) => link.to)
    const runBrowserDestinations = [...primaryLinks, ...contextLinks].map((link) => link.to)

    for (const destination of [...homeDestinations, ...runBrowserDestinations]) {
      expectViewerOnlyPath(destination)
      expect(destination).not.toMatch(adminPathPattern)
      expect(viewerRouteExists(destination)).toBe(true)
    }

    expect(runBrowserDestinations).toEqual(expect.arrayContaining(homeDestinations))
  })

  it('keeps top-level hub links pointed at existing Viewer App route patterns', () => {
    for (const link of [...buildViewerHomePrimaryHubLinks(), ...viewerTopLevelHubLinks]) {
      expectViewerOnlyPath(link.to)
      expect(viewerRouteExists(link.to)).toBe(true)
    }
  })

  it('guards Viewer Home active-run source handling and stale headings', () => {
    expect(viewerHomeSource).toContain('normalizeViewerHomeActiveRunId(activeRunId)')
    expect(viewerHomeSource).not.toContain('Top 10 Rankings')
    expect(viewerHomeSource).not.toContain('Race to Finals')
    expect(viewerHomeSource).not.toContain('getRun(activeRunId')
    expect(viewerHomeSource).not.toContain('viewerRankingsPath(activeRunId')
  })

  it('keeps deferred production pages off the pure metadata module for JSX rendering imports', () => {
    for (const [sourcePath, source] of Object.entries(viewerDeferredPageSources)) {
      expect(source, sourcePath).not.toMatch(/renderSourceMetadataList[\s\S]*from ['"]\.\/ViewerDeferredSourceMetadata['"]|from ['"]\.\/ViewerDeferredSourceMetadata['"][\s\S]*renderSourceMetadataList/)
    }
  })
})

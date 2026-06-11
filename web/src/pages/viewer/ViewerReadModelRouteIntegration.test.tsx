import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import { buildRunBrowserContextLinks, buildRunBrowserPrimaryLinks } from '../../viewer/runBrowserDisplay'
import { buildViewerHomeActiveRunLinks, buildViewerHomePrimaryHubLinks } from '../../viewer/viewerHomeDisplay'
import { viewerTopLevelHubLinks } from '../../viewer/viewerHubLinks'
import {
  viewerHistoryPath,
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
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
  '/viewer/runs/:runId/countries',
  '/viewer/runs/:runId/history',
  '/viewer/runs/:runId/finals',
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

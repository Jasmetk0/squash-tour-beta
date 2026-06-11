import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import { buildViewerHomeActiveRunLinks, buildViewerHomePrimaryHubLinks } from '../../viewer/viewerHomeDisplay'
import {
  viewerHistoryPath,
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath,
  viewerWeekDetailPath
} from '../../viewer/viewerRoutes'

const viewerOnlyPathPattern = /^\/viewer(?:\/|$)/
const adminPathPattern = /^\/admin(?:\/|$)/

function appRoutePaths(): Set<string> {
  return new Set([...appSource.matchAll(/<Route path="([^"]+)"/g)].map((match) => `/${match[1]}`))
}

describe('Viewer Home route safety', () => {
  it('keeps the App route for Viewer Home pointed at ViewerHomePage', () => {
    expect(appSource).toContain('<Route path="viewer" element={<ViewerHomePage />} />')
  })

  it('keeps active-run helper destinations aligned with existing App route patterns', () => {
    const routePaths = appRoutePaths()

    for (const routePath of [
      '/viewer/runs/:runId/rankings',
      '/viewer/runs/:runId/race',
      '/viewer/runs/:runId/tournaments',
      '/viewer/runs/:runId/calendar',
      '/viewer/runs/:runId/players',
      '/viewer/runs/:runId/countries',
      '/viewer/runs/:runId/history',
      '/viewer/runs/:runId/finals',
      '/viewer/runs/:runId/rankings/:snapshotSequence',
      '/viewer/runs/:runId/race/:snapshotSequence',
      '/viewer/runs/:runId/tournaments/:eventId',
      '/viewer/runs/:runId/calendar/:eventId',
      '/viewer/runs/:runId/weeks/:week'
    ]) {
      expect(routePaths).toContain(routePath)
    }

    expect(buildViewerHomeActiveRunLinks('run alpha').map((link) => link.to)).toEqual([
      viewerRankingsPath('run alpha'),
      viewerRacePath('run alpha'),
      viewerTournamentsPath('run alpha'),
      viewerSeasonCalendarPath('run alpha'),
      '/viewer/runs/run%20alpha/players',
      '/viewer/runs/run%20alpha/countries',
      viewerHistoryPath('run alpha'),
      '/viewer/runs/run%20alpha/finals'
    ])
  })

  it('keeps top-level hub destinations aligned with existing Viewer App routes', () => {
    const routePaths = appRoutePaths()

    for (const link of buildViewerHomePrimaryHubLinks()) {
      expect(link.to).toMatch(viewerOnlyPathPattern)
      expect(link.to).not.toMatch(adminPathPattern)
      expect(routePaths).toContain(link.to)
    }
  })

  it('keeps helper destinations Viewer-only and encodes slash-containing run ids', () => {
    const runId = 'run/alpha #1'
    const expectedEncodedRunId = 'run%2Falpha%20%231'
    const destinations = [
      ...buildViewerHomeActiveRunLinks(runId).map((link) => link.to),
      viewerRankingSnapshotPath(runId, 4),
      viewerRaceSnapshotPath(runId, 5),
      viewerTournamentDetailPath(runId, 'EVT/1'),
      viewerWeekDetailPath(runId, 7),
      viewerPlannedEventPath(runId, 'EVT/1')
    ]

    for (const destination of destinations) {
      expect(destination).toMatch(viewerOnlyPathPattern)
      expect(destination).not.toMatch(adminPathPattern)
      expect(destination).toContain(`/viewer/runs/${expectedEncodedRunId}/`)
      expect(destination).not.toContain('run/alpha #1')
    }
    expect(viewerTournamentDetailPath(runId, 'EVT/1')).toBe('/viewer/runs/run%2Falpha%20%231/tournaments/EVT%2F1')
    expect(viewerPlannedEventPath(runId, 'EVT/1')).toBe('/viewer/runs/run%2Falpha%20%231/calendar/EVT%2F1')
  })
})

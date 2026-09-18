import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import { viewerAppRouteExists, viewerAppRoutePaths } from '../../test/viewerAppRouteSource'
import historyFinalsSource from '../ViewerRunHistoryFinalsPage.tsx?raw'
import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import {
  viewerFinalsPath,
  viewerFinalsQualificationPath,
  viewerFinalsResultPath,
  viewerHistoryPath
} from '../../viewer/viewerRoutes'

const registeredRoutePatterns = viewerAppRoutePaths(appSource)
const visibleMutationLabels = [
  'Simulate',
  'Generate',
  'Persist',
  'Apply',
  'Execute',
  'Delete',
  'Edit',
  'Import',
  'Rollover',
  'Rebuild',
  'Override',
  'Save changes',
  'Commit',
  'Regenerate',
  'Repair',
  'Merge',
  'Overwrite'
]

function viewerRouteExists(to: string): boolean {
  return viewerAppRouteExists(appSource, to)
}

describe('History/Finals Viewer route source guard', () => {
  it('keeps history/finals route helpers exported, encoded, Viewer-only, and registered', () => {
    const runId = 'run/alpha #1'
    const encodedRunSegment = 'run%2Falpha%20%231'
    const destinations = [
      viewerHistoryPath(runId),
      viewerFinalsPath(runId),
      viewerFinalsQualificationPath(runId),
      viewerFinalsResultPath(runId)
    ]

    expect(viewerRoutesSource).toContain('export function viewerHistoryPath')
    expect(viewerRoutesSource).toContain('export function viewerFinalsPath')
    expect(viewerRoutesSource).toContain('export function viewerFinalsQualificationPath')
    expect(viewerRoutesSource).toContain('export function viewerFinalsResultPath')
    expect(viewerRoutesSource).toContain('export function viewerPlayerProfilePath')
    expect(viewerRoutesSource).toContain('export function viewerPlannedEventPath')
    expect(viewerRoutesSource).toContain('export function viewerTournamentDetailPath')
    expect(viewerRoutesSource).toContain('export function viewerRankingSnapshotPath')
    expect(viewerRoutesSource).toContain('export function viewerRaceSnapshotPath')

    for (const destination of destinations) {
      expect(destination).toMatch(/^\/viewer\//)
      expect(destination).not.toMatch(/^\/admin(?:\/|$)/)
      expect(destination).toContain(`/viewer/runs/${encodedRunSegment}`)
      expect(destination).not.toContain(runId)
      expect(destination).not.toContain('#')
      expect(viewerRouteExists(destination)).toBe(true)
    }
  })

  it('keeps registered history/finals components exported from the page source', () => {
    expect(registeredRoutePatterns).toContain('/viewer/runs/:runId/history')
    expect(registeredRoutePatterns).toContain('/viewer/runs/:runId/finals')
    expect(registeredRoutePatterns).toContain('/viewer/runs/:runId/finals/qualification')
    expect(registeredRoutePatterns).toContain('/viewer/runs/:runId/finals/result')
    expect(historyFinalsSource).toContain('export function ViewerRunHistoryPage')
    expect(historyFinalsSource).toContain('export function ViewerRunFinalsPage')
    expect(historyFinalsSource).toContain('export function ViewerRunFinalsQualificationPage')
    expect(historyFinalsSource).toContain('export function ViewerRunFinalsResultPage')
    expect(appSource).toContain('path="viewer/runs/:runId" element={<ViewerProductRunRouteBoundary />}')
    expect(appSource).toContain('path="history" element={<ViewerRunHistoryPage />}')
    expect(appSource).toContain('path="finals" element={<ViewerRunFinalsPage />}')
    expect(appSource).toContain('path="finals/qualification" element={<ViewerRunFinalsQualificationPage />}')
    expect(appSource).toContain('path="finals/result" element={<ViewerRunFinalsResultPage />}')
  })

  it('keeps history/finals source routed through scalar-safe helpers and Viewer route helpers', () => {
    for (const helperName of [
      'viewerFinalsPath',
      'viewerFinalsQualificationPath',
      'viewerFinalsResultPath',
      'viewerPlayerProfilePath',
      'viewerPlannedEventPath',
      'viewerTournamentDetailPath',
      'viewerRankingSnapshotPath',
      'viewerRaceSnapshotPath',
      'viewerRankingsPath',
      'viewerRacePath',
      'viewerTournamentsPath'
    ]) {
      expect(historyFinalsSource).toContain(helperName)
    }

    for (const helperName of [
      'isScalar',
      'safeScalarValue',
      'safeLinkId',
      'isPreviewableActivityItem',
      'collectPlayerIds',
      'hasQualificationPreviewData',
      'hasResultPreviewData'
    ]) {
      expect(historyFinalsSource).toContain(helperName)
    }
  })

  it('keeps history/finals source read-only without Admin or mutation affordances', () => {
    expect(historyFinalsSource).not.toContain('/admin')
    expect(historyFinalsSource).not.toContain('<button')
    expect(historyFinalsSource).not.toContain('type="submit"')
    expect(historyFinalsSource).not.toContain("type='submit'")
    expect(historyFinalsSource).not.toContain('useMutation')
    expect(historyFinalsSource).not.toContain('mutate(')
    expect(historyFinalsSource).not.toMatch(/\b(?:fetch|axios)\s*\([^)]*\b(?:POST|PUT|PATCH|DELETE)\b/i)
    expect(historyFinalsSource).not.toMatch(/\bclient\.(?:post|put|patch|delete)\b/i)
    expect(historyFinalsSource).not.toMatch(/\bmethod:\s*['"](?:POST|PUT|PATCH|DELETE)['"]/)

    for (const label of visibleMutationLabels) {
      expect(historyFinalsSource).not.toMatch(new RegExp(`>[^<]*${label}[^<]*<`, 'i'))
      expect(historyFinalsSource).not.toMatch(new RegExp(`aria-label=['"][^'"]*${label}[^'"]*['"]`, 'i'))
    }
  })

  it('keeps history/finals source free of fake-data claims and unsafe route templates', () => {
    expect(historyFinalsSource).not.toMatch(/fake champion|fake winner|invented champion|invented standings|invented finals|fake finals|fixture finals|fake history|invented history|fake finalist|invented finalist|qualification standing|champion player name/i)
    expect(historyFinalsSource).not.toContain('`/viewer/runs/${runId}/history`')
    expect(historyFinalsSource).not.toContain('`/viewer/runs/${runId}/finals`')
    expect(historyFinalsSource).not.toContain('`/viewer/runs/${runId}/rankings`')
    expect(historyFinalsSource).not.toContain('`/viewer/runs/${runId}/race`')
    expect(historyFinalsSource).not.toContain('`/viewer/runs/${runId}/tournaments`')
    expect(historyFinalsSource).not.toContain('`/viewer/runs/${runId}/calendar`')
    expect(historyFinalsSource).toContain('viewerFinalsPath(runId)')
    expect(historyFinalsSource).toContain('viewerFinalsQualificationPath(runId)')
    expect(historyFinalsSource).toContain('viewerFinalsResultPath(runId)')
    expect(historyFinalsSource).toContain('safeScalarValue')
    expect(historyFinalsSource).toContain('safeLinkId')
  })
})

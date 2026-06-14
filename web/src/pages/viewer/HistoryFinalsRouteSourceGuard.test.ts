import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import historyFinalsSource from '../ViewerRunHistoryFinalsPage.tsx?raw'
import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import { viewerFinalsPath, viewerHistoryPath } from '../../viewer/viewerRoutes'

const registeredRoutePatterns = new Set([...appSource.matchAll(/<Route\s+path="([^"]+)"/g)].map((match) => `/${match[1]}`))
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

function routePattern(path: string): RegExp {
  return new RegExp(`^${path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/:[^/]+/g, '[^/]+')}$`)
}

function viewerRouteExists(to: string): boolean {
  return [...registeredRoutePatterns].some((route) => routePattern(route).test(to))
}

describe('History/Finals Viewer route source guard', () => {
  it('keeps history/finals route helpers exported, encoded, Viewer-only, and registered', () => {
    const runId = 'run/alpha #1'
    const encodedRunSegment = 'run%2Falpha%20%231'
    const destinations = [viewerHistoryPath(runId), viewerFinalsPath(runId)]

    expect(viewerRoutesSource).toContain('export function viewerHistoryPath')
    expect(viewerRoutesSource).toContain('export function viewerFinalsPath')

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
    expect(historyFinalsSource).toContain('export function ViewerRunHistoryPage')
    expect(historyFinalsSource).toContain('export function ViewerRunFinalsPage')
    expect(appSource).toContain('path="viewer/runs/:runId/history" element={<ViewerRunHistoryPage />}')
    expect(appSource).toContain('path="viewer/runs/:runId/finals" element={<ViewerRunFinalsPage />}')
  })

  it('keeps history/finals source read-only without Admin or mutation affordances', () => {
    expect(historyFinalsSource).not.toContain('/admin')
    expect(historyFinalsSource).not.toContain('<button')
    expect(historyFinalsSource).not.toContain('type="submit"')
    expect(historyFinalsSource).not.toContain("type='submit'")
    expect(historyFinalsSource).not.toContain('useMutation')
    expect(historyFinalsSource).not.toContain('mutate(')
    expect(historyFinalsSource).not.toMatch(/\b(?:post|put|patch|delete)\s*\(/i)
    expect(historyFinalsSource).not.toMatch(/\bclient\.(?:post|put|patch|delete)\b/i)
    expect(historyFinalsSource).not.toMatch(/\bmethod:\s*['"](?:POST|PUT|PATCH|DELETE)['"]/)

    for (const label of visibleMutationLabels) {
      expect(historyFinalsSource).not.toMatch(new RegExp(`>[^<]*${label}[^<]*<`, 'i'))
      expect(historyFinalsSource).not.toMatch(new RegExp(`aria-label=['"][^'"]*${label}[^'"]*['"]`, 'i'))
    }
  })

  it('keeps history/finals source free of fake-data claims and unsafe route templates', () => {
    expect(historyFinalsSource).not.toMatch(/fake champion|fake winner|invented champion|invented standings|invented finals|fake finals|fixture finals|fake history|invented history/i)
    expect(historyFinalsSource).not.toContain('`/viewer/runs/${runId}/history`')
    expect(historyFinalsSource).not.toContain('`/viewer/runs/${runId}/finals`')
  })
})

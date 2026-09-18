import appSource from '../../App.tsx?raw'
import { viewerAppRouteExists } from '../../test/viewerAppRouteSource'

import { describe, expect, it } from 'vitest'

import { buildRunBrowserContextLinks, buildRunBrowserPrimaryLinks, buildViewerRunBrowserLinks } from '../../viewer/runBrowserDisplay'


describe('Viewer Run Browser routes', () => {
  it('keeps the run browser route path unchanged', () => {
    expect(appSource).toContain('<Route path="viewer/runs" element={<ViewerRunBrowserPage />} />')
  })

  it('links only to existing run-scoped Viewer route helpers', () => {
    const destinations = [...buildRunBrowserPrimaryLinks('run-alpha'), ...buildRunBrowserContextLinks('run-alpha')]

    expect(
      destinations.filter(
        (destination) => !viewerAppRouteExists(appSource, destination.to),
      ),
    ).toEqual([])
  })

  it('keeps run browser helper destinations Viewer-only and encoded for slash-containing run IDs', () => {
    const destinations = buildViewerRunBrowserLinks('run/with slash')

    for (const destination of destinations) {
      expect(destination.to.startsWith('/viewer/runs/')).toBe(true)
      expect(destination.to.startsWith('/admin')).toBe(false)
      expect(destination.to).toContain('/viewer/runs/run%2Fwith%20slash/')
      expect(destination.to).not.toContain('/viewer/runs/run/with slash/')
    }
  })

})

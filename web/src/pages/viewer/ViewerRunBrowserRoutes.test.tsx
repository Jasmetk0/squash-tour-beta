import appSource from '../../App.tsx?raw'

import { describe, expect, it } from 'vitest'

import { buildRunBrowserContextLinks, buildRunBrowserPrimaryLinks } from '../../viewer/runBrowserDisplay'

function appViewerRoutes(): Set<string> {
  return new Set([...appSource.matchAll(/<Route\s+path="(viewer[^"]*)"/g)].map((match) => `/${match[1]}`))
}

function routePattern(path: string): RegExp {
  return new RegExp(`^${path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/:[^/]+/g, '[^/]+')}$`)
}

describe('Viewer Run Browser routes', () => {
  it('keeps the run browser route path unchanged', () => {
    expect(appSource).toContain('<Route path="viewer/runs" element={<ViewerRunBrowserPage />} />')
  })

  it('links only to existing run-scoped Viewer route helpers', () => {
    const routes = appViewerRoutes()
    const destinations = [...buildRunBrowserPrimaryLinks('run-alpha'), ...buildRunBrowserContextLinks('run-alpha')]

    expect(destinations.filter((destination) => ![...routes].some((route) => routePattern(route).test(destination.to)))).toEqual([])
  })
})

import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import runBrowserDisplaySource from '../../viewer/runBrowserDisplay.ts?raw'
import viewerHomeDisplaySource from '../../viewer/viewerHomeDisplay.ts?raw'
import viewerHubLinksSource from '../../viewer/viewerHubLinks.ts?raw'
import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import guardSource from './ViewerTopLevelRouteSourceGuard.test.ts?raw'
import viewerHomePageSource from './ViewerHomePage.tsx?raw'
import viewerRunBrowserPageSource from './ViewerRunBrowserPage.tsx?raw'

const deferredViewerPageSources = import.meta.glob('./deferred/*.tsx', { query: '?raw', import: 'default', eager: true }) as Record<string, string>

const linkBuilderSources: Record<string, string> = {
  'viewerRoutes.ts': viewerRoutesSource,
  'viewerHubLinks.ts': viewerHubLinksSource,
  'viewerHomeDisplay.ts': viewerHomeDisplaySource,
  'runBrowserDisplay.ts': runBrowserDisplaySource,
  'ViewerHomePage.tsx': viewerHomePageSource,
  'ViewerRunBrowserPage.tsx': viewerRunBrowserPageSource
}

const topLevelAndDeferredViewerSources: Record<string, string> = {
  'viewerHubLinks.ts': viewerHubLinksSource,
  'viewerHomeDisplay.ts': viewerHomeDisplaySource,
  'runBrowserDisplay.ts': runBrowserDisplaySource,
  'ViewerHomePage.tsx': viewerHomePageSource,
  'ViewerRunBrowserPage.tsx': viewerRunBrowserPageSource,
  ...deferredViewerPageSources
}

const forbiddenMutationSource = [
  /\/admin(?:\/|['"`]|$)/,
  /<button\b/i,
  /type=["']submit["']/i,
  /\buseMutation\b/,
  /\bmutate\s*\(/,
  /\bmethod\s*:\s*['"](?:POST|PUT|PATCH|DELETE)['"]/i,
  /\b(?:fetch|request|axios\.(?:post|put|patch|delete))\s*\([^)]*['"](?:POST|PUT|PATCH|DELETE)['"]/i
]

const forbiddenVisibleMutationLabels = /(?:>\s*|['"`])(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)(?:\s*<|['"`])/i

const forbiddenFakeHubClaims = /(?:fake champion|fake winner|invented champion|invented winner|fake standings|invented standings|fake prediction|invented prediction|fake odds|invented odds|fake ranking|invented ranking|fake stat|invented stat|fake H2H|invented H2H|world champion|grand slam|career high no\. 1|Team Championship|medals|Top 100|standings table)/i

function viewerRoutesFromApp(): string[] {
  return [...appSource.matchAll(/<Route\s+path="(viewer(?:\/[^"*]+)?)"/g)].map((match) => `/${match[1]}`)
}

describe('Viewer top-level route source guard', () => {
  it('keeps top-level Viewer link builders Viewer-only', () => {
    expect(viewerRoutesSource).toContain("'/viewer")
    expect(viewerHubLinksSource).toContain('viewerTopLevelHubLinks')
    expect(viewerHomeDisplaySource).toContain('viewerTopLevelHubLinks')
    expect(runBrowserDisplaySource).toContain('viewerRankingsPath')

    for (const [sourceName, source] of Object.entries(linkBuilderSources)) {
      expect(source, sourceName).not.toMatch(/\/admin(?:\/|['"`]|$)/)
      expect(source, sourceName).not.toMatch(/to=\{?['"`]\/admin|href=\{?['"`]\/admin/i)
    }
  })

  it('keeps top-level and deferred Viewer sources read-only', () => {
    for (const [sourceName, source] of Object.entries(topLevelAndDeferredViewerSources)) {
      for (const forbiddenPattern of forbiddenMutationSource) {
        expect(source, `${sourceName} must not match ${forbiddenPattern}`).not.toMatch(forbiddenPattern)
      }
      expect(source, `${sourceName} must not expose visible mutation labels`).not.toMatch(forbiddenVisibleMutationLabels)
    }
  })

  it('keeps top-level and deferred Viewer sources free of fake or invented hub claims', () => {
    for (const [sourceName, source] of Object.entries(topLevelAndDeferredViewerSources)) {
      expect(source, sourceName).not.toMatch(forbiddenFakeHubClaims)
    }
  })

  it('keeps this guard scoped away from run-scoped production module inspection', () => {
    const collectedViewerRoutes = viewerRoutesFromApp()
    const runScopedRoutePatterns = collectedViewerRoutes.filter((route) => route.startsWith('/viewer/runs/:'))

    expect(runScopedRoutePatterns.length).toBeGreaterThan(0)
    expect(guardSource).not.toContain('ViewerRun' + 'SnapshotsPage')
    expect(guardSource).not.toContain('ViewerRun' + 'PlayersCountriesPage')
    expect(guardSource).not.toContain('ViewerRun' + 'CalendarPage')
    expect(guardSource).not.toContain('ViewerRun' + 'TournamentsPage')
    expect(guardSource).not.toContain('ViewerRun' + 'HistoryFinalsPage')
  })
})

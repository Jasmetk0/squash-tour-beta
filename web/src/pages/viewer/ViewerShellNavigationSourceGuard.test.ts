import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import layoutSource from '../../components/Layout.tsx?raw'
import viewerTopbarSource from '../../components/ViewerTopbar.tsx?raw'
import viewerRunSelectorSource from '../../components/ViewerRunSelector.tsx?raw'
import viewerShellPageSource from '../../components/viewer/ViewerShellPage.tsx?raw'
import viewerLandingComponentsSource from '../../components/viewer/ViewerLandingComponents.tsx?raw'
import activeRunDisplaySource from '../../viewer/activeRunDisplay.ts?raw'
import runBrowserDisplaySource from '../../viewer/runBrowserDisplay.ts?raw'
import viewerHomeDisplaySource from '../../viewer/viewerHomeDisplay.ts?raw'
import { buildActiveRunHubLinks, viewerTopLevelHubLinks } from '../../viewer/viewerHubLinks'
import viewerHubLinksRawSource from '../../viewer/viewerHubLinks.ts?raw'
import { viewerDropdowns } from '../../viewer/viewerNavigation'
import viewerNavigationRawSource from '../../viewer/viewerNavigation.ts?raw'
import viewerRoutesSource from '../../viewer/viewerRoutes.ts?raw'
import guardSource from './ViewerShellNavigationSourceGuard.test.ts?raw'
import viewerHomePageSource from './ViewerHomePage.tsx?raw'
import viewerRunBrowserPageSource from './ViewerRunBrowserPage.tsx?raw'


const expectedShellNavigationSourceNames = [
  'App.tsx',
  'Layout.tsx',
  'ViewerTopbar.tsx',
  'ViewerRunSelector.tsx',
  'ViewerShellPage.tsx',
  'ViewerLandingComponents.tsx',
  'viewerRoutes.ts',
  'viewerHubLinks.ts',
  'viewerNavigation.ts',
  'viewerHomeDisplay.ts',
  'runBrowserDisplay.ts',
  'activeRunDisplay.ts',
  'ViewerHomePage.tsx',
  'ViewerRunBrowserPage.tsx'
]

const expectedViewerLinkSourceNames = [
  'ViewerTopbar.tsx',
  'ViewerRunSelector.tsx',
  'ViewerLandingComponents.tsx',
  'viewerRoutes.ts',
  'viewerHubLinks.ts',
  'viewerNavigation.ts',
  'viewerHomeDisplay.ts',
  'runBrowserDisplay.ts',
  'activeRunDisplay.ts',
  'ViewerHomePage.tsx',
  'ViewerRunBrowserPage.tsx'
]

const shellNavigationSources: Record<string, string> = {
  'App.tsx': appSource,
  'Layout.tsx': layoutSource,
  'ViewerTopbar.tsx': viewerTopbarSource,
  'ViewerRunSelector.tsx': viewerRunSelectorSource,
  'ViewerShellPage.tsx': viewerShellPageSource,
  'ViewerLandingComponents.tsx': viewerLandingComponentsSource,
  'viewerRoutes.ts': viewerRoutesSource,
  'viewerHubLinks.ts': viewerHubLinksRawSource,
  'viewerNavigation.ts': viewerNavigationRawSource,
  'viewerHomeDisplay.ts': viewerHomeDisplaySource,
  'runBrowserDisplay.ts': runBrowserDisplaySource,
  'activeRunDisplay.ts': activeRunDisplaySource,
  'ViewerHomePage.tsx': viewerHomePageSource,
  'ViewerRunBrowserPage.tsx': viewerRunBrowserPageSource
}

const viewerLinkSources: Record<string, string> = {
  'ViewerTopbar.tsx': viewerTopbarSource,
  'ViewerRunSelector.tsx': viewerRunSelectorSource,
  'ViewerLandingComponents.tsx': viewerLandingComponentsSource,
  'viewerRoutes.ts': viewerRoutesSource,
  'viewerHubLinks.ts': viewerHubLinksRawSource,
  'viewerNavigation.ts': viewerNavigationRawSource,
  'viewerHomeDisplay.ts': viewerHomeDisplaySource,
  'runBrowserDisplay.ts': runBrowserDisplaySource,
  'activeRunDisplay.ts': activeRunDisplaySource,
  'ViewerHomePage.tsx': viewerHomePageSource,
  'ViewerRunBrowserPage.tsx': viewerRunBrowserPageSource
}

const forbiddenAdminDestination = /(?:to|href)=\{?['"]\/admin|['"]\/admin(?:\/|['"`]|$)/i
const forbiddenAdminViewerNavLabel = /(?:Viewer|MSA|active run|hub|topbar|landing|dropdown|navigation)[\s\S]{0,120}(?:Admin|Commissioner|Engine Mode)/i
const forbiddenUnsafeRunTemplates = /\/viewer\/runs\/\$\{\s*runId\s*\}|\/viewer\/runs\/['"`]?\s*\+\s*runId|`\/viewer\/runs\/\$\{runId\}/
const forbiddenMutationSource = [
  /\buseMutation\b/,
  /\bmutate\s*\(/,
  /\bmethod\s*:\s*['"](?:POST|PUT|PATCH|DELETE)['"]/i,
  /\b(?:fetch|request|axios\.(?:post|put|patch|delete))\s*\([^)]*['"](?:POST|PUT|PATCH|DELETE)['"]/i,
  /\bapiClient\.(?:post|put|patch|delete)\s*\(/i,
  /\b(?:post|put|patch|delete)(?:Json|Data|Run|Season|Tournament|Player|Country)?\s*\(/i
]
const forbiddenVisibleMutationLabels = /(?:>\s*|['"`])(?:Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)(?:\s*<|['"`])/i
const allowedLocalSelectionLabels = /Set active run|Viewer selection is stored locally|This only changes local Viewer context/
const forbiddenFakeNavClaims = /(?:fake champion|fake winner|invented champion|invented winner|fake standings|invented standings|fake prediction|invented prediction|fake odds|invented odds|fake ranking|invented ranking|fake stat|invented stat|fake H2H|invented H2H|world champion|grand slam|career high no\. 1|Team Championship|medals|Top 100|standings table)/i

const forbiddenRunScopedProductionModuleNames = [
  'ViewerRun' + 'SnapshotsPage',
  'ViewerRun' + 'PlayersCountriesPage',
  'ViewerRun' + 'CalendarPage',
  'ViewerRun' + 'TournamentsPage',
  'ViewerRun' + 'HistoryFinalsPage'
]

function appRoutePaths(): string[] {
  return [...appSource.matchAll(/<Route\s+path="([^"]+)"/g)].map((match) => `/${match[1]}`)
}

function routePattern(path: string): RegExp {
  return new RegExp(`^${path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/:[^/]+/g, '[^/]+')}$`)
}

function appRouteExists(destination: string): boolean {
  return appRoutePaths().some((route) => routePattern(route).test(destination))
}

describe('Viewer shell/navigation source guard', () => {
  it('keeps source coverage focused on shell/navigation and top-level Viewer sources', () => {
    expect(Object.keys(shellNavigationSources)).toEqual(expectedShellNavigationSourceNames)
    expect(Object.keys(viewerLinkSources)).toEqual(expectedViewerLinkSourceNames)

    for (const sourceName of expectedShellNavigationSourceNames) {
      expect(shellNavigationSources[sourceName], sourceName).toBeTruthy()
    }

    expect(guardSource).toContain("Layout.tsx?raw")
    expect(guardSource).toContain("ViewerTopbar.tsx?raw")
    expect(guardSource).toContain("ViewerRunSelector.tsx?raw")
    expect(guardSource).toContain("ViewerShellPage.tsx?raw")
    expect(guardSource).toContain("ViewerLandingComponents.tsx?raw")
    expect(guardSource).toContain("viewerRoutes.ts?raw")
    expect(guardSource).toContain("viewerHubLinks.ts?raw")
    expect(guardSource).toContain("viewerNavigation.ts?raw")
    expect(guardSource).toContain("viewerHomeDisplay.ts?raw")
    expect(guardSource).toContain("runBrowserDisplay.ts?raw")
    expect(guardSource).toContain("activeRunDisplay.ts?raw")
    expect(guardSource).toContain("ViewerHomePage.tsx?raw")
    expect(guardSource).toContain("ViewerRunBrowserPage.tsx?raw")
  })

  it('keeps Viewer navigation and link builder sources Viewer-only', () => {
    expect(viewerRoutesSource).toContain("'/viewer")
    expect(viewerHubLinksRawSource).toContain('viewerTopLevelHubLinks')
    expect(viewerNavigationRawSource).toContain('viewerDropdowns')
    expect(activeRunDisplaySource).toContain('buildViewerActiveRunQuickLinks')
    expect(viewerHubLinksRawSource).toContain('buildActiveRunHubLinks')

    for (const [sourceName, source] of Object.entries(viewerLinkSources)) {
      expect(source, `${sourceName} must not expose Admin destinations`).not.toMatch(forbiddenAdminDestination)
      expect(source, `${sourceName} must not mix Admin labels into Viewer navigation`).not.toMatch(forbiddenAdminViewerNavLabel)
      expect(source, `${sourceName} must not hardcode unsafe active-run templates`).not.toMatch(forbiddenUnsafeRunTemplates)
    }

    for (const link of viewerTopLevelHubLinks) {
      expect(link.to, link.label).toMatch(/^\/viewer(?:\/|$)/)
      expect(link.to, link.label).not.toMatch(/^\/admin(?:\/|$)/)
    }

    for (const dropdown of viewerDropdowns) {
      expect(dropdown.to, dropdown.label).toMatch(/^\/viewer(?:\/|$)/)
      expect(dropdown.to, dropdown.label).not.toMatch(/^\/admin(?:\/|$)/)
      for (const item of dropdown.items) {
        expect(item.to, `${dropdown.label}: ${item.label}`).toMatch(/^\/viewer(?:\/|$)/)
        expect(item.to, `${dropdown.label}: ${item.label}`).not.toMatch(/^\/admin(?:\/|$)/)
      }
    }
  })

  it('keeps top-level hub and active-run quick link destinations registered in App routes', () => {
    const runId = 'run/alpha #1'
    const encodedRunSegment = 'run%2Falpha%20%231'

    for (const link of viewerTopLevelHubLinks) {
      expect(link.to, link.label).toMatch(/^\/viewer(?:\/|$)/)
      expect(link.to, link.label).not.toMatch(/^\/admin(?:\/|$)/)
      expect(appRouteExists(link.to), link.label).toBe(true)
    }

    for (const dropdown of viewerDropdowns) {
      expect(dropdown.to, dropdown.label).toMatch(/^\/viewer(?:\/|$)/)
      expect(dropdown.to, dropdown.label).not.toMatch(/^\/admin(?:\/|$)/)
      expect(appRouteExists(dropdown.to), dropdown.label).toBe(true)
      for (const item of dropdown.items) {
        expect(item.to, `${dropdown.label}: ${item.label}`).toMatch(/^\/viewer(?:\/|$)/)
        expect(item.to, `${dropdown.label}: ${item.label}`).not.toMatch(/^\/admin(?:\/|$)/)
        expect(appRouteExists(item.to), `${dropdown.label}: ${item.label}`).toBe(true)
      }
    }

    for (const link of buildActiveRunHubLinks(runId)) {
      expect(link.to, link.label).toMatch(/^\/viewer(?:\/|$)/)
      expect(link.to, link.label).not.toMatch(/^\/admin(?:\/|$)/)
      expect(link.to, link.label).toContain(`/viewer/runs/${encodedRunSegment}`)
      expect(link.to, link.label).not.toContain(runId)
      expect(link.to, link.label).not.toContain('#')
      expect(appRouteExists(link.to), link.label).toBe(true)
    }
  })

  it('keeps selector normalization and active-run storage source paths scalar-safe and local', () => {
    expect(viewerRunSelectorSource).toContain('listRunContainers')
    expect(viewerRunBrowserPageSource).toContain('normalizeRunBrowserRuns')
    expect(runBrowserDisplaySource).toContain('getSafeRunBrowserRunId')
    expect(activeRunDisplaySource).toContain('formatSafeRunOptionValue')
    expect(viewerRunSelectorSource).toContain('readViewerActiveRunId')
    expect(viewerRunSelectorSource).toContain('writeViewerActiveRunId')

    for (const [sourceName, source] of Object.entries(shellNavigationSources)) {
      expect(source, `${sourceName} must not directly cast API run lists`).not.toContain('as ViewerRunBrowserListItem[]')
    }

    for (const [sourceName, source] of Object.entries(viewerLinkSources)) {
      expect(source, `${sourceName} must not hardcode unsafe run links`).not.toMatch(forbiddenUnsafeRunTemplates)
      expect(source, `${sourceName} must not expose /admin destinations`).not.toMatch(forbiddenAdminDestination)
    }
  })

  it('keeps shell/navigation/top-level sources read-only and free of backend mutation affordances', () => {
    for (const [sourceName, source] of Object.entries(shellNavigationSources)) {
      for (const forbiddenPattern of forbiddenMutationSource) {
        expect(source, `${sourceName} must not match ${forbiddenPattern}`).not.toMatch(forbiddenPattern)
      }
      if (!allowedLocalSelectionLabels.test(source)) {
        expect(source, `${sourceName} must not expose visible mutation labels`).not.toMatch(forbiddenVisibleMutationLabels)
      }
    }
  })

  it('keeps shell/navigation/top-level sources free of fake or invented claims', () => {
    for (const [sourceName, source] of Object.entries(shellNavigationSources)) {
      expect(source, sourceName).not.toMatch(forbiddenFakeNavClaims)
    }
  })

  it('keeps this shell/navigation guard scoped away from completed run-scoped production modules', () => {
    for (const moduleName of forbiddenRunScopedProductionModuleNames) {
      expect(guardSource).not.toContain(moduleName)
    }
  })
})

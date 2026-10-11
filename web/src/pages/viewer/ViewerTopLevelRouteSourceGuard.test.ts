import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import viewerRunSelectorSource from '../../components/ViewerRunSelector.tsx?raw'
import activeRunDisplaySource from '../../viewer/activeRunDisplay.ts?raw'
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
  'activeRunDisplay.ts': activeRunDisplaySource,
  'ViewerHomePage.tsx': viewerHomePageSource,
  'ViewerRunBrowserPage.tsx': viewerRunBrowserPageSource
}

const topLevelAndDeferredViewerSources: Record<string, string> = {
  'viewerHubLinks.ts': viewerHubLinksSource,
  'viewerHomeDisplay.ts': viewerHomeDisplaySource,
  'runBrowserDisplay.ts': runBrowserDisplaySource,
  'activeRunDisplay.ts': activeRunDisplaySource,
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

const forbiddenUnsafeRunTemplates = /\/viewer\/runs\/\$\{|\/viewer\/runs\/['"`]?\s*\+/

const forbiddenRunScopedProductionImportPatterns = [
  /from ['"](?:\.\.\/)?ViewerRun(Snapshots|PlayersCountries|Calendar|Tournaments|HistoryFinals)Page/,
  /from ['"][^'"]*\/(?:rankings|players-countries|calendar|tournaments|history-finals)\//
]

function expectNoRunScopedProductionImports(sourceName: string, source: string): void {
  for (const forbiddenPattern of forbiddenRunScopedProductionImportPatterns) {
    expect(source, `${sourceName} must not match ${forbiddenPattern}`).not.toMatch(forbiddenPattern)
  }
}

const lockedTopLevelViewerRoutes = [
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

const forbiddenFakeHubClaims = /(?:fake champion|fake winner|invented champion|invented winner|fake standings|invented standings|fake prediction|invented prediction|fake odds|invented odds|fake ranking|invented ranking|fake stat|invented stat|fake H2H|invented H2H|world champion|grand slam|career high no\. 1|Team Championship|medals|Top 100|standings table)/i

function viewerRoutesFromApp(): string[] {
  return [...appSource.matchAll(/<Route\s+path="(viewer(?:\/[^"*]+)?)"/g)].map((match) => `/${match[1]}`)
}

describe('Viewer top-level route source guard', () => {
  it('keeps top-level Viewer route registration locked', () => {
    const routes = viewerRoutesFromApp()
    const topLevelViewerRoutes = routes.filter((route) => route.startsWith('/viewer') && !route.startsWith('/viewer/runs/:'))

    expect(topLevelViewerRoutes).toEqual(lockedTopLevelViewerRoutes)
  })

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

  it('keeps top-level link and display helper exports wired into source', () => {
    const expectedHelperNames = [
      'viewerTopLevelHubLinks',
      'buildActiveRunHubLinks',
      'buildViewerHomeActiveRunLinks',
      'buildViewerHomePrimaryHubLinks',
      'buildViewerHomeReadOnlyNotes',
      'buildRunBrowserPrimaryLinks',
      'buildRunBrowserContextLinks',
      'buildRunBrowserMetadataItems',
      'normalizeRunBrowserRuns',
      'getSafeRunBrowserRunId',
      'formatViewerRunOptionLabel',
      'formatViewerCompactRunOptionLabel',
      'buildViewerActiveRunQuickLinks'
    ]
    const combinedHelperSource = [viewerHubLinksSource, viewerHomeDisplaySource, runBrowserDisplaySource, activeRunDisplaySource].join('\n')

    for (const helperName of expectedHelperNames) {
      expect(combinedHelperSource, helperName).toContain(helperName)
    }
  })

  it('keeps run browser and selector list rendering behind scalar-safe normalization', () => {
    expect(viewerRunBrowserPageSource).toContain('normalizeRunBrowserRuns')
    expect(viewerRunSelectorSource).toContain('normalizeRunBrowserRuns')
    expect(runBrowserDisplaySource).toContain('getSafeRunBrowserRunId')
    expect(runBrowserDisplaySource).toContain('normalizeRunBrowserRuns')
    expect(activeRunDisplaySource).toContain('formatSafeRunOptionValue')

    for (const [sourceName, source] of Object.entries({
      'ViewerRunBrowserPage.tsx': viewerRunBrowserPageSource,
      'ViewerRunSelector.tsx': viewerRunSelectorSource,
      'runBrowserDisplay.ts': runBrowserDisplaySource,
      'activeRunDisplay.ts': activeRunDisplaySource
    })) {
      expect(source, `${sourceName} must not directly trust API run lists`).not.toContain('as ViewerRunBrowserListItem[]')
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

  it('keeps deferred page sources conservative and free of unsafe route templates', () => {
    expect(Object.keys(deferredViewerPageSources).length).toBeGreaterThan(0)

    for (const [sourceName, source] of Object.entries(deferredViewerPageSources)) {
      expect(source, `${sourceName} should expose conservative deferred copy`).toMatch(/deferred|unavailable|not available|read-only/i)
      expect(source, `${sourceName} must not hardcode unsafe run-scoped route templates`).not.toMatch(forbiddenUnsafeRunTemplates)
      expectNoRunScopedProductionImports(sourceName, source)
    }
  })

  it('keeps top-level target pages from importing completed run-scoped production modules directly', () => {
    for (const [sourceName, source] of Object.entries(topLevelAndDeferredViewerSources)) {
      expectNoRunScopedProductionImports(sourceName, source)
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

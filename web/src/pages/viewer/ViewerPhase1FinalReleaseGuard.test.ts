import { describe, expect, it } from 'vitest'

import appSource from '../../App.tsx?raw'
import manualQaSource from '../../../../docs/viewer_phase_1_manual_qa.md?raw'
import readModelIntegrationGuardSource from './ViewerReadModelRouteIntegration.test.tsx?raw'
import runScopedFinalGuardSource from './ViewerRunScopedModuleFinalGuard.test.ts?raw'
import shellNavigationFinalGuardSource from './ViewerShellNavigationSourceGuard.test.ts?raw'
import topLevelFinalGuardSource from './ViewerTopLevelRouteSourceGuard.test.ts?raw'

const finalGuardSources: Record<string, string> = {
  'ViewerRunScopedModuleFinalGuard.test.ts': runScopedFinalGuardSource,
  'ViewerTopLevelRouteSourceGuard.test.ts': topLevelFinalGuardSource,
  'ViewerShellNavigationSourceGuard.test.ts': shellNavigationFinalGuardSource,
  'ViewerReadModelRouteIntegration.test.tsx': readModelIntegrationGuardSource
}

const expectedInvariantThemes = [
  /Viewer-only|viewerOnly|Viewer only/i,
  /read-only|readOnly|read only/i,
  /encoded/i,
  /\/admin|Admin destination|adminPathPattern/i,
  /mutation|mutate|POST|PUT|PATCH|DELETE/i,
  /fake|invented/i,
  /run-scoped|runScoped|runs\/:runId/i,
  /top-level|topLevel|hub/i,
  /shell|navigation|topbar/i
]

const expectedManualQaPhaseNotes = [
  'Viewer Phase 9',
  'Viewer Phase 10',
  'Viewer Phase 11',
  'Viewer Phase 12',
  'Viewer Phase 13A',
  'Viewer Phase 14A',
  'Viewer Phase 14B',
  'Viewer Phase 14C',
  'Viewer Phase 15A',
  'Viewer Phase 15B',
  'Viewer Phase 15C',
  'Viewer Phase 16A'
]

const expectedCoreViewerRoutes = [
  '/viewer',
  '/viewer/runs',
  '/viewer/runs/:runId/rankings',
  '/viewer/runs/:runId/race',
  '/viewer/runs/:runId/calendar',
  '/viewer/runs/:runId/tournaments',
  '/viewer/runs/:runId/players',
  '/viewer/runs/:runId/countries',
  '/viewer/runs/:runId/history',
  '/viewer/runs/:runId/finals',
  '/viewer/rankings',
  '/viewer/rankings/race',
  '/viewer/tour',
  '/viewer/tour/calendar',
  '/viewer/tour/current-week',
  '/viewer/tour/tournaments',
  '/viewer/players',
  '/viewer/countries',
  '/viewer/history',
  '/viewer/stats',
  '/viewer/predictions',
  '/viewer/search'
]

function appRoutePaths(): Set<string> {
  return new Set([...appSource.matchAll(/<Route\s+path="([^"]+)"/g)].map((match) => `/${match[1]}`))
}

describe('Viewer Phase 1 final release guard', () => {
  it('keeps the final guard structure wired through raw source imports', () => {
    expect(Object.keys(finalGuardSources)).toEqual([
      'ViewerRunScopedModuleFinalGuard.test.ts',
      'ViewerTopLevelRouteSourceGuard.test.ts',
      'ViewerShellNavigationSourceGuard.test.ts',
      'ViewerReadModelRouteIntegration.test.tsx'
    ])

    for (const [sourceName, source] of Object.entries(finalGuardSources)) {
      expect(source, sourceName).toContain('describe(')
      expect(source, sourceName).toContain('Viewer')
    }
  })

  it('keeps final guard sources covering expected release-gate invariant themes', () => {
    const combinedGuardSource = Object.values(finalGuardSources).join('\n')

    for (const invariantTheme of expectedInvariantThemes) {
      expect(combinedGuardSource).toMatch(invariantTheme)
    }
  })

  it('keeps Viewer Phase 1 manual QA notes present in chronological final-release order', () => {
    let previousIndex = -1

    for (const phaseNote of expectedManualQaPhaseNotes) {
      const phaseIndex = manualQaSource.indexOf(phaseNote)
      expect(phaseIndex, phaseNote).toBeGreaterThan(previousIndex)
      previousIndex = phaseIndex
    }
  })

  it('keeps App core Viewer route groups registered for Viewer Phase 1', () => {
    const routes = appRoutePaths()

    for (const route of expectedCoreViewerRoutes) {
      expect(routes).toContain(route)
    }
  })
})

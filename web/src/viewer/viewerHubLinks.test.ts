import appSource from '../App.tsx?raw'

import { describe, expect, it } from 'vitest'

import { buildActiveRunHubLinks, viewerTopLevelHubLinks } from './viewerHubLinks'

const forbiddenViewerActionLabels = [
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

function appViewerRoutes(): Set<string> {
  return new Set(
    [...appSource.matchAll(/<Route\s+path="(viewer[^"]*)"/g)].map((match) => `/${match[1]}`)
  )
}

function routePattern(path: string): RegExp {
  return new RegExp(`^${path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/:[^/]+/g, '[^/]+')}$`)
}

function viewerRouteExists(to: string): boolean {
  const appRoutes = appViewerRoutes()
  return [...appRoutes].some((route) => routePattern(route).test(to))
}

describe('viewerHubLinks', () => {
  it('preserves active-run hub link labels, order, and hrefs for a sample run id', () => {
    expect(buildActiveRunHubLinks('run alpha')).toEqual([
      { label: 'Active Run Rankings', to: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Active Run Race', to: '/viewer/runs/run%20alpha/race' },
      { label: 'Active Run Tournaments', to: '/viewer/runs/run%20alpha/tournaments' },
      { label: 'Active Run Calendar', to: '/viewer/runs/run%20alpha/calendar' },
      { label: 'Active Run Players', to: '/viewer/runs/run%20alpha/players' },
      { label: 'Active Run Countries', to: '/viewer/runs/run%20alpha/countries' },
      { label: 'Active Run History', to: '/viewer/runs/run%20alpha/history' },
      { label: 'Active Run Finals', to: '/viewer/runs/run%20alpha/finals' }
    ])
  })

  it('preserves top-level hub link labels, hrefs, descriptions, and order', () => {
    expect(viewerTopLevelHubLinks).toEqual([
      { label: 'MSA Rankings', to: '/viewer/rankings', description: 'Read-only rankings publication for the selected season and week context.' },
      { label: 'Race to Finals', to: '/viewer/rankings/race', description: 'Read-only Race to Finals publication for the selected Viewer run.' },
      { label: 'Season Hub', to: '/viewer/tour', description: 'Read-only season hub for the selected Viewer run.' },
      { label: 'All Tournaments', to: '/viewer/tournaments', description: 'Read-only tournament hub for active-run tournament and calendar sources.' },
      { label: 'Players Hub', to: '/viewer/players', description: 'Read-only player hub using active-run player data when available.' },
      { label: 'Countries Hub', to: '/viewer/countries', description: 'Read-only country hub using active-run country and player data when available.' },
      { label: 'H2H Explorer', to: '/viewer/h2h', description: 'Read-only head-to-head explorer shell backed by active-run player source data.' },
      { label: 'Stats Hub', to: '/viewer/stats', description: 'Read-only stats hub for deferred records and statistics groups.' },
      { label: 'Records', to: '/viewer/records', description: 'Read-only records hub for deferred historical records groups.' },
      { label: 'Predictions', to: '/viewer/predictions', description: 'Read-only predictions hub with deferred forecast outputs.' },
      { label: 'Match Predictor', to: '/viewer/predictions/match-predictor', description: 'Read-only match predictor shell using selected player inputs only.' },
      { label: 'Search', to: '/viewer/search', description: 'Read-only Viewer search across safe active-run source data.' },
      { label: 'Run Browser', to: '/viewer/runs', description: 'Browse available generated runs and open run-scoped Viewer pages using existing run list metadata only.' }
    ])
  })

  it('does not expose forbidden Viewer action labels', () => {
    const helperText = [...buildActiveRunHubLinks('run alpha'), ...viewerTopLevelHubLinks]
      .flatMap((link) => [link.label, link.description ?? ''])
      .join('\n')

    for (const forbiddenLabel of forbiddenViewerActionLabels) {
      expect(helperText).not.toContain(forbiddenLabel)
    }
  })

  it('keeps helper destinations backed by App Viewer routes', () => {
    const destinations = [...buildActiveRunHubLinks('run alpha'), ...viewerTopLevelHubLinks]

    expect(destinations.filter((destination) => !viewerRouteExists(destination.to))).toEqual([])
  })
})

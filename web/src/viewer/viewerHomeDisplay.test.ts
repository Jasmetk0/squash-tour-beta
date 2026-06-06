import { describe, expect, it } from 'vitest'

import {
  buildViewerHomeActiveRunLinks,
  buildViewerHomePrimaryHubLinks,
  buildViewerHomeReadOnlyNotes,
  getViewerHomeActiveRunLabel
} from './viewerHomeDisplay'
import { viewerTopLevelHubLinks } from './viewerHubLinks'

const forbiddenAdminPathPattern = /^\/admin(?:\/|$)/

describe('viewerHomeDisplay', () => {
  it('builds active-run links in the Viewer Home order with route-helper encoded hrefs', () => {
    expect(buildViewerHomeActiveRunLinks('run/alpha #1')).toEqual([
      { label: 'Active Run Rankings', to: '/viewer/runs/run%2Falpha%20%231/rankings' },
      { label: 'Active Run Race', to: '/viewer/runs/run%2Falpha%20%231/race' },
      { label: 'Active Run Tournaments', to: '/viewer/runs/run%2Falpha%20%231/tournaments' },
      { label: 'Active Run Calendar', to: '/viewer/runs/run%2Falpha%20%231/calendar' },
      { label: 'Active Run Players', to: '/viewer/runs/run%2Falpha%20%231/players' },
      { label: 'Active Run Countries', to: '/viewer/runs/run%2Falpha%20%231/countries' },
      { label: 'Active Run History', to: '/viewer/runs/run%2Falpha%20%231/history' },
      { label: 'Active Run Finals', to: '/viewer/runs/run%2Falpha%20%231/finals' }
    ])
  })

  it('returns no active-run scoped links when no active run exists', () => {
    expect(buildViewerHomeActiveRunLinks(null)).toEqual([])
    expect(buildViewerHomeActiveRunLinks('   ')).toEqual([])
  })

  it('keeps primary hub links backed by existing Viewer hub definitions without Admin destinations', () => {
    const links = buildViewerHomePrimaryHubLinks()

    expect(links).toBe(viewerTopLevelHubLinks)
    expect(links.map((link) => link.label)).toContain('Run Browser')
    expect(links.some((link) => forbiddenAdminPathPattern.test(link.to))).toBe(false)
  })

  it('formats active-run labels and read-only notes without invented facts', () => {
    expect(getViewerHomeActiveRunLabel('run alpha')).toBe('Active Viewer run: run alpha')
    expect(getViewerHomeActiveRunLabel(null)).toBe('No active Viewer run selected')
    expect(buildViewerHomeReadOnlyNotes()).toEqual([
      'Viewer Home is read-only and links to existing Viewer surfaces only.',
      'Active-run shortcuts appear only when an active Viewer run is selected.',
      'Unavailable previews stay empty instead of inventing progress, results, standings, winners, or schedule facts.'
    ])
  })
})

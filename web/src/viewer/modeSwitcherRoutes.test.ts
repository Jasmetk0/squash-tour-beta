import { describe, expect, it } from 'vitest'

import { getModeSwitcherTarget } from './modeSwitcherRoutes'

describe('getModeSwitcherTarget', () => {
  it('keeps context-aware top-level mappings', () => {
    expect(getModeSwitcherTarget('/viewer')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin' })
    expect(getModeSwitcherTarget('/admin/players')).toEqual({ viewerTarget: '/viewer/players', adminTarget: '/admin/players' })
    expect(getModeSwitcherTarget('/viewer/countries')).toEqual({ viewerTarget: '/viewer/countries', adminTarget: '/admin/world/countries' })
    expect(getModeSwitcherTarget('/admin/tour-seasons')).toEqual({ viewerTarget: '/viewer/tour', adminTarget: '/admin/tour-seasons' })
  })

  it('maps every Viewer Product Run page to Admin Branch management with IDs encoded exactly once', () => {
    expect(getModeSwitcherTarget('/viewer/runs/product-a/rankings')).toEqual({ viewerTarget: '/viewer/runs/product-a/rankings', adminTarget: '/admin/runs/product-a/branches' })
    expect(getModeSwitcherTarget('/viewer/runs/product%2Frun/calendar')).toEqual({ viewerTarget: '/viewer/runs/product%2Frun/calendar', adminTarget: '/admin/runs/product%2Frun/branches' })
  })

  it('maps Admin Product Run Branch management to Viewer rankings', () => {
    expect(getModeSwitcherTarget('/admin/runs/product-a/branches')).toEqual({ viewerTarget: '/viewer/runs/product-a/rankings', adminTarget: '/admin/runs/product-a/branches' })
  })

  it('only maps legacy Admin routes after an exact active identity match', () => {
    const context = { activeProductRunId: 'product-a', activeLegacySimulationRunId: 'legacy-a' }
    expect(getModeSwitcherTarget('/admin/runs/legacy-a/calendar', context)).toEqual({ viewerTarget: '/viewer/runs/product-a/rankings', adminTarget: '/admin/runs/legacy-a/calendar' })
    expect(getModeSwitcherTarget('/admin/runs/legacy-b/calendar', context)).toEqual({ viewerTarget: '/viewer/runs', adminTarget: '/admin/runs/legacy-b/calendar' })
    expect(getModeSwitcherTarget('/admin/runs/legacy-a/calendar')).toEqual({ viewerTarget: '/viewer/runs', adminTarget: '/admin/runs/legacy-a/calendar' })
    expect(getModeSwitcherTarget('/admin/runs/legacy-a/calendar', context).viewerTarget).not.toContain('legacy-a')
  })

  it('falls back predictably for unknown Viewer and Admin routes', () => {
    expect(getModeSwitcherTarget('/viewer/unknown')).toEqual({ viewerTarget: '/viewer/unknown', adminTarget: '/admin' })
    expect(getModeSwitcherTarget('/admin/unknown')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin/unknown' })
    expect(getModeSwitcherTarget('/elsewhere')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin' })
  })
})

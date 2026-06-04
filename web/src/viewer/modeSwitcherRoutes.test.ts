import { describe, expect, it } from 'vitest'

import { getModeSwitcherTarget } from './modeSwitcherRoutes'

describe('getModeSwitcherTarget', () => {
  it('maps context-aware Admin/Viewer switcher routes', () => {
    expect(getModeSwitcherTarget('/viewer')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin' })
    expect(getModeSwitcherTarget('/admin')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin' })
    expect(getModeSwitcherTarget('/viewer/players')).toEqual({ viewerTarget: '/viewer/players', adminTarget: '/admin/players' })
    expect(getModeSwitcherTarget('/admin/players')).toEqual({ viewerTarget: '/viewer/players', adminTarget: '/admin/players' })
    expect(getModeSwitcherTarget('/viewer/countries')).toEqual({ viewerTarget: '/viewer/countries', adminTarget: '/admin/world/countries' })
    expect(getModeSwitcherTarget('/admin/world/countries')).toEqual({ viewerTarget: '/viewer/countries', adminTarget: '/admin/world/countries' })
    expect(getModeSwitcherTarget('/viewer/tour')).toEqual({ viewerTarget: '/viewer/tour', adminTarget: '/admin/tour-seasons' })
    expect(getModeSwitcherTarget('/admin/tour-seasons')).toEqual({ viewerTarget: '/viewer/tour', adminTarget: '/admin/tour-seasons' })
  })

  it('maps run-scoped Admin/Viewer switcher routes without changing encoded run IDs', () => {
    expect(getModeSwitcherTarget('/viewer/runs/abc/calendar')).toEqual({ viewerTarget: '/viewer/runs/abc/calendar', adminTarget: '/admin/runs/abc/calendar' })
    expect(getModeSwitcherTarget('/admin/runs/abc/calendar')).toEqual({ viewerTarget: '/viewer/runs/abc/calendar', adminTarget: '/admin/runs/abc/calendar' })
    expect(getModeSwitcherTarget('/viewer/runs/abc/players')).toEqual({ viewerTarget: '/viewer/runs/abc/players', adminTarget: '/admin/runs/abc/players' })
    expect(getModeSwitcherTarget('/admin/runs/abc/players')).toEqual({ viewerTarget: '/viewer/runs/abc/players', adminTarget: '/admin/runs/abc/players' })
    expect(getModeSwitcherTarget('/admin/runs/run%20alpha/calendar')).toEqual({
      viewerTarget: '/viewer/runs/run%20alpha/calendar',
      adminTarget: '/admin/runs/run%20alpha/calendar'
    })
    expect(getModeSwitcherTarget('/admin/runs/run%2Falpha/players')).toEqual({
      viewerTarget: '/viewer/runs/run%2Falpha/players',
      adminTarget: '/admin/runs/run%2Falpha/players'
    })
  })

  it('falls back predictably for unknown Viewer and Admin routes', () => {
    expect(getModeSwitcherTarget('/viewer/unknown')).toEqual({ viewerTarget: '/viewer/unknown', adminTarget: '/admin' })
    expect(getModeSwitcherTarget('/admin/unknown')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin/unknown' })
    expect(getModeSwitcherTarget('/elsewhere')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin' })
  })
})

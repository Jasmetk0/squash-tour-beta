import { describe, expect, it } from 'vitest'
import { globalAdminNav, globalAdminBottomNav, runAdminNavFor, runAdminBottomNavFor } from './adminNavigation'

describe('approved pre-alpha navigation', () => {
  it('has exactly the approved four global sections and separate application settings', () => {
    expect(globalAdminNav.map(item => item.label)).toEqual(['Home', 'Runs', 'Packages', 'Test Lab'])
    expect(globalAdminBottomNav).toEqual([{ to: '/admin/settings', label: 'Settings' }])
    expect(globalAdminNav[1].children).toContainEqual({
      to: '/admin/operations', label: 'Simulation Task Center'
    })
  })
  it('has seven Run categories, functional routes and separate Run Management', () => {
    const items = runAdminNavFor('run-a')
    expect(items.map(item => item.label)).toEqual(['Home', 'World', 'Players', 'Tour', 'Rankings & Analytics', 'Simulation', 'History & Branches'])
    expect(items.map(item => item.to)).toEqual([
      '/admin/runs/run-a', '/admin/runs/run-a/world', '/admin/runs/run-a/players',
      '/admin/runs/run-a/calendar', '/admin/runs/run-a/snapshots/ranking',
      '/admin/runs/run-a/simulate', '/admin/runs/run-a/branches'
    ])
    expect(runAdminBottomNavFor('run-a')[0].to).toBe('/admin/runs/run-a/manage')
    expect(items[1].children?.[0]).toEqual({to:'/admin/runs/run-a/world',label:'World overview'})
    expect(items.find(item => item.label === 'Tour')?.children?.some(item => item.to.endsWith('/finals'))).toBe(true)
  })
})

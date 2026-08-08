import { describe, expect, it } from 'vitest'

import { globalAdminNav, runAdminNavFor } from './adminNavigation'

describe('adminNavigation', () => {
  it('keeps Global Admin navigation labels, order, and hrefs stable', () => {
    expect(globalAdminNav).toEqual([
      { to: '/admin', label: 'Dashboard' },
      { to: '/admin/world', label: 'World' },
      { to: '/admin/players', label: 'Players' },
      { to: '/admin/tour-seasons', label: 'Tour & Seasons' },
      { to: '/admin/runs', label: 'Runs' },
      { to: '/admin/simulate', label: 'Simulate' },
      { to: '/admin/diagnostics', label: 'Diagnostics' },
      { to: '/admin/settings', label: 'Settings' }
    ])
  })

  it('keeps Run Admin navigation labels, order, and hrefs stable', () => {
    expect(runAdminNavFor('run-a')).toEqual([
      { to: '/admin/runs/run-a', label: 'Home' },
      { to: '/admin/runs/run-a/events', label: 'Events' },
      { to: '/admin/runs/run-a/calendar', label: 'Season Calendar' },
      { to: '/admin/runs/run-a/activity', label: 'Activity' },
      { to: '/admin/runs/run-a/players', label: 'Players' },
      { to: '/admin/runs/run-a/nations', label: 'Nations' },
      { to: '/admin/runs/run-a/diagnostics', label: 'Diagnostics' },
      { to: '/admin/runs/run-a/world-generation', label: 'World Generation' },
      { to: '/admin/runs/run-a/finals', label: 'World Tour Finals' },
      { to: '/admin/runs/run-a/rollover', label: 'Season Rollover' },
      { to: '/admin/runs/run-a/bootstrap-lineage', label: 'Bootstrap / Lineage' },
      { to: '/admin/runs/run-a/season-chain', label: 'Season Chain' },
      { to: '/admin/runs/run-a/snapshots/ranking', label: 'Ranking Snapshots' },
      { to: '/admin/runs/run-a/snapshots/race', label: 'Race Snapshots' }
    ])
  })
})

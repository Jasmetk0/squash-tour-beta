import { describe, expect, it } from 'vitest'
import { supportsHistoricalAdminTime } from './historicalAdminTimeRoutes'

describe('supportsHistoricalAdminTime', () => {
  it('supports Home, Simulation, and only the typed historical Calendar routes', () => {
    expect(supportsHistoricalAdminTime('/admin/runs/run-a', 'run-a')).toBe(true)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/simulate', 'run-a')).toBe(true)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/calendar', 'run-a')).toBe(true)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/weeks/12', 'run-a')).toBe(true)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/calendar/event%2Fone', 'run-a')).toBe(true)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/events', 'run-a')).toBe(false)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/events/event-1', 'run-a')).toBe(false)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/calendar/event-1/extra', 'run-a')).toBe(false)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/players', 'run-a')).toBe(false)
  })
})

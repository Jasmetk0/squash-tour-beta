import { describe, expect, it } from 'vitest'
import { supportsHistoricalAdminTime } from './historicalAdminTimeRoutes'

describe('supportsHistoricalAdminTime', () => {
  it('supports only Run Home and Simulation', () => {
    expect(supportsHistoricalAdminTime('/admin/runs/run-a', 'run-a')).toBe(true)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/simulate', 'run-a')).toBe(true)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/events', 'run-a')).toBe(false)
    expect(supportsHistoricalAdminTime('/admin/runs/run-a/players', 'run-a')).toBe(false)
  })
})

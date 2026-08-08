import { describe, expect, it } from 'vitest'

import { adminRunSwitchTarget } from './adminRunSwitchTarget'

describe('adminRunSwitchTarget', () => {
  it.each(['', '/simulate', '/branches', '/events', '/calendar', '/finals'])('preserves the generic %s suffix', suffix => {
    expect(adminRunSwitchTarget(`/admin/runs/run-a${suffix}`, 'run-b')).toBe(`/admin/runs/run-b${suffix}`)
  })

  it.each([
    '/events/E123',
    '/calendar/E123',
    '/players/P123/career',
    '/snapshots/ranking/42',
    '/rollover/2030',
    '/weeks/12',
  ])('falls back to Run Home for object-specific route %s', suffix => {
    expect(adminRunSwitchTarget(`/admin/runs/run-a${suffix}`, 'run-b')).toBe('/admin/runs/run-b')
  })

  it('encodes the destination Run id', () => {
    expect(adminRunSwitchTarget('/admin/runs/run-a/branches', 'run b')).toBe('/admin/runs/run%20b/branches')
  })
})

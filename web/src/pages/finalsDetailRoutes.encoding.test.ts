import { describe, expect, it } from 'vitest'

import { getFinalsInspectionRoute } from './finalsDetailRoutes'

describe('Finals inspection links preserve exact Run ID', () => {
  it.each([
    { hasQualification: false, hasResult: false, suffix: '' },
    { hasQualification: true, hasResult: false, suffix: '/qualification' },
    { hasQualification: true, hasResult: true, suffix: '/result' }
  ])('encodes a Run with reserved characters for $suffix', ({ hasQualification, hasResult, suffix }) => {
    expect(getFinalsInspectionRoute({ runId: 'run x/y?#', hasQualification, hasResult }))
      .toBe(`/runs/run%20x%2Fy%3F%23/finals${suffix}`)
  })

  it('leaves ordinary Run routes unchanged', () => {
    expect(getFinalsInspectionRoute({ runId: 'run-a', hasQualification: true, hasResult: false }))
      .toBe('/runs/run-a/finals/qualification')
  })
})

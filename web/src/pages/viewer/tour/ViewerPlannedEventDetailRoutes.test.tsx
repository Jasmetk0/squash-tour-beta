import { describe, expect, it } from 'vitest'

import appSource from '../../../App.tsx?raw'
import viewerRoutesSource from '../../../viewer/viewerRoutes.ts?raw'

describe('Viewer planned event detail route wiring', () => {
  it('keeps run-scoped planned calendar event route and params unchanged', () => {
    expect(appSource).toContain('<Route path="viewer/runs/:runId" element={<ViewerProductRunRouteBoundary />}>')
    expect(appSource).toContain('<Route path="calendar" element={<ViewerRunCalendarPage />} />')
    expect(appSource).toContain('<Route path="calendar/:eventId" element={<ViewerRunPlannedEventPage />} />')
    expect(appSource.indexOf('path="calendar"')).toBeLessThan(
      appSource.indexOf('path="calendar/:eventId"')
    )
  })

  it('keeps planned event route helper encoded and stable', () => {
    expect(viewerRoutesSource).toContain('export function viewerPlannedEventPath(productRunId: ViewerPathSegment, eventId: ViewerPathSegment): string')
    expect(viewerRoutesSource).toContain('return `/viewer/runs/${encodePathSegment(productRunId)}/calendar/${encodePathSegment(eventId)}`')
  })
})

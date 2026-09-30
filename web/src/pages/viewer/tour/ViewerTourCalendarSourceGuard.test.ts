import source from './ViewerTourCalendarPage.tsx?raw'

import { describe, expect, it } from 'vitest'

describe('ViewerTourCalendarPage canonical source guard', () => {
  it('uses Saved Calendar authority instead of legacy run metadata', () => {
    expect(source).toContain('getViewerRunCalendar')
    expect(source).toContain('useActiveViewerProductRunId')
    expect(source).not.toContain('getRun(')
    expect(source).not.toContain('useActiveViewerRunId')
  })
})

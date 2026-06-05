import { describe, expect, it } from 'vitest'

import {
  AdminHomePage,
  LandingPage,
  ViewerHomePage,
  ViewerPlannedEventReadOnlyPage,
  ViewerRankingDeferredPage,
  ViewerRunBrowserPage,
  ViewerStatsDeferredPage,
} from './ModePages'

describe('ModePages compatibility exports', () => {
  it('keeps key route imports available as function exports', () => {
    expect(LandingPage).toEqual(expect.any(Function))
    expect(AdminHomePage).toEqual(expect.any(Function))
    expect(ViewerHomePage).toEqual(expect.any(Function))
    expect(ViewerRunBrowserPage).toEqual(expect.any(Function))
    expect(ViewerRankingDeferredPage).toEqual(expect.any(Function))
    expect(ViewerStatsDeferredPage).toEqual(expect.any(Function))
    expect(ViewerPlannedEventReadOnlyPage).toEqual(expect.any(Function))
  })
})

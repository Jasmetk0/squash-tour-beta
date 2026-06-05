import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
} from '../../../test/viewerTestUtils'
import { ViewerPredictionDeferredPage } from './ViewerPredictionDeferredPage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

function renderPredictionDeferredPage(): void {
  renderWithViewerProviders(<ViewerPredictionDeferredPage kind="match-odds" />)
}

describe('ViewerPredictionDeferredPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders the existing no-active-run empty state without forbidden Viewer actions', () => {
    renderPredictionDeferredPage()

    expect(
      screen.getByRole('heading', { level: 2, name: 'Match Odds' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('No data is available for this run yet.'),
    ).toBeInTheDocument()
    expect(api.getRunStatusSummary).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(api.getFinalsSummary).not.toHaveBeenCalled()

    expectNoForbiddenViewerActions()
  })
})

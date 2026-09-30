import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
} from '../../../test/viewerTestUtils'
import { ViewerPredictionDeferredPage } from './ViewerPredictionDeferredPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
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
      screen.getByText('No Product Run is selected yet.'),
    ).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()

    expectNoForbiddenViewerActions()
  })
})

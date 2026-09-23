import { Route, Routes } from 'react-router-dom'
import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerRankingSnapshotDetailPage } from './ViewerRankingSnapshotDetailPage'

const api = vi.hoisted(() => ({
  getViewerOfficialRankingHistoryDetail: vi.fn()
}))

vi.mock('../../../api/client', () => api)
function renderDetail(route = '/viewer/runs/run%20alpha/rankings/1'): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/rankings/:snapshotSequence" element={<ViewerRankingSnapshotDetailPage />} />
    </Routes>,
    { route }
  )
}

describe('ViewerRankingSnapshotDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue({
      schema_version: 'viewer_official_ranking.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      season_index: 0,
      week: 2,
      week_ordinal: 1,
      snapshot_fingerprint: 'a'.repeat(64),
      policy_id: 'best-15',
      best_n: 15,
      row_count: 2,
      rows: [
        { rank: 1, player_id: 'player-a', points: 1200 },
        { rank: 2, player_id: 'player-b', points: 900 }
      ]
    })
  })

  it('renders canonical historical publication rows and Viewer-safe navigation', async () => {
    renderDetail()

    expect(await screen.findByText('player-a')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledWith('run alpha', 1)
    expect(screen.getByRole('heading', { level: 2, name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText(/Policy/)).toHaveTextContent('best-15')
    expect(screen.getByRole('table', { name: 'Historical Official Ranking table' })).toHaveTextContent('1200')
    expect(screen.getByRole('link', { name: 'Back to ranking history' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expectNoForbiddenViewerActions()
  })

  it('rejects invalid publication identities without an API call', () => {
    renderDetail('/viewer/runs/run%20alpha/rankings/not-an-ordinal')

    expect(screen.getByText('Invalid ranking publication identity.')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows fail-closed API errors without legacy payload fallback', async () => {
    api.getViewerOfficialRankingHistoryDetail.mockRejectedValue(new Error('future publication'))

    renderDetail()

    expect(await screen.findByText(/future publication/)).toBeInTheDocument()
    expect(screen.queryByText('Show technical payload')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

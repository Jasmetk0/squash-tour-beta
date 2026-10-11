import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerOfficialRankingHistoryPage } from './ViewerOfficialRankingHistoryPage'

const api = vi.hoisted(() => ({
  listViewerOfficialRankingHistory: vi.fn()
}))

vi.mock('../../../api/client', () => api)
vi.mock('../../../viewer/ViewerProductRunRouteContext', () => ({
  useViewerProductRunRouteContext: () => ({ productRunId: 'run alpha' })
}))

describe('ViewerOfficialRankingHistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listViewerOfficialRankingHistory.mockResolvedValue({
      schema_version: 'viewer_official_ranking_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      public_head_ordinal: 1,
      publication_count: 2,
      publications: [
        { season_index: 0, week: 2, week_ordinal: 1, snapshot_fingerprint: 'b'.repeat(64), policy_id: 'best-15', best_n: 15, row_count: 2 },
        { season_index: 0, week: 1, week_ordinal: 0, snapshot_fingerprint: 'a'.repeat(64), policy_id: 'best-15', best_n: 15, row_count: 2 }
      ]
    })
  })

  it('renders canonical publication history newest first', async () => {
    renderWithViewerProviders(<ViewerOfficialRankingHistoryPage />)

    expect(await screen.findByRole('table', { name: 'Official Ranking publication history' })).toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('run alpha')
    expect(screen.getByRole('link', { name: 'Open Week 2 ranking' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/1')
    expect(screen.getByRole('link', { name: 'Open Week 1 ranking' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/0')
    expectNoForbiddenViewerActions()
  })
})

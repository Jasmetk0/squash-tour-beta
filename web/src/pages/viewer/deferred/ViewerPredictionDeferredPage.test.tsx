import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerPredictionDeferredPage } from './ViewerPredictionDeferredPage'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

const forbiddenViewerActionLabels = [
  'Simulate',
  'Generate',
  'Persist',
  'Apply',
  'Execute',
  'Delete',
  'Edit',
  'Import',
  'Rollover',
  'Rebuild',
  'Override',
  'Save changes',
  'Commit',
  'Regenerate',
  'Repair',
  'Merge',
  'Overwrite',
]

function renderPredictionDeferredPage(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerPredictionDeferredPage kind="match-odds" />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ViewerPredictionDeferredPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders the existing no-active-run empty state without forbidden Viewer actions', () => {
    renderPredictionDeferredPage()

    expect(screen.getByRole('heading', { level: 2, name: 'Match Odds' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(api.getRunStatusSummary).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(api.getFinalsSummary).not.toHaveBeenCalled()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })
})

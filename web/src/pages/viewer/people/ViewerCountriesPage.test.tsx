import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../../../viewer/activeRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerCountriesPage } from './ViewerCountriesPage'

const api = vi.hoisted(() => ({
  listRunNations: vi.fn()
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
  'Overwrite'
]

function renderCountriesPage(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <ViewerCountriesPage />
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ViewerCountriesPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRunNations.mockResolvedValue({
      run_id: 'run alpha',
      total: 1,
      limit: 5,
      offset: 0,
      nations: [
        {
          country_code: 'NZ',
          country_name: 'New Zealand',
          total_players: 8,
          average_overall: 78.5,
          top_player_id: 'paul coll',
          top_player_name: 'Paul Coll',
          top_player_overall: 93
        }
      ]
    })
  })

  it('shows the existing empty state when no active run is selected', () => {
    renderCountriesPage()

    expect(screen.getByRole('heading', { level: 2, name: 'Countries' })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(api.listRunNations).not.toHaveBeenCalled()

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })

  it('renders active-run country metadata and encoded source/profile links', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'run alpha')

    renderCountriesPage()

    expect(await screen.findByText('Countries summary')).toBeInTheDocument()
    expect(await screen.findByText('New Zealand')).toBeInTheDocument()
    expect(screen.getByText('Total country count')).toBeInTheDocument()
    expect(screen.getByText('Returned country count')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'NZ' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/NZ')
    expect(screen.getByRole('link', { name: 'New Zealand' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/NZ')
    expect(screen.getByRole('link', { name: 'Paul Coll' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/paul%20coll/career')
    expect(screen.getByRole('link', { name: 'Open active run countries' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/countries')
  })
})

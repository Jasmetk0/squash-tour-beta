import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveProductRunId } from '../../../test/viewerTestUtils'
import { ViewerCountriesPage } from './ViewerCountriesPage'

const api = vi.hoisted(() => ({
  getViewerCountries: vi.fn()
}))

vi.mock('../../../api/client', () => api)

function renderCountriesPage(): void {
  renderWithViewerProviders(<ViewerCountriesPage />)
}

describe('ViewerCountriesPage canonical people', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.getViewerCountries.mockResolvedValue({
      schema_version: 'viewer_countries.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-a',
      season_index: 3,
      week: 8,
      country_count: 1,
      countries: [{
        country_code: 'NZL',
        player_count: 8,
        active_player_count: 7,
        retired_player_count: 1,
        average_current_ovr: 157.5,
        top_player_id: 'paul coll',
        top_player_name: 'Paul Coll',
        top_player_current_ovr: 193
      }]
    })
  })

  it('shows Product Run empty state when nothing is selected', () => {
    renderCountriesPage()

    expect(screen.getByRole('heading', { level: 2, name: 'Countries' })).toBeInTheDocument()
    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()
    expect(api.getViewerCountries).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders canonical country metadata and encoded profile links', async () => {
    setViewerActiveProductRunId('run alpha')
    renderCountriesPage()

    expect(await screen.findByText('Countries summary')).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledWith('run alpha')
    expect(await screen.findByRole('link', { name: 'NZL' })).toBeInTheDocument()
    expect(screen.getByText('Active players')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'NZL' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/NZL')
    expect(screen.getByRole('link', { name: 'Paul Coll' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/paul%20coll/career')
    expect(screen.getByRole('link', { name: 'Open Product Run countries' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/countries')
    expectNoForbiddenViewerActions()
  })
})

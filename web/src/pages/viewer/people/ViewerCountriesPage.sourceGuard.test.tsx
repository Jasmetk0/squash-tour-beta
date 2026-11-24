import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerCountriesPage } from './ViewerCountriesPage'

const api = vi.hoisted(() => ({ getViewerCountries: vi.fn() }))
const source = vi.hoisted(() => ({
  run: 'run alpha', branch: 'branch-a', foreignContext: false
}))
vi.mock('../../../api/client', () => ({ ...api, ApiError: class ApiError extends Error {} }))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => source.run
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: { product_run_id: source.foreignContext ? 'foreign' : run, official_branch_id: source.branch },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn()
  })
}))
function payload(branch = source.branch, run = source.run) {
  return {
    schema_version: 'viewer_countries.v1', product_run_id: run,
    viewer_branch_id: branch, season_index: 4, week: 2,
    country_count: 2, countries: [
      {
        country_code: 'NZL', player_count: 2,
        active_player_count: 1, retired_player_count: 1,
        average_current_ovr: 158.5, top_player_id: 'paul coll',
        top_player_name: 'Paul Coll', top_player_current_ovr: 193
      },
      {
        country_code: 'CZE', player_count: 0,
        active_player_count: 0, retired_player_count: 0,
        average_current_ovr: null, top_player_id: null,
        top_player_name: null, top_player_current_ovr: null
      }
    ]
  }
}
function mount() {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ViewerContextProvider><ViewerCountriesPage /></ViewerContextProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('Viewer Country Hub fail-closed public Saved source (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    source.run = 'run alpha'
    source.branch = 'branch-a'
    source.foreignContext = false
    api.getViewerCountries.mockReset().mockResolvedValue(payload())
  })

  it('does not issue the country GET when the context belongs to a foreign Run', () => {
    source.foreignContext = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('could not be verified')
    expect(api.getViewerCountries).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('displays validated public country identities and canonical profile links', async () => {
    mount()
    expect(await screen.findByText('Countries summary')).toBeInTheDocument()
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'NZL' })[0])
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/NZL')
    expect(screen.getByRole('link', { name: 'Paul Coll' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/paul%20coll/career')
    expect(api.getViewerCountries).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('rejects foreign Branch, inconsistent count and unexpected private fields; explicit GET retry can recover', async () => {
    const bad = payload()
    api.getViewerCountries
      .mockReset()
      .mockResolvedValueOnce(payload('foreign-branch'))
      .mockResolvedValueOnce({ ...bad, country_count: 3 })
      .mockResolvedValueOnce({
        ...bad, countries: [{ ...bad.countries[0], private_value: 999 }, bad.countries[1]]
      })
      .mockResolvedValueOnce(payload())
    const user = userEvent.setup()
    mount()
    for (let i = 0; i < 3; i++) {
      expect(await screen.findByRole('alert')).toHaveTextContent('invalid public data')
      expect(screen.queryByText('Paul Coll')).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Retry country read (GET)' }))
    }
    expect(await screen.findByText('Countries summary')).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(4)
    expectNoForbiddenViewerActions()
  })

  it('does not show a delayed foreign-Branch reply after switching the saved Viewer Branch', async () => {
    let resolveOld: ((value: ReturnType<typeof payload>) => void) | undefined
    api.getViewerCountries.mockReset()
      .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce(payload('branch-b'))
    const view = mount()
    await waitFor(() => expect(api.getViewerCountries).toHaveBeenCalledTimes(1))
    source.branch = 'branch-b'
    await act(async () => view.refresh())
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(payload('branch-a')) })
    expect(screen.getByText('branch-b')).toBeInTheDocument()
    expect(screen.queryByText('branch-a')).not.toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(2)
  })

  it('does not manufacture a sample row from an empty but valid Saved country list', async () => {
    api.getViewerCountries.mockResolvedValueOnce({
      ...payload(), country_count: 0, countries: []
    })
    mount()
    expect(await screen.findByText('No canonical countries are available for this Product Run yet.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'NZL' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it.each([
    { average_current_ovr: 200, top_player_current_ovr: 150 },
    { top_player_id: null, top_player_name: null },
    { average_current_ovr: null },
    { top_player_current_ovr: null },
    { top_player_current_ovr: 199.5 },
  ])('rejects contradictory public OVR summary: %j', async patch => {
    const bad = payload()
    api.getViewerCountries.mockReset().mockResolvedValue({
      ...bad, countries: [{ ...bad.countries[0], ...patch }, ...bad.countries.slice(1)],
    })
    mount()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

})

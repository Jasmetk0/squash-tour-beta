import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerRacePage, ViewerRunRacePage } from './ViewerRacePage'

const api = vi.hoisted(() => ({ getViewerFinalsRace: vi.fn() }))
const source = vi.hoisted(() => ({ run: 'run alpha', branch: 'viewer-a' }))
vi.mock('../../../api/client', () => ({
  ...api, ApiError: class ApiError extends Error {}
}))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => source.run
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: { product_run_id: run, official_branch_id: source.branch },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn()
  })
}))
vi.mock('../../../viewer/ViewerProductRunRouteContext', () => ({
  useViewerProductRunRouteContext: () => ({
    productRunId: source.run, officialBranchId: source.branch,
    officialContext: { product_run_id: source.run, official_branch_id: source.branch },
    isLoading: false, isStale: false, refetch: vi.fn()
  })
}))

function publication(season: number, count: number, run = source.run, branch = source.branch) {
  return {
    schema_version: 'viewer_finals_race_publication.v1',
    product_run_id: run, viewer_branch_id: branch,
    target_season_index: season, cutoff_season_index: season, cutoff_week: 55,
    best_n: 10, selection_published: false, finals_event_id: null,
    rows: Array.from({ length: count }, (_, index) => ({
      rank: index + 1, player_id: 'player-' + season + '-' + index,
      race_points: 0, tournaments_counted: 0, counted_results: [],
      finals_selected: null, finals_seed: null, qualification_source: null
    }))
  }
}
function history(run = source.run, branch = source.branch) {
  const publications = [
    publication(0, 0, run, branch),
    publication(3, 1, run, branch),
    publication(4, 2, run, branch)
  ]
  return {
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: run, viewer_branch_id: branch,
    latest_target_season_index: 4, publications
  }
}
function Navigation(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  return <>
    <output aria-label="Current URL">{location.pathname}{location.search}</output>
    <button type="button" onClick={() => navigate(-1)}>Back</button>
    <button type="button" onClick={() => navigate(1)}>Forward</button>
  </>
}
function mount(url = '/viewer/runs/run%20alpha/race?keep=one&keep=two', mode: 'top' | 'run' = 'run') {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[url]}>
          <LanguageProvider>
            <Navigation />
            {mode === 'run' ? <ViewerRunRacePage /> : <ViewerRacePage />}
          </LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, client, refresh: () => view.rerender(<App />) }
}
function params(): URLSearchParams {
  const url = screen.getByLabelText('Current URL').textContent ?? ''
  return new URLSearchParams(url.split('?')[1] ?? '')
}

describe('Viewer Race exact-season deep links (mocked GET, not HTTP/SQLite)', () => {
  beforeEach(() => {
    localStorage.clear()
    source.run = 'run alpha'
    source.branch = 'viewer-a'
    api.getViewerFinalsRace.mockReset()
    api.getViewerFinalsRace.mockImplementation((run: string) => Promise.resolve(history(run, source.branch)))
  })

  it('opens the exact older publication from a direct URL on both route variants', async () => {
    for (const mode of ['top', 'run'] as const) {
      const view = mount('/viewer/runs/run%20alpha/race?raceSeason=3&keep=one&keep=two', mode)
      expect(await screen.findByRole('heading', { name: 'Zvolená publikace: 2003/04' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'player-3-0' })).toBeInTheDocument()
      expect(screen.queryByText('player-4-0')).not.toBeInTheDocument()
      expect(params().getAll('keep')).toEqual(['one', 'two'])
      expectNoForbiddenViewerActions()
      view.unmount()
    }
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(2)
  })

  it('navigates seasons through URL and restores Back/Forward without fetching a new snapshot', async () => {
    const user = userEvent.setup()
    mount('/viewer/runs/run%20alpha/race?keep=yes&raceSeason=3')
    expect(await screen.findByRole('heading', { name: 'Zvolená publikace: 2003/04' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Cílová sezona'), '4')
    expect(params().get('raceSeason')).toBe('4')
    expect(screen.getByRole('heading', { name: 'Zvolená publikace: 2004/05' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(params().get('raceSeason')).toBe('3')
    expect(screen.getByRole('heading', { name: 'Zvolená publikace: 2003/04' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByRole('heading', { name: 'Zvolená publikace: 2004/05' })).toBeInTheDocument()
    expect(params().get('keep')).toBe('yes')
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(1)
  })

  it('rejects malformed and missing seasons instead of silently selecting the newest', async () => {
    const user = userEvent.setup()
    mount('/viewer/runs/run%20alpha/race?keep=yes&raceSeason=3abc')
    expect(await screen.findByRole('alert')).toHaveTextContent('Požadovaná publikace Race neexistuje')
    expect(screen.queryByRole('heading', { name: /Zvolená publikace/ })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Cílová sezona')).toHaveValue('3abc')
    await user.selectOptions(screen.getByLabelText('Cílová sezona'), '3')
    expect(screen.getByRole('heading', { name: 'Zvolená publikace: 2003/04' })).toBeInTheDocument()
    expect(params().get('keep')).toBe('yes')
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(1)
  })

  it.each(['raceSeason=3&raceSeason=4', 'raceSeason=3&raceSeason=3'])(
    'rejects ambiguous duplicated season parameters and permits explicit recovery: %s', async search => {
      const user = userEvent.setup()
      mount('/viewer/runs/run%20alpha/race?' + search + '&keep=yes')
      expect(await screen.findByRole('alert')).toHaveTextContent('Požadovaná publikace Race neexistuje')
      expect(screen.queryByRole('heading', { name: /Zvolená publikace/ })).not.toBeInTheDocument()
      expect(screen.getByLabelText('Cílová sezona')).toHaveValue('')
      await user.selectOptions(screen.getByLabelText('Cílová sezona'), '3')
      expect(await screen.findByRole('heading', { name: 'Zvolená publikace: 2003/04' })).toBeInTheDocument()
      expect(params().getAll('raceSeason')).toEqual(['3'])
      expect(params().get('keep')).toBe('yes')
    }
  )

  it('withholds the previously displayed standings during an in-flight refetch', async () => {
    const view = mount('/viewer/runs/run%20alpha/race?raceSeason=3')
    expect(await screen.findByRole('link', { name: 'player-3-0' })).toBeInTheDocument()
    let release!: (value: ReturnType<typeof history>) => void
    api.getViewerFinalsRace.mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
    const refresh = view.client.invalidateQueries({ queryKey: ['viewer-canonical-finals-race', source.run, source.branch] })
    await waitFor(() => expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByRole('link', { name: 'player-3-0' })).not.toBeInTheDocument())
    expect(screen.getByText('Načítám publikované Race…')).toBeInTheDocument()
    await act(async () => { release(history()); await refresh })
    expect(await screen.findByRole('link', { name: 'player-3-0' })).toBeInTheDocument()
  })

  it('distinguishes a real zero-row season 0 publication from an unavailable season', async () => {
    const first = mount('/viewer/runs/run%20alpha/race?raceSeason=0')
    expect(await screen.findByRole('heading', { name: 'Zvolená publikace: 2000/01' })).toBeInTheDocument()
    expect(screen.getByText('Tato publikace obsahuje nula hráčů.')).toBeInTheDocument()
    first.unmount()
    mount('/viewer/runs/run%20alpha/race?raceSeason=99')
    expect(await screen.findByRole('alert')).toHaveTextContent('neexistuje')
    expect(screen.queryByText('Tato publikace obsahuje nula hráčů.')).not.toBeInTheDocument()
  })

  it('resets only the old season URL on a Run/Viewer Branch switch', async () => {
    const view = mount('/viewer/runs/run%20alpha/race?keep=two&raceSeason=3')
    expect(await screen.findByRole('heading', { name: 'Zvolená publikace: 2003/04' })).toBeInTheDocument()
    source.branch = 'viewer-b'
    await act(async () => view.refresh())
    expect(await screen.findByRole('heading', { name: 'Zvolená publikace: 2004/05' })).toBeInTheDocument()
    await waitFor(() => expect(params().get('raceSeason')).toBe(null))
    expect(params().get('keep')).toBe('two')
    expect(screen.getByText('viewer-b')).toBeInTheDocument()

    source.run = 'run beta'
    await act(async () => view.refresh())
    expect(await screen.findByRole('link', { name: 'player-4-0' })).toBeInTheDocument()
    expect(params().get('raceSeason')).toBe(null)
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(3)
    expectNoForbiddenViewerActions()
  })
})

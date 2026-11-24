import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerPlayersPage } from './ViewerPlayersPage'

const api = vi.hoisted(() => ({ getViewerPlayers: vi.fn() }))
const selected = vi.hoisted(() => ({ run: 'run alpha', branch: 'branch-a' }))
vi.mock('../../../api/client', () => ({ ...api, ApiError: class ApiError extends Error {} }))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => selected.run
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: { product_run_id: run, official_branch_id: selected.branch },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn()
  })
}))

function player(n: number, status: 'active' | 'retired', country: string) {
  return {
    player_id: 'p-' + n, name: 'Player ' + n, country_code: country,
    age: 20 + n, status, identity_source: n % 2 ? 'run_prospect' : 'initial_world',
    tour_entry_season_index: null, tour_entry_week: null,
    current_ovr: n * 10, potential_ovr: null, current_form: null,
    match_sharpness: null, long_term_fatigue: null
  }
}
const players = [
  player(1, 'active', 'CZE'), player(2, 'retired', 'NZL'),
  player(3, 'active', 'NZL'), player(4, 'active', 'CZE')
]
function roster(run = selected.run, branch = selected.branch) {
  return {
    schema_version: 'viewer_players.v1', product_run_id: run,
    viewer_branch_id: branch, season_index: 2, week: 6,
    player_count: players.length,
    active_player_count: players.filter(p => p.status === 'active').length,
    retired_player_count: players.filter(p => p.status === 'retired').length,
    players
  }
}
function LocationControls(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  return <>
    <output aria-label="Current URL">{location.pathname}{location.search}</output>
    <button type="button" onClick={() => navigate(-1)}>Back</button>
    <button type="button" onClick={() => navigate(1)}>Forward</button>
  </>
}
function mount(url = '/viewer/players?keep=one&keep=two') {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[url]}>
          <LanguageProvider><LocationControls /><ViewerPlayersPage /></LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}
function params(): URLSearchParams {
  const text = screen.getByLabelText('Current URL').textContent ?? ''
  return new URLSearchParams(text.split('?')[1] ?? '')
}

describe('Viewer player directory URL filters (mocked Saved GET, not real HTTP/SQLite)', () => {
  beforeEach(() => {
    localStorage.clear()
    selected.run = 'run alpha'
    selected.branch = 'branch-a'
    api.getViewerPlayers.mockReset().mockImplementation((run: string) => Promise.resolve(roster(run)))
  })

  it('shares all five filters as a direct link, preserving exact player and country paths', async () => {
    mount('/viewer/players?keep=one&keep=two&vpStatus=active&vpOrigin=run_prospect&vpCountry=NZL&vpSort=age&vpQ=Player')
    const table = await screen.findByRole('table', { name: 'Uložený seznam hráčů' })
    expect(screen.getByLabelText('Kariéra')).toHaveValue('active')
    expect(screen.getByLabelText('Původ hráče')).toHaveValue('run_prospect')
    expect(screen.getByLabelText('Země')).toHaveValue('NZL')
    expect(screen.getByLabelText('Řazení')).toHaveValue('age')
    expect(screen.getByLabelText('Hledat jméno, ID nebo zemi')).toHaveValue('Player')
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByRole('link', { name: 'Player 3' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/p-3/career')
    expect(within(table).getByRole('link', { name: 'NZL' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/NZL')
    expect(params().getAll('keep')).toEqual(['one', 'two'])
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('restores Back/Forward without turning each typed letter into a separate history entry', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Kariéra'), 'active')
    await user.type(screen.getByLabelText('Hledat jméno, ID nebo zemi'), 'Player 3')
    expect(params().get('vpStatus')).toBe('active')
    expect(params().get('vpQ')).toBe('Player 3')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(params().get('vpStatus')).toBe(null)
    expect(params().get('vpQ')).toBe(null)
    expect(screen.getByLabelText('Kariéra')).toHaveValue('all')
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByLabelText('Kariéra')).toHaveValue('active')
    expect(screen.getByLabelText('Hledat jméno, ID nebo zemi')).toHaveValue('Player 3')
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect([...params().keys()]).toEqual(['keep', 'keep'])
    expect(screen.getByText('Zobrazeno 1–4 z 4')).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
  })

  it('fails closed on unknown status, origin, country and sort rather than showing All', async () => {
    const user = userEvent.setup()
    mount('/viewer/players?tracking=yes&vpStatus=undefined&vpOrigin=future&vpCountry=XXX&vpSort=unknown')
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatný nebo nedostupný filtr')
    expect(screen.getByLabelText('Kariéra')).toHaveValue('undefined')
    expect(screen.getByLabelText('Původ hráče')).toHaveValue('future')
    expect(screen.getByLabelText('Země')).toHaveValue('XXX')
    expect(screen.getByLabelText('Řazení')).toHaveValue('unknown')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(params().toString()).toBe('tracking=yes')
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('removes stale owned filters when the selected Viewer Branch or Product Run changes', async () => {
    const view = mount('/viewer/players?track=yes&vpCountry=NZL&vpSort=age')
    expect(await screen.findByRole('table')).toBeInTheDocument()
    selected.branch = 'branch-b'
    await act(async () => view.refresh())
    await waitFor(() => expect(screen.getByText('branch-b')).toBeInTheDocument())
    await waitFor(() => expect(params().get('vpCountry')).toBe(null))
    expect(params().get('vpSort')).toBe(null)
    expect(params().get('track')).toBe('yes')
    expect(screen.getByText('Zobrazeno 1–4 z 4')).toBeInTheDocument()

    selected.run = 'run beta'
    await act(async () => view.refresh())
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.getByText('run beta')).toBeInTheDocument()
    expect(params().get('track')).toBe('yes')
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(3)
    expectNoForbiddenViewerActions()
  })

  it('recreates an unchanged shareable link after remount, retaining public-only data', async () => {
    const url = '/viewer/players?vpStatus=retired&vpCountry=NZL&vpSort=public_ovr'
    const first = mount(url)
    expect(await screen.findByRole('link', { name: 'Player 2' })).toBeInTheDocument()
    first.unmount()
    mount(url)
    expect(await screen.findByRole('link', { name: 'Player 2' })).toBeInTheDocument()
    expect(screen.getByLabelText('Řazení')).toHaveValue('public_ovr')
    expectNoForbiddenViewerActions()
  })

  it('shares an exact page of a large roster and restores it with Back/Forward', async () => {
    const rows = Array.from({ length: 101 }, (_, i) => ({
      ...player(i + 1, 'active', 'CZE'), name: 'Player ' + String(i + 1).padStart(3, '0'),
      age: 25 + i % 20, current_ovr: 50 + i % 100
    }))
    api.getViewerPlayers.mockResolvedValue({ ...roster(), player_count: rows.length, active_player_count: rows.length, retired_player_count: 0, players: rows })
    const user = userEvent.setup()
    mount('/viewer/players?vpPage=2&keep=yes')
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    expect(within(table).getByRole('link', { name: 'Player 051' })).toBeInTheDocument()
    expect(within(table).queryByRole('link', { name: 'Player 001' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(params().get('vpPage')).toBe('3')
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(params().get('vpPage')).toBe('2')
    expect(within(table).getByRole('link', { name: 'Player 051' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(params().get('vpPage')).toBe('3')
    await user.selectOptions(screen.getByLabelText('Kariéra'), 'active')
    expect(params().get('vpPage')).toBeNull()
    expect(params().get('keep')).toBe('yes')
    expect(within(table).getByRole('link', { name: 'Player 001' })).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
  })

  it.each(['vpPage=2', 'vpPage=01', 'vpPage=1&vpPage=1', 'vpPage=-1'])(
    'rejects invalid, noncanonical or ambiguous page links: %s', async page => {
      mount('/viewer/players?' + page + '&keep=yes')
      expect(await screen.findByRole('alert')).toHaveTextContent('neplatný nebo nedostupný filtr či stránku')
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      await userEvent.setup().click(screen.getByRole('button', { name: 'Vymazat filtry' }))
      expect(await screen.findByRole('table')).toBeInTheDocument()
      expect(params().toString()).toBe('keep=yes')
    }
  )

  it('rejects duplicate owned filters without discarding unrelated URL parameters', async () => {
    mount('/viewer/players?vpStatus=active&vpStatus=retired&keep=one&keep=two')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(params().getAll('keep')).toEqual(['one', 'two'])
    expect([...params().keys()]).toEqual(['keep', 'keep'])
  })

})

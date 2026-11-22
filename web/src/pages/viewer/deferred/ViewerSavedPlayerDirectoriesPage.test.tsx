import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ViewerPlayer, ViewerPlayers } from '../../../api/types'
import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerPlayersDeferredPage } from './ViewerPlayersDeferredPage'
import type { ViewerPlayersDeferredKind } from './viewerDeferredConfigs'

const api = vi.hoisted(() => ({ getViewerPlayers: vi.fn() }))
const context = vi.hoisted(() => ({
  run: 'run alpha' as string | null,
  branch: 'branch-a', foreign: false,
  kind: 'all' as ViewerPlayersDeferredKind,
}))
vi.mock('../../../api/client', () => ({
  ...api, ApiError: class ApiError extends Error {},
}))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => context.run,
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: {
      product_run_id: context.foreign ? 'other-run' : run,
      official_branch_id: context.branch,
    },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

function player(n: number, status: 'active' | 'retired' = 'active',
  code = 'CZE', ovr: number | null = 125): ViewerPlayer {
  return {
    player_id: 'player ' + String(n).padStart(3, '0'),
    name: 'Player ' + String(n).padStart(3, '0'),
    country_code: code, age: 18 + n % 30, status,
    identity_source: n % 2 ? 'run_prospect' : 'initial_world',
    tour_entry_season_index: null, tour_entry_week: null,
    current_ovr: ovr, potential_ovr: null,
    current_form: null, match_sharpness: null, long_term_fatigue: null,
  }
}
const sample = [
  player(1, 'active', 'CZE', 178),
  player(2, 'retired', 'NZL', null),
  player(3, 'active', 'NZL', 151),
  player(4, 'retired', 'CZE', 102),
]
function payload(
  players: ViewerPlayer[] = sample,
  run = context.run ?? '', branch = context.branch,
): ViewerPlayers {
  return {
    schema_version: 'viewer_players.v1',
    product_run_id: run, viewer_branch_id: branch,
    season_index: 6, week: 21, player_count: players.length,
    active_player_count: players.filter(p => p.status === 'active').length,
    retired_player_count: players.filter(p => p.status === 'retired').length,
    players,
  }
}
function LanguageToggle(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>
    Switch language
  </button>
}
function mount(kind: ViewerPlayersDeferredKind = 'all') {
  context.kind = kind
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return <QueryClientProvider client={client}>
      <MemoryRouter><LanguageProvider>
        <LanguageToggle />
        <ViewerPlayersDeferredPage kind={context.kind} />
      </LanguageProvider></MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('All / Active / Retired Player pages from verified public Saved GET', () => {
  beforeEach(() => {
    localStorage.clear()
    context.run = 'run alpha'; context.branch = 'branch-a'
    context.foreign = false; context.kind = 'all'
    api.getViewerPlayers.mockReset().mockImplementation((run: string) =>
      Promise.resolve(payload(sample, run, context.branch)))
  })

  it('never calls public or private player GETs without a selected Product Run', () => {
    context.run = null
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Seznam Runů' }))
      .toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerPlayers).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('rejects a foreign Viewer Branch context before GET', () => {
    context.foreign = true
    mount('retired')
    expect(screen.getByRole('alert')).toHaveTextContent('neodpovídá vybranému Runu')
    expect(api.getViewerPlayers).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows the entire all-player Saved roster with correct public metrics and canonical links', async () => {
    mount()
    const table = await screen.findByRole('table', { name: 'Veřejný seznam všech hráčů' })
    expect(within(table).getAllByRole('row')).toHaveLength(5)
    expect(within(table).getByRole('link', { name: 'Player 001' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player%20001/career')
    expect(within(table).getAllByRole('link', { name: 'CZE' })[0])
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/CZE')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText('6 · W21')).toBeInTheDocument()
    expect(screen.getByText(/nikoli libovolnému týdnu vybranému/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Všichni' }))
      .toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Aktivní' }))
      .toHaveAttribute('href', '/viewer/players/active')
    expect(screen.getByRole('link', { name: 'Po kariéře' }))
      .toHaveAttribute('href', '/viewer/players/retired')
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('shows only active players, including Run prospects without pretending they entered the Tour', async () => {
    mount('active')
    const table = await screen.findByRole('table', { name: 'Veřejný seznam aktivních hráčů' })
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(within(table).getByRole('link', { name: 'Player 001' })).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'Player 003' })).toBeInTheDocument()
    expect(within(table).queryByRole('link', { name: 'Player 002' })).not.toBeInTheDocument()
    expect(within(table).getAllByText('Nový talent Runu')).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'Aktivní' })).toHaveAttribute('aria-current', 'page')
    expectNoForbiddenViewerActions()
  })

  it('shows only retired players and preserves unavailable OVR as unknown', async () => {
    mount('retired')
    const table = await screen.findByRole('table', { name: 'Veřejný seznam hráčů po kariéře' })
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(within(table).getByRole('link', { name: 'Player 002' })).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'Player 004' })).toBeInTheDocument()
    expect(within(table).queryByRole('link', { name: 'Player 001' })).not.toBeInTheDocument()
    const row = within(table).getByRole('row', { name: /Player 002/ })
    expect(within(row).getAllByRole('cell')[4]).toHaveTextContent('—')
    expect(screen.getByRole('link', { name: 'Po kariéře' }))
      .toHaveAttribute('aria-current', 'page')
  })

  it('filters within the fixed active cohort by search, country and origin, then resets', async () => {
    const user = userEvent.setup()
    mount('active')
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Země'), 'NZL')
    let table = screen.getByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByRole('link', { name: 'Player 003' })).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat hráče nebo zemi'), 'not-here')
    expect(screen.getByText('Filtrům neodpovídá žádný hráč.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    table = screen.getByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    await user.selectOptions(screen.getByLabelText('Původ hráče'), 'initial_world')
    expect(screen.getByText('Filtrům neodpovídá žádný hráč.')).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
  })

  it('distinguishes no eligible retired player from an invalid public source', async () => {
    api.getViewerPlayers.mockReset().mockResolvedValue(payload([player(1), player(3)]))
    mount('retired')
    expect(await screen.findByText('V uloženém Runu nejsou žádní hráči v této kategorii.'))
      .toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('fails closed on wrong Branch, mismatched counts and leaked private attributes until GET recovery', async () => {
    const user = userEvent.setup()
    const original = payload()
    api.getViewerPlayers.mockReset()
      .mockResolvedValueOnce(payload(sample, 'run alpha', 'foreign'))
      .mockResolvedValueOnce({ ...original, player_count: 999 })
      .mockResolvedValueOnce({
        ...original, players: [{ ...sample[0], potential_ovr: 199 }, ...sample.slice(1)],
      })
      .mockResolvedValueOnce(original)
    mount()
    for (let i = 0; i < 3; i++) {
      expect(await screen.findByRole('alert')).toHaveTextContent('nepovolená data')
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Znovu načíst (GET)' }))
    }
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.queryByText('199')).not.toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(4)
    expectNoForbiddenViewerActions()
  })

  it('does not leak a slow response from an earlier saved Viewer Branch after source switch', async () => {
    let resolveOld: ((data: ViewerPlayers) => void) | undefined
    api.getViewerPlayers.mockReset().mockImplementation((run: string) =>
      context.branch === 'branch-a'
        ? new Promise(resolve => { resolveOld = resolve })
        : Promise.resolve(payload(sample, run, 'branch-b')))
    const view = mount('retired')
    await waitFor(() => expect(api.getViewerPlayers).toHaveBeenCalledTimes(1))
    context.branch = 'branch-b'
    await act(async () => { view.refresh() })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(payload(sample, 'run alpha', 'branch-a')) })
    expect(screen.queryByText('branch-a')).not.toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(2)
  })

  it('switches page kinds on the same public cache without extra GET, preserving fixed status', async () => {
    const view = mount('all')
    await screen.findByRole('table', { name: 'Veřejný seznam všech hráčů' })
    context.kind = 'active'
    await act(async () => { view.refresh() })
    expect(screen.getByRole('table', { name: 'Veřejný seznam aktivních hráčů' })).toBeInTheDocument()
    context.kind = 'retired'
    await act(async () => { view.refresh() })
    expect(screen.getByRole('table', { name: 'Veřejný seznam hráčů po kariéře' })).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
  })

  it('translates UI to English while preserving player names, IDs and cached GET', async () => {
    const user = userEvent.setup()
    mount('retired')
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { level: 2, name: 'Retired Players' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Retired public players' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Player 002' })).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
  })

  it('paginates more than 50 players in a cohort and resets page after a local filter', async () => {
    const players = Array.from({ length: 57 }, (_, index) =>
      player(index + 1, 'active', index % 2 ? 'CZE' : 'NZL'))
    api.getViewerPlayers.mockReset().mockResolvedValue(payload(players))
    const user = userEvent.setup()
    mount('active')
    expect(await screen.findByText('Zobrazeno 1–50 z 57')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(screen.getByText('Zobrazeno 51–57 z 57')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat hráče nebo zemi'), 'Player 057')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Player 057' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

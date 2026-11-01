import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ViewerPlayer, ViewerPlayers } from '../../../api/types'
import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { writeViewerActiveProductRunId } from '../../../viewer/activeProductRun'
import { ViewerPlayersPage } from './ViewerPlayersPage'

const api = vi.hoisted(() => ({
  getViewerOfficialRunContext: vi.fn(),
  getViewerPlayers: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../../../api/client', () => api)

const run = 'run alpha'
const branch = 'branch-a'
function context(runId = run, branchId = branch) {
  return { product_run_id: runId, official_branch_id: branchId }
}
function player(number: number, status: 'active' | 'retired' = 'active',
  country = 'CZE', ovr: number | null = 120): ViewerPlayer {
  const id = 'player ' + String(number).padStart(3, '0')
  return {
    player_id: id, name: 'Player ' + String(number).padStart(3, '0'),
    country_code: country, age: 18 + number % 30, status,
    identity_source: number % 2 ? 'run_prospect' : 'initial_world',
    tour_entry_season_index: null, tour_entry_week: null,
    current_ovr: ovr, potential_ovr: null, current_form: null,
    match_sharpness: null, long_term_fatigue: null
  }
}
function roster(items = [player(1, 'active', 'CZE', 180), player(2, 'retired', 'NZL', null),
  player(3, 'active', 'NZL', 160)], runId = run, branchId = branch): ViewerPlayers {
  return {
    schema_version: 'viewer_players.v1', product_run_id: runId,
    viewer_branch_id: branchId, season_index: 5, week: 14,
    player_count: items.length, active_player_count: items.filter(p => p.status === 'active').length,
    retired_player_count: items.filter(p => p.status === 'retired').length, players: items
  }
}
function SwitchLanguage() {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const app = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LanguageProvider><SwitchLanguage /><ViewerPlayersPage /></LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { ...app, client }
}

describe('Viewer Players directory with mocked canonical Saved GETs', () => {
  beforeEach(() => {
    localStorage.clear()
    api.getViewerOfficialRunContext.mockReset().mockResolvedValue(context())
    api.getViewerPlayers.mockReset().mockResolvedValue(roster())
  })

  it('does not query a Player Run before selecting a Product Run', () => {
    mount()
    expect(screen.getByRole('heading', { name: 'Hráči' })).toBeInTheDocument()
    expect(screen.getByText(/Nejprve vyber Product Run/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Seznam Runů' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerOfficialRunContext).not.toHaveBeenCalled()
    expect(api.getViewerPlayers).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows complete real roster, linked profile/country, active and retired totals without hidden metrics', async () => {
    writeViewerActiveProductRunId(run)
    api.getViewerPlayers.mockResolvedValue(roster([
      player(1, 'active', 'EGY', 180),
      player(2, 'retired', 'NZL', null), player(3, 'active', 'NZL', 160)
    ]))
    mount()
    const table = await screen.findByRole('table', { name: 'Uložený seznam hráčů' })
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledWith(run)
    expect(api.getViewerPlayers).toHaveBeenCalledWith(run)
    expect(within(table).getAllByRole('row')).toHaveLength(4)
    expect(within(table).getByRole('link', { name: 'Player 001' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player%20001/career')
    expect(within(table).getByRole('link', { name: 'EGY' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/EGY')
    expect(screen.getByText(branch)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Hráči vybraného Runu' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players')
    expect(within(table).queryByText('199')).not.toBeInTheDocument()
    expect(within(table).queryByText('181')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('never renders a public roster when the backend leaks one private player attribute', async () => {
    writeViewerActiveProductRunId(run)
    api.getViewerPlayers.mockResolvedValueOnce(roster([
      {...player(1), potential_ovr: 199}, player(2)
    ])).mockResolvedValueOnce(roster([player(1), player(2)]))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná nebo cizí data')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText('199')).not.toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
    // Only an explicit GET retry with a corrected projection can display
    // players again; no partial list is ever rendered.
    await user.click(screen.getByRole('button', {name:'Načíst znovu (GET)'}))
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(2)
    expectNoForbiddenViewerActions()
  })

  it('filters complete population by status, country, origin and name, then clears locally', async () => {
    writeViewerActiveProductRunId(run)
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Kariéra' }), 'active')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Země' }), 'NZL')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Původ hráče' }), 'run_prospect')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('table')).toHaveTextContent('Player 003')
    await user.type(screen.getByRole('searchbox', { name: 'Hledat jméno, ID nebo zemi' }), 'UNKNOWN')
    expect(screen.getByText('Žádní hráči neodpovídají filtrům.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(screen.getByText('Zobrazeno 1–3 z 3')).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
  })

  it('sorts only known public OVR and paginates 50 players with bounded jump', async () => {
    const many = Array.from({ length: 111 }, (_, i) => player(i + 1, 'active', 'CZE', i === 109 ? null : 100 + i % 50))
    api.getViewerPlayers.mockResolvedValue(roster(many))
    writeViewerActiveProductRunId(run)
    const user = userEvent.setup()
    mount()
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    expect(screen.getByText('Zobrazeno 1–50 z 111')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Poslední' }))
    expect(screen.getByText('Zobrazeno 101–111 z 111')).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '4')
    await user.keyboard('{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('existující číslo stránky')
    await user.clear(screen.getByRole('textbox', { name: 'Přejít na stránku' }))
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '2')
    await user.keyboard('{Enter}')
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Řazení' }), 'public_ovr')
    expect(screen.getByText('Zobrazeno 1–50 z 111')).toBeInTheDocument()
    expect(screen.getByRole('table')).not.toHaveTextContent('player 110')
    await user.type(screen.getByRole('searchbox', { name: 'Hledat jméno, ID nebo zemi' }), 'PLAYER 111')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('table')).toHaveTextContent('Player 111')
  })

  it('distinguishes genuine zero roster, wrong Branch, API failure and GET-only retry', async () => {
    writeViewerActiveProductRunId(run)
    api.getViewerPlayers.mockResolvedValue(roster([]))
    const empty = mount()
    expect(await screen.findByText('V tomto Runu nejsou žádní uložení hráči.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    empty.unmount()
    api.getViewerPlayers.mockResolvedValueOnce(roster(undefined, run, 'foreign'))
      .mockRejectedValueOnce(new Error('private server incident'))
      .mockResolvedValueOnce(roster())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná nebo cizí data')
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('není dostupný')
    expect(screen.queryByText('private server incident')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(4)
  })

  it('blocks requests when context mismatches Run and can retry the context GET', async () => {
    writeViewerActiveProductRunId(run)
    api.getViewerOfficialRunContext.mockResolvedValueOnce(context('foreign'))
      .mockResolvedValueOnce(context())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neodpovídá vybranému Product Runu')
    expect(api.getViewerPlayers).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledTimes(2)
  })

  it('keeps filters and cached source on CS/EN switch without new reads', async () => {
    writeViewerActiveProductRunId(run)
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Kariéra' }), 'retired')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Saved player directory' })).toBeInTheDocument()
    expect(screen.getByText('Showing 1–1 of 1')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Career status' })).toHaveValue('retired')
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
  })

  it('drops old source after authoritative Viewer Branch changes', async () => {
    writeViewerActiveProductRunId(run)
    const { client } = mount()
    expect(await screen.findByText(branch)).toBeInTheDocument()
    api.getViewerOfficialRunContext.mockResolvedValue(context(run, 'branch-b'))
    api.getViewerPlayers.mockResolvedValue(roster([player(4)], run, 'branch-b'))
    await act(async () => { await client.invalidateQueries({ queryKey: ['viewer-official-run-context', run] }) })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    expect(screen.queryByText(branch)).not.toBeInTheDocument()
    expect(await screen.findByRole('table')).toHaveTextContent('Player 004')
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(2)
  })

  it('does not leak delayed old Product Run results after Run switch', async () => {
    let oldReply: ((value: ViewerPlayers) => void) | undefined
    api.getViewerOfficialRunContext.mockImplementation((runId: string) => Promise.resolve(context(runId)))
    api.getViewerPlayers.mockImplementationOnce(() => new Promise(resolve => { oldReply = resolve }))
      .mockResolvedValueOnce(roster([player(5)], 'new run'))
    writeViewerActiveProductRunId(run)
    mount()
    await waitFor(() => expect(api.getViewerPlayers).toHaveBeenCalledTimes(1))
    act(() => writeViewerActiveProductRunId('new run'))
    expect(await screen.findByRole('table')).toHaveTextContent('Player 005')
    await act(async () => { oldReply?.(roster()) })
    expect(screen.getByRole('table')).toHaveTextContent('Player 005')
    expect(screen.queryByText('Player 001')).not.toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(2)
  })
})

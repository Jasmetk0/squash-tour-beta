import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ViewerMatchPredictorPage } from './ViewerMatchPredictorPage'

const source = vi.hoisted(() => ({ runId: 'run-a', language: 'en' as 'en' | 'cs' }))
const api = vi.hoisted(() => ({
  getRunPlayerDetail: vi.fn(),
  listRunPlayers: vi.fn(),
}))
vi.mock('../../../api/client', () => api)
vi.mock('../../../viewer/useActiveViewerRunId', () => ({
  useActiveViewerRunId: () => source.runId,
}))
vi.mock('../../../viewer/ViewerContext', () => ({
  useViewerContext: () => ({ selectedSeason: 0, selectedWeek: 1 }),
}))
vi.mock('../../../i18n/LanguageContext', () => ({
  useLanguage: () => ({ language: source.language }),
}))

function makePlayer(id: string, overall = 80) {
  return {
    player_id: id, name: 'Player ' + id,
    country_code: 'EGY', age: 25, source_type: 'planner_generated',
    override_id: null, quality_band: 'elite', is_top_band: true,
    origin_source_type: 'planner_generated', origin_quality_band: 'elite',
    origin_override_id: null, origin_season: 2025,
    overall, technique: 80, movement: 81, physical: 82, mental: 83,
  }
}

function Navigation() {
  const loc = useLocation()
  const navigate = useNavigate()
  return <>
    <output aria-label="Current URL">{loc.pathname}{loc.search}</output>
    <button type="button" onClick={() => navigate(-1)}>Back</button>
    <button type="button" onClick={() => navigate(1)}>Forward</button>
  </>
}
function mount(url = '/viewer/predictions/match-predictor?playerA=player-1&playerB=player-900') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  function App() {
    return <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <Navigation />
        <ViewerMatchPredictorPage />
      </MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, client, rerenderPage: () => view.rerender(<App />) }
}
function link(name: string) { return screen.getByRole('link', { name }) }

beforeEach(() => {
  source.runId = 'run-a'
  source.language = 'en'
  api.getRunPlayerDetail.mockReset()
  api.listRunPlayers.mockReset()
  api.listRunPlayers.mockResolvedValue({
    run_id: 'run-a', total: 1000, limit: 50, offset: 0,
    players: [makePlayer('player-1')],
  })
  api.getRunPlayerDetail.mockImplementation(async (_run: string, id: string) =>
    makePlayer(id, id === 'player-900' ? 76 : 80))
})
afterEach(() => cleanup())

describe('Viewer Match Predictor: verified exact IDs, no prediction model (mocked GET only)', () => {
  it('resolves URL player #900 by exact GET outside the first 50 and displays no invented odds', async () => {
    mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(api.getRunPlayerDetail).toHaveBeenCalledWith('run-a', 'player-1')
    expect(api.getRunPlayerDetail).toHaveBeenCalledWith('run-a', 'player-900')
    expect(api.listRunPlayers).toHaveBeenCalledWith('run-a', { limit: 50, offset: 0 })
    expect(screen.getByText('Power Rating difference')).toBeInTheDocument()
    expect(screen.getByText('+4')).toBeInTheDocument()
    expect(screen.getByText(/No match-win probability, odds or simulated result is calculated/))
      .toBeInTheDocument()
    expect(link('Open H2H comparison')).toHaveAttribute('href', '/viewer/h2h?playerA=player-1&playerB=player-900')
  })

  it('withholds detail GETs for same IDs, missing IDs, whitespace or excessive URL IDs', async () => {
    for (const url of [
      '?playerA=equal&playerB=equal', '?playerA=only', '?playerA=%20player-1&playerB=player-2',
      '?playerA=' + 'x'.repeat(257) + '&playerB=player-2',
    ]) {
      const view = mount('/viewer/predictions/match-predictor' + url)
      expect(await screen.findByRole('alert')).toHaveTextContent('valid player IDs')
      expect(api.getRunPlayerDetail).not.toHaveBeenCalled()
      view.unmount()
    }
  })

  it('rejects mismatched player identity or malformed numeric attributes without a false preview', async () => {
    api.getRunPlayerDetail.mockImplementation(async (_run: string, id: string) =>
      id === 'player-900' ? makePlayer('foreign-player') : makePlayer(id))
    const first = mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('do not match')
    expect(screen.queryByText('Player foreign-player')).not.toBeInTheDocument()
    expect(screen.queryByText('Power Rating difference')).not.toBeInTheDocument()
    first.unmount()

    api.getRunPlayerDetail.mockImplementation(async (_run: string, id: string) => ({
      ...makePlayer(id), technique: id === 'player-900' ? Number.NaN : 80,
    }))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('expected public fields')
    expect(screen.queryByText('Power Rating difference')).not.toBeInTheDocument()
  })

  it('keeps exact comparison available when the first-50 sample errors or belongs to another Run', async () => {
    api.listRunPlayers.mockRejectedValueOnce(new Error('sample read failed'))
    const first = mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(screen.getByText(/discovery sample is invalid or unavailable/)).toBeInTheDocument()
    first.unmount()

    api.listRunPlayers.mockResolvedValue({ run_id: 'foreign-run', total: 1,
      players: [makePlayer('foreign')] })
    mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(screen.queryByText('Player foreign')).not.toBeInTheDocument()
    expect(screen.getByText(/discovery sample is invalid or unavailable/)).toBeInTheDocument()
  })

  it('only calls GET after applying form edits; preserves unrelated params and clears selection', async () => {
    mount('/viewer/predictions/match-predictor?keep=one&keep=two')
    expect(api.getRunPlayerDetail).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Player A ID'), { target: { value: 'player-1' } })
    fireEvent.change(screen.getByLabelText('Player B ID'), { target: { value: 'player-900' } })
    expect(api.getRunPlayerDetail).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Show player attributes' }))
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    const url = screen.getByLabelText('Current URL').textContent ?? ''
    expect(url).toContain('keep=one&keep=two')
    expect(url).toContain('playerA=player-1&playerB=player-900')
    fireEvent.change(screen.getByLabelText('Player B ID'), { target: { value: 'player-901' } })
    expect(screen.getByText(/Apply the edited player IDs/)).toBeInTheDocument()
    expect(screen.queryByText('Player player-900')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show player attributes' }))
    expect(await screen.findByText('Player player-901')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear player IDs' }))
    expect(screen.queryByText('Player player-901')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Player A ID')).toHaveValue('')
    expect(screen.getByLabelText('Player B ID')).toHaveValue('')
    expect(screen.getByLabelText('Current URL')).toHaveTextContent('keep=one&keep=two')
    expect(screen.getByLabelText('Current URL')).not.toHaveTextContent('playerA=')
  })

  it('restores URL-selected exact IDs by Back/Forward without treating drafts as verified', async () => {
    mount('/viewer/predictions/match-predictor?playerA=player-1&playerB=player-900')
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Player B ID'), { target: { value: 'player-901' } })
    fireEvent.click(screen.getByRole('button', { name: 'Show player attributes' }))
    expect(await screen.findByText('Player player-901')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(screen.getByLabelText('Player B ID')).toHaveValue('player-900')
    fireEvent.click(screen.getByRole('button', { name: 'Forward' }))
    expect(await screen.findByText('Player player-901')).toBeInTheDocument()
    expect(screen.getByLabelText('Player B ID')).toHaveValue('player-901')
  })

  it('does not keep old Run details visible while a new Run is loading', async () => {
    const v = mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    source.runId = 'run-b'
    let resolve!: (value: ReturnType<typeof makePlayer>) => void
    api.getRunPlayerDetail.mockImplementation((_run: string, id: string) =>
      id === 'player-900' ? new Promise(done => { resolve = done }) : Promise.resolve(makePlayer(id, 67)))
    v.rerenderPage()
    await waitFor(() => expect(api.getRunPlayerDetail).toHaveBeenCalledWith('run-b', 'player-900'))
    expect(screen.queryByText('Player player-900')).not.toBeInTheDocument()
    expect(screen.getByText('Loading exact player details…')).toBeInTheDocument()
    await act(async () => { resolve(makePlayer('player-900', 67)) })
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(screen.queryByText('+4')).not.toBeInTheDocument()
  })

  it('does not issue any GET without an active SimulationRun', () => {
    source.runId = ''
    mount()
    expect(screen.getByText(/No active SimulationRun is selected/)).toBeInTheDocument()
    expect(api.getRunPlayerDetail).not.toHaveBeenCalled()
    expect(api.listRunPlayers).not.toHaveBeenCalled()
  })

  it('localizes its own input and status strings without refetch or changing stored attributes', async () => {
    const view = mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    const calls = api.getRunPlayerDetail.mock.calls.length
    source.language = 'cs'
    view.rerenderPage()
    expect(screen.getByRole('heading', { name: 'Prediktor zápasu' })).toBeInTheDocument()
    expect(screen.getByLabelText('ID hráče A')).toHaveValue('player-1')
    expect(screen.getByText(/Neodhadujeme pravděpodobnost výhry/)).toBeInTheDocument()
    expect(api.getRunPlayerDetail).toHaveBeenCalledTimes(calls)
    expect(screen.getByText('+4')).toBeInTheDocument()
  })
})

describe('Match Predictor audit: discovery rows are validated before rendering', () => {
  it.each([
    { players: [null] },
    { players: [makePlayer('same'), makePlayer('same')] },
    { players: [{ ...makePlayer('broken'), overall: Number.NaN }] },
    { limit: 100 },
    { offset: 50 },
  ])('rejects malformed discovery payload (%j)', async override => {
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run-a', total: 2, limit: 50, offset: 0,
      players: [makePlayer('foreign')], ...override,
    })
    mount('/viewer/predictions/match-predictor')
    expect(await screen.findByText(/discovery sample is invalid or unavailable/)).toBeInTheDocument()
    expect(screen.queryByText('Player foreign')).not.toBeInTheDocument()
    expect(api.getRunPlayerDetail).not.toHaveBeenCalled()
  })

  it('does not pass foreign-schema fields to the shared discovery renderer', async () => {
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run-a', total: 1, limit: 50, offset: 0,
      players: [{ ...makePlayer('safe'), current_ovr: 99999, identity_source: {} }],
    })
    mount('/viewer/predictions/match-predictor')
    expect(await screen.findByText('Player safe')).toBeInTheDocument()
    expect(screen.queryByText('99999')).not.toBeInTheDocument()
  })

  it('retains exact comparison even when an individual discovery row is corrupt', async () => {
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run-a', total: 1, limit: 50, offset: 0, players: [null],
    })
    mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(screen.getByText(/discovery sample is invalid or unavailable/)).toBeInTheDocument()
    expect(screen.getByText('+4')).toBeInTheDocument()
  })
})

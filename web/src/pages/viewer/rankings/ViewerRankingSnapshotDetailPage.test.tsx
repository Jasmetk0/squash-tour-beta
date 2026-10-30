import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerRankingSnapshotDetailPage } from './ViewerRankingSnapshotDetailPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error { status = 500 },
  getViewerOfficialRankingHistoryDetail: vi.fn()
}))
vi.mock('../../../api/client', () => api)

const route = vi.hoisted(() => ({
  current: {
    productRunId: 'run alpha',
    officialBranchId: 'branch-a',
    officialContext: { product_run_id: 'run alpha', official_branch_id: 'branch-a' },
    isLoading: false, isStale: false
  }
}))
vi.mock('../../../viewer/ViewerProductRunRouteContext', () => ({
  useViewerProductRunRouteContext: () => route.current
}))
function setScope(run: string, branch: string) {
  route.current = {
    productRunId: run,
    officialBranchId: branch,
    officialContext: { product_run_id: run, official_branch_id: branch },
    isLoading: false, isStale: false
  }
}
function rows(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    rank: i + 1, player_id: 'player-' + String(i + 1).padStart(3, '0'), points: 1000 - i
  }))
}
function publication(entries = rows(2), run = 'run alpha', branch = 'branch-a', ordinal = 1) {
  return {
    schema_version: 'viewer_official_ranking.v1',
    product_run_id: run, viewer_branch_id: branch,
    season_index: Math.floor(ordinal / 61),
    week: ordinal % 61 + 1,
    week_ordinal: ordinal,
    snapshot_fingerprint: 'b'.repeat(64),
    policy_id: 'past-policy',
    best_n: 12,
    row_count: entries.length,
    rows: entries
  }
}
function SwitchLanguage(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function GoToOtherOrdinal(): JSX.Element {
  const navigate = useNavigate()
  return <button onClick={() => navigate('/viewer/runs/run%20alpha/rankings/2')}>Go to ordinal 2</button>
}
function mount(path = '/viewer/runs/run%20alpha/rankings/1') {
  const queryClient = createTestQueryClient()
  function App(): JSX.Element {
    return <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <LanguageProvider>
          <SwitchLanguage />
          <GoToOtherOrdinal />
          <Routes>
            <Route path="/viewer/runs/:runId/rankings/:snapshotSequence" element={<ViewerRankingSnapshotDetailPage />} />
          </Routes>
        </LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  }
  const result = render(<App />)
  return { ...result, update: () => result.rerender(<App />) }
}

describe('historical Official Ranking detail (mocked GET API, not HTTP/SQLite)', () => {
  beforeEach(() => {
    localStorage.clear()
    setScope('run alpha', 'branch-a')
    api.getViewerOfficialRankingHistoryDetail.mockReset()
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue(publication())
  })

  it('shows sourced policy, exact players/points and safe route links without inferred metrics', async () => {
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue(publication([
      { rank: 1, player_id: 'player-001', points: 0 },
      { rank: 2, player_id: 'player with space', points: 200 }
    ]))
    mount()
    const table = await screen.findByRole('table', { name: 'Historický Official Ranking – hráči' })
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledWith('run alpha', 1)
    expect(screen.getByText('past-policy')).toBeInTheDocument()
    expect(screen.getByText(/Sezona 2000\/01/)).toBeInTheDocument()
    expect(screen.getByText('b'.repeat(64))).toBeInTheDocument()
    expect(within(table).getByText('0')).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'player-001' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player-001/career')
    expect(within(table).getByRole('link', { name: 'player with space' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player%20with%20space/career')
    expect(screen.getByRole('link', { name: 'Zpět na historii rankingů' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(screen.queryByText('Tournaments counted')).not.toBeInTheDocument()
    expect(screen.queryByText('Movement')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it.each(['nope', '01', '-1', '3050', '1e2'])('does not request an invalid ordinal %s', value => {
    mount('/viewer/runs/run%20alpha/rankings/' + value)
    expect(screen.getByRole('alert')).toHaveTextContent('Neplatný ordinal publikace.')
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
  })

  it('gates requests on an exact valid route/branch context', async () => {
    const view = mount()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    view.unmount()

    setScope('run alpha', 'branch-b')
    route.current = {
      ...route.current,
      officialContext: { product_run_id: 'run alpha', official_branch_id: 'branch-a' }
    }
    const next = mount()
    expect(screen.getByText('Čeká se na platný kontext Runu a Viewer Branch.')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(1)
    route.current = { ...route.current, isStale: true }
    next.update()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    setScope('run alpha', 'branch-b')
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue(publication(rows(1), 'run alpha', 'branch-b'))
    next.update()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(2)
  })

  it('rejects foreign Branch, duplicate players and changed row count; retry GET only', async () => {
    api.getViewerOfficialRankingHistoryDetail
      .mockResolvedValueOnce(publication(rows(2), 'run alpha', 'foreign'))
      .mockResolvedValueOnce(publication([{ rank: 1, player_id: 'same', points: 10 }, { rank: 2, player_id: 'same', points: 2 }]))
      .mockResolvedValueOnce({ ...publication(), row_count: 3 })
      .mockResolvedValueOnce(publication())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neodpovídá zvolenému zdroji')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Opakovat čtení' }))
    expect(screen.getByRole('alert')).toHaveTextContent('duplicitní data')
    await user.click(screen.getByRole('button', { name: 'Opakovat čtení' }))
    expect(screen.getByRole('alert')).toHaveTextContent('neplatná')
    await user.click(screen.getByRole('button', { name: 'Opakovat čtení' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(4)
  })

  it('does not expose late replies from an old ordinal or Branch', async () => {
    let release: ((v: ReturnType<typeof publication>) => void) | undefined
    api.getViewerOfficialRankingHistoryDetail
      .mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
      .mockResolvedValueOnce(publication([{ rank: 1, player_id: 'new-ordinal', points: 9 }], 'run alpha', 'branch-a', 2))
      .mockResolvedValueOnce(publication([{ rank: 1, player_id: 'new-branch', points: 10 }], 'run alpha', 'branch-b', 2))
    const user = userEvent.setup()
    const view = mount()
    await waitFor(() => expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(1))
    await user.click(screen.getByRole('button', { name: 'Go to ordinal 2' }))
    expect(await screen.findByText('new-ordinal')).toBeInTheDocument()
    setScope('run alpha', 'branch-b')
    view.update()
    expect(await screen.findByText('new-branch')).toBeInTheDocument()
    await act(async () => { release?.(publication([{ rank: 1, player_id: 'old-delayed', points: 12 }])) })
    expect(screen.queryByText('old-delayed')).not.toBeInTheDocument()
    expect(screen.getByText('new-branch')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(3)
  })

  it('filters full player list before pagination, jumps using keyboard, handles invalid pages and empty search', async () => {
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue(publication(rows(120)))
    const user = userEvent.setup()
    mount()
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    expect(screen.getByText('Zobrazeno 1–50 z 120')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Poslední stránka' }))
    expect(screen.getByText('Zobrazeno 101–120 z 120')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'První stránka' }))
    expect(screen.getByText('Stránka 1 / 3')).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '0')
    await user.keyboard('{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('Zadej celé číslo')
    expect(screen.getByText('Stránka 1 / 3')).toBeInTheDocument()
    await user.clear(screen.getByRole('textbox', { name: 'Přejít na stránku' }))
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '2')
    await user.keyboard('{Enter}')
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    await user.type(screen.getByRole('searchbox', { name: 'Hledat podle ID hráče' }), 'player-11')
    expect(screen.getByText('Zobrazeno 1–10 z 10')).toBeInTheDocument()
    expect(screen.queryByText('Stránka 1 / 0')).not.toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByText('player-119')).toBeInTheDocument()
    await user.clear(screen.getByRole('searchbox', { name: 'Hledat podle ID hráče' }))
    await user.type(screen.getByRole('searchbox', { name: 'Hledat podle ID hráče' }), 'unknown-id')
    expect(screen.getByText('Žádný hráč neodpovídá hledání.')).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 0–0 z 0')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat hledání' }))
    expect(screen.getByText('Zobrazeno 1–50 z 120')).toBeInTheDocument()
  })

  it('keeps filters/page on CS/EN switch without another API request', async () => {
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue(publication(rows(120)))
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Další stránka' }))
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('table', { name: 'Historical Official Ranking players' })).toBeInTheDocument()
    expect(screen.getByText('Page 2 / 3')).toBeInTheDocument()
    expect(screen.getByText('Search uses only IDs from this saved snapshot. The API does not return names, countries or point breakdowns.')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(1)
  })

  it('distinguishes a legitimate empty ranking from failed GET; retry performs one new read', async () => {
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValueOnce(publication([]))
    const first = mount()
    expect(await screen.findByText('Tato publikace platně obsahuje nula hráčů.')).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 0–0 z 0')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    first.unmount()

    api.getViewerOfficialRankingHistoryDetail.mockReset()
    api.getViewerOfficialRankingHistoryDetail.mockRejectedValueOnce(new Error('GET unavailable')).mockResolvedValueOnce(publication())
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('GET unavailable')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Opakovat čtení' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(2)
  })
})

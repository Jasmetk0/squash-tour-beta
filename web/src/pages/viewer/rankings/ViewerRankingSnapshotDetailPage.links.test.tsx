import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerRankingSnapshotDetailPage } from './ViewerRankingSnapshotDetailPage'

const api = vi.hoisted(() => ({
  getViewerOfficialRankingHistoryDetail: vi.fn(),
}))
vi.mock('../../../api/client', () => api)

const source = vi.hoisted(() => ({
  scope: {
    productRunId: 'run alpha', officialBranchId: 'branch-a',
    officialContext: { product_run_id: 'run alpha', official_branch_id: 'branch-a' },
    isLoading: false, isStale: false,
  },
}))
vi.mock('../../../viewer/ViewerProductRunRouteContext', () => ({
  useViewerProductRunRouteContext: () => source.scope,
}))
const base = '/viewer/runs/run%20alpha/rankings/1'
const fingerprint = 'b'.repeat(64)
const scope = 'rankDetailRun=run+alpha&rankDetailBranch=branch-a&rankDetailOrdinal=1&rankDetailFingerprint=' + fingerprint

function rows(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    rank: i + 1, player_id: 'player-' + String(i + 1).padStart(3, '0'), points: 1000 - i,
  }))
}
function ranking(entries = rows(120), run = 'run alpha', branch = 'branch-a', ordinal = 1) {
  return {
    schema_version: 'viewer_official_ranking.v1', product_run_id: run, viewer_branch_id: branch,
    season_index: Math.floor(ordinal / 61), week: ordinal % 61 + 1,
    week_ordinal: ordinal, snapshot_fingerprint: fingerprint, policy_id: 'old-policy',
    best_n: 20, row_count: entries.length, rows: entries,
  }
}
function BrowserControls(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  const loc = useLocation(), nav = useNavigate()
  return <>
    <output aria-label="Current URL">{loc.pathname}{loc.search}</output>
    <button type="button" onClick={() => nav(-1)}>Browser Back</button>
    <button type="button" onClick={() => nav(1)}>Browser Forward</button>
    <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Toggle language</button>
  </>
}
function mount(path = base) {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <LanguageProvider>
          <BrowserControls />
          <Routes>
            <Route path="/viewer/runs/:runId/rankings/:snapshotSequence"
              element={<ViewerRankingSnapshotDetailPage />} />
          </Routes>
        </LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  }
  return { ...render(<App />), client }
}
function currentUrl() { return screen.getByLabelText('Current URL').textContent ?? '' }

describe('Ranking publication detail: shareable filtered pages (mock GET, not HTTP/SQLite)', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('squash-engine-language-v1', 'en')
    source.scope = {
      productRunId: 'run alpha', officialBranchId: 'branch-a',
      officialContext: { product_run_id: 'run alpha', official_branch_id: 'branch-a' },
      isLoading: false, isStale: false,
    }
    api.getViewerOfficialRankingHistoryDetail.mockReset()
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue(ranking())
  })

  it('opens an exact bookmarked page and keeps original ranks and player profile routes', async () => {
    mount(base + '?' + scope + '&rankDetailPage=2&keep=one&keep=two')
    const table = await screen.findByRole('table', { name: 'Historical Official Ranking players' })
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    expect(within(table).getByRole('link', { name: 'player-051' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player-051/career')
    expect(within(table).queryByText('player-001')).not.toBeInTheDocument()
    expect(screen.getByText('Page 2 / 3')).toBeInTheDocument()
    expect(currentUrl()).toContain('keep=one&keep=two')
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledWith('run alpha', 1)
    expectNoForbiddenViewerActions()
  })

  it('stores typed player ID filter, resets page, and does not refetch on local search', async () => {
    const user = userEvent.setup()
    mount(base + '?keep=one&keep=two')
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    const calls = api.getViewerOfficialRankingHistoryDetail.mock.calls.length
    await user.click(screen.getByRole('button', { name: 'Last page' }))
    expect(screen.getByText('Page 3 / 3')).toBeInTheDocument()
    const input = screen.getByRole('searchbox', { name: 'Search by player ID' })
    await user.type(input, 'player-11')
    expect(screen.getByText('Showing 1–10 of 10')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Search by player ID' }))
      .toHaveValue('player-11')
    expect(currentUrl()).toContain('rankDetailPlayer=player-11')
    expect(currentUrl()).not.toContain('rankDetailPage=')
    expect(currentUrl()).toContain('keep=one&keep=two')
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(calls)
    await user.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(screen.getByText('Showing 1–50 of 120')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Search by player ID' })).toHaveValue('')
    expect(currentUrl()).not.toContain('rankDetailPlayer=')
  })

  it('bounds oversized input without generating an invalid URL or losing the search controls', async () => {
    mount(base + '?keep=yes')
    const search = await screen.findByRole('searchbox', { name: 'Search by player ID' })
    expect(search).toHaveAttribute('maxlength', '256')
    fireEvent.change(search, { target: { value: 'x'.repeat(257) } })
    expect(screen.getByRole('searchbox', { name: 'Search by player ID' })).toHaveValue('x'.repeat(256))
    expect(currentUrl()).toContain('rankDetailPlayer=' + 'x'.repeat(256))
    expect(currentUrl()).toContain('keep=yes')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByText('No players match the search.')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Clear search' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(1)
  })

  it('restores pages through Back/Forward without issuing another source GET', async () => {
    const user = userEvent.setup()
    mount(base)
    expect(await screen.findByRole('table')).toBeInTheDocument()
    const calls = api.getViewerOfficialRankingHistoryDetail.mock.calls.length
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByText('Page 2 / 3')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByText('Page 3 / 3')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Browser Back' }))
    expect(screen.getByText('Page 2 / 3')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Browser Forward' }))
    expect(screen.getByText('Page 3 / 3')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(calls)
  })

  it.each([
    '&rankDetailPage=99',
    '&rankDetailPage=01',
    '&rankDetailPlayer=one&rankDetailPlayer=two',
    '&rankDetailFingerprint=' + 'c'.repeat(64),
    '&rankDetailBranch=wrong',
    '&rankDetailOrdinal=2',
  ])('refuses invalid, foreign or out-of-range saved view: %s', async fragment => {
    mount(base + '?' + scope + fragment + '&keep=one&keep=two')
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match the publication')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(1)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reset to default view' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(currentUrl()).toContain('keep=one&keep=two')
    expect(currentUrl()).not.toContain('rankDetailFingerprint')
  })

  it('rejects partial filters without run+branch+ordinal+fingerprint', async () => {
    mount(base + '?rankDetailPlayer=player-1')
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match the publication')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('shows valid empty publication and zero-match search without inventing standings', async () => {
    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue(ranking([]))
    const first = mount()
    expect(await screen.findByText('This publication legitimately contains zero players.')).toBeInTheDocument()
    expect(screen.getByText('Showing 0–0 of 0')).toBeInTheDocument()
    first.unmount()

    api.getViewerOfficialRankingHistoryDetail.mockResolvedValue(ranking(rows(2)))
    mount(base + '?' + scope + '&rankDetailPlayer=nobody')
    expect(await screen.findByText('No players match the search.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('never shows stale historical rows while the same GET is refetching', async () => {
    const view = mount()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    let release!: (v: ReturnType<typeof ranking>) => void
    api.getViewerOfficialRankingHistoryDetail.mockImplementationOnce(() =>
      new Promise(resolve => { release = resolve }))
    const refetch = view.client.invalidateQueries({ queryKey: ['viewer-official-ranking-history-detail'] })
    await waitFor(() => expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(2))
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByText('Loading published ranking…')).toBeInTheDocument()
    await act(async () => { release(ranking()); await refetch })
    expect(await screen.findByRole('table')).toBeInTheDocument()
  })

  it('preserves bookmarked filters during CS/EN switching without a new GET', async () => {
    mount(base + '?' + scope + '&rankDetailPage=2')
    expect(await screen.findByText('Page 2 / 3')).toBeInTheDocument()
    const calls = api.getViewerOfficialRankingHistoryDetail.mock.calls.length
    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle language' }))
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Historický Official Ranking – hráči' })).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(calls)
  })
})

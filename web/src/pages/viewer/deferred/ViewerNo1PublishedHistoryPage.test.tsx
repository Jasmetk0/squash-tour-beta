import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerRankingDeferredPage } from './ViewerRankingDeferredPage'

const api = vi.hoisted(() => ({
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerOfficialRankingHistoryDetail: vi.fn(),
}))
const active = vi.hoisted(() => ({
  run: 'run alpha' as string | null, branch: 'branch-a', foreign: false,
}))
vi.mock('../../../api/client', () => ({
  ...api, ApiError: class ApiError extends Error {},
}))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => active.run,
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: { product_run_id: active.foreign ? 'other-run' : run, official_branch_id: active.branch },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

function publication(ordinal: number, rowCount = 2, policy = 'policy-' + ordinal) {
  return {
    season_index: Math.floor(ordinal / 61),
    week: ordinal % 61 + 1,
    week_ordinal: ordinal,
    snapshot_fingerprint: ordinal.toString(16).padStart(64, '0'),
    policy_id: policy,
    best_n: 15,
    row_count: rowCount,
  }
}
type Item = ReturnType<typeof publication>
function history(
  rows: Item[] = [publication(2), publication(1), publication(0)],
  run = active.run ?? '', branch = active.branch,
) {
  return {
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: run, viewer_branch_id: branch,
    public_head_ordinal: Math.max(0, ...rows.map(r => r.week_ordinal)),
    publication_count: rows.length, publications: rows,
  }
}
function snapshot(item: Item = publication(2), run = active.run ?? '', branch = active.branch) {
  return {
    schema_version: 'viewer_official_ranking.v1',
    product_run_id: run, viewer_branch_id: branch,
    season_index: item.season_index, week: item.week,
    week_ordinal: item.week_ordinal,
    snapshot_fingerprint: item.snapshot_fingerprint,
    policy_id: item.policy_id, best_n: item.best_n,
    row_count: item.row_count,
    rows: Array.from({ length: item.row_count }, (_, i) => ({
      rank: i + 1, player_id: (i === 0 ? 'leader-' : 'runner-') + item.week_ordinal,
      points: 1000 - i * 250,
    })),
  }
}
function ToggleLanguage(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>
    Switch language
  </button>
}
function mount() {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return <QueryClientProvider client={client}>
      <MemoryRouter><LanguageProvider>
        <ToggleLanguage /><ViewerRankingDeferredPage kind="no1-history" />
      </LanguageProvider></MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}
function table() {
  return screen.getByRole('table', { name: 'Publikace pro ověření hráče č. 1' })
}
function inspectButtons() {
  return screen.getAllByRole('button', { name: 'Ověřit hráče č. 1 (GET)' })
}

describe('On-demand No. 1 History from individually verified Saved ranking publications (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    active.run = 'run alpha'; active.branch = 'branch-a'; active.foreign = false
    api.listViewerOfficialRankingHistory.mockReset().mockImplementation((run: string) =>
      Promise.resolve(history(undefined, run, active.branch)))
    api.getViewerOfficialRankingHistoryDetail.mockReset().mockImplementation(
      (run: string, ordinal: number) => Promise.resolve(snapshot(publication(ordinal), run, active.branch)),
    )
  })

  it('never queries publication history without an explicitly selected Product Run', () => {
    active.run = null
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Seznam Runů' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('gates all public GETs when official context belongs to another Run', () => {
    active.foreign = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('Nelze ověřit Viewer Branch')
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
  })

  it('renders real publication metadata but fetches no full ranking details until the user asks', async () => {
    mount()
    const rows = within(await screen.findByRole('table')).getAllByRole('row')
    expect(rows).toHaveLength(4)
    expect(rows[1]).toHaveTextContent('3')
    expect(within(table()).getByRole('link', { name: 'Otevřít ranking #2' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/2')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText(/mezery mezi publikacemi se nedopočítávají/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Úplná historie publikací' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(1)
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('proves actual No. 1 ID and points from just the requested matching historical snapshot', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(inspectButtons()[0])
    expect(await screen.findByText('Ověřené 1. místo:')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'leader-2' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/leader-2/career')
    expect(screen.getByText(/Body: 1000/)).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(1)
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledWith('run alpha', 2)
    await user.click(screen.getByRole('button', { name: 'Skrýt detail' }))
    expect(screen.queryByRole('link', { name: 'leader-2' })).not.toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('does not request a detail or invent a No. 1 for a published ranking with zero players', async () => {
    api.listViewerOfficialRankingHistory.mockReset().mockResolvedValue(history([publication(2, 0)]))
    mount()
    expect(await screen.findByText('Publikovaný žebříček má 0 hráčů.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ověřit hráče č. 1 (GET)' })).not.toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
  })

  it('rejects a different Branch and an incorrect fingerprint, then GET-only retry succeeds', async () => {
    const orig = snapshot()
    api.getViewerOfficialRankingHistoryDetail.mockReset()
      .mockResolvedValueOnce(snapshot(publication(2), 'run alpha', 'foreign-branch'))
      .mockResolvedValueOnce({ ...orig, snapshot_fingerprint: 'f'.repeat(64) })
      .mockResolvedValueOnce(orig)
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(inspectButtons()[0])
    for (let i = 0; i < 2; i++) {
      const alert = await screen.findByRole('alert')
      expect(alert).toHaveTextContent('neshoduje')
      expect(screen.queryByRole('link', { name: 'leader-2' })).not.toBeInTheDocument()
      await user.click(within(alert).getByRole('button', { name: 'Načíst znovu (GET)' }))
    }
    expect(await screen.findByRole('link', { name: 'leader-2' })).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(3)
    expectNoForbiddenViewerActions()
  })

  it('rejects detail with mismatching historical policy or row count even under the same Run and Branch', async () => {
    api.getViewerOfficialRankingHistoryDetail.mockReset()
      .mockResolvedValueOnce({ ...snapshot(), policy_id: 'changed-policy' })
      .mockResolvedValueOnce({ ...snapshot(), row_count: 4 })
      .mockResolvedValueOnce({ ...snapshot(), rows: [{ rank: 2, player_id: 'spoof', points: 900 },
        { rank: 1, player_id: 'leader-2', points: 1000 }] })
      .mockResolvedValueOnce(snapshot())
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(inspectButtons()[0])
    for (let i = 0; i < 3; i++) {
      const alert = await screen.findByRole('alert')
      expect(alert).toHaveTextContent('Detail se neshoduje')
      await user.click(within(alert).getByRole('button', { name: 'Načíst znovu (GET)' }))
    }
    expect(await screen.findByRole('link', { name: 'leader-2' })).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(4)
  })

  it('fails closed on inconsistent history and permits a public GET retry before any detail', async () => {
    api.listViewerOfficialRankingHistory.mockReset()
      .mockResolvedValueOnce(history([publication(2), publication(2)]))
      .mockResolvedValueOnce(history())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná')
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(2)
  })

  it('distinguishes valid empty ranking publication history from unavailable GET', async () => {
    api.listViewerOfficialRankingHistory.mockReset().mockResolvedValue(history([]))
    mount()
    expect(await screen.findByText('Nejsou dostupné žádné publikace.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
  })

  it('filters and paginates only publication metadata without 10 speculative full ranking reads', async () => {
    const entries = Array.from({ length: 13 }, (_, i) => publication(i))
    api.listViewerOfficialRankingHistory.mockReset().mockResolvedValue(history(entries))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByText('Zobrazeno 1–10 z 13')).toBeInTheDocument()
    expect(within(table()).getAllByRole('row')).toHaveLength(11)
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(screen.getByText('Zobrazeno 11–13 z 13')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat Policy ID nebo ordinal'), 'policy-12')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(within(table()).getByRole('link', { name: 'Otevřít ranking #12' })).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat Policy ID nebo ordinal'), 'not-existing')
    expect(screen.getByText('Filtrům neodpovídá žádná publikace.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(screen.getByText('Zobrazeno 1–10 z 13')).toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('respects the saved season filter without pretending missing weeks were published', async () => {
    api.listViewerOfficialRankingHistory.mockReset().mockResolvedValue(
      history([publication(61), publication(60), publication(59)]))
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Sezona'), '1')
    expect(within(table()).getAllByRole('row')).toHaveLength(2)
    expect(within(table()).getByRole('link', { name: 'Otevřít ranking #61' })).toBeInTheDocument()
    expect(within(table()).queryByRole('link', { name: 'Otevřít ranking #60' })).not.toBeInTheDocument()
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
  })

  it('does not display a delayed No. 1 detail after switching Saved Viewer Branch', async () => {
    let resolveOld: ((value: ReturnType<typeof snapshot>) => void) | undefined
    api.getViewerOfficialRankingHistoryDetail.mockReset().mockImplementation((run: string, ordinal: number) =>
      active.branch === 'branch-a'
        ? new Promise(resolve => { resolveOld = resolve })
        : Promise.resolve(snapshot(publication(ordinal), run, 'branch-b')))
    const user = userEvent.setup()
    const view = mount()
    await screen.findByRole('table')
    await user.click(inspectButtons()[0])
    await waitFor(() => expect(api.getViewerOfficialRankingHistoryDetail).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    await act(async () => { view.refresh() })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(snapshot(publication(2), 'run alpha', 'branch-a')) })
    expect(screen.queryByRole('link', { name: 'leader-2' })).not.toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(2)
    expectNoForbiddenViewerActions()
  })

  it('localizes all interactive controls without changing historical player IDs or making GETs', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { level: 2, name: 'Published No. 1 History' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Publications for No. 1 verification' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Verify No. 1 (GET)' })).toHaveLength(3)
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(1)
    expect(api.getViewerOfficialRankingHistoryDetail).not.toHaveBeenCalled()
  })
})

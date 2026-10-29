import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerOfficialRankingHistoryPage } from './ViewerOfficialRankingHistoryPage'

const api = vi.hoisted(() => ({ listViewerOfficialRankingHistory: vi.fn() }))
const route = vi.hoisted(() => ({
  current: {
    productRunId: 'run alpha', officialBranchId: 'branch-a',
    officialContext: { product_run_id: 'run alpha', official_branch_id: 'branch-a' },
    isLoading: false, isStale: false
  }
}))
vi.mock('../../../api/client', () => api)
vi.mock('../../../viewer/ViewerProductRunRouteContext', () => ({
  useViewerProductRunRouteContext: () => route.current
}))

function scope(run: string, branch: string) {
  return {
    productRunId: run, officialBranchId: branch,
    officialContext: { product_run_id: run, official_branch_id: branch },
    isLoading: false, isStale: false
  }
}
function item(n: number, policy = 'policy-15', best = 15, rows = 2) {
  return {
    season_index: Math.floor(n / 61), week: n % 61 + 1,
    week_ordinal: n, snapshot_fingerprint: n.toString(16).padStart(64, '0'),
    policy_id: policy, best_n: best, row_count: rows
  }
}
function history(rows = [item(1), item(0)], run = 'run alpha', branch = 'branch-a') {
  return {
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: run, viewer_branch_id: branch,
    public_head_ordinal: Math.max(0, ...rows.map(row => row.week_ordinal)),
    publication_count: rows.length, publications: rows
  }
}
function ToggleLanguage(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Toggle language</button>
}
function mount() {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return <QueryClientProvider client={client}><MemoryRouter><LanguageProvider><ToggleLanguage /><ViewerOfficialRankingHistoryPage /></LanguageProvider></MemoryRouter></QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('ranking history browser (mocked GET API, not HTTP/SQLite integration)', () => {
  beforeEach(() => {
    localStorage.clear()
    route.current = scope('run alpha', 'branch-a')
    api.listViewerOfficialRankingHistory.mockReset()
    api.listViewerOfficialRankingHistory.mockResolvedValue(history())
  })

  it('shows exact publication snapshot links, zero player count, and no mutations', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValue(history([item(1, 'historic', 7, 0), item(0)]))
    mount()
    const table = await screen.findByRole('table', { name: 'Historie publikací Official Rankingu' })
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('run alpha')
    expect(within(table).getByRole('link', { name: 'Otevřít ranking týdne 2 (#1)' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/1')
    expect(within(table).getByRole('link', { name: 'Otevřít ranking týdne 1 (#0)' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/0')
    expect(within(table).getByText('historic')).toBeInTheDocument()
    expect(within(table).getAllByText('0').length).toBeGreaterThan(0)
    expectNoForbiddenViewerActions()
  })

  it('gates GET by route identity and ignores delayed responses after Run/Branch switches', async () => {
    route.current = { ...scope('run alpha', 'branch-a'), officialContext: { product_run_id: 'wrong', official_branch_id: 'branch-a' } }
    const view = mount()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    let resolveOld: ((value: ReturnType<typeof history>) => void) | undefined
    api.listViewerOfficialRankingHistory
      .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce(history([item(5, 'branch-b-only')], 'run alpha', 'branch-b'))
      .mockResolvedValueOnce(history([item(9, 'run-beta-only')], 'run beta', 'branch-c'))
    route.current = scope('run alpha', 'branch-a')
    view.refresh()
    await waitFor(() => expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(1))
    route.current = scope('run alpha', 'branch-b')
    view.refresh()
    expect(await screen.findByText('branch-b-only')).toBeInTheDocument()
    await userEvent.setup().type(screen.getByLabelText('Hledat policy_id nebo ordinal publikace'), 'missing')
    expect(screen.getByText('Žádné publikace neodpovídají zvoleným filtrům.')).toBeInTheDocument()
    route.current = scope('run beta', 'branch-c')
    view.refresh()
    expect(await screen.findByText('run-beta-only')).toBeInTheDocument()
    expect(screen.getByLabelText('Hledat policy_id nebo ordinal publikace')).toHaveValue('')
    await act(async () => { resolveOld?.(history([item(0, 'stale-foreign')])) })
    expect(screen.queryByText('stale-foreign')).not.toBeInTheDocument()
    expect(screen.getByText('run-beta-only')).toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(3)
  })

  it('fails closed for foreign, duplicated or inconsistent history and permits GET retry', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValueOnce(history([item(0)], 'run alpha', 'other-branch'))
      .mockResolvedValueOnce(history([item(1), item(1)]))
      .mockResolvedValueOnce({ ...history(), publication_count: 99 })
      .mockResolvedValueOnce(history())
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neodpovídá zdroji')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Zkusit znovu' }))
    expect(screen.getByRole('alert')).toHaveTextContent('duplicitní')
    await user.click(screen.getByRole('button', { name: 'Zkusit znovu' }))
    expect(screen.getByRole('alert')).toHaveTextContent('neplatné')
    await user.click(screen.getByRole('button', { name: 'Zkusit znovu' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(4)
  })

  it('filters all returned rows before paging, sorts by ordinal and resets first/last page', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValue(history(
      Array.from({ length: 70 }, (_, i) => item(i, i % 2 ? 'odd' : 'even', i % 2 ? 15 : 20))))
    const user = userEvent.setup()
    mount()
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(26)
    expect(within(table).getAllByRole('link')[0]).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/69')
    await user.selectOptions(screen.getByLabelText('Řazení'), 'oldest')
    expect(within(table).getAllByRole('link')[0]).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/0')
    await user.click(screen.getByRole('button', { name: 'Poslední stránka' }))
    expect(screen.getByText('Zobrazeno 51–70 z 70')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'První stránka' }))
    expect(screen.getByText('Zobrazeno 1–25 z 70')).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '3')
    await user.keyboard('{Enter}')
    expect(screen.getByText('Stránka 3 / 3')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat policy_id nebo ordinal publikace'), 'odd')
    expect(screen.getByText('Zobrazeno 1–25 z 35')).toBeInTheDocument()
    expect(screen.getByText('Stránka 1 / 2')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Sezona'), '1')
    expect(screen.getByText('Zobrazeno 1–5 z 5')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Historické Best N'), '20')
    expect(screen.getByText('Zobrazeno 0–0 z 0')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText('Stránka 1 / 0')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(screen.getByText('Zobrazeno 1–25 z 70')).toBeInTheDocument()
  })

  it('validates keyboard page jump and keeps filters/page when switching language without a GET', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValue(history(Array.from({ length: 60 }, (_, i) => item(i))))
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    const field = screen.getByRole('textbox', { name: 'Přejít na stránku' })
    await user.type(field, '0')
    await user.keyboard('{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('Zadej celé číslo')
    expect(screen.getByText('Stránka 1 / 3')).toBeInTheDocument()
    await user.clear(field)
    await user.type(field, '9000')
    await user.keyboard('{Enter}')
    expect(screen.getByText('Stránka 1 / 3')).toBeInTheDocument()
    await user.clear(field)
    await user.type(field, '2')
    await user.keyboard('{Enter}')
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Historické Best N'), '15')
    await user.click(screen.getByRole('button', { name: 'Další stránka' }))
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Toggle language' }))
    expect(screen.getByRole('table', { name: 'Official Ranking publication history' })).toBeInTheDocument()
    expect(screen.getByText('Page 2 / 3')).toBeInTheDocument()
    expect(screen.getByLabelText('Historical Best N')).toHaveValue('15')
    expect(screen.getByText('Search covers publication metadata only, not players inside snapshots.')).toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(1)
  })

  it('differentiates empty publication history and a failed GET; retries only reading', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValueOnce(history([]))
    const first = mount()
    expect(await screen.findByText('Pro tuto Viewer Branch zatím nejsou publikovány žádné Official Rankingy.')).toBeInTheDocument()
    expect(screen.queryByText('Stránka 1 / 0')).not.toBeInTheDocument()
    first.unmount()
    api.listViewerOfficialRankingHistory.mockReset()
    api.listViewerOfficialRankingHistory.mockRejectedValueOnce(new Error('network offline')).mockResolvedValueOnce(history())
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('network offline')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Zkusit znovu' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(2)
  })
})

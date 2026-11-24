import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
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
vi.mock('../../../api/client', () => ({ ...api, ApiError: class ApiError extends Error {} }))
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
function item(ordinal: number, policy: string, best = 15, count = 2) {
  return {
    season_index: Math.floor(ordinal / 61), week: ordinal % 61 + 1,
    week_ordinal: ordinal, snapshot_fingerprint: 'a'.repeat(64),
    policy_id: policy, best_n: best, row_count: count
  }
}
const rows = [
  item(62, 'late-B', 20), item(61, 'late-A', 20),
  item(1, 'early', 15), item(0, 'first', 15)
]
function history(
  publications = rows,
  run = 'run alpha', branch = 'branch-a'
) {
  return {
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: run, viewer_branch_id: branch,
    public_head_ordinal: Math.max(0, ...publications.map(row => row.week_ordinal)),
    publication_count: publications.length, publications
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
function mount(url = '/viewer/runs/run%20alpha/rankings/history?keep=one&keep=two') {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[url]}>
          <LanguageProvider>
            <Navigation />
            <ViewerOfficialRankingHistoryPage />
          </LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}
function query(): URLSearchParams {
  const output = screen.getByLabelText('Current URL').textContent ?? ''
  return new URLSearchParams(output.split('?')[1] ?? '')
}

describe('Viewer Official Ranking URL filters (mocked GET, not HTTP/SQLite)', () => {
  beforeEach(() => {
    localStorage.clear()
    route.current = scope('run alpha', 'branch-a')
    api.listViewerOfficialRankingHistory.mockReset()
    api.listViewerOfficialRankingHistory.mockResolvedValue(history())
  })

  it('restores a precise filtered historical view from a direct URL and retains exact publication links', async () => {
    mount('/viewer/runs/run%20alpha/rankings/history?keep=one&keep=two&rhSeason=1&rhBestN=20&rhSearch=late&rhOrder=oldest')
    const table = await screen.findByRole('table', { name: 'Historie publikací Official Rankingu' })
    expect(screen.getByLabelText('Sezona')).toHaveValue('1')
    expect(screen.getByLabelText('Historické Best N')).toHaveValue('20')
    expect(screen.getByLabelText('Hledat policy_id nebo ordinal publikace')).toHaveValue('late')
    expect(screen.getByLabelText('Řazení')).toHaveValue('oldest')
    const links = within(table).getAllByRole('link')
    expect(links).toHaveLength(2)
    expect(links[0]).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/61')
    expect(links[1]).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/62')
    expect(query().getAll('keep')).toEqual(['one', 'two'])
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('uses push for select filters, replace for typing and restores Back/Forward without a history entry per keystroke', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Sezona'), '1')
    expect(query().get('rhSeason')).toBe('1')
    await user.type(screen.getByLabelText('Hledat policy_id nebo ordinal publikace'), 'late')
    expect(query().get('rhSearch')).toBe('late')
    expect(screen.getByText('Zobrazeno 1–2 z 2')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(query().get('rhSeason')).toBe(null)
    expect(query().get('rhSearch')).toBe(null)
    expect(screen.getByLabelText('Sezona')).toHaveValue('')
    expect(screen.getByLabelText('Hledat policy_id nebo ordinal publikace')).toHaveValue('')
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByLabelText('Sezona')).toHaveValue('1')
    expect(screen.getByLabelText('Hledat policy_id nebo ordinal publikace')).toHaveValue('late')

    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect([...query().keys()]).toEqual(['keep', 'keep'])
    expect(query().getAll('keep')).toEqual(['one', 'two'])
    expect(screen.getByText('Zobrazeno 1–4 z 4')).toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(1)
  })

  it('does not silently accept malformed, unavailable, or unknown filters', async () => {
    const user = userEvent.setup()
    mount('/viewer/runs/run%20alpha/rankings/history?unrelated=yes&rhSeason=3abc&rhBestN=null&rhOrder=sideways')
    await screen.findByText('Žádné publikace neodpovídají zvoleným filtrům.')
    expect(screen.getByRole('alert')).toHaveTextContent('neplatný nebo nedostupný filtr')
    expect(screen.getByLabelText('Sezona')).toHaveValue('3abc')
    expect(screen.getByLabelText('Historické Best N')).toHaveValue('null')
    expect(screen.getByLabelText('Řazení')).toHaveValue('sideways')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(query().toString()).toBe('unrelated=yes')
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('clears own URL filters on Viewer Branch/Run change without opening a Run or rendering the prior source', async () => {
    const user = userEvent.setup()
    api.listViewerOfficialRankingHistory.mockImplementation((runId: string) => {
      if (runId === 'run beta') return Promise.resolve(history([item(0, 'run-beta')], 'run beta', 'branch-c'))
      if (route.current.officialBranchId === 'branch-b') return Promise.resolve(history([item(0, 'branch-b')], 'run alpha', 'branch-b'))
      return Promise.resolve(history())
    })
    const view = mount('/viewer/runs/run%20alpha/rankings/history?tracking=yes&rhSeason=1&rhSearch=late')
    expect(await screen.findByText('late-A')).toBeInTheDocument()
    route.current = scope('run alpha', 'branch-b')
    view.refresh()
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await waitFor(() => {
      expect(query().get('rhSeason')).toBe(null)
      expect(query().get('rhSearch')).toBe(null)
    })
    expect(query().get('tracking')).toBe('yes')
    expect(screen.queryByText('late-A')).not.toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Sezona'), '0')
    expect(query().get('rhSeason')).toBe('0')
    route.current = scope('run beta', 'branch-c')
    await act(async () => { view.refresh() })
    expect(await screen.findByText('run-beta')).toBeInTheDocument()
    await waitFor(() => expect(query().get('rhSeason')).toBe(null))
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(3)
    expectNoForbiddenViewerActions()
  })

  it('restores the same URL after remount without mutating Saved state', async () => {
    const url = '/viewer/runs/run%20alpha/rankings/history?rhSeason=0&rhBestN=15&rhOrder=oldest&rhSearch=early'
    const first = mount(url)
    expect(await screen.findByText('early')).toBeInTheDocument()
    first.unmount()
    mount(url)
    expect(await screen.findByText('early')).toBeInTheDocument()
    expect(screen.getByLabelText('Řazení')).toHaveValue('oldest')
    expectNoForbiddenViewerActions()
  })
})

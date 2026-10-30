import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { clearViewerActiveProductRunId, writeViewerActiveProductRunId } from '../../../viewer/activeProductRun'
import { ViewerRankingsPage } from './ViewerRankingsPage'

const api = vi.hoisted(() => ({
  getViewerOfficialRunContext: vi.fn(),
  getViewerOfficialRanking: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../../../api/client', () => api)

function makeContext(run = 'run alpha', branch = 'viewer-a') {
  return {
    product_run_id: run,
    official_branch_id: branch
  }
}
function makeRanking(run = 'run alpha', branch = 'viewer-a', count = 2) {
  return {
    schema_version: 'viewer_official_ranking.v1',
    product_run_id: run, viewer_branch_id: branch,
    season_index: 3, week: 14, week_ordinal: 196,
    snapshot_fingerprint: 'a'.repeat(64),
    policy_id: 'historical-policy', best_n: 12,
    row_count: count,
    rows: Array.from({ length: count }, (_, i) => ({
      rank: i + 1,
      player_id: i === 0 ? 'player one' : 'player-' + (i + 1),
      points: 2000 - i * 10
    }))
  }
}

function ToggleLanguage(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Toggle language</button>
}
function mount(): { client: QueryClient } {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LanguageProvider><ToggleLanguage /><ViewerRankingsPage /></LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { client }
}

describe('Viewer top-level current Official Ranking (mocked GET API; not HTTP/SQLite/browser integration)', () => {
  beforeEach(() => {
    localStorage.clear()
    clearViewerActiveProductRunId()
    api.getViewerOfficialRunContext.mockReset()
    api.getViewerOfficialRanking.mockReset()
    api.getViewerOfficialRunContext.mockResolvedValue(makeContext())
    api.getViewerOfficialRanking.mockResolvedValue(makeRanking())
  })

  it('does not call either GET without a selected Product Run', () => {
    mount()
    expect(screen.getByRole('heading', { name: 'MSA žebříčky' })).toBeInTheDocument()
    expect(screen.getByText(/Není vybrán žádný Product Run/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít Product Runy' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerOfficialRunContext).not.toHaveBeenCalled()
    expect(api.getViewerOfficialRanking).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows historically sourced CS Top 10, preserves zero points and exact links without invented fields', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerOfficialRanking.mockResolvedValue({
      ...makeRanking(),
      rows: [
        { rank: 1, player_id: 'player one', points: 100 },
        { rank: 2, player_id: 'player-2', points: 0 }
      ]
    })
    mount()
    const table = await screen.findByRole('table', { name: 'První desítka Official Rankingu' })
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledWith('run alpha')
    expect(api.getViewerOfficialRanking).toHaveBeenCalledWith('run alpha')
    expect(screen.getByText('2003/04')).toBeInTheDocument()
    expect(screen.getByText('historical-policy')).toBeInTheDocument()
    expect(screen.getByText('viewer-a')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(within(table).getByRole('link', { name: 'player one' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player%20one/career')
    expect(within(table).getByText('0')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít tento publikovaný snapshot' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/196')
    expect(screen.getByRole('link', { name: 'Otevřít úplnou historii publikací' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings')
    expect(screen.getByText(/API neposkytuje jména/)).toBeInTheDocument()
    expect(screen.queryByText('Movement')).not.toBeInTheDocument()
    expect(screen.queryByText('Country')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows an exactly empty ranking rather than a missing payload', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerOfficialRanking.mockResolvedValue(makeRanking('run alpha', 'viewer-a', 0))
    mount()
    expect(await screen.findByText('Publikovaný ranking obsahuje přesně 0 hráčů.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít tento publikovaný snapshot' })).toBeInTheDocument()
  })

  it('never fetches a ranking for mismatched context and retries only GET', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerOfficialRunContext.mockResolvedValueOnce(makeContext('foreign', 'viewer-a'))
      .mockResolvedValueOnce(makeContext())
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neodpovídá zvolenému Product Runu')
    expect(api.getViewerOfficialRanking).not.toHaveBeenCalled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Opakovat pouze čtení' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledTimes(2)
    expect(api.getViewerOfficialRanking).toHaveBeenCalledTimes(1)
  })

  it('rejects foreign or corrupt ranking and permits safe GET retry', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerOfficialRanking
      .mockResolvedValueOnce(makeRanking('run alpha', 'other-branch'))
      .mockResolvedValueOnce({ ...makeRanking(), row_count: 300 })
      .mockResolvedValueOnce(makeRanking())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatné důkazy')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Opakovat pouze čtení' }))
    expect(screen.getByRole('alert')).toHaveTextContent('neplatné důkazy')
    await user.click(screen.getByRole('button', { name: 'Opakovat pouze čtení' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRanking).toHaveBeenCalledTimes(3)
  })

  it('isolates delayed old-run response after active Product Run change', async () => {
    let deliverOld: ((ranking: ReturnType<typeof makeRanking>) => void) | undefined
    api.getViewerOfficialRunContext.mockImplementation((run: string) => Promise.resolve(makeContext(run, 'viewer-a')))
    api.getViewerOfficialRanking
      .mockImplementationOnce(() => new Promise(resolve => { deliverOld = resolve }))
      .mockResolvedValueOnce(makeRanking('run beta', 'viewer-a', 1))
    writeViewerActiveProductRunId('run alpha')
    mount()
    await waitFor(() => expect(api.getViewerOfficialRanking).toHaveBeenCalledTimes(1))
    act(() => writeViewerActiveProductRunId('run beta'))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.getByText('run beta')).toBeInTheDocument()
    await act(async () => { deliverOld?.(makeRanking('run alpha', 'viewer-a', 2)) })
    expect(screen.queryByText('run alpha')).not.toBeInTheDocument()
    expect(screen.getByText('run beta')).toBeInTheDocument()
    expect(api.getViewerOfficialRanking).toHaveBeenCalledTimes(2)
  })

  it('changes Viewer Branch without rendering prior cached publication', async () => {
    writeViewerActiveProductRunId('run alpha')
    const { client } = mount()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    api.getViewerOfficialRunContext.mockResolvedValue(makeContext('run alpha', 'viewer-b'))
    api.getViewerOfficialRanking.mockResolvedValue(makeRanking('run alpha', 'viewer-b', 1))
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['viewer-current-official-context', 'run alpha'] })
    })
    expect(await screen.findByText('viewer-b')).toBeInTheDocument()
    expect(api.getViewerOfficialRanking).toHaveBeenCalledTimes(2)
    expect(screen.queryByText('viewer-a')).not.toBeInTheDocument()
  })

  it('retains the same source and GET count when switching CS/EN', async () => {
    writeViewerActiveProductRunId('run alpha')
    mount()
    await screen.findByRole('table')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Toggle language' }))
    expect(screen.getByRole('table', { name: 'Current Official Ranking Top 10' })).toBeInTheDocument()
    expect(screen.getByText('Current Official Ranking')).toBeInTheDocument()
    expect(screen.getByText(/API does not supply names/)).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledTimes(1)
    expect(api.getViewerOfficialRanking).toHaveBeenCalledTimes(1)
  })

  it('distinguishes a failed context GET and failed ranking GET', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerOfficialRunContext.mockRejectedValueOnce(new Error('context unavailable'))
      .mockResolvedValueOnce(makeContext())
    api.getViewerOfficialRanking.mockRejectedValueOnce(new Error('ranking unavailable'))
      .mockResolvedValueOnce(makeRanking())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('context unavailable')
    expect(api.getViewerOfficialRanking).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Opakovat pouze čtení' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('ranking unavailable')
    await user.click(screen.getByRole('button', { name: 'Opakovat pouze čtení' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRanking).toHaveBeenCalledTimes(2)
  })
})

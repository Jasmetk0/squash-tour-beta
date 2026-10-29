import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { writeViewerActiveProductRunId } from '../../../viewer/activeProductRun'
import { ViewerHistoryPage } from './ViewerHistoryPage'

const api = vi.hoisted(() => ({
  getViewerOfficialRunContext: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../../../api/client', () => api)

const run = 'history run'
const branch = 'branch-history'

function officialContext(runId = run, branchId = branch) {
  return { product_run_id: runId, official_branch_id: branchId }
}
function tournaments(runId = run, branchId = branch) {
  return {
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: runId, viewer_branch_id: branchId,
    tournament_count: 2, published_result_count: 1,
    tournaments: [
      { event_id: 'EVT-2', season: '2032/33', season_week: 12, event_name: 'Future Open',
        ranking_status: 'planned', result_published: false,
        champion_player_id: null, finalist_player_id: null },
      { event_id: 'EVT-1', season: '2032/33', season_week: 11, event_name: 'History Open',
        ranking_status: 'completed', result_published: true,
        champion_player_id: 'P1', finalist_player_id: 'P2' }
    ]
  }
}
function rankings(runId = run, branchId = branch) {
  return {
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: runId, viewer_branch_id: branchId,
    public_head_ordinal: 2000, publication_count: 2,
    publications: [
      { season_index: 32, week: 12, week_ordinal: 1963, snapshot_fingerprint: 'a'.repeat(64), policy_id: 'best-15', best_n: 15, row_count: 64 },
      { season_index: 32, week: 49, week_ordinal: 2000, snapshot_fingerprint: 'b'.repeat(64), policy_id: 'best-15', best_n: 15, row_count: 64 }
    ]
  }
}
function race(runId = run, branchId = branch) {
  return {
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: runId, viewer_branch_id: branchId,
    latest_target_season_index: 32,
    publications: [{
      schema_version: 'viewer_finals_race_publication.v1',
      product_run_id: runId, viewer_branch_id: branchId,
      target_season_index: 32, cutoff_season_index: 32, cutoff_week: 55,
      best_n: 9, selection_published: false, finals_event_id: null, rows: []
    }]
  }
}

function ToggleLanguage() {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Toggle language</button>
}
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const result = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LanguageProvider><ToggleLanguage /><ViewerHistoryPage /></LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { ...result, client }
}

describe('ViewerHistoryPage source-safe canonical publication hub (mocked GET only)', () => {
  beforeEach(() => {
    localStorage.clear()
    api.getViewerOfficialRunContext.mockReset().mockResolvedValue(officialContext())
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(tournaments())
    api.listViewerOfficialRankingHistory.mockReset().mockResolvedValue(rankings())
    api.getViewerFinalsRace.mockReset().mockResolvedValue(race())
  })

  it('does not call any read endpoint without a selected Product Run', () => {
    mount()
    expect(screen.getByRole('heading', { name: 'Historie' })).toBeInTheDocument()
    expect(screen.getByText(/Není vybraný žádný Product Run/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vybrat Product Run' })).toHaveAttribute('href', '/viewer/runs')
    for (const fn of [api.getViewerOfficialRunContext, api.getViewerTournamentHistory,
      api.listViewerOfficialRankingHistory, api.getViewerFinalsRace]) {
      expect(fn).not.toHaveBeenCalled()
    }
    expectNoForbiddenViewerActions()
  })

  it('shows verified counts and links only to actual published latest evidence', async () => {
    writeViewerActiveProductRunId(run)
    mount()
    await screen.findByText(branch)
    const summary = screen.getByRole('article', { name: 'Publikovaná historie' })
    expect(summary).toHaveTextContent(branch)
    expect(within(summary).getByText('Turnaje v kalendáři')).toBeInTheDocument()
    expect(summary).toHaveTextContent('Publikované Official Rankingy')
    expect(summary).toHaveTextContent('Publikované výsledky turnajů')
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledWith(run)
    for (const fn of [api.getViewerTournamentHistory, api.listViewerOfficialRankingHistory, api.getViewerFinalsRace]) {
      expect(fn).toHaveBeenCalledWith(run)
    }
    expect(screen.getByRole('link', { name: /History Open/ })).toHaveAttribute('href', '/viewer/runs/history%20run/calendar/EVT-1')
    expect(screen.queryByRole('link', { name: /Future Open/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /2032\/33 · W49/ })).toHaveAttribute('href', '/viewer/runs/history%20run/rankings/2000')
    expect(screen.getByRole('link', { name: '2032/33' })).toHaveAttribute('href', '/viewer/runs/history%20run/race')
    expect(screen.getByRole('link', { name: 'Historie vybraného Runu' })).toHaveAttribute('href', '/viewer/runs/history%20run/history')
    expect(screen.getByRole('link', { name: 'Historie rankingů' })).toHaveAttribute('href', '/viewer/runs/history%20run/rankings')
    expectNoForbiddenViewerActions()
  })

  it('fails closed on one unavailable GET, without leaking the other two sources', async () => {
    writeViewerActiveProductRunId(run)
    api.listViewerOfficialRankingHistory.mockRejectedValueOnce(new Error('secret internal incident'))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('není dostupných')
    expect(screen.queryByText(branch)).not.toBeInTheDocument()
    expect(screen.queryByText('secret internal incident')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (pouze GET)' }))
    expect(await screen.findByRole('article', { name: 'Publikovaná historie' })).toBeInTheDocument()
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(2)
    expectNoForbiddenViewerActions()
  })

  it('rejects a foreign Viewer Branch even when all requests succeed', async () => {
    writeViewerActiveProductRunId(run)
    api.getViewerFinalsRace.mockResolvedValueOnce(race(run, 'foreign'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Zdroje historie si neodpovídají')
    expect(screen.queryByText(branch)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /History Open/ })).not.toBeInTheDocument()
  })

  it('does not request history when context scope is invalid, and retries the GET context', async () => {
    writeViewerActiveProductRunId(run)
    api.getViewerOfficialRunContext.mockResolvedValueOnce(officialContext('different', branch))
      .mockResolvedValueOnce(officialContext())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Kontext neodpovídá')
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (pouze GET)' }))
    expect(await screen.findByRole('article', { name: 'Publikovaná historie' })).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledTimes(2)
  })

  it('shows distinct valid no-publication state without inventing latest record links', async () => {
    writeViewerActiveProductRunId(run)
    api.getViewerTournamentHistory.mockResolvedValue({
      ...tournaments(), tournament_count: 0, published_result_count: 0, tournaments: []
    })
    api.listViewerOfficialRankingHistory.mockResolvedValue({
      ...rankings(), public_head_ordinal: 0, publication_count: 0, publications: []
    })
    api.getViewerFinalsRace.mockResolvedValue({
      ...race(), latest_target_season_index: null, publications: []
    })
    mount()
    expect(await screen.findByText(/zatím nejsou publikované sportovní výsledky/)).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Poslední publikované záznamy' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Turnaje' })).toBeInTheDocument()
  })

  it('switches CS/EN without new data requests or source reinterpretation', async () => {
    writeViewerActiveProductRunId(run)
    const user = userEvent.setup()
    mount()
    await screen.findByRole('article', { name: 'Publikovaná historie' })
    await user.click(screen.getByRole('button', { name: 'Toggle language' }))
    expect(screen.getByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(screen.getByRole('article', { name: 'Published history' })).toHaveTextContent(branch)
    expect(screen.getByRole('link', { name: 'Ranking history' })).toHaveAttribute('href', '/viewer/runs/history%20run/rankings')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledTimes(1)
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(1)
  })

  it('fences a late reply after active Run changes, and never shows stale history', async () => {
    let finishOld: ((data: ReturnType<typeof tournaments>) => void) | undefined
    api.getViewerOfficialRunContext.mockImplementation((id: string) => Promise.resolve(officialContext(id)))
    api.getViewerTournamentHistory.mockImplementationOnce(() => new Promise(resolve => { finishOld = resolve }))
      .mockResolvedValueOnce(tournaments('new run'))
    api.listViewerOfficialRankingHistory.mockImplementation((id: string) => Promise.resolve(rankings(id)))
    api.getViewerFinalsRace.mockImplementation((id: string) => Promise.resolve(race(id)))
    writeViewerActiveProductRunId(run)
    mount()
    await waitFor(() => expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1))
    act(() => writeViewerActiveProductRunId('new run'))
    await screen.findByText('new run')
    expect(screen.getByRole('article', { name: 'Publikovaná historie' })).toHaveTextContent('new run')
    await act(async () => { finishOld?.(tournaments()) })
    expect(screen.getByRole('article', { name: 'Publikovaná historie' })).toHaveTextContent('new run')
    expect(screen.queryByText(run)).not.toBeInTheDocument()
  })

  it('refreshes Branch authority and drops old publication details on Branch change', async () => {
    writeViewerActiveProductRunId(run)
    const { client } = mount()
    await screen.findByText(branch)
    expect(screen.getByRole('article', { name: 'Publikovaná historie' })).toHaveTextContent(branch)
    api.getViewerOfficialRunContext.mockResolvedValue(officialContext(run, 'branch-two'))
    api.getViewerTournamentHistory.mockResolvedValue(tournaments(run, 'branch-two'))
    api.listViewerOfficialRankingHistory.mockResolvedValue(rankings(run, 'branch-two'))
    api.getViewerFinalsRace.mockResolvedValue(race(run, 'branch-two'))
    await act(async () => { await client.invalidateQueries({ queryKey: ['viewer-official-run-context', run] }) })
    await screen.findByText('branch-two')
    expect(screen.getByRole('article', { name: 'Publikovaná historie' })).toHaveTextContent('branch-two')
    expect(screen.queryByText(branch)).not.toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(2)
  })
})

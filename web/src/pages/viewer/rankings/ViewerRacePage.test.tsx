import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ViewerFinalsRaceHistory, ViewerFinalsRacePublication, ViewerFinalsRaceRow } from '../../../api/types'
import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { expectNoForbiddenViewerActions, makeViewerProductRunRouteTestValue } from '../../../test/viewerTestUtils'
import { writeViewerActiveProductRunId } from '../../../viewer/activeProductRun'
import { ViewerProductRunRouteContextProvider, type ViewerProductRunRouteValue } from '../../../viewer/ViewerProductRunRouteContext'
import { ViewerRacePage, ViewerRunRacePage } from './ViewerRacePage'

const api = vi.hoisted(() => ({
  getViewerOfficialRunContext: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../../../api/client', () => api)

function makeRow(rank: number, season = 4): ViewerFinalsRaceRow {
  const id = 'player-' + String(rank).padStart(3, '0')
  const points = 2000 - rank
  return {
    rank, player_id: id, race_points: points,
    tournaments_counted: 1,
    finals_selected: null, finals_seed: null, qualification_source: null,
    counted_results: [{ event_id: 'event-' + id, completed_season_index: season, completed_week: 10, race_points: points }]
  }
}
function makePublication(season = 4, count = 3, branch = 'viewer-a', run = 'run alpha'): ViewerFinalsRacePublication {
  return {
    schema_version: 'viewer_finals_race_publication.v1',
    product_run_id: run, viewer_branch_id: branch,
    target_season_index: season, cutoff_season_index: season, cutoff_week: 55,
    best_n: 10, selection_published: false, finals_event_id: null,
    rows: Array.from({ length: count }, (_, index) => makeRow(index + 1, season))
  }
}
function makeHistory(publications = [makePublication()], run = 'run alpha', branch = 'viewer-a'): ViewerFinalsRaceHistory {
  return {
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: run, viewer_branch_id: branch,
    latest_target_season_index: publications.length ? Math.max(...publications.map(p => p.target_season_index)) : null,
    publications
  }
}
function makeContext(run = 'run alpha', branch = 'viewer-a') {
  return { product_run_id: run, official_branch_id: branch }
}
function ChangeLanguage(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function mount(mode: 'top' | 'run' = 'top', scoped?: ViewerProductRunRouteValue) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const context = scoped ?? {
    ...makeViewerProductRunRouteTestValue('run alpha'),
    officialBranchId: 'viewer-a',
    officialContext: makeContext() as ViewerProductRunRouteValue['officialContext']
  }
  function App(): JSX.Element {
    const element = mode === 'top' ? <ViewerRacePage /> : (
      <ViewerProductRunRouteContextProvider value={context}><ViewerRunRacePage /></ViewerProductRunRouteContextProvider>
    )
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/viewer/runs/run%20alpha/race']}>
          <LanguageProvider><ChangeLanguage />{element}</LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  return { ...render(<App />), client }
}

describe('canonical Viewer Race browsing (mocked API, not real HTTP/SQLite/Chromium)', () => {
  beforeEach(() => {
    localStorage.clear()
    api.getViewerOfficialRunContext.mockReset()
    api.getViewerFinalsRace.mockReset()
    api.getViewerOfficialRunContext.mockResolvedValue(makeContext())
    api.getViewerFinalsRace.mockResolvedValue(makeHistory())
  })

  it('requires a selected Product Run and does not call either GET when missing', () => {
    mount()
    expect(screen.getByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(screen.getByText(/Nejprve vyber Product Run/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít seznam Runů' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerOfficialRunContext).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows actual counted results, selected vs pending, encoded player link and season navigation', async () => {
    writeViewerActiveProductRunId('run alpha')
    const selected = makePublication()
    selected.selection_published = true
    selected.finals_event_id = 'FINALS-2004'
    selected.rows[0].finals_selected = true
    selected.rows[0].finals_seed = 1
    selected.rows[0].qualification_source = 'race'
    selected.rows[1].finals_selected = true
    selected.rows[1].finals_seed = 2
    selected.rows[1].qualification_source = 'direct_entry'
    selected.rows[2].finals_selected = false
    api.getViewerFinalsRace.mockResolvedValue(makeHistory([selected]))
    mount()
    const table = await screen.findByRole('table', { name: 'Uložené pořadí Race' })
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run alpha')
    expect(within(table).getByText('Kvalifikace z Race · nasazení 1')).toBeInTheDocument()
    expect(within(table).getByText('Přímý vstup · nasazení 2')).toBeInTheDocument()
    expect(within(table).getByText('Nevybrán')).toBeInTheDocument()
    expect(within(table).getByText(/event-player-001: 1999 \(2004\/05 · W10\)/)).toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'player-001' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player-001/career')
    expect(screen.getByRole('link', { name: 'Otevřít Race v Runu' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
    expectNoForbiddenViewerActions()
  })

  it('selects newest season from unordered saved history and switches to earlier season without GET', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerFinalsRace.mockResolvedValue(makeHistory([
      makePublication(2, 1), makePublication(5, 2), makePublication(4, 3)
    ]))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('heading', { name: 'Zvolená publikace: 2005/06' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Historie sezónních publikací' })).toHaveTextContent('2002/03')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Cílová sezona' }), '2')
    expect(screen.getByRole('heading', { name: 'Zvolená publikace: 2002/03' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(1)
    await user.click(within(screen.getByRole('list', { name: 'Historie sezónních publikací' })).getByRole('button', { name: '2004/05' }))
    expect(screen.getByRole('heading', { name: 'Zvolená publikace: 2004/05' })).toBeInTheDocument()
  })

  it('filters before 50-row pagination, handles bounded jumps, and preserves original ranks', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerFinalsRace.mockResolvedValue(makeHistory([makePublication(4, 120)]))
    const user = userEvent.setup()
    mount()
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    expect(screen.getByText('Zobrazeno 1–50 z 120')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Poslední' }))
    expect(screen.getByText('Zobrazeno 101–120 z 120')).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '4')
    await user.keyboard('{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('existující celé číslo')
    await user.clear(screen.getByRole('textbox', { name: 'Přejít na stránku' }))
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '2')
    await user.keyboard('{Enter}')
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    await user.type(screen.getByRole('searchbox', { name: 'Hledat ID hráče' }), 'PLAYER-11')
    expect(screen.getByText('Zobrazeno 1–10 z 10')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByRole('link', { name: 'player-119' })).toBeInTheDocument()
    await user.clear(screen.getByRole('searchbox', { name: 'Hledat ID hráče' }))
    await user.type(screen.getByRole('searchbox', { name: 'Hledat ID hráče' }), 'unknown')
    expect(screen.getByText(/Hledání neodpovídá žádnému hráči/)).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 0–0 z 0')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat hledání' }))
    expect(screen.getByText('Zobrazeno 1–50 z 120')).toBeInTheDocument()
  })

  it('distinguishes no publication, zero players, invalid payload and GET failure', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerFinalsRace.mockResolvedValue(makeHistory([]))
    const first = mount()
    expect(await screen.findByText(/zatím není žádná publikovaná Race/)).toBeInTheDocument()
    first.unmount()

    api.getViewerFinalsRace.mockResolvedValue(makeHistory([makePublication(4, 0)]))
    const second = mount()
    expect(await screen.findByText(/Tato publikace obsahuje nula hráčů/)).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    second.unmount()

    api.getViewerFinalsRace.mockResolvedValueOnce(makeHistory([makePublication(4)], 'run alpha', 'foreign'))
      .mockRejectedValueOnce(new Error('race unavailable'))
      .mockResolvedValueOnce(makeHistory())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('cizí nebo neplatná data')
    await user.click(screen.getByRole('button', { name: 'Zkusit načíst znovu' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('race unavailable')
    await user.click(screen.getByRole('button', { name: 'Zkusit načíst znovu' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
  })

  it('does not show an outdated publication after a new Viewer Branch selection', async () => {
    writeViewerActiveProductRunId('run alpha')
    const { client } = mount()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    api.getViewerOfficialRunContext.mockResolvedValue(makeContext('run alpha', 'viewer-b'))
    api.getViewerFinalsRace.mockResolvedValue(makeHistory([makePublication(4, 1, 'viewer-b')], 'run alpha', 'viewer-b'))
    await act(async () => { await client.invalidateQueries({ queryKey: ['viewer-official-run-context', 'run alpha'] }) })
    expect(await screen.findByText('viewer-b')).toBeInTheDocument()
    expect(screen.queryByText('viewer-a')).not.toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(2)
  })

  it('does not leak a delayed response from the previous Product Run', async () => {
    let oldReply: ((value: ViewerFinalsRaceHistory) => void) | undefined
    api.getViewerOfficialRunContext.mockImplementation((run: string) => Promise.resolve(makeContext(run, 'viewer-a')))
    api.getViewerFinalsRace.mockImplementationOnce(() => new Promise(resolve => { oldReply = resolve }))
      .mockResolvedValueOnce(makeHistory([makePublication(4, 1, 'viewer-a', 'run beta')], 'run beta', 'viewer-a'))
    writeViewerActiveProductRunId('run alpha')
    mount()
    await waitFor(() => expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(1))
    act(() => writeViewerActiveProductRunId('run beta'))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    await act(async () => { oldReply?.(makeHistory()) })
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(2)
  })

  it('keeps selected historical season on CS/EN switch without another GET', async () => {
    writeViewerActiveProductRunId('run alpha')
    api.getViewerFinalsRace.mockResolvedValue(makeHistory([makePublication(3), makePublication(4)]))
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Cílová sezona' }), '3')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('table', { name: 'Saved Race standings' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Selected publication: 2003/04' })).toBeInTheDocument()
    expect(api.getViewerFinalsRace).toHaveBeenCalledTimes(1)
  })

  it('run-scoped view validates the authoritative route context and never uses legacy Race', async () => {
    const context = {
      ...makeViewerProductRunRouteTestValue('run alpha'),
      officialBranchId: 'viewer-a',
      officialContext: makeContext() as ViewerProductRunRouteValue['officialContext']
    }
    mount('run', context)
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run alpha')
    expect(screen.queryByRole('link', { name: 'Otevřít Race v Runu' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('suppresses run-scoped GET if context is stale or Branch identity mismatches', () => {
    const context = {
      ...makeViewerProductRunRouteTestValue('run alpha'),
      officialBranchId: 'viewer-b',
      officialContext: makeContext() as ViewerProductRunRouteValue['officialContext']
    }
    mount('run', context)
    expect(screen.getByRole('alert')).toHaveTextContent('neodpovídá zvolenému Runu')
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
  })
})

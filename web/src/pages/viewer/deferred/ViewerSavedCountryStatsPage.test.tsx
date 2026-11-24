import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerStatsDeferredPage } from './ViewerStatsDeferredPage'

const api = vi.hoisted(() => ({ getViewerCountries: vi.fn() }))
const active = vi.hoisted(() => ({
  run: 'run alpha' as string | null,
  branch: 'branch-a', foreign: false,
}))
vi.mock('../../../api/client', () => ({
  ...api, ApiError: class ApiError extends Error {},
}))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => active.run,
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: {
      product_run_id: active.foreign ? 'foreign' : run,
      official_branch_id: active.branch,
    },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

function country(
  code: string, activeCount: number, retiredCount: number,
  avg: number | null = null, topName: string | null = null,
) {
  return {
    country_code: code,
    player_count: activeCount + retiredCount,
    active_player_count: activeCount,
    retired_player_count: retiredCount,
    average_current_ovr: avg,
    top_player_id: topName ? 'player-' + code.toLowerCase() : null,
    top_player_name: topName,
    top_player_current_ovr: topName ? 184 : null,
  }
}
type Country = ReturnType<typeof country>
const examples = [
  country('CZE', 3, 2, 143.5, 'Czech Ace'),
  country('EGY', 5, 1, 163.0, 'Egypt Ace'),
  country('NZL', 0, 2, null, null),
  country('AUS', 0, 0, null, null),
]
function source(
  countries: Country[] = examples, run = active.run ?? '', branch = active.branch,
) {
  return {
    schema_version: 'viewer_countries.v1',
    product_run_id: run,
    viewer_branch_id: branch,
    season_index: 6, week: 19,
    country_count: countries.length, countries,
  }
}
function SwitchLanguage(): JSX.Element {
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
        <SwitchLanguage />
        <ViewerStatsDeferredPage kind="country-stats" />
      </LanguageProvider></MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}
function table() {
  return screen.getByRole('table', { name: 'Veřejné statistiky zemí' })
}

describe('Country Stats from the verified Saved public countries snapshot (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    active.run = 'run alpha'; active.branch = 'branch-a'; active.foreign = false
    api.getViewerCountries.mockReset().mockImplementation((run: string) =>
      Promise.resolve(source(examples, run, active.branch)))
  })

  it('never calls public country GET without an explicitly selected Product Run', () => {
    active.run = null
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Seznam Runů' }))
      .toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerCountries).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('blocks requests under an invalid or foreign Product Run context', () => {
    active.foreign = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('Nelze ověřit Viewer Branch')
    expect(api.getViewerCountries).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('uses actual country counts, source-clock, percent of active players, and exact public links', async () => {
    mount()
    const t = await screen.findByRole('table', { name: 'Veřejné statistiky zemí' })
    expect(within(t).getAllByRole('row')).toHaveLength(5)
    const cze = within(t).getByRole('row', { name: /CZE/ })
    const cells = within(cze).getAllByRole('cell')
    expect(cells[1]).toHaveTextContent('5')
    expect(cells[2]).toHaveTextContent('3')
    expect(cells[3]).toHaveTextContent('2')
    expect(cells[4]).toHaveTextContent('60%')
    expect(cells[5]).toHaveTextContent('143.5')
    expect(within(cze).getByRole('link', { name: 'CZE' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/CZE')
    expect(within(cze).getByRole('link', { name: 'Czech Ace' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player-cze/career')
    const empty = within(t).getByRole('row', { name: /AUS/ })
    expect(within(empty).getAllByRole('cell')[4]).toHaveTextContent('—')
    expect(within(empty).getAllByRole('cell')[5]).toHaveTextContent('—')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText('6 · W19')).toBeInTheDocument()
    expect(screen.getByText(/Nejde o oficiální Country Ranking/)).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('shows source-wide, unfiltered exact totals without fabricating a global average OVR', async () => {
    mount()
    await screen.findByRole('table')
    const metadata = screen.getByText('Hráčů ve zdroji').closest('div')
    expect(metadata).toHaveTextContent('13')
    expect(screen.getByText('Aktivních hráčů').closest('div')).toHaveTextContent('8')
    expect(screen.getByText('Hráčů po kariéře').closest('div')).toHaveTextContent('5')
    expect(screen.queryByText('Global average OVR')).not.toBeInTheDocument()
  })

  it('filters by public country/top-player text and active/retired counts without refetching', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Zobrazit země'), 'active')
    expect(within(table()).getAllByRole('row')).toHaveLength(3)
    await user.selectOptions(screen.getByLabelText('Zobrazit země'), 'retired')
    expect(within(table()).getAllByRole('row')).toHaveLength(4)
    await user.type(screen.getByLabelText('Hledat kód země nebo veřejného hráče'), 'Czech Ace')
    expect(within(table()).getAllByRole('row')).toHaveLength(2)
    expect(within(table()).getByRole('link', { name: 'CZE' })).toBeInTheDocument()
    await user.clear(screen.getByLabelText('Hledat kód země nebo veřejného hráče'))
    await user.type(screen.getByLabelText('Hledat kód země nebo veřejného hráče'), 'not-here')
    expect(screen.getByText('Filtrům neodpovídá žádná země.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(within(table()).getAllByRole('row')).toHaveLength(5)
    expect(api.getViewerCountries).toHaveBeenCalledTimes(1)
  })

  it('sorts by source counts and nullable public OVR with unknown values at the end', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    expect(within(table()).getAllByRole('row')[1]).toHaveTextContent('EGY')
    await user.selectOptions(screen.getByLabelText('Seřadit podle'), 'code')
    expect(within(table()).getAllByRole('row')[1]).toHaveTextContent('AUS')
    await user.selectOptions(screen.getByLabelText('Seřadit podle'), 'ovr')
    const rows = within(table()).getAllByRole('row')
    expect(rows[1]).toHaveTextContent('EGY')
    expect(rows[2]).toHaveTextContent('CZE')
    expect(rows[3]).toHaveTextContent('AUS')
    expect(rows[4]).toHaveTextContent('NZL')
  })

  it('keeps a genuinely empty Saved country source distinct from missing data', async () => {
    api.getViewerCountries.mockReset().mockResolvedValue(source([]))
    mount()
    expect(await screen.findByText('Ve zdroji zatím nejsou žádné země.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('fails closed for cross-branch, impossible counts, duplicate country and leaked private data; retry uses GET', async () => {
    const user = userEvent.setup()
    const valid = source()
    api.getViewerCountries.mockReset()
      .mockResolvedValueOnce(source(examples, 'run alpha', 'wrong-branch'))
      .mockResolvedValueOnce({
        ...valid, countries: [{ ...examples[0], active_player_count: 99 }, ...examples.slice(1)],
      })
      .mockResolvedValueOnce(source([examples[0], examples[0]]))
      .mockResolvedValueOnce({
        ...valid, countries: [{ ...examples[0], private_potential: 199 }, ...examples.slice(1)],
      })
      .mockResolvedValueOnce(valid)
    mount()
    for (let index = 0; index < 4; index++) {
      expect(await screen.findByRole('alert')).toHaveTextContent('neplatná data')
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      expect(screen.queryByText('199')).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    }
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(5)
    expectNoForbiddenViewerActions()
  })

  it('rejects invalid schema, nonfinite OVR and mismatched top-player names', async () => {
    const valid = source()
    api.getViewerCountries.mockReset().mockResolvedValue({
      ...valid, countries: [{ ...examples[0], average_current_ovr: Number.NaN }, ...examples.slice(1)],
    })
    const view = mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná data')
    view.unmount()
    api.getViewerCountries.mockReset().mockResolvedValue({
      ...valid, countries: [{ ...examples[0], top_player_name: null }, ...examples.slice(1)],
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná data')
  })

  it('never renders a delayed old-Branch response inside a newly selected Viewer Branch', async () => {
    let resolveOld: ((value: ReturnType<typeof source>) => void) | undefined
    api.getViewerCountries.mockReset().mockImplementation((run: string) =>
      active.branch === 'branch-a'
        ? new Promise(resolve => { resolveOld = resolve })
        : Promise.resolve(source(examples, run, 'branch-b')))
    const view = mount()
    await waitFor(() => expect(api.getViewerCountries).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    await act(async () => { view.refresh() })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(source(examples, 'run alpha', 'branch-a')) })
    expect(screen.queryByText('branch-a')).not.toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(2)
  })

  it('translates UI while preserving saved names and not making another GET', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { level: 2, name: 'Saved Country Stats' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Public country statistics' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Czech Ace' })).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(1)
  })

  it('paginates 31 saved countries and returns to page 1 after a filter', async () => {
    const many = Array.from({ length: 31 }, (_, i) => country(
      'C' + String.fromCharCode(65 + Math.floor(i / 26)) + String.fromCharCode(65 + i % 26),
      i + 1, 0, null,
    ))
    api.getViewerCountries.mockReset().mockResolvedValue(source(many))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByText('Zobrazeno 1–25 z 31')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(screen.getByText('Zobrazeno 26–31 z 31')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat kód země nebo veřejného hráče'), 'CBE')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'CBE' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it.each([
    { average_current_ovr: 200, top_player_current_ovr: 150 },
    { top_player_id: null, top_player_name: null },
    { average_current_ovr: null },
    { top_player_current_ovr: null },
    { top_player_current_ovr: 199.5 },
  ])('rejects contradictory public OVR summary: %j', async patch => {
    const bad = source()
    api.getViewerCountries.mockReset().mockResolvedValue({
      ...bad, countries: [{ ...bad.countries[0], ...patch }, ...bad.countries.slice(1)],
    })
    mount()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

})

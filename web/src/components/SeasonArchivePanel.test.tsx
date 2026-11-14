import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SeasonArchivePanel } from './SeasonArchivePanel'

// Component contract tests: the API boundary is mocked, not the production HTTP/SQLite stack.
const api = vi.hoisted(() => ({ getSeasonArchive: vi.fn(), getSeasonDetail: vi.fn() }))
vi.mock('../api/client', () => ({
  ...api,
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) { super(message); this.status = status }
  }
}))

const f = 'f'.repeat(64)
const overview = (n = 2) => ({
  completed_edition_count: n, players_with_results: 8, countries_represented: 2, titles_awarded: n,
  turned_pro: ['a', 'b'], retired: [], no_completed_editions: n === 0,
  rankings: { week_w_published_fingerprint: f, season_closing_ranking_available: false, next_season_week_1_fingerprint: f }
})
const season = (i: number, best = 15) => ({
  season_index: i, season_label: `200${i}/0${i + 1}`, boundary_command_id: 'c', source_tour_fingerprint: f,
  rules: { ranking_policy_id: 'p', ranking_best_n: best, development_policy_fingerprint: f, weeks_per_season: 4 },
  overview: overview(), leading_player: { player_id: 'P1', name: 'Alice', country_code: 'CZE', titles: 2, awarded_points: 300 },
  leading_country: { country_code: 'CZE', titles: 2, finals: 1, awarded_points: 300 }
})
const archive = { schema_version: 'native_tour_season_archive.v1', run_id: 'run', branch_id: 'branch',
  saved_head_revision_id: 'rev-1', source_tour_fingerprint: f, seasons: [season(0), season(1, 1)] }
const m = (t: number, p: number) => ({ titles: t, finals: 0, awarded_points: p })
const detail = (comparable: boolean) => ({
  schema_version: 'calendar_tour_season_comparison.v1', run_id: 'run', branch_id: 'branch',
  saved_head_revision_id: 'rev-1', overview: overview(), selected: { season_index: 1 },
  detail: {
    schema_version: 'native_tour_season_comparison_detail.v1', selected_season_index: 1, comparison_season_index: 0,
    selected_overview: overview(), comparison_overview: overview(),
    comparability: { comparable, compared_fields: ['ranking_best_n'], not_compared: ['point_tables'],
      differences: comparable ? [] : [{ field: 'ranking_best_n', selected: 1, comparison: 15 }] },
    countries: [
      { country_code: 'CZE', presence: 'both', selected: m(2, 300), comparison: m(1, 100), delta: m(1, 200) },
      { country_code: 'AUT', presence: 'only_comparison', selected: null, comparison: m(1, 60), delta: null }
    ],
    players: [], note: 'n'
  }
})
function mount(cs = false, resolveName: (id: string) => string = id => (id === 'P1' ? 'Alice' : id)) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<MemoryRouter><QueryClientProvider client={client}>
    <SeasonArchivePanel runId="run" branchId="branch" savedHead="rev-1" cs={cs} playerName={resolveName} />
  </QueryClientProvider></MemoryRouter>)
}
async function compare() {
  await screen.findByRole('table', { name: 'Completed season archive' })
  const selected = screen.getByLabelText('Selected season')
  const other = screen.getByLabelText('Compare with')
  fireEvent.change(selected, { target: { value: '1' } })
  fireEvent.change(other, { target: { value: '0' } })
}

describe('SeasonArchivePanel (component, mocked API)', () => {
  beforeEach(() => { api.getSeasonArchive.mockClear(); api.getSeasonDetail.mockClear() })

  it('lists every completed season with its rules and overview', async () => {
    api.getSeasonArchive.mockResolvedValue(archive)
    mount()
    const table = await screen.findByRole('table', { name: 'Completed season archive' })
    expect(within(table).getByText('2000/01')).toBeInTheDocument()
    expect(within(table).getByText('2001/02')).toBeInTheDocument()
    expect(within(table).getAllByText('Alice (2)')).toHaveLength(2)
    expect(screen.getByText(/no composite country score/)).toBeInTheDocument()
  })

  it('shows comparable rules and a missing side as "not represented", never zero', async () => {
    api.getSeasonArchive.mockResolvedValue(archive)
    api.getSeasonDetail.mockResolvedValue(detail(true))
    mount()
    await compare()
    await screen.findByText(/recorded rules .* are the same/)
    const panel = screen.getByLabelText('Season comparison')
    const aut = within(panel).getByText('AUT').closest('tr')!
    expect(within(aut).getAllByText('not represented')).toHaveLength(3)
    expect(within(aut).getByText('no delta (one side missing)')).toBeInTheDocument()
    expect(api.getSeasonDetail).toHaveBeenLastCalledWith('run', 'branch', 1, 0)
  })

  it('flags limited comparability with the exact differing values (CS)', async () => {
    api.getSeasonArchive.mockResolvedValue(archive)
    api.getSeasonDetail.mockResolvedValue(detail(false))
    mount(true)
    await screen.findByRole('table', { name: 'Archiv dokončených sezón' })
    const selected = screen.getByLabelText('Vybraná sezóna')
    const other = screen.getByLabelText('Porovnat s')
    fireEvent.change(selected, { target: { value: '1' } })
    fireEvent.change(other, { target: { value: '0' } })
    const alert = await screen.findByText(/Omezená srovnatelnost/)
    expect(alert).toHaveTextContent('Omezená srovnatelnost')
    expect(alert.closest('[role="alert"]')).toHaveTextContent('Best N: 1 → 15')
  })

  it('does not display a response for another Saved revision', async () => {
    api.getSeasonArchive.mockResolvedValue({ ...archive, saved_head_revision_id: 'rev-2' })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent(/was not displayed/)
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('does not display a comparison for other seasons', async () => {
    api.getSeasonArchive.mockResolvedValue(archive)
    api.getSeasonDetail.mockResolvedValue({ ...detail(true), detail: { ...detail(true).detail, comparison_season_index: 5 } })
    mount()
    await compare()
    expect(await screen.findByText(/does not match the selected revision or seasons/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Season comparison')).not.toBeInTheDocument()
  })

  it('treats an unsupported Run as information', async () => {
    api.getSeasonArchive.mockImplementation(async () => { throw new Error('Season archive requires a Saved configured Tour') })
    mount()
    expect(await screen.findByText(/archive is unavailable for this revision/)).toHaveTextContent('requires a Saved configured Tour')
  })
  it('keeps a missing comparison side distinct while presence filtering', async () => {
    api.getSeasonArchive.mockResolvedValue(archive)
    api.getSeasonDetail.mockResolvedValue(detail(true))
    mount()
    await compare()
    await screen.findByLabelText('Season comparison')
    fireEvent.change(screen.getByLabelText('Country presence'), { target: { value: 'only_comparison' } })
    const panel = screen.getByLabelText('Season comparison')
    expect(within(panel).getByText('AUT')).toBeInTheDocument()
    expect(within(panel).queryByText('CZE')).not.toBeInTheDocument()
    expect(within(panel).getAllByText('not represented')).toHaveLength(3)
    expect(api.getSeasonDetail).toHaveBeenCalledTimes(1)
  })


  it('searches the actually displayed player name, not only the backend label', async () => {
    api.getSeasonArchive.mockResolvedValue(archive)
    mount(false, id => id === 'P1' ? 'Local player alias' : id)
    const table = await screen.findByRole('table', { name: 'Completed season archive' })
    fireEvent.change(screen.getByLabelText('Search archive'), { target: { value: 'local player alias' } })
    expect(within(table).getAllByText('Local player alias (2)')).toHaveLength(2)
    expect(api.getSeasonDetail).not.toHaveBeenCalled()
  })

  it('shows all supported title, final and point metrics without treating missing data as zero', async () => {
    api.getSeasonArchive.mockResolvedValue(archive)
    api.getSeasonDetail.mockResolvedValue(detail(true))
    mount()
    await compare()
    const table = await screen.findByRole('table', { name: 'Country comparison' })
    expect(within(table).getByRole('columnheader', { name: 'Finals (selected)' })).toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: 'Finals (comparison)' })).toBeInTheDocument()
    const aut = within(table).getByText('AUT').closest('tr')!
    expect(within(aut).getAllByText('not represented')).toHaveLength(3)
    expect(within(aut).getAllByText('—')).toHaveLength(2)
  })

  it('rejects the same selected and comparison season without fetching detail', async () => {
    api.getSeasonArchive.mockResolvedValue(archive)
    mount()
    await screen.findByRole('table', { name: 'Completed season archive' })
    fireEvent.change(screen.getByLabelText('Selected season'), { target: { value: '0' } })
    fireEvent.change(screen.getByLabelText('Compare with'), { target: { value: '0' } })
    expect(await screen.findByText(/Select two distinct existing seasons/)).toBeInTheDocument()
    expect(screen.getByLabelText('Compare with')).toHaveValue('0')
    expect(api.getSeasonDetail).not.toHaveBeenCalled()
  })

})

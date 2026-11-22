import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerCountriesDeferredPage } from './ViewerCountriesDeferredPage'

const api = vi.hoisted(() => ({ getViewerCountries: vi.fn() }))
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
    data: {
      product_run_id: active.foreign ? 'foreign' : run,
      official_branch_id: active.branch,
    },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

function country(
  code: string, activePlayers: number, retiredPlayers: number,
  avg: number | null, topId: string | null = null, topName: string | null = null,
) {
  return {
    country_code: code, player_count: activePlayers + retiredPlayers,
    active_player_count: activePlayers, retired_player_count: retiredPlayers,
    average_current_ovr: avg, top_player_id: topId,
    top_player_name: topName, top_player_current_ovr: topId ? 175 : null,
  }
}
const countries = [
  country('NZL', 3, 1, 162.5, 'paul coll', 'Paul Coll'),
  country('CZE', 1, 2, 121.5, 'p-one', 'A Player'),
  country('EGY', 0, 0, null),
]
function payload(
  items: ReturnType<typeof country>[] = countries,
  run = active.run ?? '', branch = active.branch,
) {
  return {
    schema_version: 'viewer_countries.v1',
    product_run_id: run, viewer_branch_id: branch,
    season_index: 4, week: 20, country_count: items.length, countries: items,
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
      <MemoryRouter>
        <LanguageProvider>
          <SwitchLanguage />
          <ViewerCountriesDeferredPage kind="all" />
        </LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}
function table() {
  return screen.getByRole('table', { name: 'Ověřený uložený seznam zemí' })
}

describe('All Countries from the verified public Saved Viewer Branch (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    active.run = 'run alpha'; active.branch = 'branch-a'; active.foreign = false
    api.getViewerCountries.mockReset().mockImplementation((run: string) =>
      Promise.resolve(payload(countries, run, active.branch)))
  })

  it('does not fetch or fabricate a directory without an explicitly selected Product Run', () => {
    active.run = null
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Seznam Runů' }))
      .toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerCountries).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('blocks public GET when the official Viewer context belongs to another Run', () => {
    active.foreign = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('neodpovídá vybranému Runu')
    expect(api.getViewerCountries).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows every saved country, exact public counts, null OVR and canonical country/player links', async () => {
    mount()
    const t = await screen.findByRole('table', { name: 'Ověřený uložený seznam zemí' })
    expect(within(t).getAllByRole('row')).toHaveLength(4)
    const nzl = within(t).getByRole('row', { name: /NZL/ })
    const cells = within(nzl).getAllByRole('cell')
    expect(cells[1]).toHaveTextContent('4')
    expect(cells[2]).toHaveTextContent('3')
    expect(cells[3]).toHaveTextContent('1')
    expect(cells[4]).toHaveTextContent('162.5')
    expect(within(nzl).getByRole('link', { name: 'NZL' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/NZL')
    expect(within(nzl).getByRole('link', { name: 'Paul Coll' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/paul%20coll/career')
    const egy = within(t).getByRole('row', { name: /EGY/ })
    expect(within(egy).getAllByRole('cell')[4]).toHaveTextContent('—')
    expect(within(egy).queryByRole('link', { name: '—' })).not.toBeInTheDocument()
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText(/nejde o historickému rekordu/)).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('filters by real country code or public player name, sorts numbers and keeps unknown OVR last', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Řadit podle'), 'players')
    expect(within(table()).getAllByRole('row')[1]).toHaveTextContent('NZL')
    await user.selectOptions(screen.getByLabelText('Řadit podle'), 'average_ovr')
    expect(within(table()).getAllByRole('row')[3]).toHaveTextContent('EGY')
    await user.type(screen.getByLabelText('Hledat zemi nebo hráče'), 'Paul')
    expect(within(table()).getAllByRole('row')).toHaveLength(2)
    expect(within(table()).getByRole('link', { name: 'NZL' })).toBeInTheDocument()
    await user.clear(screen.getByLabelText('Hledat zemi nebo hráče'))
    await user.type(screen.getByLabelText('Hledat zemi nebo hráče'), 'NOT-THERE')
    expect(screen.getByText('Hledání neodpovídá žádné uložené zemi.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(within(table()).getAllByRole('row')).toHaveLength(4)
    expect(screen.getByLabelText('Řadit podle')).toHaveValue('country')
    expect(api.getViewerCountries).toHaveBeenCalledTimes(1)
  })

  it('does not invent countries when a valid Saved directory is genuinely empty', async () => {
    api.getViewerCountries.mockReset().mockResolvedValue(payload([]))
    mount()
    expect(await screen.findByText('V tomto Runu zatím nejsou uložené země.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('fails closed on a foreign Branch, duplicate code and private field, then allows explicit GET recovery', async () => {
    const good = payload()
    api.getViewerCountries.mockReset()
      .mockResolvedValueOnce(payload(countries, 'run alpha', 'wrong-branch'))
      .mockResolvedValueOnce(payload([countries[0], countries[0]]))
      .mockResolvedValueOnce({
        ...good, countries: [{ ...countries[0], private_rating: 99 }, countries[1], countries[2]],
      })
      .mockResolvedValueOnce(good)
    const user = userEvent.setup()
    mount()
    for (let i = 0; i < 3; i++) {
      expect(await screen.findByRole('alert')).toHaveTextContent('neplatný údaj')
      expect(screen.queryByRole('link', { name: 'Paul Coll' })).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Znovu načíst (GET)' }))
    }
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(4)
    expectNoForbiddenViewerActions()
  })

  it('does not show a late prior-Branch response when the selected Viewer Branch changes', async () => {
    let resolveOld: ((data: ReturnType<typeof payload>) => void) | undefined
    api.getViewerCountries.mockReset().mockImplementation((run: string) =>
      active.branch === 'branch-a'
        ? new Promise(resolve => { resolveOld = resolve })
        : Promise.resolve(payload(countries, run, 'branch-b')))
    const view = mount()
    await waitFor(() => expect(api.getViewerCountries).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    await act(async () => view.refresh())
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(payload(countries, 'run alpha', 'branch-a')) })
    expect(screen.queryByText('branch-a')).not.toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(2)
  })

  it('switches CS/EN without changing stored codes or refetching Saved countries', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { level: 2, name: 'All Countries' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Verified Saved country directory' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'NZL' })).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledTimes(1)
  })

  it('paginates long country directories and resets to page one on search', async () => {
    const many = Array.from({ length: 30 }, (_, i) => {
      const code = 'C' + String.fromCharCode(65 + Math.floor(i / 26)) + String.fromCharCode(65 + i % 26)
      return country(code, 1, 0, 100 + i)
    })
    api.getViewerCountries.mockReset().mockResolvedValue(payload(many))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByText('Zobrazeno 1–25 z 30')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(screen.getByText('Zobrazeno 26–30 z 30')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat zemi nebo hráče'), 'CBD')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'CBD' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

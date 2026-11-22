import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ViewerSearchPage } from './ViewerSearchPage'

const mocks = vi.hoisted(() => ({
  runId: 'run-a' as string | null,
  language: 'en',
  getViewerPlayers: vi.fn(),
  getViewerCountries: vi.fn(),
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
}))
vi.mock('../../../api/client', () => ({
  getViewerPlayers: mocks.getViewerPlayers,
  getViewerCountries: mocks.getViewerCountries,
  getViewerRunCalendar: mocks.getViewerRunCalendar,
  getViewerTournamentHistory: mocks.getViewerTournamentHistory,
}))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => mocks.runId,
}))
vi.mock('../../../viewer/ViewerContext', () => ({
  useViewerContext: () => ({ selectedSeason: 0, selectedWeek: 1 }),
}))
vi.mock('../../../i18n/LanguageContext', () => ({
  useLanguage: () => ({ language: mocks.language }),
}))
vi.mock('../people', () => ({
  renderPlayerSampleMetadata: (player: { name: string }) => player.name,
  renderCountrySampleMetadata: () => null,
}))

function Navigation(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  return <>
    <output aria-label="URL">{location.pathname}{location.search}</output>
    <button onClick={() => navigate(-1)}>Back</button>
    <button onClick={() => navigate(1)}>Forward</button>
  </>
}

function mount(url = '/viewer/search?keep=one&keep=two') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  function App(): JSX.Element {
    return <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <Navigation />
        <ViewerSearchPage />
      </MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

beforeEach(() => {
  mocks.runId = 'run-a'
  mocks.language = 'en'
  mocks.getViewerPlayers.mockReset().mockResolvedValue({
    players: [{ player_id: 'alice', name: 'Alice' }, { player_id: 'bob', name: 'Bob' }],
  })
  mocks.getViewerCountries.mockReset().mockResolvedValue({ countries: [] })
  mocks.getViewerRunCalendar.mockReset().mockResolvedValue({ seasons: [] })
  mocks.getViewerTournamentHistory.mockReset().mockResolvedValue({ tournaments: [] })
})
afterEach(cleanup)

describe('Viewer Search submission (mocked GET API)', () => {
  it('submits by Enter and button, preserving other parameters and waiting for submission while typing', async () => {
    const user = userEvent.setup()
    mount()
    let input = screen.getByRole('searchbox', { name: 'Search' })
    await user.type(input, ' Alice ')
    expect(mocks.getViewerPlayers).not.toHaveBeenCalled()
    expect(screen.getByLabelText('URL').textContent).toBe('/viewer/search?keep=one&keep=two')
    await user.keyboard('{Enter}')
    expect(await screen.findByText('Alice', { selector: 'li' })).toBeInTheDocument()
    input = screen.getByRole('searchbox', { name: 'Search' })
    expect(input).toHaveValue('Alice')
    expect(screen.getByLabelText('URL').textContent).toBe('/viewer/search?keep=one&keep=two&q=Alice')
    await user.clear(input)
    await user.type(input, 'Bob')
    expect(screen.getByText('Alice', { selector: 'li' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText('Bob', { selector: 'li' })).toBeInTheDocument()
    expect(screen.queryByText('Alice', { selector: 'li' })).not.toBeInTheDocument()
    expect(mocks.getViewerPlayers).toHaveBeenCalledTimes(1)
    expect(mocks.getViewerPlayers).toHaveBeenCalledWith('run-a')
  })

  it('restores the submitted query and results on Back/Forward without recording keystrokes', async () => {
    const user = userEvent.setup()
    mount('/viewer/search?q=Alice&keep=yes')
    expect(await screen.findByText('Alice', { selector: 'li' })).toBeInTheDocument()
    const input = screen.getByRole('searchbox')
    await user.clear(input)
    await user.type(input, 'Bob{Enter}')
    expect(await screen.findByText('Bob', { selector: 'li' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(input).toHaveValue('Alice')
    expect(screen.getByText('Alice', { selector: 'li' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(input).toHaveValue('Bob')
    expect(screen.getByText('Bob', { selector: 'li' })).toBeInTheDocument()
  })

  it('opens the same search after remount and normalizes legacy aliases when clearing', async () => {
    const user = userEvent.setup()
    const view = mount('/viewer/search?query=Alice&search=Bob&keep=yes')
    expect(await screen.findByText('Alice', { selector: 'li' })).toBeInTheDocument()
    view.unmount()
    mount('/viewer/search?query=Alice&search=Bob&keep=yes')
    expect(await screen.findByText('Alice', { selector: 'li' })).toBeInTheDocument()
    await user.clear(screen.getByRole('searchbox'))
    await user.type(screen.getByRole('searchbox'), '   {Enter}')
    expect(screen.getByLabelText('URL').textContent).toBe('/viewer/search?keep=yes')
    expect(screen.getByText('Enter and submit a search term.')).toBeInTheDocument()
    expect(screen.queryByText('Alice', { selector: 'li' })).not.toBeInTheDocument()
  })

  it('keeps the empty context and makes no API calls without a Run, including a localized submission', async () => {
    mocks.runId = null
    mocks.language = 'cs'
    const user = userEvent.setup()
    mount()
    await user.type(screen.getByRole('searchbox', { name: 'Hledat' }), 'Alice')
    await user.click(screen.getByRole('button', { name: 'Vyhledat' }))
    expect(screen.getByText('Nejprve vyber Run pro vyhledávání.')).toBeInTheDocument()
    for (const fn of [mocks.getViewerPlayers, mocks.getViewerCountries, mocks.getViewerRunCalendar, mocks.getViewerTournamentHistory]) {
      expect(fn).not.toHaveBeenCalled()
    }
  })

  it('ignores a delayed old-Run response after the active Run changes', async () => {
    let resolveOld!: (value: { players: { player_id: string; name: string }[] }) => void
    mocks.getViewerPlayers.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce({ players: [{ player_id: 'bob', name: 'Bob' }] })
    const view = mount('/viewer/search?q=Bob')
    await waitFor(() => expect(mocks.getViewerPlayers).toHaveBeenCalledWith('run-a'))
    mocks.runId = 'run-b'
    view.refresh()
    expect(await screen.findByText('Bob', { selector: 'li' })).toBeInTheDocument()
    await act(async () => { resolveOld({ players: [{ player_id: 'old', name: 'Old Run Bob' }] }) })
    expect(screen.queryByText('Old Run Bob', { selector: 'li' })).not.toBeInTheDocument()
    expect(mocks.getViewerPlayers).toHaveBeenCalledWith('run-b')
  })
  it('shows Czech search results and updates language without refetching or rewriting the URL', async () => {
    mocks.language = 'cs'
    const view = mount('/viewer/search?q=Alice&keep=yes')
    expect(await screen.findByText('Alice', { selector: 'li' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vyhledávání: Alice' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Hráči' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Země' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Turnaje' })).toBeInTheDocument()
    expect(screen.getByText('Dotaz')).toBeInTheDocument()
    expect(screen.getByText('Žádné odpovídající země.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít přehled Runů' })).toBeInTheDocument()
    expect(screen.getByLabelText('URL').textContent).toBe('/viewer/search?q=Alice&keep=yes')
    const calls = mocks.getViewerPlayers.mock.calls.length

    mocks.language = 'en'
    view.refresh()
    expect(screen.getByRole('heading', { name: 'Search: Alice' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(screen.getByText('No matching countries.')).toBeInTheDocument()
    expect(screen.getByLabelText('URL').textContent).toBe('/viewer/search?q=Alice&keep=yes')
    expect(mocks.getViewerPlayers).toHaveBeenCalledTimes(calls)
  })

  it('localizes a true zero-result search and failed canonical GET without hiding the source error', async () => {
    mocks.language = 'cs'
    const view = mount('/viewer/search?q=Nobody&other=kept')
    expect(await screen.findByText('Nebyly nalezeny žádné odpovídající výsledky.')).toBeInTheDocument()
    expect(screen.getByText('Žádní odpovídající hráči.')).toBeInTheDocument()
    expect(screen.getByText('Žádné odpovídající turnaje.')).toBeInTheDocument()
    expect(screen.getByLabelText('URL').textContent).toBe('/viewer/search?q=Nobody&other=kept')
    view.unmount()

    mocks.getViewerCountries.mockReset().mockRejectedValue(new Error('read unavailable'))
    mount('/viewer/search?q=Alice&other=kept')
    expect(await screen.findByText('Některá uložená data pro vyhledávání jsou dočasně nedostupná.')).toBeInTheDocument()
    expect(screen.queryByText('Nebyly nalezeny žádné odpovídající výsledky.')).not.toBeInTheDocument()
    expect(screen.getByLabelText('URL').textContent).toBe('/viewer/search?q=Alice&other=kept')
  })
})

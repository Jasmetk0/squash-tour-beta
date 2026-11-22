import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ViewerTournamentResult, ViewerTournamentResultPlayer } from '../../../api/types'
import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import {
  calendarEvent, historyEvent, savedCalendar, savedHistory,
} from '../../../test/viewerCalendarFixtures'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerTourDeferredPage } from './ViewerTourDeferredPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  getViewerTournamentResult: vi.fn(),
}))
const active = vi.hoisted(() => ({
  run: 'run alpha' as string | null,
  branch: 'viewer-branch',
  foreign: false,
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
      product_run_id: active.foreign ? 'foreign-run' : run,
      official_branch_id: active.branch,
    },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

const event1 = calendarEvent()
const event2 = calendarEvent({
  event_id: 'EVENT/2', event_name: 'Second Open', season_week: 6,
})
const published = historyEvent(event1, {
  result_published: true, champion_player_id: 'A', finalist_player_id: 'B',
})
const unpublished = historyEvent(event2)

function player(id: string): ViewerTournamentResultPlayer {
  return {
    player_id: id, draw_type: 'main', seed_number: null, qualifier: false,
    main_entry_status: null, reached_stage: id === 'A' ? 'champion' : 'finalist',
    final_round_number: 2, eliminated_by_player_id: id === 'B' ? 'A' : null,
    last_match_id: 'final', wins: id === 'A' ? 2 : 1,
    losses: id === 'A' ? 0 : 1, byes_received: 0, walkovers_received: 0,
    retired_or_walkover_loss: false, group_index: null, group_position: null,
    played_group_wins: null, group_walkovers_received: null,
    knockout_reached_stage: null,
  }
}
function result(
  overrides: Partial<ViewerTournamentResult> = {},
): ViewerTournamentResult {
  return {
    schema_version: 'viewer_tournament_result.v1',
    product_run_id: 'run alpha', viewer_branch_id: active.branch,
    event_id: 'EVENT/1', completed_season_index: 28,
    completed_week: 5, champion_player_id: 'A', finalist_player_id: 'B',
    qualification_winner_ids: [],
    players: [player('A'), player('B')],
    matches: [
      {
        match_id: 'qualifier', draw_type: 'qualification',
        round_number: 1, bracket_position: 1,
        winner_player_id: 'A', loser_player_id: 'B', scoreline: '3-1',
      },
      {
        match_id: 'final', draw_type: 'main',
        round_number: 2, bracket_position: 1,
        winner_player_id: 'A', loser_player_id: 'B', scoreline: '3-2',
      },
    ],
    ...overrides,
  }
}
function Controls(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  const { search } = useLocation()
  const navigate = useNavigate()
  return <>
    <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>
      Toggle language
    </button>
    <button type="button" onClick={() => navigate(-1)}>Back</button>
    <p data-testid="search-params">{search}</p>
  </>
}
function mount(url = '/viewer/tour/matches') {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <LanguageProvider>
          <Controls />
          <ViewerTourDeferredPage kind="matches" />
        </LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('Saved Match Center over actual published tournament GET contract (mocked HTTP)', () => {
  beforeEach(() => {
    localStorage.clear()
    active.run = 'run alpha'; active.branch = 'viewer-branch'; active.foreign = false
    api.getViewerRunCalendar.mockReset().mockResolvedValue(savedCalendar([event1, event2]))
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(savedHistory([published, unpublished]))
    api.getViewerTournamentResult.mockReset().mockImplementation(() => Promise.resolve(result()))
  })

  it('never reads public sources without a chosen Product Run', () => {
    active.run = null
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('rejects a foreign official-context Run without issuing any GET', () => {
    active.foreign = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('nemá ověřenou Viewer Branch')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
  })

  it('lists only genuinely published events, with exact source counts and links, and no eager match GET', async () => {
    mount()
    const directory = await screen.findByRole('table', { name: 'Turnaje s publikovanými výsledky' })
    expect(within(directory).getAllByRole('row')).toHaveLength(2)
    expect(within(directory).getByRole('link', { name: 'Source Open' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVENT%2F1')
    expect(within(directory).queryByText('Second Open')).not.toBeInTheDocument()
    expect(screen.getByText('viewer-branch')).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('fetches a real selected event by stable encoded ID only after click and shows actual match scorelines', async () => {
    const user = userEvent.setup()
    mount('/viewer/tour/matches?keep=1')
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Zobrazit zápasy' }))
    const matches = await screen.findByRole('table', { name: 'Publikované zápasy vybraného turnaje' })
    expect(within(matches).getAllByRole('row')).toHaveLength(3)
    expect(within(matches).getByText('final')).toBeInTheDocument()
    expect(within(matches).getByText('3-2')).toBeInTheDocument()
    expect(within(matches).getAllByRole('link', { name: 'B' })[0])
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/B/career')
    expect(screen.getByRole('link', { name: 'Detail turnaje' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments/EVENT%2F1')
    expect(screen.getByTestId('search-params')).toHaveTextContent('keep=1')
    expect(screen.getByTestId('search-params')).toHaveTextContent('event=EVENT%2F1')
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentResult).toHaveBeenCalledWith('run alpha', 'EVENT/1')
    expectNoForbiddenViewerActions()
  })

  it('opens an explicit deep-link and restores the selected event with browser Back', async () => {
    const user = userEvent.setup()
    mount('/viewer/tour/matches?utm=from-archive')
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Zobrazit zápasy' }))
    expect(await screen.findByRole('table', { name: 'Publikované zápasy vybraného turnaje' }))
      .toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    await waitFor(() => expect(
      screen.queryByRole('table', { name: 'Publikované zápasy vybraného turnaje' }),
    ).not.toBeInTheDocument())
    expect(screen.getByTestId('search-params')).toHaveTextContent('utm=from-archive')
  })

  it('shows a direct-link result only if the event exists and is published in this Branch', async () => {
    mount('/viewer/tour/matches?event=EVENT%2F2')
    expect(await screen.findByRole('alert')).toHaveTextContent('nemá výsledek publikovaný')
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expect(screen.queryByRole('table', { name: 'Publikované zápasy vybraného turnaje' }))
      .not.toBeInTheDocument()
  })

  it('shows a genuine no-publication state without fetching any result', async () => {
    api.getViewerTournamentHistory.mockReset()
      .mockResolvedValue(savedHistory([historyEvent(event1), historyEvent(event2)]))
    mount()
    expect(await screen.findByText('Zatím není publikován žádný turnajový výsledek.'))
      .toBeInTheDocument()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
  })

  it('rejects mismatched history and calendar and permits only source GET recovery', async () => {
    api.getViewerTournamentHistory.mockReset()
      .mockResolvedValueOnce(savedHistory([published], 'foreign-run'))
      .mockResolvedValueOnce(savedHistory([published, unpublished]))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('stejného ověřeného zdroje')
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('table', { name: 'Turnaje s publikovanými výsledky' }))
      .toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(2)
  })

  it('rejects a forged result Branch, conflicting champion, and private match fields until fresh GET', async () => {
    const good = result()
    api.getViewerTournamentResult.mockReset()
      .mockResolvedValueOnce(result({ viewer_branch_id: 'foreign-branch' }))
      .mockResolvedValueOnce(result({ champion_player_id: 'B' }))
      .mockResolvedValueOnce(result({
        matches: [{ ...good.matches[0], private_potential: 200 }, good.matches[1]],
      } as unknown as ViewerTournamentResult))
      .mockResolvedValueOnce(good)
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Zobrazit zápasy' }))
    for (let i = 0; i < 3; i++) {
      const alert = await screen.findByRole('alert')
      expect(alert).toHaveTextContent('nepovolené údaje')
      expect(screen.queryByRole('table', { name: 'Publikované zápasy vybraného turnaje' }))
        .not.toBeInTheDocument()
      await user.click(within(alert).getByRole('button', { name: 'Načíst znovu (GET)' }))
    }
    expect(await screen.findByRole('table', { name: 'Publikované zápasy vybraného turnaje' }))
      .toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(4)
    expectNoForbiddenViewerActions()
  })

  it('rejects duplicate match IDs, foreign winners and malformed match fields', async () => {
    api.getViewerTournamentResult.mockReset().mockResolvedValue(result({
      matches: [result().matches[0], result().matches[0]],
    }))
    mount('/viewer/tour/matches?event=EVENT%2F1')
    expect(await screen.findByRole('alert')).toHaveTextContent('nepovolené údaje')
    expect(screen.queryByText('3-1')).not.toBeInTheDocument()
  })

  it('filters real published match rows by draw and player without refetching', async () => {
    const user = userEvent.setup()
    mount('/viewer/tour/matches?event=EVENT%2F1')
    await screen.findByRole('table', { name: 'Publikované zápasy vybraného turnaje' })
    await user.selectOptions(screen.getByLabelText('Část turnaje'), 'main')
    const table = screen.getByRole('table', { name: 'Publikované zápasy vybraného turnaje' })
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByText('3-2')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat ID zápasu, hráče nebo skóre'), 'nobody')
    expect(screen.getByText('Vyhledávání neodpovídá žádný zápas.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }).last())
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(1)
  })

  it('hides stale published details when source Branch changes during a slow fetch', async () => {
    let resolveOld: ((data: ViewerTournamentResult) => void) | undefined
    api.getViewerTournamentResult.mockReset().mockImplementation(() =>
      active.branch === 'viewer-branch'
        ? new Promise(resolve => { resolveOld = resolve })
        : Promise.resolve(result()))
    const user = userEvent.setup()
    const view = mount('/viewer/tour/matches?event=EVENT%2F1')
    await waitFor(() => expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    api.getViewerRunCalendar.mockReset().mockResolvedValue({
      ...savedCalendar([event1, event2]), viewer_branch_id: 'branch-b',
    })
    api.getViewerTournamentHistory.mockReset().mockResolvedValue({
      ...savedHistory([published, unpublished]), viewer_branch_id: 'branch-b',
    })
    await act(async () => { view.refresh() })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(result({ viewer_branch_id: 'viewer-branch' })) })
    expect(screen.queryByText('viewer-branch')).not.toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(2)
    expectNoForbiddenViewerActions()
  })

  it('translates full match detail to English without modifying public identities or extra GETs', async () => {
    const user = userEvent.setup()
    mount('/viewer/tour/matches?event=EVENT%2F1')
    await screen.findByRole('table', { name: 'Publikované zápasy vybraného turnaje' })
    await user.click(screen.getByRole('button', { name: 'Toggle language' }))
    expect(screen.getByRole('heading', { name: 'Match Center' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Published matches for selected tournament' }))
      .toHaveTextContent('3-2')
    expect(screen.getByRole('link', { name: 'Tournament detail' })).toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(1)
  })
})

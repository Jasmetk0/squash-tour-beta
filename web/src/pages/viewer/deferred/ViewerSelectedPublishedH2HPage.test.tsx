import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ViewerTournamentResult, ViewerTournamentResultPlayer } from '../../../api/types'
import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import {
  calendarEvent, historyEvent, savedCalendar, savedHistory,
} from '../../../test/viewerCalendarFixtures'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerH2HSubroutePage } from './ViewerH2HSubroutePage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(), getViewerTournamentHistory: vi.fn(),
  getViewerTournamentResult: vi.fn(), getViewerPlayers: vi.fn(),
}))
const active = vi.hoisted(() => ({
  run: 'run alpha' as string | null,
  branch: 'viewer-branch', foreign: false,
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
      product_run_id: active.foreign ? 'other-run' : run,
      official_branch_id: active.branch,
    },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

const opening = calendarEvent({ status: 'completed' })
const closing = calendarEvent({
  event_id: 'EVENT/2', event_name: 'Second Open', season_week: 6,
  start_season_week: 6, end_season_week: 6, status: 'completed',
})
const future = calendarEvent({
  event_id: 'FUTURE', event_name: 'Future Open', season_week: 7,
  start_season_week: 7, end_season_week: 7, status: 'planned',
})
const oldPublished = historyEvent(opening, {
  result_published: true, champion_player_id: 'A', finalist_player_id: 'B',
})
const laterPublished = historyEvent(closing, {
  result_published: true, champion_player_id: 'B', finalist_player_id: 'A',
})
const futureUnpublished = historyEvent(future)

function player(id: string): ViewerTournamentResultPlayer {
  return {
    player_id: id, draw_type: 'main', seed_number: null, qualifier: false,
    main_entry_status: null, reached_stage: 'semifinal',
    final_round_number: 2, eliminated_by_player_id: null, last_match_id: null,
    wins: 0, losses: 0, byes_received: 0, walkovers_received: 0,
    retired_or_walkover_loss: false, group_index: null, group_position: null,
    played_group_wins: null, group_walkovers_received: null,
    knockout_reached_stage: null,
  }
}
function result(eventId: string, overrides: Partial<ViewerTournamentResult> = {}): ViewerTournamentResult {
  const first = eventId === 'EVENT/1'
  return {
    schema_version: 'viewer_tournament_result.v1',
    product_run_id: 'run alpha', viewer_branch_id: active.branch,
    event_id: eventId, completed_season_index: 28,
    completed_week: first ? 5 : 6,
    champion_player_id: first ? 'A' : 'B',
    finalist_player_id: first ? 'B' : 'A',
    qualification_winner_ids: [], players: [player('A'), player('B'), player('C')],
    matches: [
      {
        match_id: first ? 'semi-a' : 'semi-b', draw_type: 'main',
        round_number: 1, bracket_position: 1,
        winner_player_id: first ? 'A' : 'B', loser_player_id: 'C', scoreline: '3-0',
      },
      {
        match_id: first ? 'final-a' : 'final-b', draw_type: 'main',
        round_number: 2, bracket_position: 1,
        winner_player_id: first ? 'A' : 'B',
        loser_player_id: first ? 'B' : 'A',
        scoreline: first ? '3-2' : '3-1',
      },
    ],
    ...overrides,
  }
}

function ToggleLanguage(): JSX.Element {
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
        <ToggleLanguage /><ViewerH2HSubroutePage kind="rivalries" />
      </LanguageProvider></MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}
async function selectPlayers(user: ReturnType<typeof userEvent.setup>, both = false) {
  await screen.findByRole('group', { name: 'Vybrat zdroje pro H2H' })
  await user.type(screen.getByLabelText('ID hráče A'), 'A')
  await user.type(screen.getByLabelText('ID hráče B'), 'B')
  await user.click(screen.getByRole('checkbox', { name: 'Zahrnout turnaj: Source Open' }))
  if (both) await user.click(screen.getByRole('checkbox', { name: 'Zahrnout turnaj: Second Open' }))
  await user.click(screen.getByRole('button', { name: 'Spočítat H2H z vybraných publikací' }))
}
describe('real-source-shape, explicitly bounded published tournament H2H (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    active.run = 'run alpha'; active.branch = 'viewer-branch'; active.foreign = false
    api.getViewerRunCalendar.mockReset().mockResolvedValue(
      savedCalendar([opening, closing, future]))
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(
      savedHistory([oldPublished, laterPublished, futureUnpublished]))
    api.getViewerTournamentResult.mockReset().mockImplementation(
      (_run: string, eventId: string) => Promise.resolve(result(eventId)))
    api.getViewerPlayers.mockReset()
  })

  it('does not query the public source without a selected Product Run', () => {
    active.run = null
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('rejects a foreign official Run before any Saved source GET', () => {
    active.foreign = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('nemá ověřenou Viewer Branch')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
  })

  it('lists only published events with exact Saved Branch and never prefetches match details', async () => {
    mount()
    const choices = await screen.findByRole('group', { name: 'Vybrat zdroje pro H2H' })
    expect(within(choices).getAllByRole('checkbox')).toHaveLength(2)
    expect(choices).not.toHaveTextContent('Future Open')
    expect(screen.getByText('viewer-branch')).toBeInTheDocument()
    expect(screen.getByText(/Vybráno turnajů: 0\/8/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Spočítat H2H z vybraných publikací' })).toBeDisabled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expect(api.getViewerPlayers).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('loads only a selected publication after explicit click and derives only exact pair outcomes', async () => {
    const user = userEvent.setup()
    mount()
    await selectPlayers(user)
    const table = await screen.findByRole('table', { name: 'Konkrétní vzájemné zápasy' })
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(table).toHaveTextContent('final-a')
    expect(table).toHaveTextContent('3-2')
    expect(table).not.toHaveTextContent('semi-a')
    expect(within(table).getByRole('link', { name: 'Source Open' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments/EVENT%2F1')
    expect(screen.getByText(/Vzájemné výsledkové záznamy: 1/)).toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentResult).toHaveBeenCalledWith('run alpha', 'EVENT/1')
    expectNoForbiddenViewerActions()
  })

  it('aggregates both opposing winners across exactly two explicit Saved publications', async () => {
    const user = userEvent.setup()
    mount()
    await selectPlayers(user, true)
    const rows = await screen.findByRole('table', { name: 'Konkrétní vzájemné zápasy' })
    expect(within(rows).getAllByRole('row')).toHaveLength(3)
    expect(rows).toHaveTextContent('final-a')
    expect(rows).toHaveTextContent('final-b')
    expect(screen.getByText(/Vzájemné výsledkové záznamy: 2/)).toBeInTheDocument()
    expect(screen.getByText(/Celkem záznamů zápasů ve zdrojích: 4/)).toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(2)
    expect(api.getViewerTournamentResult.mock.calls.map(c => c[1]).sort())
      .toEqual(['EVENT/1', 'EVENT/2'])
  })

  it('returns explicitly scoped zero without falsely claiming career-wide zero H2H', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('group', { name: 'Vybrat zdroje pro H2H' })
    await user.type(screen.getByLabelText('ID hráče A'), 'B')
    await user.type(screen.getByLabelText('ID hráče B'), 'C')
    await user.click(screen.getByRole('checkbox', { name: 'Zahrnout turnaj: Source Open' }))
    await user.click(screen.getByRole('button', { name: 'Spočítat H2H z vybraných publikací' }))
    expect(await screen.findByText(/To není důkaz nulové bilance za kariéru/))
      .toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Konkrétní vzájemné zápasy' }))
      .not.toBeInTheDocument()
  })

  it('does not send any result GET for an invalid or identical player pair', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('group', { name: 'Vybrat zdroje pro H2H' })
    await user.type(screen.getByLabelText('ID hráče A'), 'A')
    await user.type(screen.getByLabelText('ID hráče B'), 'A')
    await user.click(screen.getByRole('checkbox', { name: 'Zahrnout turnaj: Source Open' }))
    expect(screen.getByRole('button', { name: 'Spočítat H2H z vybraných publikací' }))
      .toBeDisabled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
  })

  it('rejects a foreign tournament Branch and withholds *all* totals until successful GET retry', async () => {
    let rejectSecondOnce = true
    api.getViewerTournamentResult.mockReset().mockImplementation(
      (_run: string, eventId: string) => {
        if (eventId === 'EVENT/2' && rejectSecondOnce) {
          rejectSecondOnce = false
          return Promise.resolve(result(eventId, { viewer_branch_id: 'foreign' }))
        }
        return Promise.resolve(result(eventId))
      },
    )
    const user = userEvent.setup()
    mount()
    await selectPlayers(user, true)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('neveřejné údaje')
    expect(screen.queryByText(/Vzájemné výsledkové záznamy:/)).not.toBeInTheDocument()
    await user.click(within(alert).getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('table', { name: 'Konkrétní vzájemné zápasy' }))
      .toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(4)
  })

  it('rejects private match metadata without showing even a partial record', async () => {
    api.getViewerTournamentResult.mockReset().mockImplementation(
      (_run: string, eventId: string) => Promise.resolve(result(eventId, {
        matches: [{ ...result(eventId).matches[0], secret_ability: 99 }, result(eventId).matches[1]],
      } as unknown as ViewerTournamentResult)),
    )
    const user = userEvent.setup()
    mount()
    await selectPlayers(user)
    expect(await screen.findByRole('alert')).toHaveTextContent('neveřejné údaje')
    expect(screen.queryByText('final-a')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not invent a partial total after a requested GET fails; supports read-only retry', async () => {
    api.getViewerTournamentResult.mockReset()
      .mockRejectedValueOnce(new Error('Saved source temporarily unreachable'))
      .mockResolvedValue(result('EVENT/1'))
    const user = userEvent.setup()
    mount()
    await selectPlayers(user)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('není dostupný')
    expect(screen.queryByText(/Vzájemné výsledkové záznamy:/)).not.toBeInTheDocument()
    await user.click(within(alert).getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('table', { name: 'Konkrétní vzájemné zápasy' }))
      .toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(2)
  })

  it('enforces eight selected tournament sources without bulk automatic GETs', async () => {
    const events = Array.from({ length: 9 }, (_, i) => calendarEvent({
      event_id: 'EVENT-' + (i + 1),
      event_name: 'Open ' + (i + 1), season_week: i + 1,
      start_season_week: i + 1, end_season_week: i + 1,
    }))
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar(events))
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory(events.map(event =>
      historyEvent(event, {
        result_published: true, champion_player_id: 'A', finalist_player_id: 'B',
      }))))
    const user = userEvent.setup()
    mount()
    const choices = await screen.findByRole('group', { name: 'Vybrat zdroje pro H2H' })
    const checks = within(choices).getAllByRole('checkbox')
    expect(checks).toHaveLength(9)
    for (let i = 0; i < 8; i++) await user.click(checks[i])
    expect(checks[8]).toBeDisabled()
    expect(screen.getByText(/Vybráno turnajů: 8\/8/)).toBeInTheDocument()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
  })

  it('discards a previous H2H result when the selected public Viewer Branch changes', async () => {
    const user = userEvent.setup()
    const view = mount()
    await selectPlayers(user)
    await screen.findByRole('table', { name: 'Konkrétní vzájemné zápasy' })
    active.branch = 'new-branch'
    api.getViewerRunCalendar.mockResolvedValue({
      ...savedCalendar([opening, closing, future]), viewer_branch_id: 'new-branch',
    })
    api.getViewerTournamentHistory.mockResolvedValue({
      ...savedHistory([oldPublished, laterPublished, futureUnpublished]), viewer_branch_id: 'new-branch',
    })
    await act(async () => { view.refresh() })
    expect(await screen.findByText('new-branch')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Konkrétní vzájemné zápasy' }))
      .not.toBeInTheDocument()
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(1)
  })

  it('does not merge corrupted Calendar and History identities or request any match result', async () => {
    api.getViewerTournamentHistory.mockResolvedValue({
      ...savedHistory([oldPublished, laterPublished, futureUnpublished]),
      viewer_branch_id: 'foreign',
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('stejné uložené Viewer Branch')
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
  })

  it('translates all H2H interactions to English and preserves original historic player IDs', async () => {
    const user = userEvent.setup()
    mount()
    await selectPlayers(user)
    await screen.findByRole('table', { name: 'Konkrétní vzájemné zápasy' })
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { name: 'H2H in Published Tournaments' }))
      .toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Exact H2H outcome records' }))
      .toHaveTextContent('3-2')
    expect(screen.getByRole('link', { name: 'A' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/A/career')
    expect(api.getViewerTournamentResult).toHaveBeenCalledTimes(1)
  })
})

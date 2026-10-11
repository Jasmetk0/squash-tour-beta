import { screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { WeekDetailPage } from './WeekDetailPage'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn()
}))
const adminTime = vi.hoisted(() => ({ viewed: vi.fn() }))

vi.mock('../api/client', () => api)
vi.mock('../admin/useAdminViewedSeasonState', () => ({ useAdminViewedSeasonState: adminTime.viewed }))

function renderAt(route: string): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/runs/:runId/weeks/:week" element={<WeekDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('WeekDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    adminTime.viewed.mockReturnValue({ historical: false, seasonState: null, unavailable: false, failed: false, query: { isLoading: false }, time: null })
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2029, seed: 7, next_event_index: 2, total_events: 5, completed_event_ids: ['E1', 'E2'] },
      season_state: {
        season: 2029,
        next_event_index: 2,
        completed_event_ids: ['E1', 'E2'],
        ordered_events: [
          { event_id: 'E1', season: 2029, week: 3, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-1' },
          { event_id: 'E2', season: 2029, week: 3, tour: 'ELITE', category: 'SILVER', template_id: 'TEMP-2' },
          { event_id: 'E3', season: 2029, week: 5, tour: 'WORLD', category: 'PLATINUM', template_id: 'TEMP-3' },
          { event_id: 'E4', season: 2029, week: 7, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-4' },
          { event_id: 'E5', season: 2029, week: 7, tour: 'ELITE', category: 'SILVER', template_id: 'TEMP-5' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({
      run_id: 'run-a',
      events: [
        { event_sequence: 1, event_id: 'E1', season: 2029, week: 3, template_id: 'TEMP-1', tournament_result: {} },
        { event_sequence: 2, event_id: 'E2', season: 2029, week: 3, template_id: 'TEMP-2', tournament_result: {} },
        { event_sequence: 4, event_id: 'E4', season: 2029, week: 7, template_id: 'TEMP-4', tournament_result: {} }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'run-a',
      snapshots: [
        { snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: {} },
        { snapshot_sequence: 11, snapshot_kind: 'WEEK', source_event_id: 'E4', payload: {} }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'run-a',
      snapshots: [
        { snapshot_sequence: 20, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 21, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }
      ]
    })
  })

  it('uses only historical SeasonState for week existence, status, and navigation while Past', async () => {
    adminTime.viewed.mockReturnValue({ historical: true, unavailable: false, failed: false, query: { isLoading: false }, time: { viewCheckpointId: 'cp-old' }, seasonState: {
      season: 2005, completed_event_ids: ['A'], next_event_index: 1, ordered_events: [
        { event_id: 'A', season: 2005, week: 10, tour: 'WORLD', category: 'GOLD', template_id: 'TA' },
        { event_id: 'B', season: 2005, week: 12, tour: 'WORLD', category: 'PLATINUM', template_id: 'TB' },
        { event_id: 'C', season: 2005, week: 14, tour: 'ELITE', category: 'SILVER', template_id: 'TC' }
      ] } })
    renderAt('/runs/run-a/weeks/12')
    expect(await screen.findByText('Past')).toBeInTheDocument(); expect(screen.getAllByText('2005').length).toBeGreaterThan(0)
    const list = screen.getByRole('list', { name: 'Week planned events' }); expect(list).toHaveTextContent('B'); expect(list).toHaveTextContent('Next')
    expect(screen.getByRole('link', { name: 'W10' })).toBeInTheDocument(); expect(screen.getByRole('link', { name: 'W14' })).toBeInTheDocument()
    expect(screen.getByText(/Persisted Events and Ranking\/Race snapshots are not available/)).toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled(); expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled(); expect(api.listRaceSnapshots).not.toHaveBeenCalled()
  })

  it('continues to load current persisted and snapshot APIs while Present', async () => {
    renderAt('/runs/run-a/weeks/3')
    await screen.findByRole('heading', { name: 'Week detail' })
    await waitFor(() => { expect(api.listEvents).toHaveBeenCalled(); expect(api.listRankingSnapshots).toHaveBeenCalled(); expect(api.listRaceSnapshots).toHaveBeenCalled() })
  })

  it('renders for a valid week with season-ordered planned events', async () => {
    renderAt('/runs/run-a/weeks/3')

    expect(await screen.findByRole('heading', { name: 'Week detail' })).toBeInTheDocument()
    expect(await screen.findByText('Completed week')).toBeInTheDocument()

    const list = screen.getByRole('list', { name: 'Week planned events' })
    const items = within(list).getAllByRole('listitem')

    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('E1')
    expect(items[1]).toHaveTextContent('E2')
  })

  it('shows readable not-found behavior for missing week and invalid week format', async () => {
    renderAt('/runs/run-a/weeks/99')
    expect(await screen.findByText("Week 99 is not present in this run's ordered season plan.")).toBeInTheDocument()

    renderAt('/runs/run-a/weeks/not-a-week')
    expect(await screen.findByText('Week must be a whole number in the URL (for example /weeks/12).')).toBeInTheDocument()
  })

  it('renders planned and persisted detail links for week events', async () => {
    renderAt('/runs/run-a/weeks/3')

    await screen.findByRole('heading', { name: 'Planned events in week' })
    const plannedLinks = screen.getAllByRole('link', { name: 'Planned detail' })
    const persistedLinks = screen.getAllByRole('link', { name: 'Persisted detail' })

    expect(plannedLinks.some((link) => link.getAttribute('href') === '/runs/run-a/calendar/E1')).toBe(true)
    expect(plannedLinks.some((link) => link.getAttribute('href') === '/runs/run-a/calendar/E2')).toBe(true)
    expect(persistedLinks.some((link) => link.getAttribute('href') === '/runs/run-a/events/E1')).toBe(true)
    expect(persistedLinks.some((link) => link.getAttribute('href') === '/runs/run-a/events/E2')).toBe(true)
  })

  it('renders related ranking and race snapshot links for week events only', async () => {
    renderAt('/runs/run-a/weeks/3')

    expect(await screen.findByRole('link', { name: 'Ranking snapshot #10' })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/ranking/10'
    )
    expect(screen.queryByRole('link', { name: 'Ranking snapshot #11' })).not.toBeInTheDocument()

    expect(screen.getByRole('link', { name: 'Race snapshot #20' })).toHaveAttribute('href', '/runs/run-a/snapshots/race/20')
    expect(screen.queryByRole('link', { name: 'Race snapshot #21' })).not.toBeInTheDocument()
  })

  it('renders previous and next week navigation in first-seen season order', async () => {
    renderAt('/runs/run-a/weeks/5')

    expect(await screen.findByRole('link', { name: 'W3' })).toHaveAttribute('href', '/runs/run-a/weeks/3')
    expect(screen.getByRole('link', { name: 'W7' })).toHaveAttribute('href', '/runs/run-a/weeks/7')

    cleanup()
    renderAt('/runs/run-a/weeks/7')
    const navSection = (await screen.findByRole('heading', { name: 'Week navigation' })).closest('article')
    expect(navSection).not.toBeNull()
    expect(navSection).toHaveTextContent('Next week:')
    expect(navSection).toHaveTextContent('None')
  })
})

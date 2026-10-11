import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EventsPage } from './EventsPage'
import { SnapshotsPage } from './SnapshotsPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listEvents: vi.fn(),
  getEvent: vi.fn(),
  getRun: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('history list ordering, detail selection, and states', () => {
  beforeEach(() => {
    vi.resetAllMocks()

    api.listEvents.mockResolvedValue({
      events: [
        { event_sequence: 2, event_id: 'E2', season: 2027, week: 9, template_id: null, tournament_result: null },
        { event_sequence: 1, event_id: 'E1', season: 2027, week: 8, template_id: null, tournament_result: null }
      ]
    })
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2027, seed: 42, config_version: null, config_fingerprint: null, world_id: 'official_fax_world', next_event_index: 1, total_events: 2, completed_event_ids: ['E2'] },
      season_state: {
        season: 2027,
        next_event_index: 1,
        completed_event_ids: ['E2'],
        ordered_events: [
          { event_id: 'E2', season: 2027, week: 9, tour: 'World Tour', category: 'Diamond', template_id: 'WT-DIAMOND' },
          { event_id: 'E1', season: 2027, week: 8, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
        ]
      }
    })
    api.getEvent.mockImplementation(async (_runId: string, eventId: string) => ({
      event_id: eventId,
      detail: `payload-${eventId}`
    }))
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'snapshot-4' } },
        { snapshot_sequence: 3, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: { name: 'snapshot-3' } }
      ]
    })
  })

  it('renders events in API order with default selected styling and click-to-update detail', async () => {
    const user = userEvent.setup()
    renderWithRoute(<EventsPage />, '/runs/run-a/events')

    const list = await screen.findByRole('list', { name: 'Events history list' })
    expect(screen.getByRole('list', { name: 'Current context' })).toBeInTheDocument()
    const items = within(list).getAllByRole('button')
    expect(items[0]).toHaveTextContent('2. E2')
    expect(items[1]).toHaveTextContent('1. E1')

    expect(items[0]).toHaveClass('is-selected')
    expect(items[0]).toHaveAttribute('aria-current', 'true')
    expect(items[1]).not.toHaveClass('is-selected')

    expect((await screen.findAllByText('E2')).length).toBeGreaterThan(0)
    expect(await screen.findByText(/payload-E2/)).toBeInTheDocument()

    expect(screen.getByRole('link', { name: /Open dedicated event detail page/i })).toHaveAttribute(
      'href',
      '/runs/run-a/events/E2'
    )

    await user.click(screen.getByRole('button', { name: /1\. E1/i }))

    await waitFor(() => {
      expect(screen.getAllByText('E1').length).toBeGreaterThan(0)
    })
    expect(await screen.findByText(/payload-E1/)).toBeInTheDocument()

    expect(screen.getByRole('button', { name: /1\. E1/i })).toHaveClass('is-selected')
    expect(screen.getByRole('button', { name: /2\. E2/i })).not.toHaveClass('is-selected')
  }, 10000)

  it('respects a valid selectedEventId query param and falls back when invalid or missing', async () => {
    const validView = renderWithRoute(<EventsPage />, '/runs/run-a/events?selectedEventId=E1')

    expect((await screen.findAllByText('E1')).length).toBeGreaterThan(0)
    expect(await screen.findByText(/payload-E1/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /1\. E1/i })).toHaveClass('is-selected')

    validView.unmount()

    renderWithRoute(<EventsPage />, '/runs/run-a/events?selectedEventId=UNKNOWN')

    expect((await screen.findAllByText('E2')).length).toBeGreaterThan(0)
    expect(await screen.findByText(/payload-E2/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /2\. E2/i })).toHaveClass('is-selected')
  })


  it('renders week and planned-event bridge links in selected event detail', async () => {
    renderWithRoute(<EventsPage />, '/runs/run-a/events')

    expect(await screen.findByRole('link', { name: /Open week detail page \(W9\)/i })).toHaveAttribute(
      'href',
      '/runs/run-a/weeks/9'
    )
    expect(screen.getByRole('link', { name: /Open planned-event detail page/i })).toHaveAttribute(
      'href',
      '/runs/run-a/calendar/E2'
    )
    expect(screen.getByRole('link', { name: /Open season calendar browser/i })).toHaveAttribute('href', '/runs/run-a/calendar')
  })

  it('shows readable ordered-plan fallback when persisted event has no plan match', async () => {
    api.listEvents.mockResolvedValue({
      events: [
        { event_sequence: 3, event_id: 'E-UNPLANNED', season: 2027, week: null, template_id: null, tournament_result: null },
        { event_sequence: 2, event_id: 'E2', season: 2027, week: 9, template_id: null, tournament_result: null }
      ]
    })

    renderWithRoute(<EventsPage />, '/runs/run-a/events')

    expect(await screen.findByRole('button', { name: /3\. E-UNPLANNED/i })).toBeInTheDocument()
    expect(screen.getByText('No ordered-plan match for this persisted event.')).toBeInTheDocument()
    expect(screen.getByText('No week context available for this persisted event.')).toBeInTheDocument()
  })

  it('filters events without reordering matching API-ordered items', async () => {
    const user = userEvent.setup()
    api.listEvents.mockResolvedValue({
      events: [
        { event_sequence: 3, event_id: 'BETA-EVENT', season: 2027, week: 8, template_id: 'BETA-TEMPLATE', tournament_result: null },
        { event_sequence: 2, event_id: 'E2', season: 2027, week: 9, template_id: null, tournament_result: null },
        { event_sequence: 1, event_id: 'ALPHA-EVENT', season: 2027, week: 8, template_id: 'ALPHA-TEMPLATE', tournament_result: null }
      ]
    })

    renderWithRoute(<EventsPage />, '/runs/run-a/events')

    await screen.findByRole('list', { name: 'Events history list' })
    await user.type(screen.getByLabelText(/Filter events by event or template/i), 'event')
    await user.selectOptions(screen.getByLabelText(/Filter events by week/i), '8')

    const list = screen.getByRole('list', { name: 'Events history list' })
    const buttons = within(list).getAllByRole('button')
    expect(buttons).toHaveLength(2)
    expect(buttons[0]).toHaveTextContent('3. BETA-EVENT')
    expect(buttons[1]).toHaveTextContent('1. ALPHA-EVENT')
  })

  it('renders ranking snapshots in API order with default selected styling and click-to-update detail', async () => {
    const user = userEvent.setup()
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 1, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'race-1' } }]
    })
    renderWithRoute(<SnapshotsPage mode="ranking" />, '/runs/run-a/snapshots/ranking')

    const list = await screen.findByRole('list', { name: 'Ranking snapshots list' })
    expect(screen.getByRole('list', { name: 'Current context' })).toBeInTheDocument()
    const snapshotItems = within(list).getAllByRole('button')
    expect(snapshotItems[0]).toHaveTextContent('4. WEEK')
    expect(snapshotItems[1]).toHaveTextContent('3. WEEK')

    expect(snapshotItems[0]).toHaveClass('is-selected')
    expect(snapshotItems[1]).not.toHaveClass('is-selected')
    expect(await screen.findByText(/snapshot-4/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open dedicated snapshot detail page/i })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/ranking/4'
    )
    expect(screen.getByRole('link', { name: /Open source event detail page/i })).toHaveAttribute('href', '/runs/run-a/events/E2')
    expect(screen.getByRole('link', { name: /Open planned-event detail page/i })).toHaveAttribute('href', '/runs/run-a/calendar/E2')
    expect(screen.getByRole('link', { name: /Open week detail page \(W9\)/i })).toHaveAttribute('href', '/runs/run-a/weeks/9')
    expect(screen.getByRole('link', { name: /Open season calendar browser/i })).toHaveAttribute('href', '/runs/run-a/calendar')
    expect(screen.getByRole('link', { name: /Open race snapshots for matching source_event_id/i })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/race'
    )

    await user.click(screen.getByRole('button', { name: /3\. WEEK/i }))
    expect(await screen.findByText(/snapshot-3/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /3\. WEEK/i })).toHaveClass('is-selected')
    expect(screen.getByRole('link', { name: /Open dedicated snapshot detail page/i })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/ranking/3'
    )
  })

  it('shows readable fallback when source_event_id is missing or has no ordered-plan match', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: null, payload: {} },
        { snapshot_sequence: 6, snapshot_kind: 'WEEK', source_event_id: 'E-UNPLANNED', payload: {} }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })

    const user = userEvent.setup()
    renderWithRoute(<SnapshotsPage mode="ranking" />, '/runs/run-a/snapshots/ranking')

    expect(await screen.findByText('No source_event_id')).toBeInTheDocument()
    expect(screen.getByText('Missing source_event_id')).toBeInTheDocument()
    expect(screen.getByText('Source persisted event detail unavailable.')).toBeInTheDocument()
    expect(screen.getByText('No ordered-plan match for source_event_id.')).toBeInTheDocument()
    expect(screen.getByText('No source week context available.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /6\. WEEK/i }))

    expect(await screen.findByText('No ordered-plan match for source_event_id.')).toBeInTheDocument()
    expect(screen.getByText('Not found')).toBeInTheDocument()
  })

  it('filters snapshots without reordering matching API-ordered items', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 12, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 8, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: {} },
        { snapshot_sequence: 5, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
    const user = userEvent.setup()
    renderWithRoute(<SnapshotsPage mode="ranking" />, '/runs/run-a/snapshots/ranking')

    await screen.findByRole('list', { name: 'Ranking snapshots list' })
    await user.selectOptions(screen.getByLabelText(/Filter snapshots by week/i), '9')
    await user.type(screen.getByLabelText(/Filter snapshots by source event/i), 'E2')

    const list = screen.getByRole('list', { name: 'Ranking snapshots list' })
    const buttons = within(list).getAllByRole('button')
    expect(buttons).toHaveLength(2)
    expect(buttons[0]).toHaveTextContent('12. WEEK')
    expect(buttons[1]).toHaveTextContent('5. WEEK')
  })

  it('respects selectedSequence query params for ranking and race snapshots', async () => {
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'race-9' } },
        { snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: { name: 'race-7' } }
      ]
    })

    const rankingView = renderWithRoute(<SnapshotsPage mode="ranking" />, '/runs/run-a/snapshots/ranking?selectedSequence=3')

    expect(await screen.findByText(/snapshot-3/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /3\. WEEK/i })).toHaveClass('is-selected')

    rankingView.unmount()

    renderWithRoute(<SnapshotsPage mode="race" />, '/runs/run-a/snapshots/race?selectedSequence=7')

    expect(await screen.findByText(/race-7/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /7\. WEEK/i })).toHaveClass('is-selected')
  })

  it('renders race snapshots route with readable empty state', async () => {
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })

    renderWithRoute(<SnapshotsPage mode="race" />, '/runs/run-a/snapshots/race')

    expect(await screen.findByText(/No snapshots are available for this run yet/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Race snapshots' })).toBeInTheDocument()
  })

  it('renders race snapshots route with readable error state', async () => {
    api.listRaceSnapshots.mockRejectedValue(new Error('race unavailable'))

    renderWithRoute(<SnapshotsPage mode="race" />, '/runs/run-a/snapshots/race')

    expect(await screen.findByText(/Failed to load snapshots history: race unavailable/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Race snapshots' })).toBeInTheDocument()
  })
})

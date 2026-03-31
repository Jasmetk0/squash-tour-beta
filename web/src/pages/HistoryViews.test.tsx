import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EventsPage } from './EventsPage'
import { SnapshotsPage } from './SnapshotsPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listEvents: vi.fn(),
  getEvent: vi.fn(),
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
    const items = within(list).getAllByRole('button')
    expect(items[0]).toHaveTextContent('2. E2')
    expect(items[1]).toHaveTextContent('1. E1')

    expect(items[0]).toHaveClass('is-selected')
    expect(items[0]).toHaveAttribute('aria-current', 'true')
    expect(items[1]).not.toHaveClass('is-selected')

    expect(await screen.findByText('E2')).toBeInTheDocument()
    expect(await screen.findByText(/payload-E2/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /1\. E1/i }))

    await waitFor(() => {
      expect(screen.getByText('E1')).toBeInTheDocument()
    })
    expect(await screen.findByText(/payload-E1/)).toBeInTheDocument()

    expect(screen.getByRole('button', { name: /1\. E1/i })).toHaveClass('is-selected')
    expect(screen.getByRole('button', { name: /2\. E2/i })).not.toHaveClass('is-selected')
  })

  it('renders ranking snapshots in API order with default selected styling and click-to-update detail', async () => {
    const user = userEvent.setup()
    renderWithRoute(<SnapshotsPage mode="ranking" />, '/runs/run-a/snapshots/ranking')

    const list = await screen.findByRole('list', { name: 'Ranking snapshots list' })
    const snapshotItems = within(list).getAllByRole('button')
    expect(snapshotItems[0]).toHaveTextContent('4. WEEK')
    expect(snapshotItems[1]).toHaveTextContent('3. WEEK')

    expect(snapshotItems[0]).toHaveClass('is-selected')
    expect(snapshotItems[1]).not.toHaveClass('is-selected')
    expect(await screen.findByText(/snapshot-4/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /3\. WEEK/i }))
    expect(await screen.findByText(/snapshot-3/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /3\. WEEK/i })).toHaveClass('is-selected')
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

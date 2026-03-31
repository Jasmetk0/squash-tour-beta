import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EventsPage } from './EventsPage'
import { SnapshotsPage } from './SnapshotsPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listEvents: vi.fn(),
  getEvent: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('history list ordering and errors', () => {
  beforeEach(() => {
    api.listEvents.mockResolvedValue({
      events: [
        { event_sequence: 2, event_id: 'E2' },
        { event_sequence: 1, event_id: 'E1' }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 2, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 1, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: {} }
      ]
    })
    api.listRaceSnapshots.mockRejectedValue(new Error('race unavailable'))
  })

  it('renders events and ranking snapshots in API order', async () => {
    const eventsView = renderWithRoute(<EventsPage />, '/runs/run-a/events')
    const items = await screen.findAllByRole('button')
    expect(items[0]).toHaveTextContent('#2 · E2')
    expect(items[1]).toHaveTextContent('#1 · E1')

    eventsView.unmount()
    renderWithRoute(<SnapshotsPage mode="ranking" />, '/runs/run-a/snapshots/ranking')
    const snapshotItems = await screen.findAllByRole('button')
    expect(snapshotItems[0]).toHaveTextContent('Seq 2')
    expect(snapshotItems[1]).toHaveTextContent('Seq 1')
  })

  it('shows readable error for failed snapshot query', async () => {
    renderWithRoute(<SnapshotsPage mode="race" />, '/runs/run-a/snapshots/race')
    expect(await screen.findByText(/Failed to load snapshots/i)).toBeInTheDocument()
  })
})

import { screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ActivityPage } from './ActivityPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunActivity: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('ActivityPage', () => {
  it('renders activity items in backend order with expected links', async () => {
    api.getRunActivity.mockResolvedValueOnce({
      run_id: 'run-a',
      items: [
        { kind: 'event', sequence: 1, label: 'Event E1', season: 2027, week: 1, event_id: 'E1', snapshot_sequence: null, source_event_id: null, related_run_id: null },
        { kind: 'ranking_snapshot', sequence: 1, label: 'Ranking snapshot 1', season: 2027, week: 1, event_id: null, snapshot_sequence: 1, source_event_id: 'E1', related_run_id: null },
        { kind: 'race_snapshot', sequence: 1, label: 'Race snapshot 1', season: 2027, week: 1, event_id: null, snapshot_sequence: 1, source_event_id: 'E1', related_run_id: null },
        { kind: 'finals_qualification', sequence: 2027, label: 'Finals qualification S2027', season: 2027, week: 40, event_id: null, snapshot_sequence: null, source_event_id: null, related_run_id: null },
        { kind: 'finals_result', sequence: 2027, label: 'Finals result S2027', season: 2027, week: 40, event_id: 'WORLD_TOUR_FINALS', snapshot_sequence: null, source_event_id: null, related_run_id: null },
        { kind: 'rollover', sequence: 2028, label: 'Season rollover S2027→S2028', season: 2028, week: null, event_id: null, snapshot_sequence: null, source_event_id: null, related_run_id: null },
        { kind: 'bootstrap_child', sequence: 2028, label: 'Bootstrapped child run run-b', season: 2028, week: null, event_id: null, snapshot_sequence: null, source_event_id: null, related_run_id: 'run-b' }
      ]
    })

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    const items = within(list).getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Event E1')
    expect(items[1]).toHaveTextContent('Ranking snapshot 1')

    expect(screen.getByRole('link', { name: 'Open event detail' })).toHaveAttribute('href', '/runs/run-a/events/E1')
    expect(screen.getByRole('link', { name: 'Open ranking snapshot' })).toHaveAttribute('href', '/runs/run-a/snapshots/ranking/1')
    expect(screen.getByRole('link', { name: 'Open race snapshot' })).toHaveAttribute('href', '/runs/run-a/snapshots/race/1')
    expect(screen.getByRole('link', { name: 'Open finals qualification detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/finals/qualification'
    )
    expect(screen.getByRole('link', { name: 'Open finals result detail' })).toHaveAttribute('href', '/runs/run-a/finals/result')
    expect(screen.getByRole('link', { name: 'Open rollover season detail' })).toHaveAttribute('href', '/runs/run-a/rollover/2028')
    expect(screen.getByRole('link', { name: 'Open child run' })).toHaveAttribute('href', '/runs/run-b')
  })

  it('renders readable empty and error states', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: [] })
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    expect(await screen.findByText(/No activity has been persisted/i)).toBeInTheDocument()

    api.getRunActivity.mockRejectedValueOnce(new Error('activity unavailable'))
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    expect(await screen.findByText(/Failed to load activity feed: activity unavailable/i)).toBeInTheDocument()
  })
})

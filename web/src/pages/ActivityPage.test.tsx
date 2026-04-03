import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ActivityPage } from './ActivityPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunActivity: vi.fn(),
  getRun: vi.fn(),
  listEvents: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

const baseItems = [
  {
    kind: 'event',
    sequence: 1,
    label: 'Event E1',
    season: 2027,
    week: 1,
    event_id: 'E1',
    snapshot_sequence: null,
    source_event_id: null,
    related_run_id: null
  },
  {
    kind: 'ranking_snapshot',
    sequence: 11,
    label: 'Ranking snapshot 11',
    season: 2027,
    week: null,
    event_id: null,
    snapshot_sequence: 11,
    source_event_id: 'E1',
    related_run_id: null
  },
  {
    kind: 'finals_result',
    sequence: 2027,
    label: 'Finals result S2027',
    season: 2027,
    week: 40,
    event_id: 'WORLD_TOUR_FINALS',
    snapshot_sequence: null,
    source_event_id: null,
    related_run_id: null
  },
  {
    kind: 'bootstrap_child',
    sequence: 2028,
    label: 'Bootstrapped child run run-b',
    season: 2028,
    week: null,
    event_id: null,
    snapshot_sequence: null,
    source_event_id: null,
    related_run_id: 'run-b'
  }
]

function mockContext(): void {
  api.getRun.mockResolvedValue({
    run: { run_id: 'run-a', season: 2027, seed: 1, config_version: null, config_fingerprint: null, next_event_index: 0, total_events: 1, completed_event_ids: [] },
    season_state: {
      season: 2027,
      next_event_index: 0,
      completed_event_ids: [],
      ordered_events: [
        { event_id: 'E1', season: 2027, week: 1, tour: 'WORLD', category: 'PLATINUM', template_id: 'T-E1' },
        { event_id: 'WORLD_TOUR_FINALS', season: 2027, week: 40, tour: 'WORLD', category: 'FINALS', template_id: 'T-FINALS' }
      ]
    }
  })
  api.listEvents.mockResolvedValue({
    run_id: 'run-a',
    events: [
      { event_sequence: 1, event_id: 'E1', season: 2027, week: 1, template_id: 'T-E1', tournament_result: null },
      { event_sequence: 15, event_id: 'WORLD_TOUR_FINALS', season: 2027, week: 40, template_id: 'T-FINALS', tournament_result: null }
    ]
  })
}

describe('ActivityPage', () => {
  it('renders activity items in backend order', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    const options = within(list).getAllByRole('button')
    expect(options[0]).toHaveTextContent('1. Event E1')
    expect(options[1]).toHaveTextContent('2. Ranking snapshot 11')
    expect(options[2]).toHaveTextContent('3. Finals result S2027')
    expect(options[3]).toHaveTextContent('4. Bootstrapped child run run-b')
  })

  it('filters without reordering matches', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    const user = userEvent.setup()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    await screen.findByRole('list', { name: 'Run activity feed list' })

    await user.selectOptions(screen.getByLabelText('Filter activity by season'), '2027')
    await user.type(screen.getByLabelText('Filter activity by label or identifier text'), 's')

    const filteredList = screen.getByRole('list', { name: 'Run activity feed list' })
    const filteredOptions = within(filteredList).getAllByRole('button')
    expect(filteredOptions).toHaveLength(2)
    expect(filteredOptions[0]).toHaveTextContent('Ranking snapshot 11')
    expect(filteredOptions[1]).toHaveTextContent('Finals result S2027')
  })

  it('uses derived week context in week filter/options without reordering', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    const user = userEvent.setup()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    await screen.findByRole('list', { name: 'Run activity feed list' })

    expect(screen.getByRole('option', { name: 'W1' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Filter activity by week'), '1')

    const filteredList = screen.getByRole('list', { name: 'Run activity feed list' })
    const filteredOptions = within(filteredList).getAllByRole('button')
    expect(filteredOptions).toHaveLength(2)
    expect(filteredOptions[0]).toHaveTextContent('1. Event E1')
    expect(filteredOptions[1]).toHaveTextContent('2. Ranking snapshot 11')
  })

  it('shows selected detail bridge links for key item kinds', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    const user = userEvent.setup()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    await user.click(within(list).getByRole('button', { name: /Ranking snapshot 11/i }))

    expect(screen.getByRole('link', { name: 'Open ranking snapshot detail' })).toHaveAttribute('href', '/runs/run-a/snapshots/ranking/11')
    expect(screen.getByRole('link', { name: 'Open source planned-event detail' })).toHaveAttribute('href', '/runs/run-a/calendar/E1')

    await user.click(within(list).getByRole('button', { name: /Finals result S2027/i }))
    expect(screen.getByRole('link', { name: 'Open finals result detail' })).toHaveAttribute('href', '/runs/run-a/finals/result')

    await user.click(within(list).getByRole('button', { name: /Bootstrapped child run run-b/i }))
    expect(screen.getByRole('link', { name: 'Open child run detail' })).toHaveAttribute('href', '/runs/run-b')
    expect(screen.getByRole('link', { name: 'Open child run season chain' })).toHaveAttribute('href', '/runs/run-b/season-chain')
  })

  it('renders week-detail links only when week context is meaningful', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    const user = userEvent.setup()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    await user.click(within(list).getByRole('button', { name: /Event E1/i }))
    expect(screen.getByRole('link', { name: 'Open week detail page (W1)' })).toHaveAttribute('href', '/runs/run-a/weeks/1')

    await user.click(within(list).getByRole('button', { name: /Bootstrapped child run run-b/i }))
    expect(screen.queryByRole('link', { name: /Open week detail page/i })).not.toBeInTheDocument()
    expect(screen.getByText('Not meaningful for this activity kind')).toBeInTheDocument()
  })

  it('shows readable fallback when selected item has no direct links', async () => {
    api.getRunActivity.mockResolvedValueOnce({
      run_id: 'run-a',
      items: [
        {
          kind: 'bootstrap_child',
          sequence: 2028,
          label: 'Bootstrap child without related run',
          season: 2028,
          week: null,
          event_id: null,
          snapshot_sequence: null,
          source_event_id: null,
          related_run_id: null
        }
      ]
    })
    mockContext()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    expect(await screen.findByText('No direct bridge links available for this activity item.')).toBeInTheDocument()
  })

  it('renders admin wildcard assignment with planned-event bridge links', async () => {
    api.getRunActivity.mockResolvedValueOnce({
      run_id: 'run-a',
      items: [
        {
          kind: 'admin_wildcard_assignment',
          sequence: 1,
          label: 'Commissioner wildcard assignment (E1)',
          season: null,
          week: null,
          event_id: 'E1',
          snapshot_sequence: null,
          source_event_id: null,
          related_run_id: null
        }
      ]
    })
    mockContext()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    expect(await screen.findByRole('link', { name: 'Open wildcard event planned detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/calendar/E1'
    )
    expect(screen.getByRole('link', { name: 'Open wildcard event persisted detail' })).toHaveAttribute('href', '/runs/run-a/events/E1')
    expect(screen.getByRole('link', { name: 'Open week detail page (W1)' })).toHaveAttribute('href', '/runs/run-a/weeks/1')
    expect(screen.queryByText('Not meaningful for this activity kind')).not.toBeInTheDocument()
  })

  it('renders admin pre-draw replacement with planned-event bridge links', async () => {
    api.getRunActivity.mockResolvedValueOnce({
      run_id: 'run-a',
      items: [
        {
          kind: 'admin_pre_draw_withdrawal_replacement',
          sequence: 1,
          label: 'Commissioner pre-draw withdrawal replacement (E1)',
          season: 2027,
          week: 1,
          event_id: 'E1',
          snapshot_sequence: null,
          source_event_id: null,
          related_run_id: null
        }
      ]
    })
    mockContext()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    expect(await screen.findByRole('link', { name: 'Open pre-draw event planned detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/calendar/E1'
    )
    expect(screen.getByRole('link', { name: 'Open pre-draw event persisted detail' })).toHaveAttribute('href', '/runs/run-a/events/E1')
    expect(screen.getByRole('link', { name: 'Open week detail page (W1)' })).toHaveAttribute('href', '/runs/run-a/weeks/1')
  })

  it('does not fabricate snapshot source links when context is absent', async () => {
    api.getRunActivity.mockResolvedValueOnce({
      run_id: 'run-a',
      items: [
        {
          kind: 'ranking_snapshot',
          sequence: 22,
          label: 'Ranking snapshot unknown source',
          season: 2027,
          week: null,
          event_id: null,
          snapshot_sequence: 22,
          source_event_id: 'UNKNOWN_EVENT',
          related_run_id: null
        }
      ]
    })
    mockContext()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    expect(await screen.findByRole('link', { name: 'Open ranking snapshot detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/ranking/22'
    )
    expect(screen.getByText('No ordered-plan context for this snapshot source event.')).toBeInTheDocument()
    expect(screen.getByText('No persisted-event context for this snapshot source event.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open source planned-event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open source persisted event detail' })).not.toBeInTheDocument()
  })

  it('honors selected-item deep links from query params', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()

    renderWithRoute(<ActivityPage />, '/runs/run-a/activity?selectedItem=2')

    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    const selectedButton = within(list).getByRole('button', { name: /3\. Finals result S2027/i })
    expect(selectedButton).toHaveAttribute('aria-current', 'true')
    expect(screen.getByRole('link', { name: 'Open finals result detail' })).toHaveAttribute('href', '/runs/run-a/finals/result')
  })

  it('renders readable empty and no-match states', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: [] })
    mockContext()
    const first = renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    expect(await screen.findByText(/No activity has been persisted/i)).toBeInTheDocument()
    first.unmount()

    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    const user = userEvent.setup()
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    await screen.findByRole('list', { name: 'Run activity feed list' })
    await user.type(screen.getByLabelText('Filter activity by label or identifier text'), 'nope')
    expect(await screen.findByText('No activity items match the current filters.')).toBeInTheDocument()
    expect(screen.getByText('Select an activity item to inspect details.')).toBeInTheDocument()
  })
})

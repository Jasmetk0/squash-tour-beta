import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
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
// Legacy assertions verify the existing English copy; CS/EN transitions have separate coverage.
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

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

  it('numbers planned event positions from one consistently with snapshot and activity history', async () => {
    renderWithRoute(<EventsPage />, '/runs/run-a/events')
    const list = await screen.findByRole('list', { name: 'Events history list' })
    const items = within(list).getAllByRole('button')
    expect(items[0]).toHaveTextContent('2. E2')
    expect(items[0]).toHaveTextContent('Plan #1')
    expect(items[1]).toHaveTextContent('1. E1')
    expect(items[1]).toHaveTextContent('Plan #2')
    expect(screen.queryByText('Plan #0')).not.toBeInTheDocument()
  })

  it('does not preserve a stale planned-event link when a formerly valid run-context refresh fails', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, seed: 42, next_event_index: 1,
        total_events: 2, completed_event_ids: ['E2'] },
      season_state: { season: 2027, next_event_index: 1,
        completed_event_ids: ['E2'], ordered_events: [
          { event_id: 'E2', season: 2027, week: 9, tour: 'World Tour',
            category: 'Diamond', template_id: 'WT-DIAMOND' },
          { event_id: 'E1', season: 2027, week: 8, tour: 'Elite Tour',
            category: 'Gold', template_id: 'ET-GOLD' }
        ] }
    }).mockRejectedValueOnce(new Error('temporary season plan outage'))
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/runs/run-a/events']}>
          <Routes><Route path="/runs/:runId/events" element={<EventsPage />} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
    expect(await screen.findByRole('link', { name: 'Open planned-event detail page' })).toBeInTheDocument()
    await act(async () => { await client.refetchQueries({ queryKey: ['run', 'run-a'] }) })
    expect(await screen.findByText('Failed to load planned season context: temporary season plan outage')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open planned-event detail page' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open dedicated event detail page' }))
      .toHaveAttribute('href', '/runs/run-a/events/E2')
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

  it.each([
    ['stored sequence', { event_sequence: 900 }],
    ['stored season', { season: 2030 }],
    ['stored week', { week: 44 }]
  ])('rejects event details contradicting the list %s even when event_id agrees', async (_field, conflicting) => {
    api.getEvent.mockResolvedValueOnce({
      event_id: 'E2', event_sequence: 2, season: 2027, week: 9,
      template_id: null, tournament_result: null,
      detail: 'UNTRUSTED_DETAIL', ...conflicting
    })
    renderWithRoute(<EventsPage />, '/runs/run-a/events')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Event detail does not match the selected event; its payload is hidden.'
    )
    expect(screen.queryByText(/UNTRUSTED_DETAIL/)).not.toBeInTheDocument()
    expect(api.getEvent).toHaveBeenCalledWith('run-a', 'E2')
  })

  it('preserves a stored historical event but hides links into the wrong current season', async () => {
    api.listEvents.mockResolvedValueOnce({
      run_id: 'run-a',
      events: [{ event_sequence: 2, event_id: 'E2', season: 2026, week: 9,
        template_id: 'WT-OLD', tournament_result: null }]
    })
    renderWithRoute(<EventsPage />, '/runs/run-a/events')
    expect(await screen.findByText('Current-season week link unavailable for this historic event.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open planned-event detail page' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail page/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open dedicated event detail page' })).toHaveAttribute('href', '/runs/run-a/events/E2')
  })

  it('rejects a same-Run but stale season_state plan without hiding persisted events', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, seed: 42, next_event_index: 1,
        total_events: 1, completed_event_ids: [] },
      season_state: { season: 2026, next_event_index: 1, completed_event_ids: [],
        ordered_events: [{ event_id: 'E2', season: 2026, week: 9, tour: 'WORLD',
          category: 'Gold', template_id: 'ST-ALE' }] }
    })
    renderWithRoute(<EventsPage />, '/runs/run-a/events')
    expect(await screen.findByText('Run season and ordered plan disagree. Planned links are unavailable.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open planned-event detail page' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open dedicated event detail page' })).toHaveAttribute('href', '/runs/run-a/events/E2')
  })

  it('keeps a snapshot payload but rejects cross-season source event plan/weekly bridges', async () => {
    api.listEvents.mockResolvedValueOnce({
      run_id: 'run-a',
      events: [{ event_sequence: 2, event_id: 'E2', season: 2026, week: 9,
        template_id: 'WT-OLD', tournament_result: null }]
    })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [] })
    renderWithRoute(<SnapshotsPage mode="ranking" />, '/runs/run-a/snapshots/ranking')
    expect(await screen.findByText(/snapshot-4/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open planned-event detail page' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open week detail page (W9)' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open dedicated snapshot detail page' })).toHaveAttribute(
      'href', '/runs/run-a/snapshots/ranking/4'
    )
  })

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


  it('selects each reused event ID by stable persisted sequence without merging rows or leaking another detail', async () => {
    const user = userEvent.setup()
    api.listEvents.mockResolvedValueOnce({
      run_id: 'run-a',
      events: [
        { event_sequence: 7, event_id: 'REUSED', season: 2027, week: 9,
          template_id: 'CURRENT', tournament_result: { winner: 'P7' } },
        { event_sequence: 2, event_id: 'REUSED', season: 2026, week: 32,
          template_id: 'HISTORICAL', tournament_result: { winner: 'P2' } }
      ]
    })
    // This ID-only API resolves the current-season event; it cannot identify
    // the historic record from event_id alone.
    api.getEvent.mockResolvedValue({
      event_id: 'REUSED', event_sequence: 7, season: 2027, week: 9,
      detail: 'CURRENT_SEASON_PAYLOAD'
    })
    renderWithRoute(<EventsPage />, '/runs/run-a/events?selectedEventId=REUSED&selectedEventSequence=2')

    const list = await screen.findByRole('list', { name: 'Events history list' })
    const items = within(list).getAllByRole('button')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('7. REUSED')
    expect(items[1]).toHaveTextContent('2. REUSED')
    expect(items[1]).toHaveAttribute('aria-current', 'true')
    expect(items[0]).not.toHaveAttribute('aria-current', 'true')
    expect(await screen.findByText('Event detail does not match the selected event; its payload is hidden.')).toBeInTheDocument()
    expect(screen.queryByText(/CURRENT_SEASON_PAYLOAD/)).not.toBeInTheDocument()
    expect(screen.getByText('Unavailable: the event ID identifies multiple stored records.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open dedicated event detail page' })).not.toBeInTheDocument()
    expect(screen.getByText('Event ID is reused in this Run. Use the selected sequence to identify the stored record; direct ID-only navigation is unavailable.')).toBeInTheDocument()

    await user.click(items[0])
    expect(items[0]).toHaveAttribute('aria-current', 'true')
    expect(items[1]).not.toHaveAttribute('aria-current', 'true')
    expect(await screen.findByText(/CURRENT_SEASON_PAYLOAD/)).toBeInTheDocument()
    expect(api.getEvent).toHaveBeenCalledTimes(2)
    await user.click(items[1])
    expect(items[1]).toHaveAttribute('aria-current', 'true')
    expect(screen.queryByText(/CURRENT_SEASON_PAYLOAD/)).not.toBeInTheDocument()
  })

  it('accepts legacy event-ID bookmarks but rejects unverifiable ID-only details for reused IDs', async () => {
    api.listEvents.mockResolvedValueOnce({
      run_id: 'run-a',
      events: [
        { event_sequence: 7, event_id: 'DUP', season: 2027, week: 9,
          template_id: null, tournament_result: null },
        { event_sequence: 2, event_id: 'DUP', season: 2026, week: 32,
          template_id: null, tournament_result: null }
      ]
    })
    api.getEvent.mockResolvedValue({ event_id: 'DUP', detail: 'UNVERIFIABLE_SAME_ID_PAYLOAD' })
    renderWithRoute(<EventsPage />, '/runs/run-a/events?selectedEventId=DUP&selectedEventSequence=7junk')

    const list = await screen.findByRole('list', { name: 'Events history list' })
    const buttons = within(list).getAllByRole('button')
    expect(buttons[0]).toHaveAttribute('aria-current', 'true')
    expect(buttons[1]).not.toHaveAttribute('aria-current', 'true')
    expect(await screen.findByText('Event detail does not match the selected event; its payload is hidden.')).toBeInTheDocument()
    expect(screen.queryByText(/UNVERIFIABLE_SAME_ID_PAYLOAD/)).not.toBeInTheDocument()
    expect(api.getEvent).toHaveBeenCalledWith('run-a', 'DUP')
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
    expect(screen.getByRole('link', { name: /Open race snapshot history/i })).toHaveAttribute(
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

  it.each(['3junk', '3.5', '3e0', '-3', '999999999999999999999999'])(
    'does not select an unrelated stored snapshot for malformed selectedSequence=%s',
    async (invalidSequence) => {
      api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
      renderWithRoute(<SnapshotsPage mode="ranking" />, `/runs/run-a/snapshots/ranking?selectedSequence=${encodeURIComponent(invalidSequence)}`)
      const list = await screen.findByRole('list', { name: 'Ranking snapshots list' })
      await waitFor(() => expect(within(list).getByRole('button', { name: /4\. WEEK/i })).toHaveClass('is-selected'))
      expect(within(list).getByRole('button', { name: /3\. WEEK/i })).not.toHaveClass('is-selected')
      expect(await screen.findByText(/snapshot-4/)).toBeInTheDocument()
      expect(api.listRankingSnapshots).toHaveBeenCalledWith('run-a')
    }
  )

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

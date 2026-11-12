import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
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
// Legacy assertions verify the existing English copy; CS/EN transitions have separate coverage.
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

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
    run: { run_id: 'run-a', season: 2027, seed: 1, config_version: null, config_fingerprint: null, world_id: 'official_fax_world', next_event_index: 0, total_events: 1, completed_event_ids: [] },
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

function ActivityHistoryHarness(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  return <>
    <ActivityPage />
    <output data-testid="activity-url">{location.search}</output>
    <button type="button" onClick={() => navigate(-1)}>Browser back</button>
  </>
}

function renderActivityWithHistory(route: string): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}>
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/runs/:runId/*" element={<ActivityHistoryHarness />} />
      </Routes>
    </MemoryRouter>
  </QueryClientProvider>)
}

describe('ActivityPage', () => {

  it.each([
    ['historical-first', [
      { event_sequence: 2, event_id: 'E1', season: 2026, week: 35, template_id: 'OLD', tournament_result: null },
      { event_sequence: 11, event_id: 'E1', season: 2027, week: 1, template_id: 'NEW', tournament_result: null }
    ]],
    ['current-first', [
      { event_sequence: 11, event_id: 'E1', season: 2027, week: 1, template_id: 'NEW', tournament_result: null },
      { event_sequence: 2, event_id: 'E1', season: 2026, week: 35, template_id: 'OLD', tournament_result: null }
    ]]
  ])('does not borrow weeks or source links from duplicated event history (%s)', async (_name, duplicates) => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: [{
      kind: 'ranking_snapshot', sequence: 10, label: 'Historic snapshot E1',
      season: 2027, week: null, event_id: null, snapshot_sequence: 10,
      source_event_id: 'E1', related_run_id: null
    }] })
    mockContext()
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-a', events: duplicates })
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')

    expect(await screen.findByText('Activity source event ID has conflicting seasons. Its navigation links are unavailable.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open ranking snapshot detail' }))
      .toHaveAttribute('href', '/runs/run-a/snapshots/ranking/10')
    expect(screen.queryByRole('link', { name: 'Open source persisted event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open source planned-event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail page/i })).not.toBeInTheDocument()
    expect(screen.queryByText('W35')).not.toBeInTheDocument()
    expect(screen.queryByText('W1')).not.toBeInTheDocument()
    expect(screen.getByText('No week context available')).toBeInTheDocument()
  })

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

  it('renders admin late-replacement with planned-event bridge links', async () => {
    api.getRunActivity.mockResolvedValueOnce({
      run_id: 'run-a',
      items: [
        {
          kind: 'admin_late_replacement_lucky_loser',
          sequence: 1,
          label: 'Commissioner late replacement lucky loser (E1)',
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

    expect(await screen.findByRole('link', { name: 'Open late-replacement event planned detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/calendar/E1'
    )
    expect(screen.getByRole('link', { name: 'Open late-replacement event persisted detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/events/E1'
    )
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

  it.each(['2junk', '2.5', '2e0', '-2', '999999999999999999999999'])(
    'falls back to the first stored activity rather than parsing malformed selectedItem=%s',
    async (invalid) => {
      api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
      mockContext()
      renderWithRoute(<ActivityPage />, `/runs/run-a/activity?selectedItem=${encodeURIComponent(invalid)}`)
      const list = await screen.findByRole('list', { name: 'Run activity feed list' })
      expect(within(list).getByRole('button', { name: /1\. Event E1/i }))
        .toHaveAttribute('aria-current', 'true')
      expect(within(list).getByRole('button', { name: /3\. Finals result S2027/i }))
        .not.toHaveAttribute('aria-current', 'true')
      expect(await screen.findByRole('link', { name: 'Open persisted event detail' }))
        .toHaveAttribute('href', '/runs/run-a/events/E1')
    }
  )

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
  it('does not invent planned detail links for a technical record without matching run plan evidence', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: [{
      kind: 'admin_wildcard_assignment', sequence: 7, label: 'Wildcard E-NOT-PLANNED',
      season: 2027, week: null, event_id: 'E-NOT-PLANNED', source_event_id: null,
      snapshot_sequence: null, related_run_id: null
    }] })
    mockContext()
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    expect(within(list).getByRole('button', { name: /Wildcard E-NOT-PLANNED/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open wildcard event planned detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open wildcard event persisted detail' })).not.toBeInTheDocument()
    expect(screen.getAllByText('No ordered-plan match').length).toBeGreaterThan(0)
  })

  it('keeps technical source context unavailable when the run context read fails', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: [{
      kind: 'admin_pre_draw_withdrawal_replacement', sequence: 8, label: 'Pre-draw E1',
      season: 2027, week: null, event_id: 'E1', source_event_id: null,
      snapshot_sequence: null, related_run_id: null
    }] })
    mockContext()
    api.getRun.mockRejectedValueOnce(new Error('plan offline'))
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    expect(await screen.findByText('Failed to load ordered-plan context: plan offline')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open pre-draw event planned detail' })).not.toBeInTheDocument()
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
  })

  it('keeps historic snapshot activity but refuses to borrow week and plan links from a reused event ID', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: [{
      kind: 'ranking_snapshot', sequence: 9, label: 'Historic ranking E1',
      season: 2026, week: null, event_id: null, snapshot_sequence: 9,
      source_event_id: 'E1', related_run_id: null
    }] })
    mockContext()
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    expect(await screen.findByRole('link', { name: 'Open ranking snapshot detail' })).toHaveAttribute(
      'href', '/runs/run-a/snapshots/ranking/9'
    )
    expect(screen.queryByRole('link', { name: 'Open source planned-event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open source persisted event detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail page/i })).not.toBeInTheDocument()
  })

  it('reports inconsistent current-season run/calendar evidence without guessing administrative links', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: [{
      kind: 'admin_wildcard_assignment', sequence: 12, label: 'Admin wildcard E1',
      season: null, week: null, event_id: 'E1', snapshot_sequence: null,
      source_event_id: null, related_run_id: null
    }] })
    mockContext()
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, next_event_index: 0, total_events: 1,
        completed_event_ids: [] },
      season_state: { season: 2026, next_event_index: 0, completed_event_ids: [],
        ordered_events: [{ event_id: 'E1', season: 2026, week: 1, tour: 'WORLD',
          category: 'PLATINUM', template_id: 'T-E1' }] }
    })
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    expect(await screen.findByText('Run season and ordered plan disagree. Planned links are unavailable.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open wildcard event planned detail' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail page/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open wildcard event persisted detail' })).toHaveAttribute(
      'href', '/runs/run-a/events/E1'
    )
  })

  it.each([
    ['event', 'Open persisted event detail'],
    ['ranking_snapshot', 'Open source persisted event detail'],
    ['admin_wildcard_assignment', 'Open wildcard event persisted detail']
  ])('does not cross-link seasonless %s activity when persisted and planned event IDs collide', async (kind, unsafeLink) => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: [{
      kind, sequence: 9, label: 'Ambiguous E1',
      season: null, week: null,
      event_id: kind === 'ranking_snapshot' ? null : 'E1',
      source_event_id: kind === 'ranking_snapshot' ? 'E1' : null,
      snapshot_sequence: kind === 'ranking_snapshot' ? 9 : null,
      related_run_id: null
    }] })
    mockContext()
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-a', events: [
      { event_sequence: 9, event_id: 'E1', season: 2026, week: 31,
        template_id: 'OLD-E1', tournament_result: null }
    ] })
    renderWithRoute(<ActivityPage />, '/runs/run-a/activity')
    expect(await screen.findByText('Activity source event ID has conflicting seasons. Its navigation links are unavailable.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: unsafeLink })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open .*planned.event detail/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail page/i })).not.toBeInTheDocument()
    expect(screen.queryByText('W31')).not.toBeInTheDocument()
    if (kind === 'ranking_snapshot') {
      expect(screen.getByRole('link', { name: 'Open ranking snapshot detail' })).toHaveAttribute(
        'href', '/runs/run-a/snapshots/ranking/9'
      )
    }
  })

  it('restores URL filters and selected original index from a bookmarked Run activity link', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    renderActivityWithHistory('/runs/run-a/activity?activityKind=ranking_snapshot&activitySeason=2027&activityWeek=1&activityText=Ranking&selectedItem=1&from=bookmarks')
    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    const buttons = within(list).getAllByRole('button')
    expect(buttons).toHaveLength(1)
    expect(buttons[0]).toHaveTextContent('Ranking snapshot 11')
    expect(screen.getByLabelText('Filter activity by kind')).toHaveValue('ranking_snapshot')
    expect(screen.getByLabelText('Filter activity by season')).toHaveValue('2027')
    expect(screen.getByLabelText('Filter activity by week')).toHaveValue('1')
    expect(screen.getByLabelText('Filter activity by label or identifier text')).toHaveValue('Ranking')
    expect(screen.getByRole('link', { name: 'Open ranking snapshot detail' })).toHaveAttribute(
      'href', '/runs/run-a/snapshots/ranking/11'
    )
    const params = new URLSearchParams(screen.getByTestId('activity-url').textContent!)
    expect(params.get('selectedItem')).toBe('1')
    expect(params.get('from')).toBe('bookmarks')
    expect(api.getRunActivity).toHaveBeenCalledWith('run-a')
  })

  it('writes filter changes into the URL, preserves unrelated parameters, and resets selection', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    const user = userEvent.setup()
    renderActivityWithHistory('/runs/run-a/activity?from=other-page&selectedItem=2')
    await screen.findByRole('list', { name: 'Run activity feed list' })

    await user.selectOptions(screen.getByLabelText('Filter activity by kind'), 'event')
    let params = new URLSearchParams(screen.getByTestId('activity-url').textContent!)
    expect(params.get('activityKind')).toBe('event')
    expect(params.get('selectedItem')).toBeNull()
    expect(params.get('from')).toBe('other-page')

    await user.type(screen.getByLabelText('Filter activity by label or identifier text'), 'E1')
    params = new URLSearchParams(screen.getByTestId('activity-url').textContent!)
    expect(params.get('activityKind')).toBe('event')
    expect(params.get('activityText')).toBe('E1')
    expect(screen.getByRole('link', { name: 'Open persisted event detail' })).toHaveAttribute(
      'href', '/runs/run-a/events/E1'
    )
    await user.click(screen.getByRole('button', { name: 'Reset filters' }))
    params = new URLSearchParams(screen.getByTestId('activity-url').textContent!)
    expect(params.get('from')).toBe('other-page')
    expect(params.has('selectedItem')).toBe(false)
    expect(['activityKind', 'activitySeason', 'activityWeek', 'activityText'].every(k => !params.has(k))).toBe(true)
    expect(within(screen.getByRole('list', { name: 'Run activity feed list' })).getAllByRole('button')).toHaveLength(4)
    expect(api.listEvents).toHaveBeenCalled()
  })

  it('keeps unknown URL filters restrictive and shows an inspectable missing value', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    renderActivityWithHistory('/runs/run-a/activity?activityKind=unknown_kind&activitySeason=9999&activityWeek=1000&from=deep-link')
    expect(await screen.findByText('No activity items match the current filters.')).toBeInTheDocument()
    expect(screen.getByLabelText('Filter activity by kind')).toHaveValue('unknown_kind')
    expect(screen.getByRole('option', { name: 'unknown_kind · Unavailable' })).toBeInTheDocument()
    expect(screen.getByLabelText('Filter activity by season')).toHaveValue('9999')
    expect(screen.getByLabelText('Filter activity by week')).toHaveValue('1000')
    expect(screen.queryByRole('link', { name: 'Open persisted event detail' })).not.toBeInTheDocument()
    expect(screen.getByTestId('activity-url')).toHaveTextContent('activityKind=unknown_kind')
    await userEvent.click(screen.getByRole('button', { name: 'Reset filters' }))
    expect(within(await screen.findByRole('list', { name: 'Run activity feed list' })).getAllByRole('button')).toHaveLength(4)
    expect(new URLSearchParams(screen.getByTestId('activity-url').textContent!).get('from')).toBe('deep-link')
  })

  it('restores prior filters when navigating back without replacing selected activity history', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    const user = userEvent.setup()
    renderActivityWithHistory('/runs/run-a/activity?from=history')
    await screen.findByRole('list', { name: 'Run activity feed list' })
    await user.selectOptions(screen.getByLabelText('Filter activity by kind'), 'event')
    await user.selectOptions(screen.getByLabelText('Filter activity by season'), '2027')
    let params = new URLSearchParams(screen.getByTestId('activity-url').textContent!)
    expect(params.get('activityKind')).toBe('event')
    expect(params.get('activitySeason')).toBe('2027')
    await user.click(screen.getByRole('button', { name: 'Browser back' }))
    expect(screen.getByLabelText('Filter activity by kind')).toHaveValue('event')
    expect(screen.getByLabelText('Filter activity by season')).toHaveValue('')
    await user.click(screen.getByRole('button', { name: 'Browser back' }))
    expect(screen.getByLabelText('Filter activity by kind')).toHaveValue('')
    expect(within(screen.getByRole('list', { name: 'Run activity feed list' })).getAllByRole('button')).toHaveLength(4)
    expect(new URLSearchParams(screen.getByTestId('activity-url').textContent!).get('from')).toBe('history')
  })

  it('keeps active URL filters while selecting another activity item', async () => {
    api.getRunActivity.mockResolvedValueOnce({ run_id: 'run-a', items: baseItems })
    mockContext()
    const user = userEvent.setup()
    renderActivityWithHistory('/runs/run-a/activity?activitySeason=2027&from=timeline')
    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    await user.click(within(list).getByRole('button', { name: /Ranking snapshot 11/i }))
    const params = new URLSearchParams(screen.getByTestId('activity-url').textContent!)
    expect(params.get('selectedItem')).toBe('1')
    expect(params.get('activitySeason')).toBe('2027')
    expect(params.get('from')).toBe('timeline')
    expect(screen.getByRole('link', { name: 'Open ranking snapshot detail' })).toHaveAttribute(
      'href', '/runs/run-a/snapshots/ranking/11'
    )
    expect(api.getRunActivity).toHaveBeenCalledTimes(1)
  })

})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ViewerRunTournamentDetailPage, ViewerRunTournamentsPage } from './ViewerRunTournamentsPage'

const api = vi.hoisted(() => ({
  getEvent: vi.fn(),
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

function renderViewerTournamentRoute(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/viewer/runs/:runId/tournaments" element={<ViewerRunTournamentsPage />} />
          <Route path="/viewer/runs/:runId/tournaments/:eventId" element={<ViewerRunTournamentDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function mockRunMetadata(): void {
  api.getRun.mockResolvedValue({
    run: {
      run_id: 'viewer-run-1',
      season: 2027,
      seed: 42,
      config_version: 'v1',
      config_fingerprint: 'fp',
      next_event_index: 1,
      total_events: 2,
      completed_event_ids: ['EVENT-1']
    },
    season_state: {
      season: 2027,
      next_event_index: 1,
      completed_event_ids: ['EVENT-1'],
      ordered_events: [
        { event_id: 'EVENT-1', season: 2027, week: 3, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
        { event_id: 'EVENT-2', season: 2027, week: 4, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
      ]
    }
  })
}

function mockEvents(): void {
  api.listEvents.mockResolvedValue({
    run_id: 'viewer-run-1',
    events: [
      {
        event_sequence: 8,
        event_id: 'EVENT-1',
        season: 2027,
        week: 3,
        template_id: 'WT-PLAT',
        tournament_result: {
          summary: {
            champion: { player_id: 'P-001', name: 'Ali Farag', country: 'EGY' },
            match_count: 31,
            status: 'completed',
            secret_debug_marker: 'event-list-payload-should-not-render',
            matches: [{ label: 'Match 1 should not render from raw payload' }]
          }
        }
      },
      { event_sequence: 9, event_id: 'EVENT-2', season: 2027, week: 4, template_id: 'ET-GOLD', tournament_result: null }
    ]
  })
}

function expectNoForbiddenViewerActions(): void {
  const forbiddenLabels = [
    'Simulate',
    'Generate',
    'Persist',
    'Apply',
    'Execute',
    'Delete',
    'Edit',
    'Import',
    'Rollover',
    'Rebuild',
    'Override',
    'Save changes',
    'Commit',
    'Regenerate',
    'Repair',
    'Merge',
    'Overwrite'
  ]

  forbiddenLabels.forEach((label) => {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  })
}

describe('ViewerRunTournamentsPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
    mockEvents()
  })

  it('renders parseable tournament result metadata on the sports-facing tournaments list', async () => {
    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments')

    expect(await screen.findByRole('heading', { name: 'Tournaments' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-1').length).toBeGreaterThan(0)
    const eventOne = (await screen.findByText('EVENT-1')).closest('li') as HTMLElement
    expect(screen.getByText('EVENT-2')).toBeInTheDocument()
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()
    expect(screen.getByText('ET-GOLD')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour').length).toBeGreaterThan(0)
    expect(within(eventOne).getByText('Champion')).toBeInTheDocument()
    expect(within(eventOne).getByRole('link', { name: 'Ali Farag (EGY)' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/players/P-001/career'
    )
    expect(within(eventOne).getByText('Result status')).toBeInTheDocument()
    expect(within(eventOne).getByText('completed')).toBeInTheDocument()
    expect(within(eventOne).getByText('Matches')).toBeInTheDocument()
    expect(within(eventOne).getByText('31')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Open tournament detail/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments/EVENT-1'
    )
    expect(screen.queryByText(/event-list-payload-should-not-render/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Match 1 should not render/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })

  it('keeps missing tournament list weeks as plain text without a broken week link', async () => {
    api.listEvents.mockResolvedValueOnce({
      run_id: 'viewer-run-1',
      events: [
        {
          event_sequence: 10,
          event_id: 'EVENT-NO-WEEK',
          season: 2027,
          week: null,
          template_id: 'WT-GOLD',
          tournament_result: null
        }
      ]
    })

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments')

    const eventWithoutWeek = (await screen.findByText('EVENT-NO-WEEK')).closest('li') as HTMLElement
    expect(within(eventWithoutWeek).getByText('—')).toBeInTheDocument()
    expect(within(eventWithoutWeek).queryByRole('link', { name: /^W/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('hides unknown tournament result payloads on the tournaments list without fake result metadata', async () => {
    api.listEvents.mockResolvedValueOnce({
      run_id: 'viewer-run-1',
      events: [
        {
          event_sequence: 10,
          event_id: 'EVENT-UNKNOWN',
          season: 2027,
          week: 5,
          template_id: 'WT-GOLD',
          tournament_result: {
            secret_debug_marker: 'unknown-list-payload-should-not-render',
            fake_champion: 'Fake Champion',
            unknown_status: 'invented'
          }
        }
      ]
    })

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments')

    expect(await screen.findByText('EVENT-UNKNOWN')).toBeInTheDocument()
    expect(screen.getByText('Result publication available')).toBeInTheDocument()
    expect(screen.queryByText('Champion')).not.toBeInTheDocument()
    expect(screen.queryByText(/Fake Champion/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Fake Champion/i })).not.toBeInTheDocument()
    expect(screen.queryByText('Result status')).not.toBeInTheDocument()
    expect(screen.queryByText(/unknown-list-payload-should-not-render/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

})

describe('ViewerRunTournamentDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
    api.getEvent.mockResolvedValue({
      event_sequence: 8,
      event_id: 'EVENT-1',
      season: 2027,
      week: 3,
      template_id: 'WT-PLAT',
      tournament_result: { secret_debug_marker: 'event-detail-hidden-payload' }
    })
  })

  it('renders parseable tournament result preview with collapsed technical data', async () => {
    api.getEvent.mockResolvedValueOnce({
      event_sequence: 8,
      event_id: 'EVENT-1',
      season: 2027,
      week: 3,
      template_id: 'WT-PLAT',
      tournament_result: {
        summary: {
          champion: { player_id: 'P-001', name: 'Ali Farag', country: 'EGY' },
          finalist: { player_id: 'P-002', name: 'Paul Coll', country: 'NZL' },
          final_score: '11-8, 9-11, 11-7, 11-6',
          match_count: 31,
          completed_matches: 30,
          draw_size: 32,
          round_count: 5,
          status: 'completed',
          secret_debug_marker: 'parseable-hidden-payload'
        }
      }
    })

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-1')

    expect(await screen.findByRole('heading', { name: 'Tournament Result Preview' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ali Farag (EGY)' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/players/P-001/career'
    )
    expect(screen.getByRole('link', { name: 'Paul Coll (NZL)' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/players/P-002/career'
    )
    expect(screen.getByText('11-8, 9-11, 11-7, 11-6')).toBeInTheDocument()
    expect(screen.getByText('31')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
    expect(screen.getByText('32')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
    expect(screen.queryByText(/This preview is not connected/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Match 1/i)).not.toBeInTheDocument()
    const technicalSection = screen.getByText('Show technical event data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/parseable-hidden-payload/i)).not.toBeVisible()
    expectNoForbiddenViewerActions()
  })


  it('keeps tournament result champion and finalist as plain text when player IDs are missing', async () => {
    api.getEvent.mockResolvedValueOnce({
      event_sequence: 8,
      event_id: 'EVENT-1',
      season: 2027,
      week: 3,
      template_id: 'WT-PLAT',
      tournament_result: {
        summary: {
          champion: { name: 'Ali Farag', country: 'EGY' },
          finalist: { name: 'Paul Coll', country: 'NZL' },
          status: 'completed'
        }
      }
    })

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-1')

    expect(await screen.findByRole('heading', { name: 'Tournament Result Preview' })).toBeInTheDocument()
    expect(screen.getByText('Ali Farag (EGY)')).toBeInTheDocument()
    expect(screen.getByText('Paul Coll (NZL)')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ali Farag (EGY)' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Paul Coll (NZL)' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders sports-facing tournament detail with deferred preview for unknown result shapes', async () => {
    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-1')

    expect(await screen.findByRole('heading', { name: 'Tournament Detail' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-1').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('2027')).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'W3' })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour').length).toBeGreaterThan(0)
    expect(screen.getByText('WT-PLAT')).toBeInTheDocument()
    expect(screen.getByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to tournaments/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/tournaments'
    )
    expect(screen.getByRole('link', { name: /Open calendar event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/calendar/EVENT-1'
    )
    expect(screen.getByRole('link', { name: /Open week detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-1/weeks/3')
    const technicalSection = screen.getByText('Show technical event data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/event-detail-hidden-payload/i)).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical event data'))
    expect(within(technicalSection as HTMLElement).getByText(/event-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })

  it('keeps missing tournament detail weeks as plain text without a broken week link', async () => {
    api.getEvent.mockResolvedValueOnce({
      event_sequence: 10,
      event_id: 'EVENT-NO-WEEK',
      season: 2027,
      week: null,
      template_id: 'WT-GOLD',
      tournament_result: {
        summary: {
          champion: { player_id: 'P-001', name: 'Ali Farag', country: 'EGY' },
          status: 'completed'
        }
      }
    })

    renderViewerTournamentRoute('/viewer/runs/viewer-run-1/tournaments/EVENT-NO-WEEK')

    expect(await screen.findByRole('heading', { name: 'Tournament Result Preview' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ali Farag (EGY)' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/players/P-001/career'
    )
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.queryByRole('link', { name: /^W/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open week detail/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { PlannedEventDetailPage } from './PlannedEventDetailPage'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  listEvents: vi.fn(),
  getEventWildcards: vi.fn(),
  getEventWildcardCandidates: vi.fn(),
  assignEventWildcards: vi.fn()
}))

vi.mock('../api/client', () => api)

function renderAt(route: string): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/runs/:runId/calendar/:eventId" element={<PlannedEventDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('PlannedEventDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2029, seed: 7, next_event_index: 1, total_events: 3, completed_event_ids: ['E2'] },
      season_state: {
        season: 2029,
        next_event_index: 1,
        completed_event_ids: ['E2'],
        ordered_events: [
          { event_id: 'E2', season: 2029, week: 4, tour: 'WORLD', category: 'PLATINUM', template_id: 'TEMP-C' },
          { event_id: 'E1', season: 2029, week: 6, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-A' },
          { event_id: 'E3', season: 2029, week: 8, tour: 'ELITE', category: 'SILVER', template_id: 'TEMP-B' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({
      run_id: 'run-a',
      events: [{ event_sequence: 2, event_id: 'E2', season: 2029, week: 4, template_id: 'TEMP-C', tournament_result: { ok: true } }]
    })
    api.getEventWildcards.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      eligible: true,
      eligibility_reason: null,
      total_slots: 1,
      slots: [{ slot_index: 1, entry_id: 'E1:WILD_CARD_PLACEHOLDER:1', assigned_player_id: null }]
    })
    api.assignEventWildcards.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      eligible: true,
      eligibility_reason: null,
      total_slots: 1,
      slots: [{ slot_index: 1, entry_id: 'E1:WILD_CARD_PLACEHOLDER:1', assigned_player_id: 'P1' }]
    })
    api.getEventWildcardCandidates.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      candidates: [
        {
          player_id: 'P1',
          player_name: 'Player One',
          country_code: 'EGY',
          country_name: 'Egypt',
          source: 'main_draw_waitlist',
          source_priority: 1,
          entry_score: 0.98
        },
        {
          player_id: 'P2',
          player_name: 'Player Two',
          country_code: 'ENG',
          country_name: 'England',
          source: 'qualification_waitlist',
          source_priority: 2,
          entry_score: 0.79
        }
      ]
    })
  })

  it('renders planned-event detail for valid event id with status and position', async () => {
    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByRole('heading', { name: 'Planned event detail' })).toBeInTheDocument()
    expect(await screen.findByText('Event ID')).toBeInTheDocument()
    expect(screen.getAllByText('E1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Next').length).toBeGreaterThan(0)
    expect(screen.getByText('2 of 3')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open week detail' })).toHaveAttribute('href', '/runs/run-a/weeks/6')
  })

  it('shows readable not-found behavior for event id missing from ordered season state', async () => {
    renderAt('/runs/run-a/calendar/DOES_NOT_EXIST')

    expect(await screen.findByText("Event DOES_NOT_EXIST is not present in this run's ordered season plan.")).toBeInTheDocument()
  })

  it('shows completed status and persisted history link only when available', async () => {
    renderAt('/runs/run-a/calendar/E2')

    expect((await screen.findAllByText('Completed')).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Inspect persisted event detail for E2' })).toHaveAttribute('href', '/runs/run-a/events/E2')
  })

  it('renders prev/next planned navigation using season order', async () => {
    renderAt('/runs/run-a/calendar/E1')

    const prevLink = await screen.findByRole('link', { name: 'E2' })
    expect(prevLink).toHaveAttribute('href', '/runs/run-a/calendar/E2')
    expect(screen.getByRole('link', { name: 'E3' })).toHaveAttribute('href', '/runs/run-a/calendar/E3')
  })

  it('shows safe boundary navigation labels at the end of the ordered season plan', async () => {
    renderAt('/runs/run-a/calendar/E3')

    expect(await screen.findByText(/· Next:/)).toBeInTheDocument()
    expect(screen.getAllByText('None').length).toBeGreaterThan(0)
  })

  it('renders wildcard commissioner section with slot visibility', async () => {
    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByRole('heading', { name: 'Commissioner wildcards' })).toBeInTheDocument()
    expect(await screen.findByText('Slot 1: Unassigned')).toBeInTheDocument()
    expect(await screen.findByRole('option', { name: /Player One \(P1\)/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Assign wildcard' })).toBeInTheDocument()
  })

  it('assigns wildcard using selected candidate player instead of manual id typing', async () => {
    renderAt('/runs/run-a/calendar/E1')

    const candidateSelect = await screen.findByLabelText('Candidate player')
    const slotSelect = screen.getByLabelText('Slot')
    fireEvent.change(slotSelect, { target: { value: '1' } })
    fireEvent.change(candidateSelect, { target: { value: 'P2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Assign wildcard' }))

    await waitFor(() =>
      expect(api.assignEventWildcards).toHaveBeenCalledWith('run-a', 'E1', {
        assignments: [{ slot_index: 1, player_id: 'P2' }]
      })
    )
  })
})

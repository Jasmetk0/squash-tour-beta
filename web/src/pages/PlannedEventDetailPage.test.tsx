import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { useState } from 'react'

import { PlannedEventDetailPage } from './PlannedEventDetailPage'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  listEvents: vi.fn(),
  getEventWildcards: vi.fn(),
  getEventLateReplacementState: vi.fn(),
  getEventLateReplacementCandidates: vi.fn(),
  getEventLateReplacementActions: vi.fn(),
  applyEventLateReplacement: vi.fn(),
  getEventPreDrawWithdrawalState: vi.fn(),
  getEventPreDrawWithdrawalActions: vi.fn(),
  applyEventPreDrawWithdrawal: vi.fn(),
  getEventWildcardCandidates: vi.fn(),
  getEventWildcardActions: vi.fn(),
  assignEventWildcards: vi.fn()
}))
const adminTime = vi.hoisted(() => ({ viewed: vi.fn() }))

vi.mock('../api/client', () => api)
vi.mock('../admin/useAdminViewedSeasonState', () => ({ useAdminViewedSeasonState: adminTime.viewed }))

const presentView = () => ({ historical: false, seasonState: null, unavailable: false, failed: false, query: { isLoading: false }, time: null })
const historicalView = () => ({ historical: true, unavailable: false, failed: false, query: { isLoading: false }, time: { viewCheckpointId: 'cp-old' }, seasonState: {
  season: 2005, completed_event_ids: ['event-a'], next_event_index: 1, ordered_events: [
    { event_id: 'event-before', season: 2005, week: 9, tour: 'ELITE', category: 'SILVER', template_id: 'BEFORE' },
    { event_id: 'event-a', season: 2005, week: 10, tour: 'WORLD', category: 'GOLD', template_id: 'EVENT-A' },
    { event_id: 'event-after', season: 2005, week: 12, tour: 'WORLD', category: 'PLATINUM', template_id: 'AFTER' }
  ] } })

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
    adminTime.viewed.mockImplementation(presentView)
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
    api.getEventPreDrawWithdrawalState.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      eligible: true,
      eligibility_reason: null,
      withdrawable_main_draw_players: [
        {
          player_id: 'P100',
          player_name: 'Player Main',
          country_code: 'EGY',
          country_name: 'Egypt',
          entry_id: 'E1:P100:MAIN',
          acceptance_status: 'DIRECT_ACCEPTANCE'
        }
      ]
    })
    api.getEventLateReplacementState.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      eligible: true,
      eligibility_reason: null,
      replaceable_main_draw_players: [
        {
          player_id: 'P100',
          player_name: 'Player Main',
          country_code: 'EGY',
          country_name: 'Egypt',
          entry_id: 'E1:P100:MAIN',
          acceptance_status: 'DIRECT_ACCEPTANCE'
        }
      ],
      remaining_capacity: 2
    })
    api.getEventLateReplacementCandidates.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      candidates: [
        {
          candidate_slot_index: 1,
          player_id: 'P300',
          player_name: 'Player Three',
          country_code: 'ENG',
          country_name: 'England',
          source: 'qualification_waitlist',
          source_priority: 0,
          ranking_priority: 3,
          entry_id: 'E1:P300:APPLICANT_QUALIFICATION'
        }
      ]
    })
    api.getEventLateReplacementActions.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      actions: [
        {
          action_sequence: 1,
          action_kind: 'late_replacement_lucky_loser',
          event_id: 'E1',
          withdrawn_player_id: 'P100',
          replacement_player_id: 'P300',
          replacement_source: 'qualification_waitlist',
          withdrawn_entry_id: 'E1:P100:MAIN',
          replacement_entry_id: 'E1:LATE_REPLACEMENT_PLACEHOLDER:1',
          candidate_slot_index: 1,
          notes: null
        }
      ]
    })
    api.applyEventLateReplacement.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      withdrawn_player_id: 'P100',
      replacement_player_id: 'P300',
      replacement_source: 'qualification_waitlist',
      withdrawn_entry_id: 'E1:P100:MAIN',
      replacement_entry_id: 'E1:LATE_REPLACEMENT_PLACEHOLDER:1',
      candidate_slot_index: 1,
      eligible: true,
      eligibility_reason: null,
      remaining_capacity: 1
    })
    api.applyEventPreDrawWithdrawal.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      withdrawn_player_id: 'P100',
      replacement_player_id: 'P200',
      replacement_source: 'main_draw_waitlist',
      withdrawn_entry_id: 'E1:P100:MAIN',
      replacement_entry_id: 'E1:WITHDRAWAL_PLACEHOLDER:1',
      eligible: true,
      eligibility_reason: null
    })
    api.getEventPreDrawWithdrawalActions.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      actions: [
        {
          action_sequence: 1,
          action_kind: 'pre_draw_withdrawal_replacement',
          event_id: 'E1',
          withdrawn_player_id: 'P100',
          replacement_player_id: 'P200',
          replacement_source: 'main_draw_waitlist',
          withdrawn_entry_id: 'E1:P100:MAIN',
          replacement_entry_id: 'E1:WITHDRAWAL_PLACEHOLDER:1',
          notes: null
        }
      ]
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
    api.getEventWildcardActions.mockResolvedValue({
      run_id: 'run-a',
      event_id: 'E1',
      actions: [
        {
          action_sequence: 1,
          action_kind: 'assign_wildcards',
          event_id: 'E1',
          assignment_payload_summary: [{ slot_index: 1, player_id: 'P1' }]
        },
        {
          action_sequence: 2,
          action_kind: 'assign_wildcards',
          event_id: 'E1',
          assignment_payload_summary: [{ slot_index: 1, player_id: 'P2' }]
        }
      ]
    })
  })

  it('renders historical planned-event detail without current or commissioner API reads', async () => {
    adminTime.viewed.mockReturnValue(historicalView())
    renderAt('/runs/run-a/calendar/event-a')
    expect(await screen.findByText('Past')).toBeInTheDocument(); expect(screen.getAllByText('2005').length).toBeGreaterThan(0)
    expect(screen.getAllByText('event-a').length).toBeGreaterThan(0)
    expect(screen.getByText('2 of 3')).toBeInTheDocument(); expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getAllByText('WORLD').length).toBeGreaterThan(0); expect(screen.getByText('GOLD')).toBeInTheDocument(); expect(screen.getByText('EVENT-A')).toBeInTheDocument()
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0); expect(screen.getByText('Yes')).toBeInTheDocument()
    expect(screen.getAllByText('event-before').length).toBeGreaterThan(0); expect(screen.getAllByText('event-after').length).toBeGreaterThan(0)
    for (const name of ['Commissioner wildcards', 'Wildcard action history', 'Commissioner pre-draw withdrawal replacement', 'Pre-draw withdrawal action history', 'Commissioner late replacement lucky loser', 'Late-replacement action history']) expect(screen.queryByRole('heading', { name })).not.toBeInTheDocument()
    for (const method of ['getRun', 'listEvents', 'getEventWildcards', 'getEventWildcardCandidates', 'getEventWildcardActions', 'getEventPreDrawWithdrawalState', 'getEventPreDrawWithdrawalActions', 'getEventLateReplacementState', 'getEventLateReplacementCandidates', 'getEventLateReplacementActions'] as const) expect(api[method]).not.toHaveBeenCalled()
    expect(screen.queryByRole('link', { name: /Inspect persisted event detail/ })).not.toBeInTheDocument()
  })

  it('re-enables current and commissioner queries after Past changes to Present', async () => {
    let current = historicalView(); adminTime.viewed.mockImplementation(() => current)
    function Harness() { const [, update] = useState(0); return <><button onClick={() => { current = presentView(); update(value => value + 1) }}>Switch Present</button><PlannedEventDetailPage /></> }
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/runs/run-a/calendar/E1']}><Routes><Route path="/runs/:runId/calendar/:eventId" element={<Harness />} /></Routes></MemoryRouter></QueryClientProvider>)
    await screen.findByText('Past'); expect(api.getEventWildcards).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Switch Present' }))
    await waitFor(() => expect(api.getRun).toHaveBeenCalled())
    await waitFor(() => expect(api.getEventWildcards).toHaveBeenCalled())
    expect(screen.getByText('Present')).toBeInTheDocument()
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

  it('renders pre-draw withdrawal controls and submits deterministic one-step action', async () => {
    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByRole('heading', { name: 'Commissioner pre-draw withdrawal replacement' })).toBeInTheDocument()
    const playerSelect = (await screen.findAllByLabelText('Main-draw player to withdraw'))[1]
    fireEvent.change(playerSelect, { target: { value: 'P100' } })
    fireEvent.click(screen.getByRole('button', { name: 'Withdraw + auto-replace' }))

    await waitFor(() =>
      expect(api.applyEventPreDrawWithdrawal).toHaveBeenCalledWith('run-a', 'E1', {
        withdrawn_player_id: 'P100'
      })
    )
  })

  it('renders late-replacement controls, candidates, and submits deterministic one-step action', async () => {
    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByRole('heading', { name: 'Commissioner late replacement lucky loser' })).toBeInTheDocument()
    expect(await screen.findByText('#1 · Player Three (P300) · qualification_waitlist · ranking 3')).toBeInTheDocument()
    const playerSelect = (await screen.findAllByLabelText('Main-draw player to withdraw'))[0]
    fireEvent.change(playerSelect, { target: { value: 'P100' } })
    fireEvent.click(screen.getByRole('button', { name: 'Withdraw + late-replace' }))

    await waitFor(() =>
      expect(api.applyEventLateReplacement).toHaveBeenCalledWith('run-a', 'E1', {
        withdrawn_player_id: 'P100'
      })
    )
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
    await waitFor(() => {
      expect(api.getEventPreDrawWithdrawalState.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventLateReplacementState.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventWildcardActions.mock.calls.length).toBeGreaterThan(1)
    })
  })

  it('renders wildcard action history in append-only sequence order', async () => {
    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByRole('heading', { name: 'Wildcard action history' })).toBeInTheDocument()
    const historyItems = await screen.findAllByRole('listitem')
    const actionRows = historyItems.filter((item) => item.textContent?.includes('assign_wildcards'))
    expect(actionRows[0]).toHaveTextContent('#1 · assign_wildcards · slot 1 → P1')
    expect(actionRows[1]).toHaveTextContent('#2 · assign_wildcards · slot 1 → P2')
    expect(screen.getByRole('link', { name: 'Open run activity' })).toHaveAttribute('href', '/runs/run-a/activity')
  })

  it('renders pre-draw withdrawal history in append-only sequence order', async () => {
    renderAt('/runs/run-a/calendar/E1')
    expect(await screen.findByRole('heading', { name: 'Pre-draw withdrawal action history' })).toBeInTheDocument()
    expect(await screen.findByText('#1 · pre_draw_withdrawal_replacement · P100 → P200 (main_draw_waitlist)')).toBeInTheDocument()
  })

  it('renders late-replacement history in append-only sequence order', async () => {
    renderAt('/runs/run-a/calendar/E1')
    expect(await screen.findByRole('heading', { name: 'Late-replacement action history' })).toBeInTheDocument()
    expect(await screen.findByText('#1 · late_replacement_lucky_loser · P100 → P300 (qualification_waitlist)')).toBeInTheDocument()
  })

  it('pre-draw mutation invalidates all commissioner read surfaces', async () => {
    renderAt('/runs/run-a/calendar/E1')
    const playerSelect = (await screen.findAllByLabelText('Main-draw player to withdraw'))[1]
    fireEvent.change(playerSelect, { target: { value: 'P100' } })
    fireEvent.click(screen.getByRole('button', { name: 'Withdraw + auto-replace' }))

    await waitFor(() => expect(api.applyEventPreDrawWithdrawal).toHaveBeenCalled())
    await waitFor(() => {
      expect(api.getEventWildcards.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventWildcardCandidates.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventWildcardActions.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventPreDrawWithdrawalState.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventPreDrawWithdrawalActions.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventLateReplacementState.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventLateReplacementCandidates.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventLateReplacementActions.mock.calls.length).toBeGreaterThan(1)
    })
  })

  it('late-replacement mutation invalidates all commissioner read surfaces', async () => {
    renderAt('/runs/run-a/calendar/E1')
    const playerSelect = (await screen.findAllByLabelText('Main-draw player to withdraw'))[0]
    fireEvent.change(playerSelect, { target: { value: 'P100' } })
    fireEvent.click(screen.getByRole('button', { name: 'Withdraw + late-replace' }))

    await waitFor(() => expect(api.applyEventLateReplacement).toHaveBeenCalled())
    await waitFor(() => {
      expect(api.getEventWildcards.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventWildcardCandidates.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventWildcardActions.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventPreDrawWithdrawalState.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventPreDrawWithdrawalActions.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventLateReplacementState.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventLateReplacementCandidates.mock.calls.length).toBeGreaterThan(1)
      expect(api.getEventLateReplacementActions.mock.calls.length).toBeGreaterThan(1)
    })
  })
})

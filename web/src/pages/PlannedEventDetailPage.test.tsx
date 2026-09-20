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
  getCanonicalTournamentEntryFieldState: vi.fn(),
  getCanonicalTournamentDrawState: vi.fn(),
  getCanonicalTournamentDrawAuthority: vi.fn(),
  getCanonicalTournamentEffectiveDrawAuthority: vi.fn(),
  getCanonicalTournamentDrawRevisionHistory: vi.fn(),
  getCanonicalTournamentDrawProcessState: vi.fn(),
  configureCanonicalTournamentDrawProcess: vi.fn(),
  commitCanonicalTournamentDrawInput: vi.fn(),
  generateCanonicalTournamentDraw: vi.fn(),
  previewCanonicalFrozenMainReplacement: vi.fn(),
  commitCanonicalFrozenMainReplacement: vi.fn(),
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
const presentBranchView = () => ({
  historical: false,
  seasonState: null,
  unavailable: false,
  failed: false,
  query: { isLoading: false },
  time: { branchId: 'branch-a' }
})
const historicalView = () => ({ historical: true, unavailable: false, failed: false, query: { isLoading: false }, time: { viewCheckpointId: 'cp-old' }, seasonState: {
  season: 2005, completed_event_ids: ['event-a'], next_event_index: 1, ordered_events: [
    { event_id: 'event-before', season: 2005, week: 9, tour: 'ELITE', category: 'SILVER', template_id: 'BEFORE' },
    { event_id: 'event-a', season: 2005, week: 10, tour: 'WORLD', category: 'GOLD', template_id: 'EVENT-A' },
    { event_id: 'event-after', season: 2005, week: 12, tour: 'WORLD', category: 'PLATINUM', template_id: 'AFTER' }
  ] } })
type MockViewedState = ReturnType<typeof presentView> | ReturnType<typeof historicalView>

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
    api.getCanonicalTournamentEntryFieldState.mockResolvedValue({
      schema_version: 'canonical_tournament_entry_field_state.v2',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      field_sequence: 1,
      field_fingerprint: 'a'.repeat(64),
      mode: 'initial',
      direct_main_player_ids: ['P1', 'P2', 'P3'],
      qualification_player_ids: ['Q1', 'Q2'],
      below_qualification_cut_player_ids: [],
      withdrawn_player_ids: [],
      main_draw_capacity: 4,
      active_main_entrant_count: 4,
      effective_main_bye_count: 0,
      main_diagnostics: [],
      draw_input_committed: false,
      pre_draw_repair_locked_by_draw_input: false
    })
    api.getCanonicalTournamentDrawState.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_state.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      field_sequence: 1,
      field_fingerprint: 'a'.repeat(64),
      main_draw_capacity: 4,
      active_main_entrant_count: 4,
      effective_main_bye_count: 0,
      draw_input_committed: false,
      draw_input_fingerprint: null,
      draw_seed: null,
      main_seed_count: null,
      qualification_seed_count: null,
      initial_draw_generated: false,
      draw_authority_fingerprint: null,
      draw_algorithm_version: null,
      main_slot_count: null,
      main_node_count: null,
      main_bye_count: null,
      qualification_section_count: null,
      qualification_section_sizes: [],
      main_diagnostics: []
    })
    api.commitCanonicalTournamentDrawInput.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_state.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      field_sequence: 1,
      field_fingerprint: 'a'.repeat(64),
      main_draw_capacity: 4,
      active_main_entrant_count: 4,
      effective_main_bye_count: 0,
      draw_input_committed: true,
      draw_input_fingerprint: 'b'.repeat(64),
      draw_seed: 12345,
      main_seed_count: 1,
      qualification_seed_count: 1,
      initial_draw_generated: false,
      draw_authority_fingerprint: null,
      draw_algorithm_version: null,
      main_slot_count: null,
      main_node_count: null,
      main_bye_count: null,
      qualification_section_count: null,
      qualification_section_sizes: [],
      main_diagnostics: []
    })
    api.generateCanonicalTournamentDraw.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_state.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      field_sequence: 1,
      field_fingerprint: 'a'.repeat(64),
      main_draw_capacity: 4,
      active_main_entrant_count: 4,
      effective_main_bye_count: 0,
      draw_input_committed: true,
      draw_input_fingerprint: 'b'.repeat(64),
      draw_seed: 12345,
      main_seed_count: 1,
      qualification_seed_count: 1,
      initial_draw_generated: true,
      draw_authority_fingerprint: 'c'.repeat(64),
      draw_algorithm_version: 'idealized_seed_tiers.v2',
      main_slot_count: 4,
      main_node_count: 3,
      main_bye_count: 0,
      qualification_section_count: 1,
      qualification_section_sizes: [2],
      main_diagnostics: []
    })
    api.getCanonicalTournamentDrawAuthority.mockResolvedValue({
      schema_version: 'tournament_draw_authority.v1',
      algorithm_version: 'idealized_seed_tiers.v2',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      generated_by_command_id: 'draw-command',
      draw_input_fingerprint: 'b'.repeat(64),
      qualification: {
        draw_type: 'qualification',
        bracket_size: 2,
        seed_positions: [[1, 1]],
        slots: [
          { slot_index: 1, idealized_slot_number: 1, entrant_kind: 'player', player_id: 'Q1', placeholder_id: null, seed_number: 1, is_seed_protected: true },
          { slot_index: 2, idealized_slot_number: 2, entrant_kind: 'player', player_id: 'Q2', placeholder_id: null, seed_number: null, is_seed_protected: false }
        ],
        nodes: [{ node_id: 'Q-final', round_number: 1, round_sequence: 1, source_top: 'slot:1', source_bottom: 'slot:2' }],
        bye_slot_indexes: [],
        qualifier_placeholder_slots: []
      },
      main: {
        draw_type: 'main',
        bracket_size: 4,
        seed_positions: [[1, 1]],
        slots: [
          { slot_index: 1, idealized_slot_number: 1, entrant_kind: 'player', player_id: 'P1', placeholder_id: null, seed_number: 1, is_seed_protected: true },
          { slot_index: 2, idealized_slot_number: 4, entrant_kind: 'player', player_id: 'P2', placeholder_id: null, seed_number: null, is_seed_protected: false },
          { slot_index: 3, idealized_slot_number: 3, entrant_kind: 'player', player_id: 'P3', placeholder_id: null, seed_number: null, is_seed_protected: false },
          { slot_index: 4, idealized_slot_number: 2, entrant_kind: 'qualifier_placeholder', player_id: null, placeholder_id: 'Q1', seed_number: null, is_seed_protected: false }
        ],
        nodes: [
          { node_id: 'M1', round_number: 1, round_sequence: 1, source_top: 'slot:1', source_bottom: 'slot:2' },
          { node_id: 'M2', round_number: 1, round_sequence: 2, source_top: 'slot:3', source_bottom: 'slot:4' },
          { node_id: 'M3', round_number: 2, round_sequence: 1, source_top: 'winner:M1', source_bottom: 'winner:M2' }
        ],
        bye_slot_indexes: [],
        qualifier_placeholder_slots: [['Q1', 4]]
      }
    })
    api.getCanonicalTournamentEffectiveDrawAuthority.mockImplementation(
      (...args: unknown[]) => api.getCanonicalTournamentDrawAuthority(...args)
    )
    api.getCanonicalTournamentDrawRevisionHistory.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_revision_history.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      initial_draw_fingerprint: 'c'.repeat(64),
      effective_draw_fingerprint: 'c'.repeat(64),
      revisions: []
    })
    api.getCanonicalTournamentDrawProcessState.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_process_state.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      draw_authority_fingerprint: 'c'.repeat(64),
      has_qualification: true,
      configured: false,
      authority_fingerprint: null,
      main: null,
      qualification: null
    })
    api.configureCanonicalTournamentDrawProcess.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_process_state.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      draw_authority_fingerprint: 'c'.repeat(64),
      has_qualification: true,
      configured: true,
      authority_fingerprint: 'd'.repeat(64),
      main: {
        process_window_count: 4,
        redraw_cutoff_window_ordinal: 3,
        draw_freeze_window_ordinal: 4
      },
      qualification: {
        process_window_count: 3,
        redraw_cutoff_window_ordinal: 2,
        draw_freeze_window_ordinal: 3
      }
    })
    api.previewCanonicalFrozenMainReplacement.mockResolvedValue({
      schema_version: 'authoritative_frozen_main_replacement_preview.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      withdrawn_player_id: 'P2',
      source: 'qualification_promotion',
      selected_player_id: 'Q1',
      physical_slot_index: 2,
      cutoff_status: 'replacement_open',
      source_authority_fingerprint: '7'.repeat(64),
      source_authority: {
        schema_version: 'tournament_replacement_source.v1',
        run_id: 'run-a',
        branch_id: 'branch-a',
        event_id: 'E1',
        withdrawn_player_id: 'P2'
      },
      commit_mode: 'draw_revision'
    })
    api.commitCanonicalFrozenMainReplacement.mockResolvedValue({
      schema_version: 'authoritative_frozen_main_replacement_commit.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      withdrawn_player_id: 'P2',
      source: 'qualification_promotion',
      source_authority_fingerprint: '7'.repeat(64),
      draw_revision_sequences: [1],
      draw_revision_fingerprints: ['8'.repeat(64)],
      successor_draw_fingerprint: '9'.repeat(64)
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
    for (const method of ['getRun', 'listEvents', 'getEventWildcards', 'getEventWildcardCandidates', 'getEventWildcardActions', 'getEventPreDrawWithdrawalState', 'getEventPreDrawWithdrawalActions', 'getEventLateReplacementState', 'getEventLateReplacementCandidates', 'getEventLateReplacementActions', 'getCanonicalTournamentEntryFieldState', 'getCanonicalTournamentDrawState', 'getCanonicalTournamentDrawAuthority', 'getCanonicalTournamentEffectiveDrawAuthority', 'getCanonicalTournamentDrawRevisionHistory', 'getCanonicalTournamentDrawProcessState', 'configureCanonicalTournamentDrawProcess', 'commitCanonicalTournamentDrawInput', 'generateCanonicalTournamentDraw'] as const) expect(api[method]).not.toHaveBeenCalled()
    expect(screen.queryByRole('link', { name: /Inspect persisted event detail/ })).not.toBeInTheDocument()
  })

  it('re-enables current and commissioner queries after Past changes to Present', async () => {
    let current: MockViewedState = historicalView(); adminTime.viewed.mockImplementation(() => current)
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

  it('renders canonical Main Draw warning for the active Admin Branch', async () => {
    adminTime.viewed.mockImplementation(presentBranchView)
    api.getCanonicalTournamentEntryFieldState.mockResolvedValue({
      schema_version: 'canonical_tournament_entry_field_state.v2',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      field_sequence: 2,
      field_fingerprint: 'a'.repeat(64),
      mode: 'pre_draw_repair',
      direct_main_player_ids: ['P1', 'P2', 'P3'],
      qualification_player_ids: [],
      below_qualification_cut_player_ids: [],
      withdrawn_player_ids: ['P4'],
      main_draw_capacity: 4,
      active_main_entrant_count: 3,
      effective_main_bye_count: 1,
      main_diagnostics: [
        {
          severity: 'warning',
          code: 'odd_main_entrant_count',
          message: '! Main Draw has an odd entrant count (3). Odd fields always receive an Admin warning because opening-round paths cannot be fully symmetric.',
          entrant_count: 3,
          bracket_capacity: 4,
          bye_count: 1,
          first_round_match_count: 2,
          first_round_bye_match_count: 1,
          first_round_bye_share: 0.5
        }
      ],
      draw_input_committed: false,
      pre_draw_repair_locked_by_draw_input: false
    })

    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByRole('heading', { name: 'Canonical Main Draw preflight' })).toBeInTheDocument()
    expect(api.getCanonicalTournamentEntryFieldState).toHaveBeenCalledWith('run-a', 'branch-a', 'E1')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText('Bracket capacity')).toBeInTheDocument()
    expect(screen.getByText('Current entrants')).toBeInTheDocument()
    expect(screen.getByText('Effective BYEs')).toBeInTheDocument()
    const warnings = screen.getByRole('list', { name: 'Main Draw warnings' })
    expect(warnings).toHaveTextContent('! Main Draw has an odd entrant count (3).')
  })

  it('commits canonical Draw Input from the active Branch without manual seed counts', async () => {
    adminTime.viewed.mockImplementation(presentBranchView)
    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByRole('heading', { name: 'Canonical Tournament Draw authority' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Technical draw seed'), { target: { value: '24680' } })
    fireEvent.click(screen.getByRole('button', { name: 'Commit canonical Draw Input' }))

    await waitFor(() =>
      expect(api.commitCanonicalTournamentDrawInput).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        'E1',
        expect.objectContaining({
          schema_version: 'canonical_tournament_draw_input_commit_command.v1',
          run_id: 'run-a',
          branch_id: 'branch-a',
          event_id: 'E1',
          expected_field_fingerprint: 'a'.repeat(64),
          draw_seed: 24680
        })
      )
    )
    const payload = api.commitCanonicalTournamentDrawInput.mock.calls[0][3]
    expect(payload).not.toHaveProperty('main_seed_count')
    expect(payload).not.toHaveProperty('qualification_seed_count')
  })

  it('generates canonical initial Draw only from the committed Draw Input fingerprint', async () => {
    adminTime.viewed.mockImplementation(presentBranchView)
    api.getCanonicalTournamentDrawState.mockResolvedValue({
      ...(await api.commitCanonicalTournamentDrawInput()),
      draw_input_committed: true,
      draw_input_fingerprint: 'b'.repeat(64),
      initial_draw_generated: false
    })

    renderAt('/runs/run-a/calendar/E1')
    fireEvent.click(await screen.findByRole('button', { name: 'Generate canonical initial Draw' }))

    await waitFor(() =>
      expect(api.generateCanonicalTournamentDraw).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        'E1',
        expect.objectContaining({
          schema_version: 'canonical_tournament_draw_generate_command.v1',
          expected_draw_input_fingerprint: 'b'.repeat(64)
        })
      )
    )
  })

  it('renders the immutable canonical Main and Qualification bracket payload', async () => {
    adminTime.viewed.mockImplementation(presentBranchView)
    api.getCanonicalTournamentDrawState.mockResolvedValue({
      ...(await api.generateCanonicalTournamentDraw()),
      initial_draw_generated: true
    })

    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByRole('table', { name: 'Canonical Main Draw slots' })).toBeInTheDocument()
    expect(screen.getByText('P1')).toBeInTheDocument()
    expect(screen.getAllByText('Q1').length).toBeGreaterThanOrEqual(2)
    expect(await screen.findByRole('table', { name: 'Canonical Qualification slots' })).toBeInTheDocument()
    expect(api.getCanonicalTournamentDrawAuthority).toHaveBeenCalledWith('run-a', 'branch-a', 'E1')
  })

  it('configures canonical Draw process windows explicitly against the immutable Draw fingerprint', async () => {
    adminTime.viewed.mockImplementation(presentBranchView)
    api.getCanonicalTournamentDrawState.mockResolvedValue({
      ...(await api.generateCanonicalTournamentDraw()),
      initial_draw_generated: true,
      draw_authority_fingerprint: 'c'.repeat(64)
    })

    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByText('Draw process windows')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Main process windows'), { target: { value: '4' } })
    fireEvent.change(screen.getByLabelText('Qualification process windows'), { target: { value: '3' } })
    fireEvent.click(screen.getByRole('button', { name: 'Configure canonical Draw process' }))

    await waitFor(() =>
      expect(api.configureCanonicalTournamentDrawProcess).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        'E1',
        expect.objectContaining({
          schema_version: 'canonical_tournament_draw_process_configure_command.v1',
          expected_draw_authority_fingerprint: 'c'.repeat(64),
          main_process_window_count: 4,
          qualification_process_window_count: 3
        })
      )
    )
  })

  it('previews and commits canonical frozen Main replacement against reviewed source fingerprint', async () => {
    adminTime.viewed.mockImplementation(presentBranchView)
    api.getCanonicalTournamentDrawState.mockResolvedValue({
      ...(await api.generateCanonicalTournamentDraw()),
      initial_draw_generated: true,
      draw_authority_fingerprint: 'c'.repeat(64)
    })
    api.getCanonicalTournamentDrawProcessState.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_process_state.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      draw_authority_fingerprint: 'c'.repeat(64),
      has_qualification: true,
      configured: true,
      authority_fingerprint: 'd'.repeat(64),
      main: {
        process_window_count: 3,
        redraw_cutoff_window_ordinal: 2,
        draw_freeze_window_ordinal: 3
      },
      qualification: {
        process_window_count: 3,
        redraw_cutoff_window_ordinal: 2,
        draw_freeze_window_ordinal: 3
      }
    })

    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByText('Frozen Main replacement')).toBeInTheDocument()
    const player = await screen.findByLabelText('Frozen Main withdrawn player')
    fireEvent.change(player, { target: { value: 'P2' } })
    fireEvent.change(screen.getByLabelText('Frozen Main unavailable players'), {
      target: { value: 'Q9, Q8, Q9' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview frozen Main replacement' }))

    await waitFor(() =>
      expect(api.previewCanonicalFrozenMainReplacement).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        'E1',
        {
          withdrawn_player_id: 'P2',
          unavailable_player_ids: ['Q8', 'Q9']
        }
      )
    )
    expect(await screen.findByText('qualification_promotion')).toBeInTheDocument()
    expect(screen.getAllByText('Q1').length).toBeGreaterThan(0)

    fireEvent.change(
      screen.getByLabelText('Frozen Main Qualification process window'),
      { target: { value: '2' } }
    )
    fireEvent.change(screen.getByLabelText('Frozen Main repair draw seed'), {
      target: { value: '777' }
    })
    fireEvent.click(
      screen.getByRole('button', {
        name: 'Commit reviewed frozen Main replacement'
      })
    )

    await waitFor(() =>
      expect(api.commitCanonicalFrozenMainReplacement).toHaveBeenCalledWith(
        'run-a',
        'branch-a',
        'E1',
        expect.objectContaining({
          withdrawn_player_id: 'P2',
          unavailable_player_ids: ['Q8', 'Q9'],
          expected_source_fingerprint: '7'.repeat(64),
          main_process_window_ordinal: 3,
          qualification_process_window_ordinal: 2,
          repair_draw_seed: 777
        })
      )
    )
  })

  it('hands walkover replacement preview back to canonical Simulation instead of mutating Draw', async () => {
    adminTime.viewed.mockImplementation(presentBranchView)
    api.getCanonicalTournamentDrawState.mockResolvedValue({
      ...(await api.generateCanonicalTournamentDraw()),
      initial_draw_generated: true,
      draw_authority_fingerprint: 'c'.repeat(64)
    })
    api.getCanonicalTournamentDrawProcessState.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_process_state.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      draw_authority_fingerprint: 'c'.repeat(64),
      has_qualification: true,
      configured: true,
      authority_fingerprint: 'd'.repeat(64),
      main: {
        process_window_count: 3,
        redraw_cutoff_window_ordinal: 2,
        draw_freeze_window_ordinal: 3
      },
      qualification: {
        process_window_count: 3,
        redraw_cutoff_window_ordinal: 2,
        draw_freeze_window_ordinal: 3
      }
    })
    api.previewCanonicalFrozenMainReplacement.mockResolvedValue({
      schema_version: 'authoritative_frozen_main_replacement_preview.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      withdrawn_player_id: 'P1',
      source: 'walkover',
      selected_player_id: null,
      physical_slot_index: 1,
      cutoff_status: 'walkover_required',
      source_authority_fingerprint: '6'.repeat(64),
      source_authority: {},
      commit_mode: 'walkover_handoff'
    })

    renderAt('/runs/run-a/calendar/E1')
    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Preview frozen Main replacement'
      })
    )

    expect(
      await screen.findByText(/complete the next consuming match through canonical post-cutoff W\/O in Simulation/i)
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', {
        name: 'Commit reviewed frozen Main replacement'
      })
    ).not.toBeInTheDocument()
    expect(api.commitCanonicalFrozenMainReplacement).not.toHaveBeenCalled()
  })

  it('renders effective successor Draw and append-only revision audit instead of stale initial slots', async () => {
    adminTime.viewed.mockImplementation(presentBranchView)
    api.getCanonicalTournamentDrawState.mockResolvedValue({
      ...(await api.generateCanonicalTournamentDraw()),
      initial_draw_generated: true,
      draw_authority_fingerprint: 'c'.repeat(64)
    })
    api.getCanonicalTournamentEffectiveDrawAuthority.mockResolvedValue({
      ...(await api.getCanonicalTournamentDrawAuthority()),
      draw_input_fingerprint: 'e'.repeat(64),
      main: {
        ...(await api.getCanonicalTournamentDrawAuthority()).main,
        slots: [
          { slot_index: 1, idealized_slot_number: 1, entrant_kind: 'player', player_id: 'P1', placeholder_id: null, seed_number: 1, is_seed_protected: true },
          { slot_index: 2, idealized_slot_number: 4, entrant_kind: 'player', player_id: 'P2', placeholder_id: null, seed_number: null, is_seed_protected: false },
          { slot_index: 3, idealized_slot_number: 3, entrant_kind: 'player', player_id: 'P4-EFFECTIVE', placeholder_id: null, seed_number: null, is_seed_protected: false },
          { slot_index: 4, idealized_slot_number: 2, entrant_kind: 'qualifier_placeholder', player_id: null, placeholder_id: 'Q1', seed_number: null, is_seed_protected: false }
        ]
      }
    })
    api.getCanonicalTournamentDrawRevisionHistory.mockResolvedValue({
      schema_version: 'canonical_tournament_draw_revision_history.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      event_id: 'E1',
      initial_draw_fingerprint: 'c'.repeat(64),
      effective_draw_fingerprint: 'f'.repeat(64),
      revisions: [{
        sequence: 1,
        schema_version: 'tournament_draw_revision.v5',
        command_id: 'withdraw-p3',
        repair_kind: 'full_redraw',
        affected_draw_types: ['main', 'qualification'],
        withdrawn_player_ids: ['P3'],
        main_process_window_ordinal: 1,
        qualification_process_window_ordinal: 1,
        main_repair_action: null,
        qualification_repair_action: null,
        repair_draw_seed: 987,
        predecessor_draw_fingerprint: 'c'.repeat(64),
        successor_draw_input_fingerprint: 'e'.repeat(64),
        successor_draw_fingerprint: 'f'.repeat(64)
      }]
    })

    renderAt('/runs/run-a/calendar/E1')

    expect(await screen.findByText('P4-EFFECTIVE')).toBeInTheDocument()
    expect(screen.queryByText('P3')).not.toBeInTheDocument()
    const history = screen.getByRole('list', { name: 'Canonical Draw revision history' })
    expect(history).toHaveTextContent('#1 · full_redraw · main + qualification · withdrawn P3 · Main window 1 · Q window 1')
    expect(screen.getByText('Latest effective successor Draw')).toBeInTheDocument()
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

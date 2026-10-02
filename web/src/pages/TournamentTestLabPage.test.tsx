import { fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TournamentTestLabPage } from './TournamentTestLabPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getTournamentLabBuiltInScenarios: vi.fn(),
  inspectTournamentLabScenario: vi.fn(),
  runTournamentTestLab: vi.fn()
}))
vi.mock('../api/client', () => api)

const participant = (id: string, base: number) => ({
  player: {
    player_id: id,
    name: id,
    age: 27,
    nationality: 'TST',
    technique: base,
    movement: base,
    physical: base,
    mental: base,
    consistency: base,
    clutch: base,
    recovery: base,
    play_style: 'tempo-controller',
    archetype: 'all-court tactician',
    hidden_career_traits: {
      potential_ceiling: 90,
      growth_curve: 'balanced',
      professionalism: 0.7,
      ambition: 0.7,
      travel_tolerance: 0.7,
      schedule_aggression: 0.6,
      injury_proneness: 0.2,
      resilience: 0.8
    }
  },
  form_modifier: 0,
  sharpness_modifier: 0,
  fatigue_modifier: 0,
  health_modifier: 0,
  travel_modifier: 0
})

const scenario = {
  schema_version: 'tournament_test_lab_scenario.v1',
  scenario_id: 'standard-four-player',
  display_name: 'Standard four-player',
  format_kind: 'knockout',
  participants: [
    participant('P1', 90),
    participant('P2', 85),
    participant('P3', 80),
    participant('P4', 75)
  ],
  main_draw_size: 4,
  seed_order_player_ids: ['P1', 'P2', 'P3', 'P4'],
  draw_seed: 11,
  match_seed: 21,
  match_format: { best_of: 5, games_to: 11, win_by: 2, upset_variance: 0.12 },
  stop_after_round: null,
  assertions: { expected_played_match_count: 3 },
  source_kind: 'portable'
}

const compatibility = {
  runnable_in_lab: true,
  normal_run_compatible: true,
  isolated: true,
  run_mutation_performed: false,
  run_live_link: false,
  shared_authorities: [
    'beta_engine.domain.tournaments.format_authority.TournamentFormatAuthority',
    'beta_engine.domain.tournaments.draw_authority.TournamentDrawAuthorityBuilder',
    'beta_engine.domain.matches.match_engine.MatchEngine.simulate'
  ],
  issues: []
}

const draw = {
  schema_version: 'tournament_draw_authority.v1',
  algorithm_version: 'idealized_seed_tiers.v2',
  run_id: 'lab:test',
  branch_id: 'isolated',
  event_id: 'event',
  generated_by_command_id: 'command',
  draw_input_fingerprint: 'd'.repeat(64),
  qualification: null,
  main: {
    draw_type: 'main',
    bracket_size: 4,
    seed_positions: [[1, 1], [2, 4]],
    slots: [
      { slot_index: 1, idealized_slot_number: 1, entrant_kind: 'player', player_id: 'P1', placeholder_id: null, seed_number: 1, is_seed_protected: true },
      { slot_index: 2, idealized_slot_number: 2, entrant_kind: 'player', player_id: 'P3', placeholder_id: null, seed_number: null, is_seed_protected: false },
      { slot_index: 3, idealized_slot_number: 3, entrant_kind: 'player', player_id: 'P4', placeholder_id: null, seed_number: null, is_seed_protected: false },
      { slot_index: 4, idealized_slot_number: 4, entrant_kind: 'player', player_id: 'P2', placeholder_id: null, seed_number: 2, is_seed_protected: true }
    ],
    nodes: [
      { node_id: 'R1-M1', round_number: 1, round_sequence: 1, source_top: 'slot:1', source_bottom: 'slot:2' },
      { node_id: 'R1-M2', round_number: 1, round_sequence: 2, source_top: 'slot:3', source_bottom: 'slot:4' },
      { node_id: 'R2-M1', round_number: 2, round_sequence: 1, source_top: 'winner:R1-M1', source_bottom: 'winner:R1-M2' }
    ],
    bye_slot_indexes: [],
    qualifier_placeholder_slots: []
  }
}

const result = {
  schema_version: 'tournament_test_lab_result.v1',
  scenario_id: scenario.scenario_id,
  scenario_fingerprint: 'a'.repeat(64),
  request_fingerprint: 'b'.repeat(64),
  compatibility,
  format_authority_fingerprint: 'c'.repeat(64),
  draw_input_fingerprint: 'd'.repeat(64),
  draw_authority_fingerprint: 'e'.repeat(64),
  draw,
  runs: [{
    match_seed: 100,
    completed_rounds: 2,
    tournament_complete: true,
    champion_player_id: 'P1',
    played_match_count: 3,
    bye_advance_count: 0,
    match_results: [{
      node_id: 'R1-M1',
      round_number: 1,
      round_sequence: 1,
      player_a_id: 'P1',
      player_b_id: 'P3',
      winner_player_id: 'P1',
      loser_player_id: 'P3',
      status: 'played',
      match_seed: 777,
      result_fingerprint: 'f'.repeat(64),
      set_scores: ['11-7', '11-8', '11-9'],
      rally_count: 57,
      elapsed_seconds: 1500
    }],
    assertions: [{
      assertion: 'expected_played_match_count',
      status: 'passed',
      expected: '3',
      actual: '3'
    }],
    run_fingerprint: '9'.repeat(64)
  }],
  diagnostics: {
    run_count: 2,
    completed_run_count: 2,
    champions: { P1: 2 },
    assertion_failure_count: 0,
    average_played_match_count: 3
  }
}

describe('TournamentTestLabPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getTournamentLabBuiltInScenarios.mockResolvedValue([{
      scenario_id: scenario.scenario_id,
      display_name: scenario.display_name,
      description: 'Shared-kernel baseline.',
      read_only: true,
      scenario_fingerprint: 'a'.repeat(64),
      scenario
    }])
    api.inspectTournamentLabScenario.mockResolvedValue(compatibility)
    api.runTournamentTestLab.mockResolvedValue(result)
  })

  it('loads an editable built-in, inspects compatibility and runs a batch report', async () => {
    const user = userEvent.setup()
    renderWithRoute(<TournamentTestLabPage />, '/admin/labs/tournament')

    expect(screen.getByRole('heading', { name: 'Tournament Test Lab' })).toBeInTheDocument()
    expect(screen.getByText(/outside Runs/i)).toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: 'Load editable copy' }))
    expect((screen.getByLabelText('Tournament Lab scenario JSON') as HTMLTextAreaElement).value).toContain('standard-four-player')

    await user.click(screen.getByRole('button', { name: 'Inspect compatibility' }))
    expect(api.inspectTournamentLabScenario).toHaveBeenCalledWith(expect.objectContaining({ scenario_id: 'standard-four-player' }), expect.anything())
    expect(await screen.findByText('No compatibility issues.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Tournament Lab batch match seeds'), '100, 101')
    await user.click(screen.getByRole('button', { name: 'Run tournament scenario' }))

    expect(api.runTournamentTestLab).toHaveBeenCalledWith(
      expect.objectContaining({
        batch_match_seeds: [100, 101],
        scenario: expect.objectContaining({ scenario_id: 'standard-four-player' })
      }),
      expect.anything()
    )
    expect(await screen.findByText('idealized_seed_tiers.v2')).toBeInTheDocument()
    expect(screen.getByText('P1: 2')).toBeInTheDocument()
    const drawTable = screen.getByRole('table', { name: 'Tournament Lab draw slots' })
    expect(within(drawTable).getByRole('cell', { name: 'P1' })).toBeInTheDocument()
    const matchTable = screen.getByRole('table', { name: 'Tournament Lab match results' })
    expect(within(matchTable).getByText('11-7, 11-8, 11-9')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Tournament Lab assertions' })).toBeInTheDocument()
  })

  it('shows structured incompatibility instead of fabricating a tournament result', async () => {
    const user = userEvent.setup()
    const blocked = {
      ...compatibility,
      runnable_in_lab: false,
      normal_run_compatible: false,
      issues: [{
        severity: 'error',
        code: 'FORMAT_NOT_EXECUTABLE_V1',
        message: 'Tournament Lab V1 does not yet execute groups.'
      }]
    }
    api.inspectTournamentLabScenario.mockResolvedValue(blocked)

    renderWithRoute(<TournamentTestLabPage />, '/admin/labs/tournament')
    await user.click(await screen.findByRole('button', { name: 'Load editable copy' }))
    const editor = screen.getByLabelText('Tournament Lab scenario JSON')
    fireEvent.change(editor, {
      target: { value: JSON.stringify({ ...scenario, format_kind: 'groups' }) }
    })
    await user.click(screen.getByRole('button', { name: 'Inspect compatibility' }))

    const issues = await screen.findByRole('table', { name: 'Tournament Lab compatibility issues' })
    expect(within(issues).getByText('FORMAT_NOT_EXECUTABLE_V1')).toBeInTheDocument()
    expect(screen.getByText(/does not yet execute groups/)).toBeInTheDocument()
  })
})

import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PlayerTestLabPage } from './PlayerTestLabPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getPlayerLabBuiltInScenarios: vi.fn(),
  runPlayerTestLab: vi.fn()
}))
vi.mock('../api/client', () => api)

const scenario = {
  schema_version: 'player_test_lab_scenario.v1',
  scenario_id: 'development-activity-baseline',
  player: {
    player_id: 'LAB-PLAYER',
    attributes: [['Forehand', 100]],
    potential_ovr: 160,
    potential_identity: 'potential',
    potential_provenance: 'test',
    development_timing: 'Standard',
    current_form: 100,
    long_term_form_norm: 100,
    match_sharpness: 80,
    long_term_fatigue: 20,
    health_state: 'unsupported'
  },
  birth_year: 1980,
  birth_year_week: 1,
  start_week: { season_index: 0, week: 1 },
  development_policy: { policy_id: 'weekly-player-development.provisional.v1' },
  variants: [
    { variant_id: 'active', display_name: 'Active', competitive_match_counts: [1] },
    { variant_id: 'idle', display_name: 'Idle', competitive_match_counts: [0] }
  ],
  source_kind: 'portable'
}

const result = {
  schema_version: 'player_test_lab_result.v1',
  scenario_id: 'development-activity-baseline',
  scenario_fingerprint: 'a'.repeat(64),
  request_fingerprint: 'b'.repeat(64),
  compatibility: {
    production_kernels: ['weekly_player_development_update', 'between_week_state_update'],
    portable: true,
    isolated: true,
    run_mutation_performed: false,
    run_live_link: false,
    health_supported: true,
    training_load_supported: false,
    career_ai_supported: false,
    warnings: ['Health projection supported; numeric effects remain uncalibrated.']
  },
  variants: [
    {
      variant_id: 'active',
      display_name: 'Active',
      initial_state_fingerprint: 'c'.repeat(64),
      initial_health_projection: {
        player_id: 'LAB-PLAYER',
        current_records: [],
        permanent_consequences: [],
        affected_domains: [],
        highest_current_severity: 0,
        highest_permanent_limitation: 0,
        numeric_effect_applied: false,
        numeric_calibration_required: false
      },
      initial_health_projection_fingerprint: '2'.repeat(64),
      final_state_fingerprint: 'd'.repeat(64),
      snapshots: [{
        week: { season_index: 0, week: 2 },
        age: 20,
        completed_competitive_matches: 1,
        ovr: 101,
        potential_ovr: 160,
        current_form: 100,
        match_sharpness: 80,
        long_term_fatigue: 12,
        changed_attribute_count: 4,
        attribute_delta_total: 4,
        health_projection: {
          player_id: 'LAB-PLAYER',
          current_records: [],
          permanent_consequences: [],
          affected_domains: [],
          highest_current_severity: 0,
          highest_permanent_limitation: 0,
          numeric_effect_applied: false,
          numeric_calibration_required: false
        },
        health_projection_fingerprint: '3'.repeat(64),
        state_fingerprint: 'e'.repeat(64)
      }],
      final_player: {}
    },
    {
      variant_id: 'idle',
      display_name: 'Idle',
      initial_state_fingerprint: 'c'.repeat(64),
      initial_health_projection: {
        player_id: 'LAB-PLAYER',
        current_records: [],
        permanent_consequences: [],
        affected_domains: [],
        highest_current_severity: 0,
        highest_permanent_limitation: 0,
        numeric_effect_applied: false,
        numeric_calibration_required: false
      },
      initial_health_projection_fingerprint: '2'.repeat(64),
      final_state_fingerprint: 'f'.repeat(64),
      snapshots: [{
        week: { season_index: 0, week: 2 },
        age: 20,
        completed_competitive_matches: 0,
        ovr: 101,
        potential_ovr: 160,
        current_form: 100,
        match_sharpness: 78,
        long_term_fatigue: 12,
        changed_attribute_count: 4,
        attribute_delta_total: 4,
        health_projection: {
          player_id: 'LAB-PLAYER',
          current_records: [],
          permanent_consequences: [],
          affected_domains: [],
          highest_current_severity: 0,
          highest_permanent_limitation: 0,
          numeric_effect_applied: false,
          numeric_calibration_required: false
        },
        health_projection_fingerprint: '3'.repeat(64),
        state_fingerprint: '1'.repeat(64)
      }],
      final_player: {}
    }
  ],
  diagnostics: {
    variant_count: 2,
    duration_weeks: 1,
    distinct_final_state_count: 2,
    min_final_ovr: 101,
    max_final_ovr: 101,
    min_final_sharpness: 78,
    max_final_sharpness: 80
  }
}

describe('PlayerTestLabPage', () => {
  beforeEach(() => {
    api.getPlayerLabBuiltInScenarios.mockReset()
    api.runPlayerTestLab.mockReset()
    api.getPlayerLabBuiltInScenarios.mockResolvedValue([{
      scenario_id: scenario.scenario_id,
      display_name: 'Development activity baseline',
      description: 'Shared-kernel development comparison.',
      read_only: true,
      scenario_fingerprint: 'a'.repeat(64),
      scenario
    }])
    api.runPlayerTestLab.mockResolvedValue(result)
  })

  it('loads a built-in and renders shared-kernel diagnostics', async () => {
    const user = userEvent.setup()
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')

    expect(screen.getByRole('heading', { name: 'Player Test Lab' })).toBeInTheDocument()
    expect(await screen.findByText('Development activity baseline')).toBeInTheDocument()
    expect(screen.getByText(/never creates, saves or mutates a Product Run/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Run scenario' }))

    expect(api.runPlayerTestLab).toHaveBeenCalledTimes(1)
    expect(api.runPlayerTestLab.mock.calls[0][0]).toEqual({
      scenario: expect.objectContaining({
        schema_version: 'player_test_lab_scenario.v1',
        scenario_id: 'development-activity-baseline'
      })
    })
    expect(await screen.findByText(/weekly_player_development_update/)).toBeInTheDocument()
    expect(screen.getByText('supported')).toBeInTheDocument()
    expect(screen.getAllByText('not yet supported')).toHaveLength(2)
    expect(screen.getAllByText('not calibrated').length).toBeGreaterThan(0)
    expect(screen.getByRole('table', { name: 'Player Lab active timeline' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Player Lab idle timeline' })).toBeInTheDocument()
  })
})

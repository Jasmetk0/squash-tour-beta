import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PlayerTestLabPage } from './PlayerTestLabPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn().mockResolvedValue({run_containers: []}),
  listRunBranches: vi.fn().mockResolvedValue({run_branches: []}),
  listSavedRevisionHistory: vi.fn().mockResolvedValue({saved_revisions: []}),
  getPlayerLabBuiltInScenarios: vi.fn(),
  runPlayerTestLab: vi.fn(),
  runPlayerLabSession: vi.fn(),
  listPlayerLabSessions: vi.fn().mockResolvedValue([]),
  savePlayerLabSession: vi.fn(),
  importPlayerLabHistory: vi.fn(),
  listInitialPopulationComparisons: vi.fn().mockResolvedValue([]),
  getInitialPopulationComparison: vi.fn(),
  getInitialPopulationPlayers: vi.fn(),
  runInitialPopulationComparison: vi.fn(),
  initialPopulationExportUrl: vi.fn()
}))
vi.mock('../api/client', () => api)
vi.mock('../i18n/LanguageContext', () => ({useLanguage: () => ({language: 'en', t: (key: string) => key})}))

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
    api.listPlayerLabSessions.mockReset().mockResolvedValue([])
    api.savePlayerLabSession.mockReset()
    api.importPlayerLabHistory.mockReset()
    api.runPlayerLabSession.mockReset().mockResolvedValue(result)
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

  it.each(['edit', 'source'])('does not install a delayed historical import after a newer %s', async change => {
    let resolve!: (value: typeof scenario) => void
    const pending = new Promise<typeof scenario>(done => {resolve = done})
    api.importPlayerLabHistory.mockReturnValue(pending)
    const user = userEvent.setup()
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    await screen.findByText('Development activity baseline')
    const editor = screen.getByLabelText('Player Lab scenario JSON') as HTMLTextAreaElement
    for (const key of ['run', 'branch', 'revision', 'player']) fireEvent.change(screen.getByLabelText(`Player Lab import ${key}`), {target: {value: key + '-old'}})
    await user.click(screen.getByRole('button', {name: 'Import historical Player scenario'}))
    const local = {...scenario, scenario_id: 'newer-local'}
    if (change === 'edit') fireEvent.change(editor, {target: {value: JSON.stringify(local)}})
    else fireEvent.change(screen.getByLabelText('Player Lab import revision'), {target: {value: 'another-revision'}})
    const expected = editor.value
    await act(async () => {resolve({...scenario, scenario_id: 'late-import'}); await pending})
    await waitFor(() => expect(screen.getByRole('button', {name: 'Import historical Player scenario'})).toBeEnabled())
    expect(editor.value).toBe(expected)
  })

  it('preserves newer edits after Save and blocks stale sessions until explicit reload', async () => {
    const stored = {session_id: 'saved-player', version: 1, session_fingerprint: '1'.repeat(64), display_name: 'Saved Player', scenario}
    api.listPlayerLabSessions.mockResolvedValue([stored])
    let resolve!: (value: typeof stored) => void
    const pending = new Promise<typeof stored>(done => {resolve = done})
    api.savePlayerLabSession.mockReturnValue(pending)
    const user = userEvent.setup()
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    await screen.findByRole('option', {name: 'Saved Player'})
    await user.selectOptions(screen.getByLabelText('Open Player Test Session'), stored.session_id)
    const editor = screen.getByLabelText('Player Lab scenario JSON') as HTMLTextAreaElement
    const submitted = {...scenario, scenario_id: 'submitted'}
    fireEvent.change(editor, {target: {value: JSON.stringify(submitted)}})
    await user.click(screen.getByRole('button', {name: 'Save Player Test Session'}))
    const local = {...scenario, scenario_id: 'newer-local'}
    fireEvent.change(editor, {target: {value: JSON.stringify(local)}})
    const saved = {...stored, version: 2, session_fingerprint: '2'.repeat(64), scenario: submitted}
    api.listPlayerLabSessions.mockResolvedValue([saved])
    await act(async () => {resolve(saved); await pending})
    expect(JSON.parse(editor.value)).toEqual(local)
    expect(screen.getByRole('button', {name: 'Run scenario'})).toBeDisabled()
    api.listPlayerLabSessions.mockResolvedValue([{...saved, version: 3, session_fingerprint: '3'.repeat(64)}])
    await user.click(screen.getByRole('button', {name: 'Refresh Player Test Sessions'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('saved Test Session changed')
    expect(JSON.parse(editor.value)).toEqual(local)
    expect(screen.getByRole('button', {name: 'Reload saved Test Session'})).toBeDisabled()
    await user.click(screen.getByRole('checkbox', {name: 'Discard local edits when reloading'}))
    await user.click(screen.getByRole('button', {name: 'Reload saved Test Session'}))
    expect(JSON.parse(editor.value)).toEqual(submitted)
    await user.click(screen.getByRole('button', {name: 'Run scenario'}))
    expect(api.runPlayerLabSession).toHaveBeenCalledWith('saved-player', '3'.repeat(64))
  })

  it('retains in-flight status after editing and never publishes the detached old result', async () => {
    const user = userEvent.setup()
    let resolve!: (value: typeof result) => void
    const pending = new Promise<typeof result>(done => { resolve = done })
    api.runPlayerTestLab.mockImplementation(() => pending)
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Run scenario' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    const editor = screen.getByLabelText('Player Lab scenario JSON')
    fireEvent.change(editor, { target: { value: JSON.stringify({ ...scenario, scenario_id: 'newer-input' }) } })
    expect(screen.getByRole('button', { name: 'Running…' })).toBeDisabled()
    fireEvent.submit(editor.closest('form')!)
    expect(api.runPlayerTestLab).toHaveBeenCalledTimes(1)
    await act(async () => { resolve(result); await pending })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Run scenario' })).toBeEnabled())
    expect(screen.queryByRole('table', { name: 'Player Lab variant comparison' })).not.toBeInTheDocument()
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
  it('compares all Player Lab variants while filtering visible timelines without rerunning development', async () => {
    const user = userEvent.setup()
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    await screen.findByText('Development activity baseline')
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    const comparison = await screen.findByRole('table', { name: 'Player Lab variant comparison' })
    expect(within(comparison).getAllByRole('row')).toHaveLength(3)
    expect(screen.getByRole('table', { name: 'Player Lab active timeline' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Player Lab idle timeline' })).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Player Lab variant filter' }), 'idle')
    expect(screen.queryByRole('table', { name: 'Player Lab active timeline' })).not.toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Player Lab idle timeline' })).toBeInTheDocument()
    expect(within(comparison).getAllByRole('row')).toHaveLength(3)
    expect(screen.getByText('Showing 1 of 2 variants. Filters do not recalculate development.')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Player Lab variant filter' }), 'all')
    expect(screen.getByRole('table', { name: 'Player Lab active timeline' })).toBeInTheDocument()
    expect(api.runPlayerTestLab).toHaveBeenCalledTimes(1)
  })

  it('shows the last ten saved snapshots without changing final variant metrics', async () => {
    const user = userEvent.setup()
    const snapshots = Array.from({ length: 12 }, (_, index) => ({
      ...result.variants[0].snapshots[0],
      week: { season_index: 0, week: index + 1 },
      ovr: 90 + index,
      state_fingerprint: String(index).padStart(64, '0')
    }))
    api.runPlayerTestLab.mockResolvedValue({
      ...result,
      variants: [{
        ...result.variants[0],
        snapshots
      }]
    })
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    await screen.findByText('Development activity baseline')
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    const timeline = await screen.findByRole('table', { name: 'Player Lab active timeline' })
    expect(within(timeline).getAllByRole('row')).toHaveLength(13)
    const comparison = screen.getByRole('table', { name: 'Player Lab variant comparison' })
    expect(within(comparison).getByRole('cell', { name: '101' })).toBeInTheDocument()
    expect(within(comparison).getByRole('cell', { name: '+11' })).toBeInTheDocument()
    expect(screen.getByText(/Changes compare first and last recorded snapshots/)).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Player Lab timeline limit' }), '10')
    expect(within(timeline).getAllByRole('row')).toHaveLength(11)
    expect(within(timeline).queryByRole('cell', { name: 'S1 W1' })).not.toBeInTheDocument()
    expect(within(timeline).getByRole('cell', { name: 'S1 W12' })).toBeInTheDocument()
    expect(screen.getByText('Showing 10 of 12 saved snapshots.')).toBeInTheDocument()
    expect(within(comparison).getByRole('cell', { name: '101' })).toBeInTheDocument()
    expect(api.runPlayerTestLab).toHaveBeenCalledTimes(1)
  })

  it('formats valid JSON and clears stale results when the scenario is edited or reloaded', async () => {
    const user = userEvent.setup()
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    await screen.findByText('Development activity baseline')
    const editor = screen.getByRole('textbox', { name: 'Player Lab scenario JSON' })

    fireEvent.change(editor, { target: { value: JSON.stringify(scenario) } })
    await user.click(screen.getByRole('button', { name: 'Format JSON' }))
    expect(editor).toHaveValue(JSON.stringify(scenario, null, 2))

    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    expect(await screen.findByRole('table', { name: 'Player Lab active timeline' })).toBeInTheDocument()

    fireEvent.change(editor, { target: { value: '{}' } })
    expect(screen.queryByRole('table', { name: 'Player Lab active timeline' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run scenario' })).toBeDisabled()
    expect(screen.getByText(/invalid \/ incomplete JSON/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Load scenario' }))
    expect(screen.getByRole('button', { name: 'Run scenario' })).toBeEnabled()
    expect(screen.queryByRole('table', { name: 'Player Lab active timeline' })).not.toBeInTheDocument()
  })

  it('refreshes an empty built-in list without running the Player development engine', async () => {
    const user = userEvent.setup()
    api.getPlayerLabBuiltInScenarios.mockResolvedValueOnce([]).mockResolvedValue([{
      scenario_id: scenario.scenario_id,
      display_name: 'Development activity baseline',
      description: 'Shared-kernel development comparison.',
      read_only: true,
      scenario_fingerprint: 'a'.repeat(64),
      scenario
    }])
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    expect(await screen.findByText('No built-in Player Lab scenarios are available.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Refresh built-in scenarios' }))
    expect(await screen.findByText('Development activity baseline')).toBeInTheDocument()
    expect(api.getPlayerLabBuiltInScenarios).toHaveBeenCalledTimes(2)
    expect(api.runPlayerTestLab).not.toHaveBeenCalled()
  })

  it('shows a failed Player Lab built-in fetch as an error, not an empty list', async () => {
    api.getPlayerLabBuiltInScenarios.mockRejectedValue(new Error('No connection'))
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    expect(await screen.findByRole('alert')).toHaveTextContent('Built-in Player Lab scenarios unavailable.')
    expect(screen.queryByText('No built-in Player Lab scenarios are available.')).not.toBeInTheDocument()
  })

  it('does not overwrite an intentionally emptied editor with the built-in baseline', async () => {
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    await screen.findByText('Development activity baseline')
    const editor = screen.getByRole('textbox', { name: 'Player Lab scenario JSON' })
    fireEvent.change(editor, { target: { value: '' } })
    expect(editor).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Run scenario' })).toBeDisabled()
    expect(editor).toHaveValue('')
  })

  it('does not read an invalid variants value as a valid scenario', async () => {
    renderWithRoute(<PlayerTestLabPage />, '/admin/labs/player')
    await screen.findByText('Development activity baseline')
    const editor = screen.getByRole('textbox', { name: 'Player Lab scenario JSON' })
    fireEvent.change(editor, { target: { value: JSON.stringify({
      schema_version: 'player_test_lab_scenario.v1', scenario_id: 'partial', variants: null
    }) } })
    expect(screen.getByRole('button', { name: 'Run scenario' })).toBeDisabled()
    expect(screen.getByText(/invalid \/ incomplete JSON/)).toBeInTheDocument()
    expect(api.runPlayerTestLab).not.toHaveBeenCalled()
  })

})

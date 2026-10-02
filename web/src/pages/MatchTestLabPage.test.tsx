import { fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MatchTestLabPage } from './MatchTestLabPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({ runMatchTestLab: vi.fn(), getMatchLabBuiltInScenarios: vi.fn(), getMatchLabSessions: vi.fn(), createMatchLabSession: vi.fn(), updateMatchLabSession: vi.fn(), runMatchLabSession: vi.fn() }))
vi.mock('../api/client', () => api)

const result = {
  schema_version: 'match_test_lab_result.v1',
  scenario_id: 'portable-match-example',
  scenario_fingerprint: 'a'.repeat(64),
  request_fingerprint: 'b'.repeat(64),
  compatibility: {
    production_kernel: 'beta_engine.domain.matches.match_engine.MatchEngine.simulate',
    match_engine_version: 'match_engine_v10',
    portable: true,
    isolated: true,
    run_mutation_performed: false,
    run_live_link: false,
    normal_format: true,
    warnings: []
  },
  results: [
    {
      seed: 100,
      result_fingerprint: 'c'.repeat(64),
      winner_player_id: 'LAB-A',
      loser_player_id: 'LAB-B',
      sets_won: { 'LAB-A': 3, 'LAB-B': 1 },
      set_scores: ['11-7', '9-11', '11-8', '11-6'],
      termination_reason: 'COMPLETED',
      rally_count: 74,
      elapsed_seconds: 1860
    },
    {
      seed: 101,
      result_fingerprint: 'd'.repeat(64),
      winner_player_id: 'LAB-B',
      loser_player_id: 'LAB-A',
      sets_won: { 'LAB-A': 2, 'LAB-B': 3 },
      set_scores: ['11-9', '7-11', '11-8', '8-11', '9-11'],
      termination_reason: 'COMPLETED',
      rally_count: 95,
      elapsed_seconds: 2410
    }
  ],
  diagnostics: {
    seed_count: 2,
    wins_by_player: { 'LAB-A': 1, 'LAB-B': 1 },
    retirement_count: 0,
    average_rally_count: 84.5,
    average_elapsed_seconds: 2135,
    distinct_result_count: 2
  }
}

describe('MatchTestLabPage', () => {
  beforeEach(() => {
    for (const fn of Object.values(api)) fn.mockReset()
    api.runMatchTestLab.mockResolvedValue(result)
    api.runMatchLabSession.mockResolvedValue(result)
    api.getMatchLabBuiltInScenarios.mockResolvedValue([])
    api.getMatchLabSessions.mockResolvedValue([])
  })

  it('runs a portable multi-seed scenario and renders isolation diagnostics', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')

    expect(screen.getByRole('heading', { name: 'Match Test Lab' })).toBeInTheDocument()
    expect(screen.getByText(/outside every Run and Branch/i)).toBeInTheDocument()
    expect((screen.getByLabelText('Match Lab scenario JSON') as HTMLTextAreaElement).value).toContain('portable-match-example')

    await user.type(screen.getByLabelText('Match Lab batch seeds'), '100, 101')
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))

    expect(api.runMatchTestLab).toHaveBeenCalledTimes(1)
    expect(api.runMatchTestLab.mock.calls[0][0]).toEqual(expect.objectContaining({
      batch_seeds: [100, 101],
      scenario: expect.objectContaining({
        schema_version: 'match_test_lab_scenario.v1',
        scenario_id: 'portable-match-example',
        seed: 777,
        source_kind: 'portable'
      })
    }))

    expect(await screen.findByText('match_engine_v10')).toBeInTheDocument()
    expect(screen.getByText(/No compatibility warnings/i)).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Match Lab results' })
    expect(within(table).getByRole('cell', { name: '100' })).toBeInTheDocument()
    expect(within(table).getByRole('cell', { name: '101' })).toBeInTheDocument()
    expect(within(table).getByText('LAB-A')).toBeInTheDocument()
    expect(screen.getByText(/LAB-A: 1/)).toBeInTheDocument()
    expect(screen.getByText(/LAB-B: 1/)).toBeInTheDocument()
  })

  it('rejects malformed local JSON before calling the API', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')

    const editor = screen.getByLabelText('Match Lab scenario JSON')
    fireEvent.change(editor, { target: { value: '{bad json' } })
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))

    expect(api.runMatchTestLab).not.toHaveBeenCalled()
    expect(screen.getByText("Expected property name or '}' in JSON at position 1")).toBeInTheDocument()
  })

  it('creates an isolated editable Test Session from a read-only built-in', async () => {
    const user = userEvent.setup()
    const builtIn = {
      scenario_id: 'standard-even-match',
      display_name: 'Standard even match',
      description: 'Normal baseline',
      read_only: true,
      scenario_fingerprint: 'e'.repeat(64),
      scenario: {
        schema_version: 'match_test_lab_scenario.v1',
        scenario_id: 'standard-even-match',
        seed: 777,
        source_kind: 'portable',
        context: {}
      }
    }
    const created = {
      schema_version: 'match_test_lab_session.v1',
      session_id: 'session-1',
      display_name: 'Standard even match — Test Session',
      version: 1,
      session_fingerprint: 'f'.repeat(64),
      scenario: {
        ...builtIn.scenario,
        scenario_id: 'session-copy:standard-even-match',
        source_kind: 'built_in_copy',
        source_reference: 'standard-even-match',
        source_fingerprint: builtIn.scenario_fingerprint
      }
    }
    api.getMatchLabBuiltInScenarios.mockResolvedValue([builtIn])
    api.createMatchLabSession.mockResolvedValue(created)
    api.getMatchLabSessions.mockResolvedValueOnce([]).mockResolvedValue([created])

    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')

    expect(await screen.findByText('Standard even match')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /New Test Session from Standard even match/ }))

    expect(api.createMatchLabSession).toHaveBeenCalledWith({
      display_name: 'Standard even match — Test Session',
      built_in_scenario_id: 'standard-even-match'
    })
    expect(await screen.findByDisplayValue('Standard even match — Test Session')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Match Lab scenario JSON'), {
      target: { value: JSON.stringify({ ...created.scenario, seed: 999 }) }
    })
    await user.click(screen.getByRole('button', { name: 'Save Test Session' }))

    expect(api.updateMatchLabSession).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({
        expected_session_fingerprint: 'f'.repeat(64),
        scenario: expect.objectContaining({ seed: 999 })
      })
    )
  })

})

import { fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MatchTestLabPage } from './MatchTestLabPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({ runMatchTestLab: vi.fn() }))
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
    api.runMatchTestLab.mockReset()
    api.runMatchTestLab.mockResolvedValue(result)
  })

  it('runs a portable multi-seed scenario and renders isolation diagnostics', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')

    expect(screen.getByRole('heading', { name: 'Match Test Lab' })).toBeInTheDocument()
    expect(screen.getByText(/never mutate a Run or Branch/i)).toBeInTheDocument()
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
    expect(screen.getByText(/Expected property name|JSON/i)).toBeInTheDocument()
  })
})

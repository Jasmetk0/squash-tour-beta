import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MatchTestLabPage } from './MatchTestLabPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn().mockResolvedValue({run_containers: []}),
  listRunBranches: vi.fn().mockResolvedValue({run_branches: []}),
  listSavedRevisionHistory: vi.fn().mockResolvedValue({saved_revisions: []}), runMatchTestLab: vi.fn(), getMatchLabBuiltInScenarios: vi.fn(), getMatchLabSessions: vi.fn(), createMatchLabSession: vi.fn(), updateMatchLabSession: vi.fn(), runMatchLabSession: vi.fn(), importMatchLabSavedRevisionPlayer: vi.fn() }))
vi.mock('../api/client', () => api)
const testLocale = vi.hoisted(() => ({language: 'en' as 'en' | 'cs'}))
vi.mock('../i18n/LanguageContext', () => ({useLanguage: () => ({language: testLocale.language, t: (key: string) => key})}))
function LocalizedMatchPage(): JSX.Element {
  const [cs, setCs] = useState(false)
  testLocale.language = cs ? 'cs' : 'en'
  return <><button type="button" onClick={() => setCs(value => !value)}>Toggle test language</button><MatchTestLabPage /></>
}

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
    testLocale.language = 'en'
    for (const fn of Object.values(api)) fn.mockReset()
    api.runMatchTestLab.mockResolvedValue(result)
    api.runMatchLabSession.mockResolvedValue(result)
    api.getMatchLabBuiltInScenarios.mockResolvedValue([])
    api.getMatchLabSessions.mockResolvedValue([])
    api.importMatchLabSavedRevisionPlayer.mockResolvedValue(undefined)
  })


  it('shows Czech batch-seed validation without issuing a Match request', async () => {
    renderWithRoute(<LocalizedMatchPage />, '/admin/labs/match')
    fireEvent.click(screen.getByRole('button', {name: 'Toggle test language'}))
    fireEvent.change(screen.getByLabelText('Match Lab batch seeds'), {target: {value: '1, 1'}})
    fireEvent.click(screen.getByRole('button', {name: 'Spustit scénář'}))
    expect(screen.getByRole('alert')).toHaveTextContent('Seedy dávky se nesmí opakovat.')
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
    expect(api.createMatchLabSession).not.toHaveBeenCalled()
  })

  it('keeps the scratch JSON, seed and request intact when switching to Czech', async () => {
    renderWithRoute(<LocalizedMatchPage />, '/admin/labs/match')
    const editor = screen.getByLabelText('Match Lab scenario JSON') as HTMLTextAreaElement
    const draft = JSON.parse(editor.value)
    draft.seed = 429
    fireEvent.change(editor, {target: {value: JSON.stringify(draft)}})
    fireEvent.change(screen.getByLabelText('Match Lab batch seeds'), {target: {value: '12, 13'}})
    fireEvent.click(screen.getByRole('button', {name: 'Toggle test language'}))
    expect(screen.getByLabelText('Match Lab batch seeds')).toHaveValue('12, 13')
    expect(JSON.parse((screen.getByLabelText('Match Lab scenario JSON') as HTMLTextAreaElement).value).seed).toBe(429)
    expect(api.createMatchLabSession).not.toHaveBeenCalled()
    expect(api.updateMatchLabSession).not.toHaveBeenCalled()
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', {name: 'Spustit scénář'}))
    await waitFor(() => expect(api.runMatchTestLab).toHaveBeenCalledWith(expect.objectContaining({
      scenario: expect.objectContaining({seed: 429}),
      batch_seeds: [12, 13]
    })))
  })

  it('creates an isolated Session from the current scratch JSON without automatically running', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
    const draft = JSON.parse((screen.getByLabelText('Match Lab scenario JSON') as HTMLTextAreaElement).value)
    const created = {
      schema_version: 'match_test_lab_session.v1', session_id: 'scratch-created',
      display_name: 'My Match experiments', version: 1,
      session_fingerprint: 'f'.repeat(64), participant_imports: [], scenario: draft
    }
    api.createMatchLabSession.mockResolvedValue(created)
    api.getMatchLabSessions.mockResolvedValueOnce([]).mockResolvedValue([created])
    const nameInput = screen.getByLabelText('Match Lab new Session name')
    await user.clear(nameInput)
    await user.type(nameInput, 'My Match experiments')
    await user.click(screen.getByRole('button', {name: 'Create Test Session from scratch'}))
    expect(api.createMatchLabSession).toHaveBeenCalledWith({
      display_name: 'My Match experiments', scenario: draft
    })
    expect(await screen.findByDisplayValue('My Match experiments')).toBeInTheDocument()
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
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

  it('filters Match Lab batch results by winner without changing diagnostics or rerunning the API', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    const table = await screen.findByRole('table', { name: 'Match Lab results' })
    const winnerFilter = screen.getByRole('combobox', { name: 'Match Lab winner filter' })
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(screen.getByText('Showing 2 of 2 results · Batch diagnostics above include all matches.')).toBeInTheDocument()
    await user.selectOptions(winnerFilter, 'LAB-A')
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByRole('cell', { name: '100' })).toBeInTheDocument()
    expect(within(table).queryByRole('cell', { name: '101' })).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 2 results · Batch diagnostics above include all matches.')).toBeInTheDocument()
    expect(screen.getByText('Wins: LAB-A: 1 · LAB-B: 1')).toBeInTheDocument()
    await user.selectOptions(winnerFilter, 'all')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(api.runMatchTestLab).toHaveBeenCalledTimes(1)
  })

  it('clears previous Match Lab results when the current scenario or batch seeds change', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    expect(await screen.findByRole('table', { name: 'Match Lab results' })).toBeInTheDocument()

    const editor = screen.getByRole('textbox', { name: 'Match Lab scenario JSON' })
    const value = JSON.parse((editor as HTMLTextAreaElement).value)
    fireEvent.change(editor, { target: { value: JSON.stringify({ ...value, scenario_id: 'edited-match' }) } })
    expect(screen.queryByRole('table', { name: 'Match Lab results' })).not.toBeInTheDocument()
    expect(screen.getByText(/Scenario: edited-match/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    expect(await screen.findByRole('table', { name: 'Match Lab results' })).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Match Lab batch seeds' }), { target: { value: '100, 101' } })
    expect(screen.queryByRole('table', { name: 'Match Lab results' })).not.toBeInTheDocument()
  })

  it('rejects empty and unsafe batch seed tokens rather than silently treating them as zero', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
    const field = screen.getByRole('textbox', { name: 'Match Lab batch seeds' })
    fireEvent.change(field, { target: { value: '100, ' } })
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Batch seeds must be comma-separated integers.')
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
    fireEvent.change(field, { target: { value: '9007199254740992' } })
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Batch seeds must be comma-separated integers.')
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
  })

  it('recovers a failed built-in list in Czech without replacing scratch JSON or writing', async () => {
    const user = userEvent.setup()
    api.getMatchLabBuiltInScenarios.mockRejectedValueOnce(new Error('Match registry offline'))
      .mockResolvedValue([])
    renderWithRoute(<LocalizedMatchPage />, '/admin/labs/match')
    await user.click(screen.getByRole('button', { name: 'Toggle test language' }))
    const editor = screen.getByRole('textbox', { name: 'Match Lab scenario JSON' })
    fireEvent.change(editor, { target: { value: '{"preserve":"local"}' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Match registry offline')
    await user.click(screen.getByRole('button', { name: 'Obnovit vestavěné scénáře' }))
    expect(await screen.findByText('Registr neobsahuje žádné vestavěné scénáře.')).toBeInTheDocument()
    expect(editor).toHaveValue('{"preserve":"local"}')
    expect(api.getMatchLabBuiltInScenarios).toHaveBeenCalledTimes(2)
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
    expect(api.createMatchLabSession).not.toHaveBeenCalled()
  })

  it('manually refreshes Match Test Session inventory without modifying or running any session', async () => {
    const user = userEvent.setup()
    api.getMatchLabSessions.mockResolvedValueOnce([]).mockResolvedValue([{
      session_id: 'new-session', display_name: 'Fresh Match Session', version: 1
    }])
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
    expect(await screen.findByText('No saved Match Test Sessions yet. Scratch mode remains available.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Refresh Test Sessions' }))
    expect(await screen.findByRole('option', { name: 'Fresh Match Session · v1' })).toBeInTheDocument()
    expect(api.getMatchLabSessions).toHaveBeenCalledTimes(2)
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
    expect(api.createMatchLabSession).not.toHaveBeenCalled()
  })

  it('formats scratch JSON without running and reports a missing saved-session inventory honestly', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
    expect(await screen.findByText('No saved Match Test Sessions yet. Scratch mode remains available.')).toBeInTheDocument()
    const editor = screen.getByRole('textbox', { name: 'Match Lab scenario JSON' })
    const compact = JSON.stringify(JSON.parse((editor as HTMLTextAreaElement).value))
    fireEvent.change(editor, { target: { value: compact } })
    await user.click(screen.getByRole('button', { name: 'Format JSON' }))
    expect(editor).toHaveValue(JSON.stringify(JSON.parse(compact), null, 2))
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
    fireEvent.change(editor, { target: { value: 'null' } })
    await user.click(screen.getByRole('button', { name: 'Format JSON' }))
    expect(screen.getByRole('alert')).toHaveTextContent('A Lab scenario must be a JSON object.')
    expect(editor).toHaveValue('null')
  })

  it('reports an unavailable saved Match Test Session list rather than claiming no saved sessions', async () => {
    api.getMatchLabSessions.mockRejectedValue(new Error('Backend unavailable'))
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
    expect(await screen.findByRole('alert')).toHaveTextContent('Saved Match Test Sessions unavailable.')
    expect(screen.queryByText('No saved Match Test Sessions yet. Scratch mode remains available.')).not.toBeInTheDocument()
  })

  it('rejects malformed local JSON before calling the API', async () => {
    const user = userEvent.setup()
    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')

    const editor = screen.getByLabelText('Match Lab scenario JSON')
    fireEvent.change(editor, { target: { value: '{bad json' } })
    await user.click(screen.getByRole('button', { name: 'Run scenario' }))

    expect(api.runMatchTestLab).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid scenario JSON. Check the syntax before running or saving.')
    expect(editor).toHaveValue('{bad json')
    expect(api.runMatchLabSession).not.toHaveBeenCalled()
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
      participant_imports: [],
      scenario: {
        ...builtIn.scenario,
        scenario_id: 'session-copy:standard-even-match',
        source_kind: 'built_in_copy',
        source_reference: 'standard-even-match',
        source_fingerprint: builtIn.scenario_fingerprint
      }
    }
    api.getMatchLabBuiltInScenarios.mockResolvedValue([builtIn])
    const updated = {
      ...created, version: 2, session_fingerprint: '9'.repeat(64),
      scenario: { ...created.scenario, seed: 999 }
    }
    api.createMatchLabSession.mockResolvedValue(created)
    api.updateMatchLabSession.mockResolvedValue(updated)
    api.getMatchLabSessions.mockResolvedValueOnce([]).mockResolvedValueOnce([created]).mockResolvedValue([updated])

    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')

    expect(await screen.findByText('Standard even match')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /New Test Session from Standard even match/ }))

    expect(api.createMatchLabSession).toHaveBeenCalledWith(
      {
        display_name: 'Standard even match — Test Session',
        built_in_scenario_id: 'standard-even-match'
      }
    )
    expect(await screen.findByDisplayValue('Standard even match — Test Session')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Match Lab scenario JSON'), { target: { value: '{bad json' } })
    await user.click(screen.getByRole('button', { name: 'Save Test Session' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid scenario JSON.')
    expect(api.updateMatchLabSession).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Match Lab scenario JSON'), {
      target: { value: JSON.stringify({ ...created.scenario, seed: 999 }) }
    })
    expect(screen.getByRole('button', { name: 'Run Test Session' })).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Unsaved Test Session changes.')
    expect(api.runMatchLabSession).not.toHaveBeenCalled()
    // Enter/programmatic form submission must enforce the same saved boundary.
    fireEvent.submit(screen.getByRole('button', { name: 'Run Test Session' }).closest('form')!)
    expect(screen.getByRole('alert')).toHaveTextContent('Save Test Session changes before running this scenario.')
    expect(api.runMatchLabSession).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Save Test Session' }))

    expect(api.updateMatchLabSession).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({
        expected_session_fingerprint: 'f'.repeat(64),
        scenario: expect.objectContaining({ seed: 999 })
      })
    )
    await waitFor(() => expect(screen.getByRole('button', { name: 'Run Test Session' })).toBeEnabled())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByText('Unsaved Test Session changes. Save before running.')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Run Test Session' }))
    expect(api.runMatchLabSession).toHaveBeenCalledWith('session-1', {
      expected_session_fingerprint: '9'.repeat(64), batch_seeds: []
    })
    expect(api.runMatchTestLab).not.toHaveBeenCalled()
  })


  it('imports a reviewed historical Saved Revision player into an isolated Test Session', async () => {
    const user = userEvent.setup()
    const session = {
      schema_version: 'match_test_lab_session.v1',
      session_id: 'session-history',
      display_name: 'Historical session',
      version: 1,
      session_fingerprint: '1'.repeat(64),
      participant_imports: [],
      scenario: {
        schema_version: 'match_test_lab_scenario.v1',
        scenario_id: 'history',
        seed: 7,
        source_kind: 'portable',
        context: {}
      }
    }
    const imported = {
      ...session,
      version: 2,
      session_fingerprint: '2'.repeat(64),
      participant_imports: [{
        side: 'player_a',
        product_run_id: 'run-1',
        branch_id: 'branch-1',
        saved_revision_id: 'revision-1',
        saved_revision_content_hash: 'a'.repeat(64),
        sporting_state_fingerprint: 'b'.repeat(64),
        sporting_week_ordinal: 61,
        player_id: 'P1',
        source_profile_fingerprint: 'profile:P1',
        canonical_projection_fingerprint: 'c'.repeat(64)
      }],
      scenario: {
        ...session.scenario,
        context: { player_a: { player: { player_id: 'P1' } } }
      }
    }
    api.getMatchLabSessions.mockResolvedValueOnce([session]).mockResolvedValue([imported])
    api.importMatchLabSavedRevisionPlayer.mockResolvedValue(imported)

    renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
    await screen.findByRole('option', { name: /Historical session/ })
    await user.selectOptions(screen.getByLabelText('Open Match Test Session'), 'session-history')
    await user.type(screen.getByLabelText('Match Lab import Run ID'), 'run-1')
    await user.type(screen.getByLabelText('Match Lab import Branch ID'), 'branch-1')
    await user.type(screen.getByLabelText('Match Lab import Saved Revision ID'), 'revision-1')
    await user.type(screen.getByLabelText('Match Lab import Player ID'), 'P1')
    await user.click(screen.getByRole('button', { name: 'Import historical player' }))

    expect(api.importMatchLabSavedRevisionPlayer).toHaveBeenCalledWith(
      'session-history',
      {
        expected_session_fingerprint: '1'.repeat(64),
        product_run_id: 'run-1',
        branch_id: 'branch-1',
        saved_revision_id: 'revision-1',
        player_id: 'P1',
        side: 'player_a'
      }
    )
    expect(await screen.findByRole('table', { name: 'Match Lab historical imports' })).toBeInTheDocument()
    expect(screen.getByText('run-1 / branch-1 / revision-1')).toBeInTheDocument()
  })

})

import { screen, waitFor } from '@testing-library/react'
import { QueryClient } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminRunBranchesPage, simulationEligibility } from './AdminRunBranchesPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => { class ApiError extends Error { constructor(message: string, public status: number) { super(message) } }; return { ApiError, getRunContainer: vi.fn(), listRunBranches: vi.fn(), listBranchStates: vi.fn(), listBranchCheckpoints: vi.fn(), forkRunBranch: vi.fn(), makeOfficialRunBranch: vi.fn(), simulateNextMatchOnBranch: vi.fn(), simulateNextRoundOnBranch: vi.fn(), simulateNextWeekOnBranch: vi.fn(), simulateNextTournamentOnBranch: vi.fn(), simulateFullSeasonOnBranch: vi.fn() } })
vi.mock('../api/client', () => api)
const run = { run_id: 'run-a', display_name: 'Admin Run', status: 'active', read_only: false, storage_kind: 'custom_local', official_branch_id: 'official' }
const official = { branch_id: 'official', run_id: 'run-a', display_name: 'Official Branch', status: 'active', read_only: false, branch_seed: 17, legacy_simulation_run_id: 'legacy-official', forked_from_branch_id: null, forked_from_checkpoint_id: null, head_checkpoint_id: 'cp-initial', is_official: true }
const readonly = { ...official, branch_id: 'readonly', display_name: 'Read only Branch', read_only: true, head_checkpoint_id: 'cp-readonly', is_official: false }
const state = (branchId = 'official', head = 'cp-initial') => ({ branch_id: branchId, run_id: 'run-a', head_checkpoint_id: head, current_season: 2030, current_week: 12, current_event_id: 'EVENT-12', current_event_sequence: 4 })
const checkpoint = (id = 'cp-initial', kind = 'initial', branchId = 'official') => ({ checkpoint_id: id, run_id: 'run-a', branch_id: branchId, kind, sequence: 1, season: 2030, week: 12, event_id: 'EVENT-12', event_sequence: 4 })
const success = (replay = false) => ({ product_run_id: 'run-a', source_branch_id: 'official', source_checkpoint_id: 'cp-initial', target_branch_id: 'fork-a', target_legacy_simulation_run_id: 'legacy-fork', target_checkpoint_id: 'cp-fork', target_branch_seed: 44, source_inventory_hash: 'source', normalized_clone_equivalence_hash: 'clone', request_fingerprint: 'request', idempotent_replay: replay, created_mapping: false, official_branch_changed: false })
const simulationSuccess = (replay = false) => ({ product_run_id: 'run-a', branch_id: 'official', legacy_simulation_run_id: 'legacy-official', command_id: 'simulation-command', request_fingerprint: 'simulation-fingerprint', idempotent_replay: replay, previous_head_checkpoint_id: 'cp-initial', new_head_checkpoint_id: 'cp-next', previous_season: 2030, previous_week: 12, previous_event_id: 'EVENT-12', previous_event_sequence: 4, current_season: 2030, current_week: 12, current_event_id: 'EVENT-12', current_event_sequence: 5, official_branch_changed: false, simulation_result: { mode: 'simulate_next_match', active_tournament: null, completed_event_count: 2, next_event_index: 3 } })
function setup({ branches = [official, readonly], states = [state(), state('readonly', 'cp-readonly')], checkpoints = [checkpoint(), checkpoint('cp-readonly', 'initial', 'readonly')] } = {}) { api.getRunContainer.mockResolvedValue(run); api.listRunBranches.mockResolvedValue({ run_branches: branches }); api.listBranchStates.mockResolvedValue({ branch_states: states }); api.listBranchCheckpoints.mockResolvedValue({ branch_checkpoints: checkpoints }); api.forkRunBranch.mockResolvedValue(success()); api.simulateNextMatchOnBranch.mockResolvedValue(simulationSuccess()); api.simulateNextRoundOnBranch.mockResolvedValue({ ...simulationSuccess(), simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_round' } }); api.simulateNextWeekOnBranch.mockResolvedValue({ ...simulationSuccess(), simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_week' } }); api.simulateNextTournamentOnBranch.mockResolvedValue({ ...simulationSuccess(), simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_tournament' } }); api.simulateFullSeasonOnBranch.mockResolvedValue(fullSeasonSuccess()) }
const fullSeasonSuccess = (replay = false) => ({ ...simulationSuccess(replay), new_head_checkpoint_id: 'cp-season', current_week: null, current_event_id: null, current_event_sequence: null, simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_full_season', completed_event_count: 24, next_event_index: 25, completed_in_command_count: 20, completed_week_group_count: 12, season_complete: true } })
async function fillValidForm(confirm = true) { const user = userEvent.setup(); await user.type(screen.getByLabelText('target_branch_display_name'), ' Fork Name '); await user.type(screen.getByLabelText('target_branch_id'), ' fork-a '); await user.type(screen.getByLabelText('target_legacy_simulation_run_id'), ' legacy-fork '); await user.type(screen.getByLabelText('target_branch_seed'), ' 44 '); await user.type(screen.getByLabelText('command_id'), ' command-a '); if (confirm) await user.click(screen.getByRole('checkbox')) }
beforeEach(() => { vi.clearAllMocks(); for (const value of Object.values(api)) if (vi.isMockFunction(value)) value.mockReset(); setup() })
describe('AdminRunBranchesPage', () => {
  it('renders Product Run Branch overview and effective BranchState context', async () => { renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); expect(await screen.findByText('Admin Run')).toBeInTheDocument(); expect(screen.getAllByText('Official Branch')[0]).toBeInTheDocument(); expect(screen.getAllByText('official').length).toBeGreaterThan(0); expect(screen.getByText('Official')).toBeInTheDocument(); expect(screen.getAllByText('17').length).toBeGreaterThan(0); expect(screen.getAllByText('legacy-official').length).toBeGreaterThan(0); expect(screen.getAllByText('cp-initial').length).toBeGreaterThan(0); for (const value of ['2030', '12', 'EVENT-12', '4']) expect(screen.getAllByText(value).length).toBeGreaterThan(0) })
  it.each(['initial', 'current_state_capture'])('enables a safe %s effective head after valid confirmed input', async (kind) => { setup({ checkpoints: [checkpoint('cp-initial', kind), checkpoint('cp-readonly', 'initial', 'readonly')] }); renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); const submit = await screen.findByRole('button', { name: 'Create Branch fork' }); expect(submit).toBeDisabled(); await fillValidForm(); expect(submit).toBeEnabled() })
  it.each([['read-only Branch', [readonly], [state('readonly', 'cp-readonly')], [checkpoint('cp-readonly', 'initial', 'readonly')]], ['inactive Branch', [{ ...official, status: 'inactive' }], [state()], [checkpoint()]], ['disagreeing heads', [official], [state('official', 'other-head')], [checkpoint()]], ['missing head checkpoint', [official], [state()], []], ['unsupported checkpoint kind', [official], [state()], [checkpoint('cp-initial', 'event_completed')]]])('keeps submission disabled for %s', async (_name, branches, states, checkpoints) => { setup({ branches, states, checkpoints }); renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await screen.findByRole('heading', { name: 'Create Branch fork' }); await fillValidForm(); expect(screen.getByRole('button', { name: 'Create Branch fork' })).toBeDisabled() })
  it('only submits explicitly, with the exact trimmed payload after validation and confirmation', async () => { renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); const submit = await screen.findByRole('button', { name: 'Create Branch fork' }); await fillValidForm(false); expect(api.forkRunBranch).not.toHaveBeenCalled(); expect(submit).toBeDisabled(); await userEvent.click(screen.getByRole('checkbox')); await userEvent.click(submit); await waitFor(() => expect(api.forkRunBranch).toHaveBeenCalledTimes(1)); expect(api.forkRunBranch).toHaveBeenCalledWith('run-a', { source_branch_id: 'official', source_checkpoint_id: 'cp-initial', target_branch_id: 'fork-a', target_branch_display_name: 'Fork Name', target_legacy_simulation_run_id: 'legacy-fork', target_branch_seed: 44, command_id: 'command-a' }); expect(api.listRunBranches.mock.calls.length).toBeGreaterThanOrEqual(2); expect(api.listBranchStates.mock.calls.length).toBeGreaterThanOrEqual(2); expect(api.listBranchCheckpoints.mock.calls.length).toBeGreaterThanOrEqual(2); expect(api.getRunContainer.mock.calls.length).toBeGreaterThanOrEqual(2) })
  it('blocks blank and non-integer seed submissions', async () => { renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await screen.findByRole('heading', { name: 'Create Branch fork' }); await userEvent.click(screen.getByRole('checkbox')); expect(screen.getByRole('button', { name: 'Create Branch fork' })).toBeDisabled(); await fillValidForm(false); await userEvent.clear(screen.getByLabelText('target_branch_seed')); await userEvent.type(screen.getByLabelText('target_branch_seed'), '4.4'); expect(screen.getByRole('button', { name: 'Create Branch fork' })).toBeDisabled(); expect(api.forkRunBranch).not.toHaveBeenCalled() })
  it('displays a successful idempotent fork result without claiming another Branch', async () => { api.forkRunBranch.mockResolvedValueOnce(success(true)); renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await screen.findByRole('heading', { name: 'Create Branch fork' }); await fillValidForm(); await userEvent.click(screen.getByRole('button', { name: 'Create Branch fork' })); const result = await screen.findByLabelText('Fork result'); for (const value of ['fork-a', 'cp-fork', 'legacy-fork', 'idempotent replay: true', 'created_mapping: false', 'official_branch_changed: false']) expect(result).toHaveTextContent(value); expect(result).not.toHaveTextContent('another separate Branch') })
  it('shows formatted 409 conflicts while preserving form values and the Branch overview', async () => { api.forkRunBranch.mockRejectedValueOnce(new api.ApiError(JSON.stringify({ detail: 'target Branch already exists' }), 409)); renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await screen.findAllByText('Official Branch'); await fillValidForm(); await userEvent.click(screen.getByRole('button', { name: 'Create Branch fork' })); expect(await screen.findByText('target Branch already exists')).toBeInTheDocument(); expect(screen.getByLabelText('target_branch_id')).toHaveValue(' fork-a '); expect(screen.getAllByText('Official Branch')[0]).toBeInTheDocument(); expect(api.forkRunBranch).toHaveBeenCalledTimes(1) })

  it('opens official selection for an active coherent read-only Branch and submits the exact guarded request', async () => {
    api.makeOfficialRunBranch.mockResolvedValueOnce({ product_run_id: 'run-a', previous_official_branch_id: 'official', official_branch_id: 'readonly', target_branch_id: 'readonly', changed: true, idempotent_replay: false, request_fingerprint: 'fingerprint-a' })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    await screen.findByText('Admin Run')
    const action = screen.getByRole('button', { name: 'Make official' })
    expect(action).toBeEnabled()
    await userEvent.click(action)
    expect(api.makeOfficialRunBranch).not.toHaveBeenCalled()
    await userEvent.type(screen.getByLabelText('Audit reason'), ' publish readonly ')
    const boxes = screen.getAllByRole('checkbox')
    await userEvent.click(boxes[0])
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Make official' }))
    await waitFor(() => expect(api.makeOfficialRunBranch).toHaveBeenCalledTimes(1))
    expect(api.makeOfficialRunBranch).toHaveBeenCalledWith('run-a', 'readonly', expect.objectContaining({ expected_current_official_branch_id: 'official', audit_reason: 'publish readonly', explicit_confirmation: true }))
    expect(api.forkRunBranch).not.toHaveBeenCalled()
    expect(await screen.findByLabelText('Official Branch result')).toHaveTextContent('The official Branch was changed successfully.')
  })
  it('preserves the reviewed official Branch and command ID for an ordinary error retry', async () => {
    api.makeOfficialRunBranch.mockRejectedValueOnce(new api.ApiError(JSON.stringify({ detail: 'try again' }), 400)).mockResolvedValueOnce({ product_run_id: 'run-a', previous_official_branch_id: 'official', official_branch_id: 'readonly', target_branch_id: 'readonly', changed: true, idempotent_replay: false, request_fingerprint: 'retry' })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    await screen.findByText('Admin Run'); await userEvent.click(screen.getByRole('button', { name: 'Make official' })); await userEvent.type(screen.getByLabelText('Audit reason'), 'reviewed reason'); await userEvent.click(screen.getAllByRole('checkbox')[0]); await userEvent.click(screen.getByRole('button', { name: 'Confirm Make official' }))
    await waitFor(() => expect(api.makeOfficialRunBranch).toHaveBeenCalledTimes(1))
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Make official' }))
    await waitFor(() => expect(api.makeOfficialRunBranch).toHaveBeenCalledTimes(2))
    expect(api.makeOfficialRunBranch.mock.calls[1]).toEqual(api.makeOfficialRunBranch.mock.calls[0])
  })
  it('refreshes the reviewed official Branch snapshot after a 409 conflict', async () => {
    const refreshedRun = { ...run, official_branch_id: 'official-b' }
    api.getRunContainer.mockResolvedValueOnce({ ...run, official_branch_id: 'official-a' }).mockResolvedValue(refreshedRun)
    api.makeOfficialRunBranch.mockRejectedValueOnce(new api.ApiError(JSON.stringify({ detail: 'official changed' }), 409)).mockResolvedValueOnce({ product_run_id: 'run-a', previous_official_branch_id: 'official-b', official_branch_id: 'readonly', target_branch_id: 'readonly', changed: true, idempotent_replay: false, request_fingerprint: 'after-conflict' })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    await screen.findByText('Admin Run'); await userEvent.click(screen.getAllByRole('button', { name: 'Make official' })[1]); await userEvent.type(screen.getByLabelText('Audit reason'), 'reviewed reason'); await userEvent.click(screen.getAllByRole('checkbox')[0]); await userEvent.click(screen.getByRole('button', { name: 'Confirm Make official' }))
    await waitFor(() => expect(api.makeOfficialRunBranch).toHaveBeenCalledTimes(1)); expect(api.makeOfficialRunBranch.mock.calls[0][2].expected_current_official_branch_id).toBe('official-a')
    await screen.findByText('Official Branch state changed or must be reviewed again.')
    expect(screen.getAllByRole('checkbox')[0]).not.toBeChecked(); expect(screen.getAllByText('official-b').length).toBeGreaterThan(0)
    const firstCommandId = api.makeOfficialRunBranch.mock.calls[0][2].command_id
    await userEvent.click(screen.getAllByRole('checkbox')[0]); await userEvent.click(screen.getByRole('button', { name: 'Confirm Make official' }))
    await waitFor(() => expect(api.makeOfficialRunBranch).toHaveBeenCalledTimes(2)); expect(api.makeOfficialRunBranch.mock.calls[1][2]).toMatchObject({ expected_current_official_branch_id: 'official-b', audit_reason: 'reviewed reason' }); expect(api.makeOfficialRunBranch.mock.calls[1][2].command_id).not.toBe(firstCommandId)
  })
  it.each(['read-only Product Run', 'built-in Product Run', 'inactive Branch', 'missing legacy binding', 'missing BranchState', 'disagreeing heads', 'missing checkpoint', 'foreign Branch checkpoint', 'foreign Run checkpoint'])('disables Make official for an ineligible target: %s', async (caseName) => {
    let modifiedRun = run; let branches = [official, readonly]; let states = [state(), state('readonly', 'cp-readonly')]; let checkpoints = [checkpoint(), checkpoint('cp-readonly', 'initial', 'readonly')]
    if (caseName === 'read-only Product Run') modifiedRun = { ...run, read_only: true }
    if (caseName === 'built-in Product Run') modifiedRun = { ...run, storage_kind: 'built_in' }
    if (caseName === 'inactive Branch') branches = [official, { ...readonly, status: 'inactive' }]
    if (caseName === 'missing legacy binding') branches = [official, { ...readonly, legacy_simulation_run_id: '' }]
    if (caseName === 'missing BranchState') states = [state()]
    if (caseName === 'disagreeing heads') states = [state(), state('readonly', 'other')]
    if (caseName === 'missing checkpoint') checkpoints = [checkpoint()]
    if (caseName === 'foreign Branch checkpoint') checkpoints = [checkpoint(), checkpoint('cp-readonly', 'initial', 'other')]
    if (caseName === 'foreign Run checkpoint') checkpoints = [checkpoint(), { ...checkpoint('cp-readonly', 'initial', 'readonly'), run_id: 'other-run' }]
    api.getRunContainer.mockResolvedValue(modifiedRun); setup({ branches, states, checkpoints })
    api.getRunContainer.mockResolvedValue(modifiedRun)
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    expect(await screen.findByRole('button', { name: 'Make official' })).toBeDisabled()
  })
  it('links read-only to the official Viewer Product Run without additional requests', async () => { renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); const link = await screen.findByRole('link', { name: 'Open official Viewer' }); expect(link).toHaveAttribute('href', '/viewer/runs/run-a/rankings'); expect(api.getRunContainer).toHaveBeenCalledTimes(1); expect(api.listRunBranches).toHaveBeenCalledTimes(1); expect(api.listBranchStates).toHaveBeenCalledTimes(1); expect(api.listBranchCheckpoints).toHaveBeenCalledTimes(1) })
  it('has no unsafe Branch action surface', async () => { renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await screen.findAllByText('Official Branch'); for (const text of ['delete Branch', 'replay checkpoint', 'restore checkpoint', 'simulate against selected Branch']) expect(screen.queryByText(text, { exact: false })).not.toBeInTheDocument() })

  it('opens an explicit reviewed execution for official and non-official writable Branches without executing', async () => {
    const fork = { ...official, branch_id: 'fork', display_name: 'Fork Branch', head_checkpoint_id: 'cp-fork', legacy_simulation_run_id: 'legacy-fork', is_official: false }
    setup({ branches: [official, fork], states: [state(), state('fork', 'cp-fork')], checkpoints: [checkpoint(), checkpoint('cp-fork', 'branch_fork_start', 'fork')] })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    const actions = await screen.findAllByRole('button', { name: 'Simulate Next Match' }); expect(actions).toHaveLength(2); expect(actions.every((button) => !button.hasAttribute('disabled'))).toBe(true)
    await userEvent.click(actions[1]); expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled()
    expect(screen.getAllByText('Fork Branch (fork)').length).toBeGreaterThan(0); expect(screen.getAllByText('cp-fork').length).toBeGreaterThan(0); expect(screen.getByText(/official Branch pointer will not change/)).toBeInTheDocument()
  })

  it('submits only after confirmation with the reviewed head and exact trimmed payload', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0])
    const commandId = screen.getByLabelText('Simulation command ID').textContent as string
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), ' reviewed advance ')
    expect(screen.getByRole('button', { name: 'Confirm Simulate Next Match' })).toBeDisabled(); expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled()
    await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' }))
    await waitFor(() => expect(api.simulateNextMatchOnBranch).toHaveBeenCalledTimes(1))
    expect(api.simulateNextMatchOnBranch).toHaveBeenCalledWith('run-a', 'official', { expected_head_checkpoint_id: 'cp-initial', command_id: commandId, audit_reason: 'reviewed advance', explicit_confirmation: true })
  })

  it.each(['initial', 'current_state_capture', 'branch_fork_start'])('supports the %s execution head kind', async (kind) => {
    setup({ checkpoints: [checkpoint('cp-initial', kind), checkpoint('cp-readonly', 'initial', 'readonly')] }); renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    expect((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0]).toBeEnabled()
  })

  it('renders scalar success and idempotent safety messages without another request', async () => {
    const resultPayload = { ...simulationSuccess(true), current_season: 2031, current_week: 2, current_event_id: 'EVENT-NEXT', current_event_sequence: 5 }
    api.simulateNextMatchOnBranch.mockResolvedValueOnce(resultPayload); renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0]); const originalCommand = screen.getByLabelText('Simulation command ID').textContent; await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'advance'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' }))
    const result = await screen.findByLabelText('Next Match result'); const review = screen.getByRole('heading', { name: 'Review Simulate Next Match' }).closest('article') as HTMLElement
    expect(result).toHaveTextContent('No duplicate match was simulated'); expect(result).toHaveTextContent('official Branch pointer was not changed'); expect(result).toHaveTextContent('cp-next'); expect(result).toHaveTextContent('simulation-fingerprint'); expect(result).not.toHaveTextContent('[object Object]')
    expect(review).toHaveTextContent('cp-next'); expect(review).toHaveTextContent('2031'); expect(review).toHaveTextContent('EVENT-NEXT'); expect(review).toHaveTextContent('5'); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(originalCommand ?? ''); expect(api.simulateNextMatchOnBranch).toHaveBeenCalledTimes(1)
  })

  it('executes a coherent non-official Branch without changing the official pointer', async () => {
    const fork = { ...official, branch_id: 'fork', display_name: 'Fork Branch', head_checkpoint_id: 'cp-fork', legacy_simulation_run_id: 'legacy-fork', is_official: false }
    setup({ branches: [official, fork], states: [state(), state('fork', 'cp-fork')], checkpoints: [checkpoint(), checkpoint('cp-fork', 'branch_fork_start', 'fork')] })
    api.simulateNextMatchOnBranch.mockResolvedValueOnce({ ...simulationSuccess(), branch_id: 'fork', legacy_simulation_run_id: 'legacy-fork', previous_head_checkpoint_id: 'cp-fork', new_head_checkpoint_id: 'cp-fork-next' })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[1]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'advance fork'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' }))
    await waitFor(() => expect(api.simulateNextMatchOnBranch).toHaveBeenCalledTimes(1)); expect(api.simulateNextMatchOnBranch.mock.calls[0][1]).toBe('fork'); expect(api.makeOfficialRunBranch).not.toHaveBeenCalled(); expect(screen.queryByText(/official Branch pointer was changed/i)).not.toBeInTheDocument()
  })

  it('preserves the complete reviewed form and command ID for an explicit ordinary-error retry', async () => {
    api.simulateNextMatchOnBranch.mockRejectedValueOnce(new api.ApiError(JSON.stringify({ detail: 'uncertain response' }), 500)).mockResolvedValueOnce(simulationSuccess())
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'retry safely'); await userEvent.click(screen.getByLabelText('Confirm simulation')); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' }))
    expect(await screen.findByText('uncertain response')).toBeInTheDocument(); expect(api.simulateNextMatchOnBranch).toHaveBeenCalledTimes(1); expect(screen.getAllByText('Official Branch (official)').length).toBeGreaterThan(0); expect(screen.getAllByText('cp-initial').length).toBeGreaterThan(0); expect(screen.getByLabelText('Simulation audit reason')).toHaveValue('retry safely'); expect(screen.getByLabelText('Simulation command ID')).toHaveTextContent(command ?? ''); expect(screen.getByLabelText('Confirm simulation')).toBeChecked()
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' })); await waitFor(() => expect(api.simulateNextMatchOnBranch).toHaveBeenCalledTimes(2)); expect(api.simulateNextMatchOnBranch.mock.calls[1]).toEqual(api.simulateNextMatchOnBranch.mock.calls[0])
  })

  it('adopts a coherent refreshed head and locator after a 409 without retrying', async () => {
    const nextBranch = { ...official, head_checkpoint_id: 'cp-refreshed' }; const nextState = { ...state(), head_checkpoint_id: 'cp-refreshed', current_week: 13, current_event_id: 'EVENT-13', current_event_sequence: 8 }; const nextCheckpoint = checkpoint('cp-refreshed')
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [official] }).mockResolvedValue({ run_branches: [nextBranch] }); api.listBranchStates.mockResolvedValueOnce({ branch_states: [state()] }).mockResolvedValue({ branch_states: [nextState] }); api.listBranchCheckpoints.mockResolvedValueOnce({ branch_checkpoints: [checkpoint()] }).mockResolvedValue({ branch_checkpoints: [nextCheckpoint] }); api.simulateNextMatchOnBranch.mockRejectedValueOnce(new api.ApiError('conflict', 409))
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'review conflict'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' }))
    expect(await screen.findByText('Branch execution state changed or must be reviewed again.')).toBeInTheDocument(); await waitFor(() => expect(screen.getAllByText('cp-refreshed').length).toBeGreaterThan(0)); expect(screen.getAllByText('EVENT-13').length).toBeGreaterThan(0); expect(screen.getAllByText('8').length).toBeGreaterThan(0); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(command ?? ''); expect(api.simulateNextMatchOnBranch).toHaveBeenCalledTimes(1)
  })

  it('clears the reviewed head after an incoherent 409 refresh', async () => {
    const nextBranch = { ...official, head_checkpoint_id: 'cp-refreshed' }; const disagreeingState = { ...state(), head_checkpoint_id: 'other-head' }
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [official] }).mockResolvedValue({ run_branches: [nextBranch] }); api.listBranchStates.mockResolvedValueOnce({ branch_states: [state()] }).mockResolvedValue({ branch_states: [disagreeingState] }); api.listBranchCheckpoints.mockResolvedValueOnce({ branch_checkpoints: [checkpoint()] }).mockResolvedValue({ branch_checkpoints: [checkpoint('cp-refreshed')] }); api.simulateNextMatchOnBranch.mockRejectedValueOnce(new api.ApiError('conflict', 409))
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'review conflict'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' }))
    await screen.findByText('Branch execution state changed or must be reviewed again.'); const review = screen.getByRole('heading', { name: 'Review Simulate Next Match' }).closest('article') as HTMLElement; await waitFor(() => expect(review).toHaveTextContent('Branch and BranchState heads disagree.')); expect(review).toHaveTextContent('Reviewed head checkpoint ID—'); expect(screen.getByRole('button', { name: 'Confirm Simulate Next Match' })).toBeDisabled(); expect(api.simulateNextMatchOnBranch).toHaveBeenCalledTimes(1)
  })

  it.each([true, false])('invalidates precise success queries when official is %s', async (isOfficial) => {
    const invalidate = vi.spyOn(QueryClient.prototype, 'invalidateQueries'); const branch = isOfficial ? official : { ...official, branch_id: 'fork', head_checkpoint_id: 'cp-fork', legacy_simulation_run_id: 'legacy-fork' }; const branchState = isOfficial ? state() : state('fork', 'cp-fork'); const branchCheckpoint = isOfficial ? checkpoint() : checkpoint('cp-fork', 'branch_fork_start', 'fork')
    if (!isOfficial) setup({ branches: [official, branch], states: [state(), branchState], checkpoints: [checkpoint(), branchCheckpoint] }); api.simulateNextMatchOnBranch.mockResolvedValueOnce({ ...simulationSuccess(), branch_id: branch.branch_id, legacy_simulation_run_id: branch.legacy_simulation_run_id })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[isOfficial ? 0 : 1]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'invalidate'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' })); await waitFor(() => expect(api.simulateNextMatchOnBranch).toHaveBeenCalledTimes(1))
    for (const key of ['run-branches', 'branch-states', 'branch-checkpoints']) expect(invalidate).toHaveBeenCalledWith(expect.objectContaining({ queryKey: [key, 'run-a'] })); const predicate = invalidate.mock.calls.map(([filters]) => filters).find((filters) => Boolean(filters && 'predicate' in filters))?.predicate; expect(predicate?.({ queryKey: ['read', branch.legacy_simulation_run_id] } as never)).toBe(true); const viewerCall = invalidate.mock.calls.some(([filters]) => Boolean(filters && 'queryKey' in filters && JSON.stringify(filters.queryKey) === JSON.stringify(['viewer-official-run-context', 'run-a']))); expect(viewerCall).toBe(isOfficial); invalidate.mockRestore()
  })
  it('reviews and submits Next Round exclusively with the exact guarded payload', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    const action = (await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[0]
    await userEvent.click(action)
    expect(api.simulateNextRoundOnBranch).not.toHaveBeenCalled()
    expect(screen.getByText('Next Round', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByText(/may simulate multiple matches/)).toBeInTheDocument()
    const commandId = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), ' round reviewed ')
    expect(screen.getByRole('button', { name: 'Confirm Simulate Next Round' })).toBeDisabled()
    await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' }))
    await waitFor(() => expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(1))
    expect(api.simulateNextRoundOnBranch).toHaveBeenCalledWith('run-a', 'official', { expected_head_checkpoint_id: 'cp-initial', command_id: commandId, audit_reason: 'round reviewed', explicit_confirmation: true })
    expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled()
  })

  it('switches reviewed actions with a fresh command ID and reset confirmation', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0]); const first = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.click(screen.getByLabelText('Confirm simulation'))
    await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[0])
    expect(screen.getByRole('heading', { name: 'Review Simulate Next Round' })).toBeInTheDocument(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(first ?? ''); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked()
    expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled(); expect(api.simulateNextRoundOnBranch).not.toHaveBeenCalled()
  })

  it('executes Next Round on a coherent non-official Branch without making it official', async () => {
    const fork = { ...official, branch_id: 'fork', display_name: 'Fork Branch', head_checkpoint_id: 'cp-fork', legacy_simulation_run_id: 'legacy-fork', is_official: false }
    setup({ branches: [official, fork], states: [state(), state('fork', 'cp-fork')], checkpoints: [checkpoint(), checkpoint('cp-fork', 'branch_fork_start', 'fork')] }); api.simulateNextRoundOnBranch.mockResolvedValueOnce({ ...simulationSuccess(), branch_id: 'fork', legacy_simulation_run_id: 'legacy-fork', previous_head_checkpoint_id: 'cp-fork', new_head_checkpoint_id: 'cp-fork-next', simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_round' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[1]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'round fork'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' }))
    await waitFor(() => expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(1)); expect(api.simulateNextRoundOnBranch.mock.calls[0][1]).toBe('fork'); expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled(); expect(api.makeOfficialRunBranch).not.toHaveBeenCalled()
  })

  it('preserves the exact Next Round operation for an explicit ordinary-error retry', async () => {
    api.simulateNextRoundOnBranch.mockRejectedValueOnce(new api.ApiError(JSON.stringify({ detail: 'uncertain round response' }), 500)).mockResolvedValueOnce({ ...simulationSuccess(), simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_round' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'retry round'); await userEvent.click(screen.getByLabelText('Confirm simulation')); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' }))
    expect(await screen.findByText('uncertain round response')).toBeInTheDocument(); expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(1); expect(screen.getByRole('heading', { name: 'Review Simulate Next Round' })).toBeInTheDocument(); expect(screen.getByLabelText('Simulation audit reason')).toHaveValue('retry round'); expect(screen.getByLabelText('Simulation command ID')).toHaveTextContent(command ?? ''); expect(screen.getByLabelText('Confirm simulation')).toBeChecked()
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' })); await waitFor(() => expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(2)); expect(api.simulateNextRoundOnBranch.mock.calls[1]).toEqual(api.simulateNextRoundOnBranch.mock.calls[0])
  })

  it.each([false, true])('refreshes Next Round after a 409 and coherent is %s', async (incoherent) => {
    const freshBranch = { ...official, head_checkpoint_id: 'cp-round-fresh' }; const freshState = { ...state(), head_checkpoint_id: incoherent ? 'other' : 'cp-round-fresh', current_week: 15, current_event_id: 'ROUND-FRESH', current_event_sequence: 10 }
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [official] }).mockResolvedValue({ run_branches: [freshBranch] }); api.listBranchStates.mockResolvedValueOnce({ branch_states: [state()] }).mockResolvedValue({ branch_states: [freshState] }); api.listBranchCheckpoints.mockResolvedValueOnce({ branch_checkpoints: [checkpoint()] }).mockResolvedValue({ branch_checkpoints: [checkpoint('cp-round-fresh')] }); api.simulateNextRoundOnBranch.mockRejectedValueOnce(new api.ApiError('conflict', 409))
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'round conflict'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' }))
    await screen.findByText('Branch execution state changed or must be reviewed again.'); const review = screen.getByRole('heading', { name: 'Review Simulate Next Round' }).closest('article') as HTMLElement; await waitFor(() => expect(review).toHaveTextContent(incoherent ? 'Reviewed head checkpoint ID—' : 'cp-round-fresh')); expect(review).toHaveTextContent('ROUND-FRESH'); if (incoherent) expect(review).toHaveTextContent('Branch and BranchState heads disagree.'); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(command ?? ''); expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(1)
  })

  it.each([true, false])('invalidates precise Next Round queries when official is %s', async (isOfficial) => {
    const invalidate = vi.spyOn(QueryClient.prototype, 'invalidateQueries'); const branch = isOfficial ? official : { ...official, branch_id: 'fork', head_checkpoint_id: 'cp-fork', legacy_simulation_run_id: 'legacy-fork' }; const branchState = isOfficial ? state() : state('fork', 'cp-fork'); const branchCheckpoint = isOfficial ? checkpoint() : checkpoint('cp-fork', 'branch_fork_start', 'fork')
    if (!isOfficial) setup({ branches: [official, branch], states: [state(), branchState], checkpoints: [checkpoint(), branchCheckpoint] }); api.simulateNextRoundOnBranch.mockResolvedValueOnce({ ...simulationSuccess(), branch_id: branch.branch_id, legacy_simulation_run_id: branch.legacy_simulation_run_id, simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_round' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[isOfficial ? 0 : 1]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'invalidate round'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' })); await waitFor(() => expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(1))
    for (const key of ['run-branches', 'branch-states', 'branch-checkpoints']) expect(invalidate).toHaveBeenCalledWith(expect.objectContaining({ queryKey: [key, 'run-a'] })); const predicate = invalidate.mock.calls.map(([filters]) => filters).find((filters) => Boolean(filters && 'predicate' in filters))?.predicate; expect(predicate?.({ queryKey: ['read', branch.legacy_simulation_run_id] } as never)).toBe(true); const viewerCall = invalidate.mock.calls.some(([filters]) => Boolean(filters && 'queryKey' in filters && JSON.stringify(filters.queryKey) === JSON.stringify(['viewer-official-run-context', 'run-a']))); expect(viewerCall).toBe(isOfficial); invalidate.mockRestore()
  })

  it('shows the exact Next Round replay safety message without a duplicate request', async () => {
    api.simulateNextRoundOnBranch.mockResolvedValueOnce({ ...simulationSuccess(true), simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_round' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'round'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' }))
    expect(await screen.findByText('The previously completed Next Round command was returned. No duplicate round progression was simulated.')).toBeInTheDocument()
    expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(1)
  })

  it.each([false, true])('refreshes %s coherent state instead of trusting an invalid Next Round mode', async (incoherent) => {
    const freshBranch = { ...official, head_checkpoint_id: 'cp-server' }; const freshState = { ...state(), head_checkpoint_id: incoherent ? 'cp-disagree' : 'cp-server', current_week: 14, current_event_id: 'SERVER-EVENT', current_event_sequence: 9 }
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [official] }).mockResolvedValue({ run_branches: [freshBranch] }); api.listBranchStates.mockResolvedValueOnce({ branch_states: [state()] }).mockResolvedValue({ branch_states: [freshState] }); api.listBranchCheckpoints.mockResolvedValueOnce({ branch_checkpoints: [checkpoint()] }).mockResolvedValue({ branch_checkpoints: [checkpoint('cp-server')] })
    api.simulateNextRoundOnBranch.mockResolvedValueOnce({ ...simulationSuccess(), new_head_checkpoint_id: 'cp-untrusted', current_event_id: 'UNTRUSTED-EVENT', simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_match' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'keep reason'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' }))
    expect(await screen.findByText(/Response contract error: expected simulate_next_round/)).toBeInTheDocument(); expect(screen.queryByLabelText('Next Round result')).not.toBeInTheDocument(); expect(screen.queryByText('cp-untrusted')).not.toBeInTheDocument(); expect(screen.queryByText('UNTRUSTED-EVENT')).not.toBeInTheDocument()
    const review = screen.getByRole('heading', { name: 'Review Simulate Next Round' }).closest('article') as HTMLElement
    await waitFor(() => expect(review).toHaveTextContent(incoherent ? 'Reviewed head checkpoint ID—' : 'cp-server')); expect(review).toHaveTextContent('SERVER-EVENT'); if (incoherent) expect(review).toHaveTextContent('Branch and BranchState heads disagree.')
    expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(command ?? ''); expect(screen.getByLabelText('Simulation audit reason')).toHaveValue('keep reason'); expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(1)
  })

  it('rejects an official pointer change response without making a false safety claim', async () => {
    api.simulateNextRoundOnBranch.mockResolvedValueOnce({ ...simulationSuccess(), official_branch_changed: true, simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_round' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'round'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Round' }))
    expect(await screen.findByText(/official_branch_changed must be false/)).toBeInTheDocument(); expect(screen.queryByLabelText('Next Round result')).not.toBeInTheDocument(); expect(screen.queryByText('The official Branch pointer was not changed.')).not.toBeInTheDocument(); expect(api.simulateNextRoundOnBranch).toHaveBeenCalledTimes(1)
  })

  it('reviews and submits Next Week exclusively through the shared guarded flow', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    const actions = await screen.findAllByRole('button', { name: 'Simulate Next Week' })
    expect(actions).toHaveLength(2); expect(actions[0]).toBeEnabled(); expect(actions[1]).toBeDisabled()
    await userEvent.click(actions[0])
    expect(api.simulateNextWeekOnBranch).not.toHaveBeenCalled()
    const review = screen.getByRole('heading', { name: 'Review Simulate Next Week' }).closest('article') as HTMLElement
    expect(review).toHaveTextContent('Next Week'); expect(review).toHaveTextContent('Official Branch (official)'); expect(review).toHaveTextContent('cp-initial'); expect(review).toHaveTextContent('every consecutive event belonging to the next calendar week group')
    const commandId = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), ' week reviewed ')
    expect(screen.getByRole('button', { name: 'Confirm Simulate Next Week' })).toBeDisabled()
    await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Week' }))
    await waitFor(() => expect(api.simulateNextWeekOnBranch).toHaveBeenCalledTimes(1))
    expect(api.simulateNextWeekOnBranch).toHaveBeenCalledWith('run-a', 'official', { expected_head_checkpoint_id: 'cp-initial', command_id: commandId, audit_reason: 'week reviewed', explicit_confirmation: true })
    expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled(); expect(api.simulateNextRoundOnBranch).not.toHaveBeenCalled(); expect(api.simulateNextWeekOnBranch).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText('Next Week result')).toHaveTextContent('Executed actionNext Week')
  })

  it('switches to Next Week with a fresh command and no request', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Round' }))[0]); const old = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.click(screen.getByLabelText('Confirm simulation'))
    await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Week' }))[0])
    expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(old ?? ''); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked()
    expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled(); expect(api.simulateNextRoundOnBranch).not.toHaveBeenCalled(); expect(api.simulateNextWeekOnBranch).not.toHaveBeenCalled()
  })

  it('shows the exact Next Week replay text and does not issue a second command', async () => {
    api.simulateNextWeekOnBranch.mockResolvedValueOnce({ ...simulationSuccess(true), simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_week' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Week' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'week'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Week' }))
    expect(await screen.findByText('The previously completed Next Week command was returned. No duplicate week progression was simulated.')).toBeInTheDocument(); expect(api.simulateNextWeekOnBranch).toHaveBeenCalledTimes(1)
  })

  it.each(['simulate_next_round', 'official-change'])('rejects malformed Next Week response %s', async (malformation) => {
    api.simulateNextWeekOnBranch.mockResolvedValueOnce({ ...simulationSuccess(), official_branch_changed: malformation === 'official-change', simulation_result: { ...simulationSuccess().simulation_result, mode: malformation === 'official-change' ? 'simulate_next_week' : 'simulate_next_round' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Week' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'week'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Week' }))
    expect(await screen.findByText(/Response contract error/)).toBeInTheDocument(); expect(screen.queryByLabelText('Next Week result')).not.toBeInTheDocument(); expect(screen.queryByText('The official Branch pointer was not changed.')).not.toBeInTheDocument(); expect(api.simulateNextWeekOnBranch).toHaveBeenCalledTimes(1)
  })


  it('reviews and submits Next Tournament exclusively with the exact guarded payload', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    const actions = await screen.findAllByRole('button', { name: 'Simulate Next Tournament' })
    expect(actions).toHaveLength(2); expect(actions[0]).toBeEnabled(); expect(actions[1]).toBeDisabled()
    await userEvent.click(actions[0]); expect(api.simulateNextTournamentOnBranch).not.toHaveBeenCalled()
    const review = screen.getByRole('heading', { name: 'Review Simulate Next Tournament' }).closest('article') as HTMLElement
    expect(review).toHaveTextContent('ActionNext Tournament'); expect(review).toHaveTextContent('Official Branch (official)'); expect(review).toHaveTextContent('cp-initial'); expect(review).toHaveTextContent('If a tournament is currently active, that tournament will be finalized')
    const commandId = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), ' tournament reviewed ')
    expect(screen.getByRole('button', { name: 'Confirm Simulate Next Tournament' })).toBeDisabled()
    await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Tournament' }))
    await waitFor(() => expect(api.simulateNextTournamentOnBranch).toHaveBeenCalledTimes(1))
    expect(api.simulateNextTournamentOnBranch).toHaveBeenCalledWith('run-a', 'official', { expected_head_checkpoint_id: 'cp-initial', command_id: commandId, audit_reason: 'tournament reviewed', explicit_confirmation: true })
    expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled(); expect(api.simulateNextRoundOnBranch).not.toHaveBeenCalled(); expect(api.simulateNextWeekOnBranch).not.toHaveBeenCalled()
  })

  it('switches to Next Tournament with a fresh command, reset confirmation, and no request', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Week' }))[0]); const old = screen.getByLabelText('Simulation command ID').textContent; await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Tournament' }))[0])
    expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(old ?? ''); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(api.simulateNextTournamentOnBranch).not.toHaveBeenCalled()
  })

  it('renders Next Tournament success and exact replay without a second request', async () => {
    api.simulateNextTournamentOnBranch.mockResolvedValueOnce({ ...simulationSuccess(true), new_head_checkpoint_id: 'cp-tournament', current_event_id: null, simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_tournament', active_tournament: null } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Tournament' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'tournament'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Tournament' }))
    expect(await screen.findByText('The previously completed Next Tournament command was returned. No duplicate tournament progression was simulated.')).toBeInTheDocument(); expect(screen.getByLabelText('Next Tournament result')).toHaveTextContent('cp-tournament'); expect(screen.getByLabelText('Next Tournament result')).toHaveTextContent('Active tournament—'); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(command ?? ''); expect(api.simulateNextTournamentOnBranch).toHaveBeenCalledTimes(1)
  })

  it.each(['simulate_next_week', 'official-change'])('rejects malformed Next Tournament response %s', async (malformation) => {
    api.simulateNextTournamentOnBranch.mockResolvedValueOnce({ ...simulationSuccess(), official_branch_changed: malformation === 'official-change', simulation_result: { ...simulationSuccess().simulation_result, mode: malformation === 'official-change' ? 'simulate_next_tournament' : 'simulate_next_week' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Tournament' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'tournament'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Tournament' }))
    expect(await screen.findByText(/Response contract error/)).toBeInTheDocument(); expect(screen.queryByLabelText('Next Tournament result')).not.toBeInTheDocument(); expect(screen.queryByText('The official Branch pointer was not changed.')).not.toBeInTheDocument(); expect(api.simulateNextTournamentOnBranch).toHaveBeenCalledTimes(1)
  })


  it('preserves the exact Next Tournament request for an explicit ordinary-error retry', async () => {
    api.simulateNextTournamentOnBranch.mockRejectedValueOnce(new api.ApiError(JSON.stringify({ detail: 'uncertain tournament response' }), 500)).mockResolvedValueOnce({ ...simulationSuccess(), simulation_result: { ...simulationSuccess().simulation_result, mode: 'simulate_next_tournament' } })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Tournament' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'retry tournament'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Tournament' }))
    expect(await screen.findByText('uncertain tournament response')).toBeInTheDocument(); expect(api.simulateNextTournamentOnBranch).toHaveBeenCalledTimes(1); expect(screen.getByLabelText('Simulation command ID')).toHaveTextContent(command ?? ''); expect(screen.getByLabelText('Simulation audit reason')).toHaveValue('retry tournament'); expect(screen.getByLabelText('Confirm simulation')).toBeChecked()
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Tournament' })); await waitFor(() => expect(api.simulateNextTournamentOnBranch).toHaveBeenCalledTimes(2)); expect(api.simulateNextTournamentOnBranch.mock.calls[1]).toEqual(api.simulateNextTournamentOnBranch.mock.calls[0])
  })

  it.each([false, true])('refreshes a %s incoherent Next Tournament review after 409 without retrying', async (incoherent) => {
    const freshBranch = { ...official, head_checkpoint_id: 'cp-tournament-fresh' }; const freshState = { ...state(), head_checkpoint_id: incoherent ? 'cp-disagree' : 'cp-tournament-fresh', current_event_id: 'TOURNAMENT-FRESH' }
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [official] }).mockResolvedValue({ run_branches: [freshBranch] }); api.listBranchStates.mockResolvedValueOnce({ branch_states: [state()] }).mockResolvedValue({ branch_states: [freshState] }); api.listBranchCheckpoints.mockResolvedValueOnce({ branch_checkpoints: [checkpoint()] }).mockResolvedValue({ branch_checkpoints: [checkpoint('cp-tournament-fresh')] }); api.simulateNextTournamentOnBranch.mockRejectedValueOnce(new api.ApiError('conflict', 409))
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Tournament' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'keep tournament'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Tournament' }))
    await screen.findByText('Branch execution state changed or must be reviewed again.'); const review = screen.getByRole('heading', { name: 'Review Simulate Next Tournament' }).closest('article') as HTMLElement; await waitFor(() => expect(review).toHaveTextContent(incoherent ? 'Reviewed head checkpoint ID—' : 'cp-tournament-fresh')); expect(review).toHaveTextContent('TOURNAMENT-FRESH'); expect(screen.getByLabelText('Simulation audit reason')).toHaveValue('keep tournament'); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(command ?? ''); expect(api.simulateNextTournamentOnBranch).toHaveBeenCalledTimes(1)
  })

  it('offers all five shared actions to eligible official and non-official Branches while keeping Make official independent', async () => {
    const fork = { ...official, branch_id: 'fork', display_name: 'Fork Branch', head_checkpoint_id: 'cp-fork', legacy_simulation_run_id: 'legacy-fork', is_official: false }
    setup({ branches: [official, fork, readonly], states: [state(), state('fork', 'cp-fork'), state('readonly', 'cp-readonly')], checkpoints: [checkpoint(), checkpoint('cp-fork', 'branch_fork_start', 'fork'), checkpoint('cp-readonly', 'initial', 'readonly')] })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await screen.findByText('Admin Run')
    for (const label of ['Simulate Next Match', 'Simulate Next Round', 'Simulate Next Week', 'Simulate Next Tournament', 'Simulate Full Season']) {
      const buttons = screen.getAllByRole('button', { name: label }); expect(buttons).toHaveLength(3); expect(buttons[0]).toBeEnabled(); expect(buttons[1]).toBeEnabled(); expect(buttons[2]).toBeDisabled()
    }
    expect(screen.getAllByRole('button', { name: 'Make official' })[0]).toBeEnabled()
  })

  it('reviews and submits Full Season only after explicit confirmation with the exact guarded payload', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Full Season' }))[0])
    expect(api.simulateFullSeasonOnBranch).not.toHaveBeenCalled()
    const review = screen.getByRole('heading', { name: 'Review Simulate Full Season' }).closest('article') as HTMLElement
    expect(review).toHaveTextContent('ActionFull Season'); expect(review).toHaveTextContent('Official Branch (official)'); expect(review).toHaveTextContent('cp-initial')
    expect(review).toHaveTextContent('finalize any currently active tournament and then complete every remaining calendar event'); expect(review).toHaveTextContent('This command may complete many tournaments and weeks in one atomic operation. It does not run Finals or create the next season.')
    const command = screen.getByLabelText('Simulation command ID').textContent ?? ''
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), '  finish season safely  '); expect(screen.getByRole('button', { name: 'Confirm Simulate Full Season' })).toBeDisabled()
    await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Full Season' }))
    await waitFor(() => expect(api.simulateFullSeasonOnBranch).toHaveBeenCalledWith('run-a', 'official', { expected_head_checkpoint_id: 'cp-initial', command_id: command, audit_reason: 'finish season safely', explicit_confirmation: true }))
    for (const client of [api.simulateNextMatchOnBranch, api.simulateNextRoundOnBranch, api.simulateNextWeekOnBranch, api.simulateNextTournamentOnBranch, api.makeOfficialRunBranch]) expect(client).not.toHaveBeenCalled()
  })

  it('switches the shared review to Full Season with a fresh command and cleared confirmation without requesting', async () => {
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Full Season' }))[0])
    expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(command ?? ''); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(api.simulateFullSeasonOnBranch).not.toHaveBeenCalled()
  })

  it('validates a pending Full Season result against its executed action after the review switches', async () => {
    let resolveFullSeason!: (result: ReturnType<typeof fullSeasonSuccess>) => void
    api.simulateFullSeasonOnBranch.mockReturnValueOnce(new Promise((resolve) => { resolveFullSeason = resolve }))
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches')
    await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Full Season' }))[0])
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'pending season')
    await userEvent.click(screen.getByLabelText('Confirm simulation'))
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Full Season' }))
    await waitFor(() => expect(api.simulateFullSeasonOnBranch).toHaveBeenCalledTimes(1))

    await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Next Match' }))[0])
    expect(screen.getByRole('heading', { name: 'Review Simulate Next Match' })).toBeInTheDocument()
    resolveFullSeason({ ...fullSeasonSuccess(), simulation_result: { ...fullSeasonSuccess().simulation_result, completed_in_command_count: undefined as never } })

    expect(await screen.findByText('Response contract error: Full Season summary fields are missing or invalid.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Full Season result')).not.toBeInTheDocument()
    expect(screen.queryByText('The official Branch pointer was not changed.')).not.toBeInTheDocument()
    expect(screen.queryByText(/Completed by this command/)).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Review Simulate Next Match' })).toBeInTheDocument()
    expect(api.simulateFullSeasonOnBranch).toHaveBeenCalledTimes(1)
    expect(api.simulateNextMatchOnBranch).not.toHaveBeenCalled()
  })

  it('renders truthful Full Season success fields and exact replay without continuing automatically', async () => {
    api.simulateFullSeasonOnBranch.mockResolvedValueOnce(fullSeasonSuccess(true))
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Full Season' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'season'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Full Season' }))
    const result = await screen.findByLabelText('Full Season result'); expect(result).toHaveTextContent('Completed by this command20'); expect(result).toHaveTextContent('Completed week groups12'); expect(result).toHaveTextContent('Season completeYes'); expect(result).toHaveTextContent('Current locator2030 / — / — / —')
    expect(await screen.findByText('The previously completed Full Season command was returned. No duplicate season progression was simulated.')).toBeInTheDocument(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(command ?? ''); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(api.simulateFullSeasonOnBranch).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['wrong mode', { simulation_result: { ...fullSeasonSuccess().simulation_result, mode: 'simulate_next_tournament' } }],
    ['official pointer', { official_branch_changed: true }],
    ['missing completed count', { simulation_result: { ...fullSeasonSuccess().simulation_result, completed_in_command_count: undefined } }],
    ['invalid week groups', { simulation_result: { ...fullSeasonSuccess().simulation_result, completed_week_group_count: -1 } }],
    ['invalid season complete', { simulation_result: { ...fullSeasonSuccess().simulation_result, season_complete: 'yes' } }]
  ])('rejects malformed Full Season response: %s', async (_name, changes) => {
    api.simulateFullSeasonOnBranch.mockResolvedValueOnce({ ...fullSeasonSuccess(), ...changes })
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Full Season' }))[0]); await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'season'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Full Season' }))
    expect(await screen.findByText(/Response contract error/)).toBeInTheDocument(); expect(screen.queryByLabelText('Full Season result')).not.toBeInTheDocument(); expect(screen.queryByText('The official Branch pointer was not changed.')).not.toBeInTheDocument(); expect(api.simulateFullSeasonOnBranch).toHaveBeenCalledTimes(1)
  })

  it('preserves the exact Full Season request for an explicit ordinary-error retry', async () => {
    api.simulateFullSeasonOnBranch.mockRejectedValueOnce(new api.ApiError(JSON.stringify({ detail: 'no executable Full Season' }), 400)).mockResolvedValueOnce(fullSeasonSuccess())
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Full Season' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'retry season'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Full Season' }))
    expect(await screen.findByText('no executable Full Season')).toBeInTheDocument(); expect(screen.getByLabelText('Simulation command ID')).toHaveTextContent(command ?? ''); expect(screen.getByLabelText('Simulation audit reason')).toHaveValue('retry season'); expect(screen.getByLabelText('Confirm simulation')).toBeChecked(); expect(api.simulateFullSeasonOnBranch).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Full Season' })); await waitFor(() => expect(api.simulateFullSeasonOnBranch).toHaveBeenCalledTimes(2)); expect(api.simulateFullSeasonOnBranch.mock.calls[1]).toEqual(api.simulateFullSeasonOnBranch.mock.calls[0])
  })

  it.each([false, true])('refreshes a %s incoherent Full Season review after 409 without retrying', async (incoherent) => {
    const freshBranch = { ...official, head_checkpoint_id: 'cp-season-fresh' }; const freshState = { ...state(), head_checkpoint_id: incoherent ? 'cp-disagree' : 'cp-season-fresh', current_event_id: 'SEASON-FRESH' }
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [official] }).mockResolvedValue({ run_branches: [freshBranch] }); api.listBranchStates.mockResolvedValueOnce({ branch_states: [state()] }).mockResolvedValue({ branch_states: [freshState] }); api.listBranchCheckpoints.mockResolvedValueOnce({ branch_checkpoints: [checkpoint()] }).mockResolvedValue({ branch_checkpoints: [checkpoint('cp-season-fresh')] }); api.simulateFullSeasonOnBranch.mockRejectedValueOnce(new api.ApiError('conflict', 409))
    renderWithRoute(<AdminRunBranchesPage />, '/admin/runs/run-a/branches'); await userEvent.click((await screen.findAllByRole('button', { name: 'Simulate Full Season' }))[0]); const command = screen.getByLabelText('Simulation command ID').textContent; await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'keep season'); await userEvent.click(screen.getByLabelText('Confirm simulation')); await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Full Season' }))
    await screen.findByText('Branch execution state changed or must be reviewed again.'); const review = screen.getByRole('heading', { name: 'Review Simulate Full Season' }).closest('article') as HTMLElement; await waitFor(() => expect(review).toHaveTextContent(incoherent ? 'Reviewed head checkpoint ID—' : 'cp-season-fresh')); expect(review).toHaveTextContent('SEASON-FRESH'); expect(screen.getByLabelText('Simulation audit reason')).toHaveValue('keep season'); expect(screen.getByLabelText('Confirm simulation')).not.toBeChecked(); expect(screen.getByLabelText('Simulation command ID')).not.toHaveTextContent(command ?? ''); expect(api.simulateFullSeasonOnBranch).toHaveBeenCalledTimes(1)
  })

})

describe('simulationEligibility', () => {
  const eligible = () => simulationEligibility(run as never, official as never, state() as never, [checkpoint()] as never)
  it('accepts a coherent writable active custom Product Run Branch without requiring official status', () => { expect(eligible()).toBeNull(); expect(simulationEligibility(run as never, { ...official, is_official: false } as never, state() as never, [checkpoint()] as never)).toBeNull() })
  it.each([
    ['read-only Product Run', { run: { ...run, read_only: true } }], ['built-in Product Run', { run: { ...run, storage_kind: 'built_in' } }], ['inactive Product Run', { run: { ...run, status: 'inactive' } }],
    ['read-only Branch', { branch: { ...official, read_only: true } }], ['inactive Branch', { branch: { ...official, status: 'inactive' } }], ['foreign Branch', { branch: { ...official, run_id: 'other' } }], ['missing legacy binding', { branch: { ...official, legacy_simulation_run_id: '' } }],
    ['missing BranchState', { state: undefined }], ['foreign BranchState', { state: { ...state(), run_id: 'other' } }], ['disagreeing heads', { state: state('official', 'other') }], ['missing checkpoint', { checkpoints: [] }],
    ['foreign Branch checkpoint', { checkpoints: [{ ...checkpoint(), branch_id: 'other' }] }], ['foreign Product Run checkpoint', { checkpoints: [{ ...checkpoint(), run_id: 'other' }] }], ['unsupported checkpoint kind', { checkpoints: [checkpoint('cp-initial', 'event_completed')] }]
  ])('rejects %s', (_name, rawChanges) => { const changes = rawChanges as Record<string, any>; expect(simulationEligibility((changes.run ?? run) as never, (changes.branch ?? official) as never, changes.state === undefined && 'state' in changes ? undefined : (changes.state ?? state()) as never, (changes.checkpoints ?? [checkpoint()]) as never)).toBeTruthy() })
})

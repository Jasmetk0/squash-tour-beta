import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MatchTestLabPage } from './MatchTestLabPage'
import { TournamentTestLabPage } from './TournamentTestLabPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getMatchLabBuiltInScenarios: vi.fn(), getMatchLabSessions: vi.fn(),
  createMatchLabSession: vi.fn(), updateMatchLabSession: vi.fn(),
  runMatchLabSession: vi.fn(), runMatchTestLab: vi.fn(), importMatchLabSavedRevisionPlayer: vi.fn(),
  getTournamentLabBuiltInScenarios: vi.fn(), getTournamentLabSessions: vi.fn(),
  createTournamentLabSession: vi.fn(), updateTournamentLabSession: vi.fn(),
  runTournamentLabSession: vi.fn(), runTournamentTestLab: vi.fn(),
  inspectTournamentLabScenario: vi.fn(), previewTournamentLabRunDraft: vi.fn(), applyTournamentLabRunDraft: vi.fn()
}))
vi.mock('../api/client', () => api)

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

const cases = [
  { kind: 'Match', Page: MatchTestLabPage, path: 'match', list: api.getMatchLabSessions, update: api.updateMatchLabSession },
  { kind: 'Tournament', Page: TournamentTestLabPage, path: 'tournament', list: api.getTournamentLabSessions, update: api.updateTournamentLabSession }
] as const

function session(kind: string, id = 'session-a', version = 1) {
  return {
    schema_version: `${kind.toLowerCase()}_test_lab_session.v1`,
    session_id: id, display_name: id === 'session-a' ? 'Session A' : 'Session B',
    version, session_fingerprint: String(version).repeat(64), participant_imports: [],
    scenario: {
      schema_version: `${kind.toLowerCase()}_test_lab_scenario.v1`,
      scenario_id: `${id}-scenario`, source_kind: 'portable', seed: version, context: {}
    }
  }
}

beforeEach(() => {
  Object.values(api).forEach(fn => fn.mockReset())
  api.getMatchLabBuiltInScenarios.mockResolvedValue([])
  api.getTournamentLabBuiltInScenarios.mockResolvedValue([])
})

describe.each(cases)('$kind Lab editor concurrency', ({ kind, Page, path, list, update }) => {
  const editorName = `${kind} Lab scenario JSON`
  const selectName = `Open ${kind} Test Session`
  const edit = (seed: number) => {
    const editor = screen.getByRole('textbox', { name: editorName })
    const current = JSON.parse((editor as HTMLTextAreaElement).value)
    fireEvent.change(editor, { target: { value: JSON.stringify({ ...current, seed }) } })
    return editor
  }

  it('preserves local edits when refreshing a remotely updated saved session', async () => {
    const user = userEvent.setup()
    const first = session(kind), remote = session(kind, 'session-a', 2)
    list.mockResolvedValueOnce([first]).mockResolvedValue([remote])
    renderWithRoute(<Page />, `/admin/labs/${path}`)
    await screen.findByRole('option', { name: 'Session A · v1' })
    await user.selectOptions(screen.getByLabelText(selectName), first.session_id)
    const editor = edit(333)
    await user.click(screen.getByRole('button', { name: 'Refresh Test Sessions' }))
    await screen.findByRole('option', { name: 'Session A · v2' })
    expect(JSON.parse((editor as HTMLTextAreaElement).value).seed).toBe(333)
    expect(screen.getByRole('alert')).toHaveTextContent(/saved Test Session changed/i)
    expect(screen.getByRole('button', { name: 'Run Test Session' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Save Test Session' })).toBeDisabled()
    expect(update).not.toHaveBeenCalled()
  })

  it('retains edits made while Save is in flight and uses its acknowledged fingerprint next time', async () => {
    const user = userEvent.setup()
    const first = session(kind)
    const saved = { ...session(kind, 'session-a', 2), scenario: { ...first.scenario, seed: 111 } }
    const pending = deferred<typeof saved>()
    list.mockResolvedValue([first])
    update.mockImplementationOnce(() => pending.promise).mockResolvedValue({ ...saved, version: 3 })
    renderWithRoute(<Page />, `/admin/labs/${path}`)
    await screen.findByRole('option', { name: 'Session A · v1' })
    await user.selectOptions(screen.getByLabelText(selectName), first.session_id)
    edit(111)
    await user.click(screen.getByRole('button', { name: 'Save Test Session' }))
    const editor = edit(222)
    list.mockResolvedValue([saved])
    await act(async () => { pending.resolve(saved); await pending.promise })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save Test Session' })).toBeEnabled())
    expect(JSON.parse((editor as HTMLTextAreaElement).value).seed).toBe(222)
    expect(screen.getByRole('button', { name: 'Run Test Session' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Save Test Session' }))
    expect(update).toHaveBeenLastCalledWith(first.session_id, expect.objectContaining({
      expected_session_fingerprint: saved.session_fingerprint,
      scenario: expect.objectContaining({ seed: 222 })
    }))
  })

  it('does not switch back to an old session when its delayed Save completes', async () => {
    const user = userEvent.setup()
    const first = session(kind), second = session(kind, 'session-b')
    const saved = session(kind, 'session-a', 2)
    const pending = deferred<typeof saved>()
    list.mockResolvedValue([first, second])
    update.mockImplementation(() => pending.promise)
    renderWithRoute(<Page />, `/admin/labs/${path}`)
    await screen.findByRole('option', { name: 'Session A · v1' })
    await user.selectOptions(screen.getByLabelText(selectName), first.session_id)
    edit(111)
    await user.click(screen.getByRole('button', { name: 'Save Test Session' }))
    await user.selectOptions(screen.getByLabelText(selectName), second.session_id)
    const editor = edit(444)
    list.mockResolvedValue([saved, second])
    await act(async () => { pending.resolve(saved); await pending.promise })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save Test Session' })).toBeEnabled())
    expect(screen.getByLabelText(selectName)).toHaveValue(second.session_id)
    expect(JSON.parse((editor as HTMLTextAreaElement).value)).toMatchObject({ scenario_id: 'session-b-scenario', seed: 444 })
  })

  it('requires explicit discard before replacing dirty text with a remotely saved version', async () => {
    const user = userEvent.setup()
    const first = session(kind), remote = session(kind, 'session-a', 2)
    list.mockResolvedValueOnce([first]).mockResolvedValue([remote])
    renderWithRoute(<Page />, `/admin/labs/${path}`)
    await screen.findByRole('option', { name: 'Session A · v1' })
    await user.selectOptions(screen.getByLabelText(selectName), first.session_id)
    const editor = edit(333)
    await user.click(screen.getByRole('button', { name: 'Refresh Test Sessions' }))
    const reload = await screen.findByRole('button', { name: 'Reload saved Test Session' })
    expect(reload).toBeDisabled()
    await user.click(screen.getByRole('checkbox', { name: 'Discard local edits when reloading' }))
    expect(reload).toBeEnabled()
    edit(444)
    expect(screen.getByRole('button', { name: 'Reload saved Test Session' })).toBeDisabled()
    await user.click(screen.getByRole('checkbox', { name: 'Discard local edits when reloading' }))
    await user.click(screen.getByRole('button', { name: 'Reload saved Test Session' }))
    expect(JSON.parse((editor as HTMLTextAreaElement).value)).toEqual(remote.scenario)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run Test Session' })).toBeEnabled()
    expect(update).not.toHaveBeenCalled()
  })

  it('never silently turns a missing saved session into a runnable scratch scenario', async () => {
    const user = userEvent.setup()
    const first = session(kind)
    list.mockResolvedValueOnce([first]).mockResolvedValue([])
    renderWithRoute(<Page />, `/admin/labs/${path}`)
    await screen.findByRole('option', { name: 'Session A · v1' })
    await user.selectOptions(screen.getByLabelText(selectName), first.session_id)
    const editor = edit(333)
    await user.click(screen.getByRole('button', { name: 'Refresh Test Sessions' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no longer in the inventory')
    expect(screen.getByLabelText(selectName)).toHaveValue(first.session_id)
    expect(JSON.parse((editor as HTMLTextAreaElement).value).seed).toBe(333)
    expect(screen.getByRole('button', { name: 'Run Test Session' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Reload saved Test Session' })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText(selectName), '')
    expect(JSON.parse((editor as HTMLTextAreaElement).value).seed).toBe(333)
    expect(screen.getByRole('button', { name: kind === 'Match' ? 'Run scenario' : 'Run tournament scenario' })).toBeEnabled()
  })

  it('captures the submitted editor before asynchronous mutation setup can observe newer edits', async () => {
    const user = userEvent.setup()
    const first = session(kind)
    const saved = { ...session(kind, 'session-a', 2), scenario: { ...first.scenario, seed: 111 } }
    const pending = deferred<typeof saved>()
    list.mockResolvedValue([first])
    update.mockImplementation(() => pending.promise)
    renderWithRoute(<Page />, `/admin/labs/${path}`)
    await screen.findByRole('option', { name: 'Session A · v1' })
    await user.selectOptions(screen.getByLabelText(selectName), first.session_id)
    edit(111)
    fireEvent.click(screen.getByRole('button', { name: 'Save Test Session' }))
    const editor = edit(222)
    await waitFor(() => expect(update).toHaveBeenCalledTimes(1))
    list.mockResolvedValue([saved])
    await act(async () => { pending.resolve(saved); await pending.promise })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save Test Session' })).toBeEnabled())
    expect(JSON.parse((editor as HTMLTextAreaElement).value).seed).toBe(222)
  })

  it('keeps a detached run pending after edits instead of starting another expensive simulation', async () => {
    const user = userEvent.setup()
    const run = kind === 'Match' ? api.runMatchTestLab : api.runTournamentTestLab
    const pending = deferred<undefined>()
    list.mockResolvedValue([])
    run.mockImplementation(() => pending.promise)
    renderWithRoute(<Page />, `/admin/labs/${path}`)
    const editor = screen.getByRole('textbox', { name: editorName })
    fireEvent.change(editor, { target: { value: JSON.stringify(session(kind).scenario) } })
    await user.click(screen.getByRole('button', { name: kind === 'Match' ? 'Run scenario' : 'Run tournament scenario' }))
    edit(333)
    expect(screen.getByRole('button', { name: 'Running…' })).toBeDisabled()
    fireEvent.submit(editor.closest('form')!)
    expect(run).toHaveBeenCalledTimes(1)
    await act(async () => { pending.resolve(undefined); await pending.promise })
    await waitFor(() => expect(screen.getByRole('button', { name: kind === 'Match' ? 'Run scenario' : 'Run tournament scenario' })).toBeEnabled())
  })
})

it('preserves the local Match editor when a historical import finishes after further edits', async () => {
  const user = userEvent.setup()
  const first = session('Match'), imported = session('Match', 'session-a', 2)
  const pending = deferred<typeof imported>()
  api.getMatchLabSessions.mockResolvedValue([first])
  api.importMatchLabSavedRevisionPlayer.mockImplementation(() => pending.promise)
  renderWithRoute(<MatchTestLabPage />, '/admin/labs/match')
  await screen.findByRole('option', { name: 'Session A · v1' })
  await user.selectOptions(screen.getByLabelText('Open Match Test Session'), first.session_id)
  for (const [field, value] of [['Run ID', 'run'], ['Branch ID', 'branch'], ['Saved Revision ID', 'revision'], ['Player ID', 'player']]) {
    fireEvent.change(screen.getByLabelText(`Match Lab import ${field}`), { target: { value } })
  }
  await user.click(screen.getByRole('button', { name: 'Import historical player' }))
  const editor = screen.getByLabelText('Match Lab scenario JSON')
  fireEvent.change(editor, { target: { value: JSON.stringify({ ...first.scenario, seed: 333 }) } })
  api.getMatchLabSessions.mockResolvedValue([imported])
  await act(async () => { pending.resolve(imported); await pending.promise })
  expect(await screen.findByRole('alert')).toHaveTextContent('saved Test Session changed')
  expect(JSON.parse((editor as HTMLTextAreaElement).value).seed).toBe(333)
  expect(screen.getByRole('button', { name: 'Save Test Session' })).toBeDisabled()
})

describe('reviewed Tournament Lab transfer', () => {
  async function openProposal() {
    const user = userEvent.setup()
    const source = session('Tournament')
    api.getTournamentLabSessions.mockResolvedValue([source])
    renderWithRoute(<TournamentTestLabPage />, '/admin/labs/tournament')
    await screen.findByRole('option', { name: 'Session A · v1' })
    await user.selectOptions(screen.getByLabelText('Open Tournament Test Session'), source.session_id)
    fireEvent.change(screen.getByLabelText('Tournament Lab target Run ID'), { target: { value: 'target-run' } })
    fireEvent.change(screen.getByLabelText('Tournament Lab target Branch ID'), { target: { value: 'target-branch' } })
    fireEvent.change(screen.getByLabelText('Tournament Lab target event ID'), { target: { value: 'target-event' } })
    return { user, preview: {
      schema_version: 'tournament_test_lab_run_draft_preview.v1', mutation_performed: false,
      session_id: source.session_id, session_fingerprint: source.session_fingerprint,
      product_run_id: 'target-run', branch_id: 'target-branch', event_id: 'target-event',
      target_saved_revision_id: 'saved-head', target_working_draft_version: 0,
      ready_for_draft: true, issues: [], preview_fingerprint: 'a'.repeat(64), candidate_fingerprint: 'b'.repeat(64)
    } }
  }

  it('rejects a response bound to a foreign target rather than offering Apply', async () => {
    const { user, preview } = await openProposal()
    api.previewTournamentLabRunDraft.mockResolvedValue({ ...preview, branch_id: 'another-branch' })
    await user.click(screen.getByRole('button', { name: 'Preview Run draft' }))
    expect(await screen.findByText(/Run proposal preview does not match/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Apply to Run Working Draft' })).not.toBeInTheDocument()
    expect(api.applyTournamentLabRunDraft).not.toHaveBeenCalled()
  })

  it('does not display an old target preview delivered after the target was edited', async () => {
    const { user, preview } = await openProposal()
    const pending = deferred<typeof preview>()
    api.previewTournamentLabRunDraft.mockImplementation(() => pending.promise)
    await user.click(screen.getByRole('button', { name: 'Preview Run draft' }))
    fireEvent.change(screen.getByLabelText('Tournament Lab target Branch ID'), { target: { value: 'new-branch' } })
    await act(async () => { pending.resolve(preview); await pending.promise })
    expect(screen.queryByRole('button', { name: 'Apply to Run Working Draft' })).not.toBeInTheDocument()
    expect(api.applyTournamentLabRunDraft).not.toHaveBeenCalled()
  })

  it('retries an uncertain Apply with the same exact command and reviewed authority', async () => {
    const { user, preview } = await openProposal()
    api.previewTournamentLabRunDraft.mockResolvedValue(preview)
    api.applyTournamentLabRunDraft.mockRejectedValueOnce(new Error('Response lost'))
      .mockImplementation(async (_id, request) => ({
        ...request, proposal_version: 1, proposal_fingerprint: 'c'.repeat(64),
        working_draft_version: 1, mutation_performed: true, already_applied: true,
        candidate_fingerprint: request.expected_candidate_fingerprint
      }))
    await user.click(screen.getByRole('button', { name: 'Preview Run draft' }))
    await user.click(await screen.findByRole('button', { name: 'Apply to Run Working Draft' }))
    expect(await screen.findByText(/Run draft apply failed/)).toBeInTheDocument()
    const first = api.applyTournamentLabRunDraft.mock.calls[0]
    await user.click(screen.getByRole('button', { name: 'Apply to Run Working Draft' }))
    expect(await screen.findByText('idempotent')).toBeInTheDocument()
    expect(api.applyTournamentLabRunDraft.mock.calls[1]).toEqual(first)
    expect(first).toEqual(['session-a', expect.objectContaining({
      expected_session_fingerprint: preview.session_fingerprint,
      expected_saved_revision_id: preview.target_saved_revision_id,
      expected_preview_fingerprint: preview.preview_fingerprint,
      expected_candidate_fingerprint: preview.candidate_fingerprint,
      product_run_id: 'target-run', branch_id: 'target-branch', event_id: 'target-event'
    })])
  })
})

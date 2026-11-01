import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { RunBranch } from '../api/types'
import { LanguageProvider } from '../i18n/LanguageContext'
import { runHomeReadinessFixture } from '../test/runHomeReadinessFixture'
import { RunBranchReadinessComparison } from './RunBranchReadinessComparison'

const client = vi.hoisted(() => ({
  listRunBranches: vi.fn(), getRunHomeReadiness: vi.fn()
}))
vi.mock('../api/client', () => client)
const runId = 'run-branch-compare'
const left = 'timeline-a', right = 'timeline-b'
function branch(id: string, head: string): RunBranch {
  return {
    run_id: runId, branch_id: id, display_name: id === left ? 'Timeline A' : 'Timeline B',
    status: 'active', read_only: false, branch_seed: null, forked_from_branch_id: null,
    forked_from_checkpoint_id: null, saved_head_revision_id: head,
    head_checkpoint_id: null, legacy_simulation_run_id: null, metadata_json: {},
    is_official: false
  }
}
const branches = [branch(left, 'head-a'), branch(right, 'head-b')]
function renderPanel(rows = branches) {
  return render(<LanguageProvider><RunBranchReadinessComparison
    runId={runId} branchId={left} head="head-a" branches={rows}
  /></LanguageProvider>)
}
function chooseRight() {
  fireEvent.change(screen.getByRole('combobox', { name: 'Porovnat s Branch' }), {
    target: { value: right }
  })
}
function evidence(id: string, head: string) {
  return runHomeReadinessFixture(runId, id, { saved_revision_id: head })
}

describe('Admin Branch readiness comparison (CS/EN)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    client.listRunBranches.mockResolvedValue({run_branches: branches})
    client.getRunHomeReadiness.mockImplementation(async (_run: string, id: string) =>
      evidence(id, id === left ? 'head-a' : 'head-b'))
  })

  it('remains request-free until the user chooses another Branch and explicitly starts', async () => {
    renderPanel()
    expect(screen.getByText('Porovnání uložených podkladů Branchí')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Načíst porovnání' })).toBeDisabled()
    expect(client.getRunHomeReadiness).not.toHaveBeenCalled()
    chooseRight()
    fireEvent.click(screen.getByRole('button', { name: 'Načíst porovnání' }))
    expect(await screen.findByText('Kalendář turnajů')).toBeVisible()
    expect(screen.getByText('Zdrojová revize')).toBeVisible()
    expect(screen.getByText(/Samostatných/)).toBeDefined()
    expect(screen.getByRole('button', { name: 'Stáhnout ověřené srovnání JSON' })).toBeEnabled()
    expect(client.listRunBranches).toHaveBeenCalledTimes(2)
    expect(client.getRunHomeReadiness).toHaveBeenCalledTimes(2)
  })

  it('supports English without changing the Saved source request', async () => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    renderPanel()
    expect(screen.getByRole('combobox', { name: 'Compare with Branch' })).toBeVisible()
    fireEvent.change(screen.getByRole('combobox'), { target: { value: right } })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect comparison' }))
    expect(await screen.findByText('Tournament calendar')).toBeVisible()
    expect(screen.getByText(/not an execution readiness certificate/)).toBeVisible()
  })

  it('never renders a mixed/foreign or older right HEAD as valid evidence', async () => {
    client.getRunHomeReadiness.mockImplementation(async (_run: string, id: string) =>
      evidence(id, id === left ? 'head-a' : 'stale-right'))
    renderPanel()
    chooseRight()
    fireEvent.click(screen.getByRole('button', { name: 'Načíst porovnání' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Porovnání není důvěryhodné')
    expect(screen.queryByText('Kalendář turnajů')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Stáhnout/ })).not.toBeInTheDocument()
  })

  it('invalidates the visible comparison on a later HEAD change without claiming historical evidence is current', async () => {
    const view = renderPanel()
    chooseRight()
    fireEvent.click(screen.getByRole('button', { name: 'Načíst porovnání' }))
    expect(await screen.findByText('Kalendář turnajů')).toBeVisible()
    view.rerender(<LanguageProvider><RunBranchReadinessComparison
      runId={runId} branchId={left} head="head-a"
      branches={[branches[0], branch(right,'new-head')]}
    /></LanguageProvider>)
    await waitFor(() =>
      expect(screen.queryByText('Kalendář turnajů')).not.toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent('změnil Saved HEAD')
  })

  it('does not display previously verified comparison after failed explicit refresh', async () => {
    renderPanel()
    chooseRight()
    fireEvent.click(screen.getByRole('button', { name: 'Načíst porovnání' }))
    expect(await screen.findByText('Kalendář turnajů')).toBeVisible()
    client.getRunHomeReadiness.mockRejectedValue(new Error('HTTP 409 conflicting source'))
    fireEvent.click(screen.getByRole('button', { name: 'Načíst znovu' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Porovnání není důvěryhodné')
    expect(screen.queryByText('Kalendář turnajů')).not.toBeInTheDocument()
  })

  it('skips the panel for no alternate saved Branch', () => {
    const only = renderPanel([branches[0]])
    expect(screen.queryByRole('heading', {name:'Porovnání uložených podkladů Branchí'}))
      .not.toBeInTheDocument()
    only.unmount()
  })
})

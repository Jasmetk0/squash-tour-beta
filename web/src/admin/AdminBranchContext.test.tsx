import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminBranchProvider } from './AdminBranchContext'
import { AdminBranchSelector } from '../components/AdminBranchSelector'
import type { RunBranch } from '../api/types'

const api = vi.hoisted(() => ({
  getRunContainer: vi.fn(),
  listRunBranches: vi.fn(),
  ApiError: class ApiError extends Error { constructor(message: string, public status: number) { super(message) } },
}))
vi.mock('../api/client', () => api)

function branch(runId: string, branchId: string, displayName: string, readOnly = false): RunBranch {
  return {
    run_id: runId, branch_id: branchId, display_name: displayName, status: 'active', read_only: readOnly,
    branch_seed: 1, forked_from_branch_id: null, forked_from_checkpoint_id: null, head_checkpoint_id: null,
    legacy_simulation_run_id: null, metadata_json: {}, is_official: false,
  }
}

function Harness(): JSX.Element {
  const [runId, setRunId] = useState('run-a')
  const [page, setPage] = useState('home')
  return (
    <AdminBranchProvider runId={runId}>
      <AdminBranchSelector />
      <button onClick={() => setPage(page === 'home' ? 'branches' : 'home')}>Navigate page</button>
      <output aria-label="Current page">{page}</output>
      <button onClick={() => setRunId('run-b')}>Change Run</button>
    </AdminBranchProvider>
  )
}

function renderHarness(): void {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><Harness /></QueryClientProvider>)
}

describe('AdminBranchProvider and selector', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.getRunContainer.mockImplementation(async (runId: string) => ({ run_id: runId, official_branch_id: runId === 'run-a' ? 'a-viewer' : 'b-viewer' }))
    api.listRunBranches.mockImplementation(async (runId: string) => ({ run_branches: runId === 'run-a'
      ? [branch(runId, 'a-other', 'Experimental 2031', true), branch(runId, 'a-viewer', 'Viewer timeline')]
      : [branch(runId, 'same-id-is-not-equivalent', 'Other Run Branch'), branch(runId, 'b-viewer', 'Run B Viewer')]
    }))
  })

  it('initializes from Viewer Branch, changes only local context, and survives nested-page navigation', async () => {
    localStorage.setItem('beta_engine:viewer_active_product_run_id', 'viewer-product')
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-legacy')
    renderHarness()

    const selector = await screen.findByRole('combobox', { name: 'Admin active Branch' })
    await waitFor(() => expect(selector).toHaveValue('a-viewer'))
    expect(screen.getByText('Viewer timeline', { selector: 'strong' })).toBeInTheDocument()
    fireEvent.change(selector, { target: { value: 'a-other' } })
    expect(selector).toHaveValue('a-other')
    expect(screen.getByText('Experimental 2031', { selector: 'strong' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Navigate page' }))
    expect(screen.getByLabelText('Current page')).toHaveTextContent('branches')
    expect(selector).toHaveValue('a-other')
    expect(localStorage.getItem('beta_engine:viewer_active_product_run_id')).toBe('viewer-product')
    expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBe('viewer-legacy')
    expect(api.getRunContainer).toHaveBeenCalledTimes(1)
    expect(api.listRunBranches).toHaveBeenCalledTimes(1)
  })

  it('initializes a changed Run independently from its Viewer Branch', async () => {
    renderHarness()
    const selector = await screen.findByRole('combobox', { name: 'Admin active Branch' })
    await waitFor(() => expect(selector).toHaveValue('a-viewer'))
    fireEvent.change(selector, { target: { value: 'a-other' } })
    fireEvent.click(screen.getByRole('button', { name: 'Change Run' }))
    await waitFor(() => expect(selector).toHaveValue('b-viewer'))
    expect(screen.getByText('Run B Viewer', { selector: 'strong' })).toBeInTheDocument()
  })

  it('uses stable Branch identity fallback when the Viewer pointer is missing and permits read-only selection', async () => {
    api.getRunContainer.mockResolvedValue({ run_id: 'run-a', official_branch_id: 'missing' })
    api.listRunBranches.mockResolvedValue({ run_branches: [branch('run-a', 'z-last', 'Zed'), branch('run-a', 'a-first', '', true)] })
    renderHarness()
    const selector = await screen.findByRole('combobox', { name: 'Admin active Branch' })
    await waitFor(() => expect(selector).toHaveValue('a-first'))
    expect(screen.getByText(/Viewer Branch is missing from the available Branches/)).toBeInTheDocument()
    fireEvent.change(selector, { target: { value: 'z-last' } })
    expect(selector).toHaveValue('z-last')
  })

  it('keeps the shell usable without fabricated data when Branch loading fails', async () => {
    api.listRunBranches.mockRejectedValue(new Error('branch service unavailable'))
    renderHarness()
    const selector = await screen.findByRole('combobox', { name: 'Admin active Branch' })
    await waitFor(() => expect(selector).toBeDisabled())
    expect(selector).toHaveValue('')
    expect(screen.getByText(/Branch metadata unavailable: branch service unavailable/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Change Run' })).toBeEnabled()
  })

  it('uses deterministic Branch fallback when Run metadata is unavailable', async () => {
    api.getRunContainer.mockRejectedValue(new Error('run metadata unavailable'))
    api.listRunBranches.mockResolvedValue({ run_branches: [branch('run-a', 'z-last', 'Zed'), branch('run-a', 'a-first', 'Alpha')] })
    renderHarness()

    const selector = await screen.findByRole('combobox', { name: 'Admin active Branch' })
    await waitFor(() => expect(selector).toHaveValue('a-first'))
    expect(selector).toBeEnabled()
    expect(screen.getByText(/Run metadata unavailable: run metadata unavailable/)).toBeInTheDocument()

    fireEvent.change(selector, { target: { value: 'z-last' } })
    expect(selector).toHaveValue('z-last')
  })
})

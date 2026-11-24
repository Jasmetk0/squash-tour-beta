import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../../i18n/LanguageContext'
import { WorldPackageApplyPage } from './WorldPackageApplyPage'

const api = vi.hoisted(() => ({
  getWorldPackage: vi.fn(), listRunContainers: vi.fn(), listRunBranches: vi.fn(),
  getBranchWorkingDraft: vi.fn(), getRunPackageState: vi.fn(), previewWorldSelection: vi.fn(),
  confirmWorldSelection: vi.fn(), saveRunPackageWorkingDraft: vi.fn(),
}))
vi.mock('../../api/client', () => api)

const runId = 'run/1'
const branchId = 'timeline&1'
const search = '?run=run%2F1&branch=timeline%261'
const state = {
  run_id: runId, branch_id: branchId, package_versions: [{package_id: 'atp_earth'}],
}
const draft = {
  run_id: runId, branch_id: branchId, base_saved_revision_id: 'saved-world',
  draft_version: 1, status: 'clean',
}

function mount() {
  render(<QueryClientProvider client={new QueryClient()}>
    <MemoryRouter initialEntries={['/admin/packages/world/atp_earth/apply'+search]}>
      <LanguageProvider><Routes>
        <Route path="/admin/packages/world/:worldId/apply" element={<WorldPackageApplyPage/>}/>
      </Routes></LanguageProvider>
    </MemoryRouter>
  </QueryClientProvider>)
}

describe('ATP Earth setup handoff', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    localStorage.clear()
    api.getWorldPackage.mockResolvedValue({world_id: 'atp_earth', name: 'ATP Earth'})
    api.listRunContainers.mockResolvedValue({run_containers: [{
      run_id: runId, display_name: 'My ATP Run', read_only: false,
      storage_kind: 'custom_local', status: 'working', metadata_json: {run_calendar: {
        schema_version: 'run_calendar.v1', weeks_per_year: 52, season_start_year_week: 1,
        start_year: 2024, season_count: 3,
      }},
    }]})
    api.listRunBranches.mockResolvedValue({run_branches: [{
      run_id: runId, branch_id: branchId, display_name: 'Timeline 1',
      read_only: false, status: 'active', saved_head_revision_id: 'saved-world',
    }]})
    api.getBranchWorkingDraft.mockResolvedValue(draft)
    api.getRunPackageState.mockResolvedValue({state, fingerprint: 'a'.repeat(64)})
    api.previewWorldSelection.mockResolvedValue({
      run_id: runId, branch_id: branchId, saved_head_revision_id: 'saved-world', draft_version: 1,
      source: {package_id: 'atp_earth', source_version: 1, source_fingerprint: 'b'.repeat(64)},
      current_state_fingerprint: 'a'.repeat(64), preview_fingerprint: 'c'.repeat(64),
      selection_fingerprint: 'd'.repeat(64), selected_entities: [], excluded_entities: [],
      available: [], changes: [], blockers: [], can_confirm: false,
    })
  })

  it('continues from the clean saved World to the same Run and Timeline after reload', async () => {
    mount()
    const next = await screen.findByRole('link', {name: /historickému kalendáři ATP/})
    expect(next).toHaveAttribute('href', '/admin/packages/atp-tour-calendar-reference'+search)
    expect(screen.getByRole('combobox', {name: 'Target Branch'})).toHaveValue(branchId)
    expect(api.confirmWorldSelection).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('keeps a staged World in the current setup step until explicit Save', async () => {
    api.getBranchWorkingDraft.mockResolvedValue({...draft, status: 'dirty'})
    mount()
    expect(await screen.findByText(/Tato branch má již neuložený Working Draft/)).toBeVisible()
    expect(screen.queryByRole('link', {name: /historickému kalendáři ATP/})).toBeNull()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })
})

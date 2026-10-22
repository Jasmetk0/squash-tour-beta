import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CalendarTourPage } from './CalendarTourPage'

const state = vi.hoisted(() => ({
  language: 'en',
  selectedBranch: null as null | { run_id: string; branch_id: string; saved_head_revision_id: string | null },
}))
vi.mock('../admin/AdminBranchContext', () => ({
  useAdminBranch: () => ({ selectedBranch: state.selectedBranch }),
}))
vi.mock('../i18n/LanguageContext', () => ({
  useLanguage: () => ({ language: state.language }),
}))
vi.mock('./CalendarTourPanel', () => ({
  CalendarTourPanel: ({ branchId, head }: { branchId: string; head: string }) =>
    <p>Tour calendar loaded from {branchId} / {head}</p>,
}))
vi.mock('./NativeProspectSourceEpochPanel', () => ({
  NativeProspectSourceEpochPanel: ({ branchId }: { branchId: string }) =>
    <p>Epoch data loaded for {branchId}</p>,
}))

function mount(runId = 'run-a') {
  render(
    <MemoryRouter initialEntries={[`/admin/runs/${runId}/tour/calendar`]}>
      <Routes>
        <Route path="/admin/runs/:runId/tour/calendar" element={<CalendarTourPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Tour Calendar Branch readiness messages', () => {
  beforeEach(() => {
    state.selectedBranch = null
    state.language = 'en'
  })

  it('requests a Branch only when no matching Branch is actually selected', () => {
    mount()
    expect(screen.getByRole('status')).toHaveTextContent('Select a Branch of this Run.')
    expect(screen.queryByText(/Tour calendar loaded from/)).not.toBeInTheDocument()
  })

  it('does not pretend a selected Branch without a persisted HEAD is unselected', () => {
    state.selectedBranch = { run_id: 'run-a', branch_id: 'branch-empty', saved_head_revision_id: null }
    mount()
    expect(screen.getByRole('status')).toHaveTextContent('no saved HEAD revision yet')
    expect(screen.queryByText(/Tour calendar loaded from/)).not.toBeInTheDocument()
  })

  it('preserves Czech explanation and denies a selected Branch belonging to a different Run', () => {
    state.language = 'cs'
    state.selectedBranch = { run_id: 'run-b', branch_id: 'other', saved_head_revision_id: 'head-b' }
    mount()
    expect(screen.getByRole('status')).toHaveTextContent('Vyberte Branch tohoto Runu.')
    expect(screen.queryByText(/Tour calendar loaded from/)).not.toBeInTheDocument()
  })

  it('loads both read-only panels only for a matching saved HEAD', () => {
    state.selectedBranch = { run_id: 'run-a', branch_id: 'main', saved_head_revision_id: 'head-a' }
    mount()
    expect(screen.getByText('Tour calendar loaded from main / head-a')).toBeInTheDocument()
    expect(screen.getByText('Epoch data loaded for main')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})

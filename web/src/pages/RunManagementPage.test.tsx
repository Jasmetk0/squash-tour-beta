import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../i18n/LanguageContext'
import { renderWithRoute } from '../test/testUtils'
import { RunManagementPage } from './RunManagementPage'

const mocks = vi.hoisted(() => ({
  getRunContainer: vi.fn(),
  selectedBranch: {
    current: {
      run_id: 'run/with space',
      branch_id: 'branch-one',
      display_name: 'Timeline A',
      saved_head_revision_id: 'saved-123'
    }
  }
}))
vi.mock('../api/client', () => ({ getRunContainer: mocks.getRunContainer }))
vi.mock('../admin/AdminBranchContext', () => ({
  useAdminBranch: () => ({ selectedBranch: mocks.selectedBranch.current })
}))
vi.mock('../components/RunPackageSetupPanel', () => ({
  RunPackageSetupPanel: () => <p>Run-owned package setup</p>
}))

function mount(): void {
  renderWithRoute(
    <LanguageProvider><RunManagementPage /></LanguageProvider>,
    '/admin/runs/run%2Fwith%20space/manage'
  )
}

describe('Run Management saved context', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mocks.selectedBranch.current = {
      run_id: 'run/with space', branch_id: 'branch-one',
      display_name: 'Timeline A', saved_head_revision_id: 'saved-123'
    }
    mocks.getRunContainer.mockResolvedValue({
      run_id: 'run/with space', display_name: 'A new Run',
      storage_kind: 'custom_local', read_only: false, status: 'active'
    })
  })

  it('shows the verified selected Branch, saved HEAD and encoded overview navigation', async () => {
    mount()
    expect(await screen.findByText('A new Run', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/Vybraná Branch: Timeline A/)).toHaveTextContent('Uložená revize: Dostupná')
    expect(screen.getByRole('link', { name: 'Otevřít přehled Runu →' }))
      .toHaveAttribute('href', '/admin/runs/run%2Fwith%20space')
    expect(screen.getByText('Run-owned package setup')).toBeInTheDocument()
  })

  it('does not display or pass a Branch that belongs to a different Run', async () => {
    mocks.selectedBranch.current = {
      run_id: 'another-run', branch_id: 'foreign',
      display_name: 'Foreign Timeline', saved_head_revision_id: 'foreign-head'
    }
    mount()
    expect(await screen.findByText('A new Run', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/Vybraná Branch: Zatím nevybraná/))
      .toHaveTextContent('Uložená revize: Nedostupná')
    expect(screen.queryByText(/Foreign Timeline/)).not.toBeInTheDocument()
  })

  it('hides editing controls when the API returns a different Run identity', async () => {
    mocks.getRunContainer.mockResolvedValue({
      run_id: 'other-run', display_name: 'Foreign Run',
      storage_kind: 'custom_local', read_only: false, status: 'active'
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Server vrátil jiný Run.')
    expect(screen.queryByText('Foreign Run')).not.toBeInTheDocument()
    expect(screen.queryByText('Run-owned package setup')).not.toBeInTheDocument()
  })

  it('keeps read-only Runs free of package editing controls', async () => {
    mocks.getRunContainer.mockResolvedValue({
      run_id: 'run/with space', display_name: 'Protected Run',
      storage_kind: 'built_in', read_only: true, status: 'active'
    })
    mount()
    expect(await screen.findByText(/Protected Run · active · Pouze ke čtení/)).toBeInTheDocument()
    expect(screen.queryByText('Run-owned package setup')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít přehled Runu →' })).toBeInTheDocument()
  })
})

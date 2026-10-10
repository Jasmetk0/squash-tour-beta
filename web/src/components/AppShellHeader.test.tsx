import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppShellHeader } from './AppShellHeader'
import { resolveAdminScope } from '../navigation/appShellMode'
import { AdminBranchProvider } from '../admin/AdminBranchContext'
import { AdminTimeProvider } from '../admin/AdminTimeContext'
import { LanguageProvider } from '../i18n/LanguageContext'

const api = vi.hoisted(() => ({ listRunContainers: vi.fn(), getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchState: vi.fn(), listBranchCheckpoints: vi.fn() }))
vi.mock('../api/client', () => api)

function renderHeader(path: string): void {
  const scope = resolveAdminScope(path)
  const header = <AppShellHeader mode="admin" pathname={path} adminScope={scope} />
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[path]}><LanguageProvider>
      {scope.kind === 'run' ? <AdminBranchProvider runId={scope.runId}><AdminTimeProvider>{header}</AdminTimeProvider></AdminBranchProvider> : header}
    </LanguageProvider></MemoryRouter>
  </QueryClientProvider>)
}

describe('approved Admin header', () => {
  beforeEach(() => {
    localStorage.clear()
    api.listRunContainers.mockResolvedValue({ run_containers: [] })
    api.getRunContainer.mockResolvedValue({ run_id: 'run-a', official_branch_id: null })
    api.listRunBranches.mockResolvedValue({ run_branches: [] })
    api.getBranchState.mockResolvedValue({})
    api.listBranchCheckpoints.mockResolvedValue({ branch_checkpoints: [] })
  })
  it('uses a global Home logo without Run/Branch/Time on global pages', () => {
    renderHeader('/admin/packages')
    expect(screen.getByRole('link', { name: 'Squash Engine global Home' })).toHaveAttribute('href', '/admin')
    expect(screen.queryByRole('combobox', { name: 'Admin active Run' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Mode switcher' })).not.toBeInTheDocument()
  })
  it('allows Czech and English selection and retains Run / Branch / Time controls only within Run scope', () => {
    renderHeader('/admin/runs/run-a')
    expect(screen.getByRole('combobox', { name: 'Admin active Run' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Admin active Branch' })).toBeInTheDocument()
    expect(screen.getByLabelText('Admin view time')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Language / Jazyk' }), { target: { value: 'en' } })
    expect(screen.getByText('Admin · Pre-alpha')).toBeInTheDocument()
    expect(localStorage.getItem('squash-engine-language-v1')).toBe('en')
  })
})

import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AppShellHeader } from './AppShellHeader'
import type { AppShellMode } from '../navigation/appShellMode'
import { resolveAdminScope } from '../navigation/appShellMode'
import { AdminBranchProvider } from '../admin/AdminBranchContext'
import { AdminTimeProvider } from '../admin/AdminTimeContext'

const api = vi.hoisted(() => ({ listRunContainers: vi.fn(), getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchState: vi.fn() }))
vi.mock('../api/client', () => api)

function renderAppShellHeader(mode: AppShellMode, pathname: string): void {
  const scope = resolveAdminScope(pathname)
  const header = <AppShellHeader mode={mode} pathname={pathname} adminScope={scope} />
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[pathname]}>
        {mode === 'admin' && scope.kind === 'run' ? <AdminBranchProvider runId={scope.runId}><AdminTimeProvider>{header}</AdminTimeProvider></AdminBranchProvider> : header}
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('AppShellHeader', () => {
  beforeEach(() => {
    api.listRunContainers.mockResolvedValue({ run_containers: [] })
    api.getRunContainer.mockResolvedValue({ run_id: 'run-a', official_branch_id: null })
    api.listRunBranches.mockResolvedValue({ run_branches: [] })
    api.getBranchState.mockResolvedValue({})
  })
  it('renders the Viewer mode title and subtitle', () => {
    renderAppShellHeader('viewer', '/viewer')

    expect(screen.getByRole('heading', { name: 'MSA Squash' })).toBeInTheDocument()
    expect(screen.getByText('Viewer / MSA Website Mode')).toHaveClass('subtitle')
  })

  it('renders the Admin mode title and subtitle', () => {
    renderAppShellHeader('admin', '/admin')

    expect(screen.getByRole('heading', { name: 'Squash Tour Beta Engine' })).toBeInTheDocument()
    expect(screen.getByText('Admin / Engine Mode')).toHaveClass('subtitle')
  })

  it('shows Run, Branch, then Present Time controls only in Run Admin scope', async () => {
    renderAppShellHeader('admin', '/admin/runs/run-a')
    expect(await screen.findByRole('combobox', { name: 'Admin active Run' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Admin active Branch' })).toBeInTheDocument()
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present')
  })

  it('renders the landing mode title and subtitle', () => {
    renderAppShellHeader('landing', '/')

    expect(screen.getByRole('heading', { name: 'Squash Tour Beta Engine' })).toBeInTheDocument()
    expect(screen.getByText('Mode selection')).toHaveClass('subtitle')
  })

  it('renders the mode switcher in the header', () => {
    renderAppShellHeader('viewer', '/viewer')

    expect(screen.getByLabelText('Mode switcher')).toBeInTheDocument()
  })

  it('preserves mode switcher targets from a Viewer route', () => {
    renderAppShellHeader('viewer', '/viewer')

    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin')
  })

  it('preserves mode switcher targets from an Admin route', () => {
    renderAppShellHeader('admin', '/admin/runs/run-a/finals')

    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin/runs/run-a/finals')
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer/runs')
  })
})

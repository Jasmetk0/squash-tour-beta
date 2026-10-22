import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminDiagnosticsPage } from './AdminDiagnosticsPage'

const storage = vi.hoisted(() => ({ lastRunId: null as string | null }))
vi.mock('../viewer/activeRun', () => ({
  readLastRunId: () => storage.lastRunId,
}))

function mount() {
  render(
    <MemoryRouter>
      <AdminDiagnosticsPage />
    </MemoryRouter>,
  )
}

describe('AdminDiagnosticsPage launcher', () => {
  beforeEach(() => {
    storage.lastRunId = null
  })

  it('distinguishes linked tools from planned diagnostics without claiming a consolidated scan', () => {
    mount()
    expect(screen.getByText(/not a consolidated diagnostic scan/)).toBeInTheDocument()
    expect(screen.getByText('Showing 6 of 6 diagnostic areas')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'World Balance' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Calendar Validation' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Run Health' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invalidated Data' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Narrative Locks' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit / Warnings' })).toBeInTheDocument()
    expect(screen.getByText(/configured season-week range rather than assuming W01–W61/)).toBeInTheDocument()

    const filter = screen.getByRole('combobox', { name: 'Show diagnostics sections' })
    fireEvent.change(filter, { target: { value: 'available' } })
    expect(screen.getByText('Showing 3 of 6 diagnostic areas')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'World Balance' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Run Health' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Narrative Locks' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Invalidated Data' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Talent Preview' })).toHaveAttribute('href', '/admin/world/talent-preview')

    fireEvent.change(filter, { target: { value: 'planned' } })
    expect(screen.getByText('Showing 3 of 6 diagnostic areas')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invalidated Data' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Narrative Locks' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit / Warnings' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'World Balance' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Run Health' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Runs' })).toHaveAttribute('href', '/admin/runs')

    fireEvent.change(filter, { target: { value: 'all' } })
    expect(screen.getByText('Showing 6 of 6 diagnostic areas')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Calendar Validation' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit / Warnings' })).toBeInTheDocument()
  })

  it('does not invent a last Run link when there is no remembered Run', () => {
    mount()
    expect(screen.getByRole('link', { name: 'Open Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.queryByRole('link', { name: /last run diagnostics/i })).not.toBeInTheDocument()
  })

  it('escapes the trimmed last Run ID as one route segment in both diagnostic shortcuts', () => {
    storage.lastRunId = '  saved A/B?x  '
    mount()
    const path = '/admin/runs/saved%20A%2FB%3Fx/diagnostics'
    expect(screen.getByRole('link', { name: 'Open last run diagnostics (saved A/B?x)' }))
      .toHaveAttribute('href', path)
    expect(screen.getByRole('link', { name: 'Last run diagnostics' }))
      .toHaveAttribute('href', path)
  })

  it('treats a whitespace-only remembered Run ID as absent', () => {
    storage.lastRunId = '   '
    mount()
    expect(screen.queryByRole('link', { name: /last run diagnostics/i })).not.toBeInTheDocument()
  })
})

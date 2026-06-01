import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { VIEWER_ACTIVE_RUN_CHANGED_EVENT } from '../viewer/activeRun'
import { ViewerActiveRunCompact, ViewerRunSelector } from './ViewerRunSelector'

const api = vi.hoisted(() => ({
  listRuns: vi.fn()
}))

vi.mock('../api/client', () => api)

function renderSelector(component: JSX.Element = <ViewerRunSelector />): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{component}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ViewerRunSelector', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run-a',
          season: 2027,
          seed: 5,
          progress: { next_event_index: 1, total_events: 10, completed_event_count: 0 },
          source_type: 'new_run',
          parent_run_id: null,
          child_run_count: 0
        },
        {
          run_id: 'run-b',
          season: 2028,
          seed: 8,
          progress: { next_event_index: 2, total_events: 12, completed_event_count: 1 },
          source_type: 'new_run',
          parent_run_id: null,
          child_run_count: 0
        }
      ]
    })
  })

  it('sets active viewer run in localStorage', async () => {
    const user = userEvent.setup()
    renderSelector()

    await screen.findByRole('option', { name: /run-a/i })
    await user.selectOptions(screen.getByLabelText('Available runs'), 'run-b')
    await user.click(screen.getByRole('button', { name: 'Set active run' }))

    expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBe('run-b')
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-b')
    expect(screen.getByText('run-b')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open Admin Run Detail' })).not.toBeInTheDocument()
  })

  it('auto-applies the compact topbar selector without rendering a compact Set run button', async () => {
    const user = userEvent.setup()
    const activeRunChanged = vi.fn()
    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, activeRunChanged)
    renderSelector(<ViewerActiveRunCompact />)

    const control = screen.getByRole('form', { name: 'Viewer topbar active run' })
    expect(control).toHaveTextContent('Active run: None')
    expect(screen.getByLabelText('Viewer active run')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Set run' })).not.toBeInTheDocument()

    await screen.findByRole('option', { name: /run-b/i })
    await user.selectOptions(screen.getByLabelText('Viewer active run'), 'run-b')

    expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBe('run-b')
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-b')
    expect(activeRunChanged).toHaveBeenCalledTimes(1)
    expect(control).toHaveTextContent('Active run: run-b')
    window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, activeRunChanged)
  })

  it('shows the no-runs empty state from the read-only runs API', async () => {
    api.listRuns.mockResolvedValue({ runs: [] })
    renderSelector()

    expect(await screen.findByText('No runs are available yet.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Set active run' })).toBeDisabled()
  })
})

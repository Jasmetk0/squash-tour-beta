import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ViewerRunSelector } from './ViewerRunSelector'

const api = vi.hoisted(() => ({
  listRuns: vi.fn()
}))

vi.mock('../api/client', () => api)

function renderSelector(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerRunSelector />
      </MemoryRouter>
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
    await user.selectOptions(screen.getByLabelText('Select existing run'), 'run-b')
    await user.click(screen.getByRole('button', { name: 'Set as Viewer Run' }))

    expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBe('run-b')
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-b')
    expect(screen.getByText('run-b')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Admin Run Detail' })).toHaveAttribute('href', '/admin/runs/run-b')
  })

  it('clears active viewer run from localStorage', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    const user = userEvent.setup()
    renderSelector()

    expect(await screen.findByText('run-a')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear Viewer Run' }))

    await waitFor(() => expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBeNull())
    expect(screen.getByText('No Viewer run selected')).toBeInTheDocument()
  })
})

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunsPage } from './RunsPage'
import { renderWithRoute } from '../test/testUtils'

const navigateMock = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

const api = vi.hoisted(() => {
  class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }

  return {
    ApiError,
    listRuns: vi.fn(),
    getRun: vi.fn()
  }
})

vi.mock('../api/client', () => api)

describe('RunsPage', () => {
  beforeEach(() => {
    localStorage.clear()
    navigateMock.mockReset()
    api.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run-3',
          season: 2029,
          seed: 3,
          progress: { next_event_index: 8, total_events: 24, completed_event_count: 7 },
          source_type: 'bootstrap',
          parent_run_id: 'run-2',
          child_run_count: 1
        },
        {
          run_id: 'run-1',
          season: 2027,
          seed: 1,
          progress: { next_event_index: 2, total_events: 24, completed_event_count: 1 },
          source_type: 'new_run',
          parent_run_id: null,
          child_run_count: 0
        },
        {
          run_id: 'run-2',
          season: 2028,
          seed: 2,
          progress: { next_event_index: 4, total_events: 24, completed_event_count: 3 },
          source_type: null,
          parent_run_id: null,
          child_run_count: 0
        }
      ]
    })
    api.getRun.mockResolvedValue({ run: { run_id: 'run-3' } })
  })

  it('renders /runs route shell and runs list from GET /runs', async () => {
    renderWithRoute(<RunsPage />, '/runs')

    expect(await screen.findByRole('heading', { name: 'Runs browser' })).toBeInTheDocument()
    expect(api.listRuns).toHaveBeenCalledTimes(1)
    expect(await screen.findByRole('heading', { name: 'run-3' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'run-1' })).toBeInTheDocument()
  })

  it('preserves backend order exactly as returned', async () => {
    renderWithRoute(<RunsPage />, '/runs')

    const run3 = await screen.findByRole('heading', { name: 'run-3' })
    const run1 = await screen.findByRole('heading', { name: 'run-1' })
    const run2 = await screen.findByRole('heading', { name: 'run-2' })

    expect(run3.compareDocumentPosition(run1) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(run1.compareDocumentPosition(run2) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('filters without re-sorting matches', async () => {
    renderWithRoute(<RunsPage />, '/runs')

    await screen.findByRole('heading', { name: 'run-3' })
    await userEvent.type(screen.getByLabelText('Filter by run ID'), 'run-')
    await userEvent.type(screen.getByLabelText('Filter by source type'), 'new')

    expect(screen.getByRole('heading', { name: 'run-1' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'run-3' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'run-2' })).not.toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText('Filter by source type'))
    await userEvent.type(screen.getByLabelText('Filter by season'), '2028')
    expect(screen.getByRole('heading', { name: 'run-2' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'run-1' })).not.toBeInTheDocument()
  })

  it('shows remembered-run marker and correct links', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'run-3')
    renderWithRoute(<RunsPage />, '/runs')

    const runCard = (await screen.findByRole('heading', { name: 'run-3' })).closest('article') as HTMLElement
    expect(within(runCard).getByText('Remembered run')).toBeInTheDocument()
    expect(within(runCard).getByRole('link', { name: 'Run Detail' })).toHaveAttribute('href', '/runs/run-3')
    expect(within(runCard).getByRole('link', { name: 'Diagnostics' })).toHaveAttribute('href', '/runs/run-3/diagnostics')
    expect(within(runCard).getByRole('link', { name: 'Activity' })).toHaveAttribute('href', '/runs/run-3/activity')
    expect(within(runCard).getByRole('link', { name: 'Season Chain' })).toHaveAttribute('href', '/runs/run-3/season-chain')

    const nonChainRunCard = (await screen.findByRole('heading', { name: 'run-1' })).closest('article') as HTMLElement
    expect(within(nonChainRunCard).queryByRole('link', { name: 'Season Chain' })).not.toBeInTheDocument()
  })

  it('opens/continues a run through existing open flow', async () => {
    renderWithRoute(<RunsPage />, '/runs')

    const runCard = (await screen.findByRole('heading', { name: 'run-3' })).closest('article') as HTMLElement
    await userEvent.click(within(runCard).getByRole('button', { name: 'Open / continue' }))

    await waitFor(() => expect(api.getRun).toHaveBeenCalledWith('run-3'))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-3')
    expect(navigateMock).toHaveBeenCalledWith('/runs/run-3')
  })
})

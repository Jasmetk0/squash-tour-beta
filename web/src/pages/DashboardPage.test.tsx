import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DashboardPage } from './DashboardPage'
import { SUPPORTED_CALENDAR_SEASON } from '../config'
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
    createRun: vi.fn(),
    getHealth: vi.fn(),
    getRunStatusSummary: vi.fn(),
    getRunSource: vi.fn(),
    getRunLineage: vi.fn(),
    getRun: vi.fn()
  }
})

vi.mock('../api/client', () => api)

describe('DashboardPage', () => {
  beforeEach(() => {
    localStorage.clear()
    api.getHealth.mockResolvedValue({ status: 'ok' })
    api.createRun.mockResolvedValue({ run_id: 'run-a' })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      seed: 77,
      progress: { next_event_index: 2, total_events: 14, completed_event_count: 2 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
      history_counts: { events: 2, ranking_snapshots: 2, race_snapshots: 2 }
    })
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'new_run',
        parent_run_id: null,
        source_rollover_run_id: null,
        source_rollover_from_season: null,
        source_rollover_to_season: null
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'new_run',
          parent_run_id: null,
          source_rollover_run_id: null,
          source_rollover_from_season: null,
          source_rollover_to_season: null
        },
        children: []
      }
    })
    api.getRun.mockResolvedValue({ run: { run_id: 'run-a' } })
    navigateMock.mockReset()
  })

  it('renders API health status when health check succeeds', async () => {
    renderWithRoute(<DashboardPage />, '/')

    expect(await screen.findByText('API status: ok')).toBeInTheDocument()
  })

  it('shows a readable health error when health check fails', async () => {
    api.getHealth.mockRejectedValueOnce(new api.ApiError('health down', 503))

    renderWithRoute(<DashboardPage />, '/')

    expect(await screen.findByText('Health check unavailable: health down')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Create run/i })).toBeInTheDocument()
  })

  it('creates a run and navigates to run detail', async () => {
    renderWithRoute(<DashboardPage />, '/')

    expect(screen.getByLabelText('Season')).toHaveValue(SUPPORTED_CALENDAR_SEASON)

    const runIdInput = screen.getByLabelText('Run ID')
    await userEvent.clear(runIdInput)
    await userEvent.type(runIdInput, 'run-a')
    await userEvent.click(screen.getByRole('button', { name: 'Create and open run' }))

    await waitFor(() =>
      expect(api.createRun).toHaveBeenCalledWith({
        run_id: 'run-a',
        seed: 42,
        season: SUPPORTED_CALENDAR_SEASON
      })
    )
    expect(navigateMock).toHaveBeenCalledWith('/runs/run-a')
  })

  it('opens an existing run and navigates using the same route pattern', async () => {
    renderWithRoute(<DashboardPage />, '/')

    await userEvent.type(screen.getByLabelText('Existing run ID'), 'run-b')
    await userEvent.click(screen.getByRole('button', { name: 'Open and continue' }))

    await waitFor(() => expect(api.getRun).toHaveBeenCalledWith('run-b'))
    expect(navigateMock).toHaveBeenCalledWith('/runs/run-a')
  })

  it('shows empty resume state when no remembered run exists', async () => {
    renderWithRoute(<DashboardPage />, '/')

    expect(
      screen.getByText('No remembered run yet. Create or open a run to enable quick resume.')
    ).toBeInTheDocument()
  })

  it('renders remembered last run id and resumes it', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'remembered-run')
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'remembered-run',
      season: 2027,
      seed: 77,
      progress: { next_event_index: 2, total_events: 14, completed_event_count: 2 },
      finals: { qualification_available: true, result_available: false },
      rollover: { latest_to_season: 2028, transitioned_players: 128 },
      source: { source_type: 'bootstrap', parent_run_id: 'parent-run' },
      lineage: { child_run_count: 2 },
      history_counts: { events: 12, ranking_snapshots: 12, race_snapshots: 12 }
    })
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'bootstrap',
        parent_run_id: 'parent-run',
        source_rollover_run_id: 'parent-run',
        source_rollover_from_season: 2027,
        source_rollover_to_season: 2028
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'remembered-run',
        source: {
          source_type: 'bootstrap',
          parent_run_id: 'parent-run',
          source_rollover_run_id: 'parent-run',
          source_rollover_from_season: 2027,
          source_rollover_to_season: 2028
        },
        children: ['child-run-1', 'child-run-2']
      }
    })
    api.getRun.mockResolvedValue({ run: { run_id: 'remembered-run' } })

    renderWithRoute(<DashboardPage />, '/')

    expect(await screen.findByText('Remembered run ID: remembered-run')).toBeInTheDocument()
    expect(api.getRunStatusSummary).toHaveBeenCalledWith('remembered-run')
    const resumePanel = screen.getByRole('heading', { name: 'Resume remembered run' }).closest('section') as HTMLElement
    expect(await within(resumePanel).findByText('Season')).toBeInTheDocument()
    expect(await within(resumePanel).findByText('Seed')).toBeInTheDocument()
    expect(await within(resumePanel).findByText('Run ID')).toBeInTheDocument()
    expect(await within(resumePanel).findByText(/2\s*\/\s*14/)).toBeInTheDocument()
    expect(await within(resumePanel).findByText('Completed events')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Finals' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Rollover' })).toBeInTheDocument()
    expect(await within(resumePanel).findByText('Most relevant next inspections')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Run Detail' })[0]).toHaveAttribute('href', '/runs/remembered-run')
    expect(screen.getByRole('link', { name: 'Diagnostics' })).toHaveAttribute('href', '/runs/remembered-run/diagnostics')
    expect(screen.getByRole('link', { name: 'Season Chain' })).toHaveAttribute('href', '/runs/remembered-run/season-chain')
    expect(screen.getByRole('link', { name: 'Finals' })).toHaveAttribute('href', '/runs/remembered-run/finals')
    expect(screen.getByRole('link', { name: 'Rollover' })).toHaveAttribute('href', '/runs/remembered-run/rollover')
    expect(screen.getByRole('link', { name: 'Bootstrap / Lineage' })).toHaveAttribute('href', '/runs/remembered-run/bootstrap-lineage')
    expect(screen.getByRole('link', { name: 'parent-run' })).toHaveAttribute('href', '/runs/parent-run')
    expect(screen.getByRole('link', { name: 'child-run-1' })).toHaveAttribute('href', '/runs/child-run-1')
    expect(screen.getByRole('link', { name: 'child-run-2' })).toHaveAttribute('href', '/runs/child-run-2')
    await userEvent.click(screen.getByRole('button', { name: 'Resume Run' }))

    await waitFor(() => expect(api.getRun).toHaveBeenCalledWith('remembered-run'))
    expect(navigateMock).toHaveBeenCalledWith('/runs/remembered-run')
  })

  it('shows readable resume error if remembered run cannot be opened', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'missing-run')
    api.getRun.mockRejectedValue(new api.ApiError('{"detail":"Run not found"}', 404))

    renderWithRoute(<DashboardPage />, '/')

    await userEvent.click(screen.getByRole('button', { name: 'Resume Run' }))

    expect(await screen.findByText('Could not open run: Run not found')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Open run by ID/i })).toBeInTheDocument()
  })

  it('clears remembered run from localStorage and updates visible state', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'remembered-run')

    renderWithRoute(<DashboardPage />, '/')

    await userEvent.click(screen.getByRole('button', { name: 'Clear remembered run' }))

    expect(localStorage.getItem('beta_engine:last_run_id')).toBeNull()
    expect(
      screen.getByText('No remembered run yet. Create or open a run to enable quick resume.')
    ).toBeInTheDocument()
  })

  it('shows create-run failures with a readable message', async () => {
    api.createRun.mockRejectedValueOnce(new api.ApiError('{"detail":"Run already exists"}', 409))

    renderWithRoute(<DashboardPage />, '/')

    await userEvent.click(screen.getByRole('button', { name: 'Create and open run' }))

    expect(await screen.findByText('Could not create run: Run already exists')).toBeInTheDocument()
  })

  it('shows open-run failures with a readable message', async () => {
    api.getRun.mockRejectedValueOnce(new api.ApiError('{"detail":"Run not found"}', 404))

    renderWithRoute(<DashboardPage />, '/')

    await userEvent.type(screen.getByLabelText('Existing run ID'), 'missing-run')
    await userEvent.click(screen.getByRole('button', { name: 'Open and continue' }))

    expect(await screen.findByText('Could not open run: Run not found')).toBeInTheDocument()
  })

  it('shows a readable remembered-run summary fallback if summary cannot be loaded yet', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'missing-run')
    api.getRunStatusSummary.mockRejectedValue(new api.ApiError('{"detail":"Run not found"}', 404))

    renderWithRoute(<DashboardPage />, '/')

    expect(await screen.findByText('Summary unavailable until this run is opened again.')).toBeInTheDocument()
  })

  it('keeps next inspections compact when lineage/source are absent', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'remembered-run')

    renderWithRoute(<DashboardPage />, '/')

    expect(await screen.findByRole('link', { name: 'Run Detail' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Diagnostics' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Season Chain' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Finals' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Rollover' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Bootstrap / Lineage' })).toBeInTheDocument()
  })
})

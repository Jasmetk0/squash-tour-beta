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
    getRun: vi.fn(),
    getRunStatusSummary: vi.fn()
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
          source_type: 'rollover_bootstrap',
          parent_run_id: 'run-2',
          child_run_count: 1
        },
        {
          run_id: 'run-1',
          season: 2027,
          seed: 1,
          progress: { next_event_index: 2, total_events: 24, completed_event_count: 1 },
          source_type: 'fresh_seed',
          parent_run_id: null,
          child_run_count: 0
        },
        {
          run_id: 'run-2',
          season: 2028,
          seed: 2,
          progress: { next_event_index: 4, total_events: 24, completed_event_count: 3 },
          source_type: 'fresh_seed',
          parent_run_id: null,
          child_run_count: 0
        }
      ]
    })
    api.getRunStatusSummary.mockImplementation(async (runId: string) => ({
      run_id: runId,
      season: runId === 'run-1' ? 2027 : 2029,
      seed: runId === 'run-1' ? 1 : 3,
      progress: { next_event_index: runId === 'run-1' ? 2 : 8, total_events: 24, completed_event_count: runId === 'run-1' ? 1 : 7 },
      finals: { qualification_available: true, result_available: false },
      rollover: { latest_to_season: 2030, transitioned_players: 64 },
      source: { source_type: runId === 'run-1' ? 'fresh_seed' : 'rollover_bootstrap', parent_run_id: runId === 'run-1' ? null : 'run-2' },
      lineage: { child_run_count: runId === 'run-1' ? 0 : 1 },
      history_counts: { events: runId === 'run-1' ? 1 : 7, ranking_snapshots: 9, race_snapshots: 9 }
    }))
    api.getRun.mockResolvedValue({ run: { run_id: 'run-3' } })
  })

  it('renders /runs route shell and runs list from GET /runs', async () => {
    renderWithRoute(<RunsPage />, '/runs')

    expect(await screen.findByRole('heading', { name: 'Runs browser' })).toBeInTheDocument()
    expect(api.listRuns).toHaveBeenCalledTimes(1)
    expect(await screen.findByRole('button', { name: 'Selected run-3' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Inspect run-1' })).toBeInTheDocument()
  })

  it('preserves backend order exactly as returned', async () => {
    renderWithRoute(<RunsPage />, '/runs')

    const runButtons = await screen.findAllByRole('button', { name: /run-/i })
    expect(runButtons[0]).toHaveTextContent('run-3')
    expect(runButtons[1]).toHaveTextContent('run-1')
    expect(runButtons[2]).toHaveTextContent('run-2')
  })

  it('filters without re-sorting matches', async () => {
    renderWithRoute(<RunsPage />, '/runs')

    await screen.findByRole('button', { name: 'Selected run-3' })
    await userEvent.type(screen.getByLabelText('Filter by run ID'), 'run-')
    await userEvent.type(screen.getByLabelText('Filter by source type'), 'rollover')

    const buttonsAfterSourceFilter = screen.getAllByRole('button', { name: /run-/i })
    expect(buttonsAfterSourceFilter).toHaveLength(1)
    expect(buttonsAfterSourceFilter[0]).toHaveTextContent('run-3')

    await userEvent.clear(screen.getByLabelText('Filter by source type'))
    await userEvent.type(screen.getByLabelText('Filter by season'), '2028')
    const buttonsAfterSeasonFilter = screen.getAllByRole('button', { name: /run-/i })
    expect(buttonsAfterSeasonFilter).toHaveLength(1)
    expect(buttonsAfterSeasonFilter[0]).toHaveTextContent('run-2')
  })

  it('renders selected run detail from selection and status-summary with bridge links', async () => {
    renderWithRoute(<RunsPage />, '/runs?selected=run-1')

    await screen.findByText('Run ID')
    expect(api.getRunStatusSummary).toHaveBeenCalledWith('run-1')
    expect(screen.getByRole('link', { name: 'Run Detail' })).toHaveAttribute('href', '/runs/run-1')
    expect(screen.getByRole('link', { name: 'Diagnostics' })).toHaveAttribute('href', '/runs/run-1/diagnostics')
    expect(screen.getByRole('link', { name: 'Activity' })).toHaveAttribute('href', '/runs/run-1/activity')
    expect(screen.getByRole('link', { name: 'Season Calendar' })).toHaveAttribute('href', '/runs/run-1/calendar')
  })

  it('shows remembered-run marker and keeps open/continue behavior', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'run-3')
    renderWithRoute(<RunsPage />, '/runs')

    const selectedPanel = (await screen.findByRole('heading', { name: 'Selected run detail' })).closest('article') as HTMLElement
    expect(within(selectedPanel).getByText('Remembered run')).toBeInTheDocument()

    await userEvent.click(within(selectedPanel).getByRole('button', { name: 'Open / continue' }))

    await waitFor(() => expect(api.getRun).toHaveBeenCalledWith('run-3'))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-3')
    expect(navigateMock).toHaveBeenCalledWith('/runs/run-3')
  })

  it('supports has-children filter and renders no-match state', async () => {
    renderWithRoute(<RunsPage />, '/runs')

    await screen.findByRole('button', { name: 'Selected run-3' })
    await userEvent.selectOptions(screen.getByLabelText('Child runs'), 'with-children')

    const withChildrenButtons = screen.getAllByRole('button', { name: /run-/i })
    expect(withChildrenButtons).toHaveLength(1)
    expect(withChildrenButtons[0]).toHaveTextContent('run-3')

    await userEvent.type(screen.getByLabelText('Filter by season'), '9999')
    expect(screen.getByText('No runs match the current filters.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Selected run detail' })).not.toBeInTheDocument()
  })
})

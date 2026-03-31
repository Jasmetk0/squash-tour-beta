import { screen, waitFor } from '@testing-library/react'
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

const api = vi.hoisted(() => ({
  createRun: vi.fn(),
  getHealth: vi.fn(),
  getRun: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('DashboardPage', () => {
  beforeEach(() => {
    api.getHealth.mockResolvedValue({ status: 'ok' })
    api.createRun.mockResolvedValue({ run_id: 'run-a' })
    api.getRun.mockResolvedValue({ run: { run_id: 'run-a' } })
    navigateMock.mockReset()
  })

  it('creates a run and navigates to run detail', async () => {
    renderWithRoute(<DashboardPage />, '/')

    expect(screen.getByLabelText('Season')).toHaveValue(SUPPORTED_CALENDAR_SEASON)

    const runIdInput = screen.getAllByLabelText('Run ID')[0]
    await userEvent.clear(runIdInput)
    await userEvent.type(runIdInput, 'run-a')
    await userEvent.click(screen.getByRole('button', { name: 'Initialize Simulation Run' }))

    await waitFor(() =>
      expect(api.createRun).toHaveBeenCalledWith({
        run_id: 'run-a',
        seed: 42,
        season: SUPPORTED_CALENDAR_SEASON
      })
    )
    expect(navigateMock).toHaveBeenCalledWith('/runs/run-a')
  })
})

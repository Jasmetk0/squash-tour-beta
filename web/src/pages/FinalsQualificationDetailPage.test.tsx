import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { FinalsQualificationDetailPage } from './FinalsQualificationDetailPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getFinalsQualification: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('FinalsQualificationDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      qualification: { run_id: 'run-a' },
      result: null
    })
    api.getFinalsQualification.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      source_as_of_season: 2027,
      source_as_of_week: 42,
      qualification: { qualified_player_ids: ['P1', 'P2'], groups: [{ id: 'A' }] }
    })
  })

  it('renders qualification detail route with summary-first content', async () => {
    renderWithRoute(<FinalsQualificationDetailPage />, '/runs/run-a/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals qualification detail' })).toBeInTheDocument()
    expect(screen.getByText('Summary')).toBeInTheDocument()
    expect(await screen.findByText('As of week')).toBeInTheDocument()
    expect(screen.getByText('Qualified players')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Finals overview page' })).toHaveAttribute('href', '/runs/run-a/finals')
    expect(screen.getByText(/qualified_player_ids/i)).toBeInTheDocument()
  })

  it('shows readable empty state when qualification is missing', async () => {
    api.getFinalsQualification.mockRejectedValueOnce(new api.ApiError('{"detail":"No finals qualification for run"}', 404))
    renderWithRoute(<FinalsQualificationDetailPage />, '/runs/run-a/finals/qualification')

    expect(await screen.findByText('No Finals qualification is available for this run yet.')).toBeInTheDocument()
    expect(screen.getByText('No qualification payload is available yet.')).toBeInTheDocument()
  })
})

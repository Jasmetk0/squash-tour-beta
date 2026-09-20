import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearViewerStorage,
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
  setViewerActiveRunId,
} from '../../../test/viewerTestUtils'
import { ViewerNextGenPlayersPage } from './ViewerNextGenPlayersPage'

const api = vi.hoisted(() => ({
  getViewerVisibleProspects: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

function page(offset: number, names: string[], total = names.length) {
  return {
    schema_version: 'visible_pre_tour_prospects.v1' as const,
    run_id: 'product run',
    branch_id: 'viewer-branch',
    week: { season_index: 4, week: 10 },
    lifecycle_fingerprint: 'a'.repeat(64),
    total,
    limit: 50,
    offset,
    prospects: names.map((name, index) => ({
      player_id: `prospect-${offset + index + 1}`,
      display_name: name,
      short_name: null,
      country_code: index % 2 === 0 ? 'CZE' : 'EGY',
      country_name: index % 2 === 0 ? 'Czechia' : 'Egypt',
      age: 15,
      birth_year: 1989,
      birth_year_week: 46,
      lifecycle_status: 'active' as const,
      tour_status: 'pre_tour' as const,
      visible_since_week: { season_index: 4, week: 10 },
    })),
  }
}

describe('ViewerNextGenPlayersPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
  })

  it('does not query technical prospect storage without an active Product Run', () => {
    renderWithViewerProviders(<ViewerNextGenPlayersPage />)

    expect(
      screen.getByRole('heading', { level: 2, name: 'Prospects / Next Gen' })
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Select a Product Run before opening the historical prospect list/)
    ).toBeInTheDocument()
    expect(api.getViewerVisibleProspects).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders only canonical public pre-Tour prospect fields', async () => {
    setViewerActiveRunId('product run')
    api.getViewerVisibleProspects.mockResolvedValue(
      page(0, ['Jan Novak', 'Omar Hassan'], 2)
    )

    renderWithViewerProviders(<ViewerNextGenPlayersPage />)

    expect(await screen.findByText('Jan Novak')).toBeInTheDocument()
    expect(screen.getByText('Omar Hassan')).toBeInTheDocument()
    expect(screen.getAllByText(/2004\/05 · W10/).length).toBeGreaterThan(0)
    expect(screen.getByText(/1–2 of 2/)).toBeInTheDocument()
    expect(screen.getAllByText(/pre-Tour/).length).toBeGreaterThan(0)
    expect(api.getViewerVisibleProspects).toHaveBeenCalledWith('product run', {
      limit: 50,
      offset: 0,
    })

    expect(document.body).not.toHaveTextContent(/identity_seed|profile_seed|potential_seed|trait_seed/i)
    expect(document.body).not.toHaveTextContent(/profile_json|potential_json|development_json|trait_json/i)
    expect(document.body).not.toHaveTextContent(/cohort_policy_version|profile_version/i)
    expectNoForbiddenViewerActions()
  })

  it('pages the canonical read model instead of requesting the full prospect world', async () => {
    const user = userEvent.setup()
    setViewerActiveRunId('product run')
    api.getViewerVisibleProspects
      .mockResolvedValueOnce(page(0, ['First page prospect'], 51))
      .mockResolvedValueOnce(page(50, ['Final prospect'], 51))

    renderWithViewerProviders(<ViewerNextGenPlayersPage />)

    expect(await screen.findByText('First page prospect')).toBeInTheDocument()
    const next = screen.getByRole('button', { name: 'Next' })
    expect(next).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()

    await user.click(next)

    await waitFor(() =>
      expect(api.getViewerVisibleProspects).toHaveBeenLastCalledWith(
        'product run',
        { limit: 50, offset: 50 }
      )
    )
    expect(await screen.findByText('Final prospect')).toBeInTheDocument()
    expect(screen.getByText(/51–51 of 51/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeEnabled()
  })
})

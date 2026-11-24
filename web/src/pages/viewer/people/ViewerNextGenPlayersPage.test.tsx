import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearViewerStorage, expectNoForbiddenViewerActions,
  renderWithViewerProviders, setViewerActiveProductRunId,
} from '../../../test/viewerTestUtils'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerNextGenPlayersPage } from './ViewerNextGenPlayersPage'

const api = vi.hoisted(() => ({ getViewerVisibleProspects: vi.fn() }))
const chosen = vi.hoisted(() => ({
  run: 'product run', branch: 'viewer-branch',
  pending: false, fetching: false, error: false, refetch: vi.fn(),
  language: 'cs' as 'cs' | 'en',
}))
vi.mock('../../../api/client', () => api)
vi.mock('../../../i18n/LanguageContext', () => ({
  useLanguage: () => ({ language: chosen.language }),
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: () => ({
    data: { product_run_id: chosen.run, official_branch_id: chosen.branch },
    isPending: chosen.pending, isFetching: chosen.fetching,
    isError: chosen.error, refetch: chosen.refetch,
  }),
}))

function page(offset: number, names: string[], total = names.length, branchId = chosen.branch) {
  return {
    schema_version: 'visible_pre_tour_prospects.v1' as const,
    run_id: 'product run', branch_id: branchId,
    week: { season_index: 4, week: 10 },
    lifecycle_fingerprint: 'a'.repeat(64), total, limit: 50, offset,
    prospects: names.map((name, index) => ({
      player_id: 'prospect-' + (offset + index + 1),
      display_name: name, short_name: null,
      country_code: index % 2 === 0 ? 'CZE' : 'EGY',
      country_name: index % 2 === 0 ? 'Czechia' : 'Egypt',
      age: 15, birth_year: 1989, birth_year_week: 46,
      lifecycle_status: 'active' as const, tour_status: 'pre_tour' as const,
      visible_since_week: { season_index: 4, week: 10 },
    })),
  }
}

describe('ViewerNextGenPlayersPage public Saved source guard (mocked GET)', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    chosen.run = 'product run'
    chosen.branch = 'viewer-branch'
    chosen.pending = false
    chosen.fetching = false
    chosen.error = false
    chosen.language = 'cs'
    api.getViewerVisibleProspects.mockResolvedValue(page(0, ['Jan Novak'], 1))
  })

  it('does not query prospects without any active Product Run', () => {
    renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(api.getViewerVisibleProspects).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders only verified birth-week public fields from the saved Viewer Branch', async () => {
    setViewerActiveProductRunId('product run')
    api.getViewerVisibleProspects.mockResolvedValue(page(0, ['Jan Novak', 'Omar Hassan'], 2))
    renderWithViewerProviders(<ViewerNextGenPlayersPage />)

    expect(await screen.findByText('Jan Novak')).toBeInTheDocument()
    expect(screen.getByText('Omar Hassan')).toBeInTheDocument()
    expect(screen.getAllByText(/2004\/05 · W10/).length).toBeGreaterThan(0)
    expect(screen.getByText(/1–2 z 2/)).toBeInTheDocument()
    expect(api.getViewerVisibleProspects).toHaveBeenCalledWith('product run', {
      limit: 50, offset: 0,
    })
    expect(document.body).not.toHaveTextContent(/identity_seed|profile_seed|potential_seed|trait_seed/i)
    expect(document.body).not.toHaveTextContent(/profile_json|potential_json|development_json|trait_json/i)
    expectNoForbiddenViewerActions()
  })

  it('paginates a full canonical page of 50 and never loads the entire world', async () => {
    const user = userEvent.setup()
    setViewerActiveProductRunId('product run')
    const first = ['First page prospect', ...Array.from({ length: 49 }, (_, i) => 'Prospect ' + i)]
    api.getViewerVisibleProspects.mockResolvedValueOnce(page(0, first, 51))
      .mockResolvedValueOnce(page(50, ['Final prospect'], 51))
    renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    expect(await screen.findByText('First page prospect')).toBeInTheDocument()
    const next = screen.getByRole('button', { name: 'Další' })
    expect(next).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Předchozí' })).toBeDisabled()
    await user.click(next)
    await waitFor(() => expect(api.getViewerVisibleProspects)
      .toHaveBeenLastCalledWith('product run', { limit: 50, offset: 50 }))
    expect(await screen.findByText('Final prospect')).toBeInTheDocument()
    expect(screen.getByText(/51–51 z 51/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Další' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Předchozí' })).toBeEnabled()
  })

  it.each([0, 2])('recovers an out-of-range page after the visible cohort shrinks to %i', async total => {
    const user = userEvent.setup()
    setViewerActiveProductRunId('product run')
    const first = Array.from({ length: 50 }, (_, i) => 'Old prospect ' + i)
    const newNames = Array.from({ length: total }, (_, i) => 'New prospect ' + i)
    api.getViewerVisibleProspects.mockReset()
      .mockResolvedValueOnce(page(0, first, 51))
      .mockResolvedValueOnce(page(50, [], total))
      .mockResolvedValueOnce(page(0, newNames, total))
    renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    expect(await screen.findByText('Old prospect 0')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(await screen.findByText('Tato stránka už neobsahuje žádné hráče.')).toBeInTheDocument()
    expect(screen.queryByText(/0–50 z/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Další' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Přejít na první stránku' }))
    await waitFor(() => expect(api.getViewerVisibleProspects)
      .toHaveBeenLastCalledWith('product run', { limit: 50, offset: 0 }))
    if (total === 0) {
      expect(await screen.findByText('V tomto uloženém týdnu nejsou viditelní žádní hráči před vstupem na Tour.')).toBeInTheDocument()
    } else {
      expect(await screen.findByText('New prospect 0')).toBeInTheDocument()
      expect(screen.getByText('1–2 z 2')).toBeInTheDocument()
    }
    expect(screen.queryByText('Old prospect 0')).not.toBeInTheDocument()
    expect(api.getViewerVisibleProspects).toHaveBeenCalledTimes(3)
  })

  it('does not fetch any prospect page when the official context belongs to another Run', async () => {
    const user = userEvent.setup()
    setViewerActiveProductRunId('product run')
    chosen.run = 'foreign-run'
    renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    expect(screen.getByRole('alert')).toHaveTextContent('nelze ověřit')
    expect(api.getViewerVisibleProspects).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(chosen.refetch).toHaveBeenCalledTimes(1)
    expect(api.getViewerVisibleProspects).not.toHaveBeenCalled()
  })

  it('rejects foreign Branch and private fields until a fresh public GET', async () => {
    const user = userEvent.setup()
    setViewerActiveProductRunId('product run')
    const safe = page(0, ['Jan Novak'], 1)
    api.getViewerVisibleProspects.mockReset()
      .mockResolvedValueOnce(page(0, ['Foreign player'], 1, 'foreign-branch'))
      .mockResolvedValueOnce({
        ...safe, prospects: [{ ...safe.prospects[0], potential_seed: 'private' }],
      })
      .mockResolvedValueOnce(safe)
    renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    for (let i = 0; i < 2; i++) {
      expect(await screen.findByRole('alert')).toHaveTextContent('neplatný veřejný zdroj')
      expect(screen.queryByText('Foreign player')).not.toBeInTheDocument()
      expect(screen.queryByText('Jan Novak')).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    }
    expect(await screen.findByText('Jan Novak')).toBeInTheDocument()
    expect(api.getViewerVisibleProspects).toHaveBeenCalledTimes(3)
  })

  it('distinguishes a genuine empty public cohort from GET failure', async () => {
    setViewerActiveProductRunId('product run')
    api.getViewerVisibleProspects.mockResolvedValueOnce(page(0, [], 0))
    const view = renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    expect(await screen.findByText('V tomto uloženém týdnu nejsou viditelní žádní hráči před vstupem na Tour.'))
      .toBeInTheDocument()
    view.unmount()
    api.getViewerVisibleProspects.mockReset().mockRejectedValue(new Error('offline'))
    renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('momentálně není dostupný')
    expect(screen.queryByText('Jan Novak')).not.toBeInTheDocument()
  })

  it('does not display a delayed old-Branch result after switching Viewer Branch', async () => {
    setViewerActiveProductRunId('product run')
    let resolveOld!: (value: ReturnType<typeof page>) => void
    api.getViewerVisibleProspects.mockReset().mockImplementationOnce(() =>
      new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce(page(0, ['New Branch player'], 1, 'branch-b'))
    const view = renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    await waitFor(() => expect(api.getViewerVisibleProspects).toHaveBeenCalledTimes(1))
    chosen.branch = 'branch-b'
    view.rerender(<ViewerContextProvider><ViewerNextGenPlayersPage /></ViewerContextProvider>)
    expect(await screen.findByText('New Branch player')).toBeInTheDocument()
    await act(async () => { resolveOld(page(0, ['Old Branch player'], 1, 'viewer-branch')) })
    expect(screen.getByText('branch-b')).toBeInTheDocument()
    expect(screen.queryByText('Old Branch player')).not.toBeInTheDocument()
    expect(api.getViewerVisibleProspects).toHaveBeenCalledTimes(2)
  })

  it('switches English copy without changing public identities or triggering more GETs', async () => {
    setViewerActiveProductRunId('product run')
    const view = renderWithViewerProviders(<ViewerNextGenPlayersPage />)
    expect(await screen.findByText('Jan Novak')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Mladé talenty / Next Gen' })).toBeInTheDocument()
    chosen.language = 'en'
    view.rerender(<ViewerContextProvider><ViewerNextGenPlayersPage /></ViewerContextProvider>)
    expect(screen.getByRole('heading', { name: 'Prospects / Next Gen' })).toBeInTheDocument()
    expect(screen.getByText(/1–1 of 1/)).toBeInTheDocument()
    expect(screen.getByText('Jan Novak')).toBeInTheDocument()
    expect(api.getViewerVisibleProspects).toHaveBeenCalledTimes(1)
  })
})

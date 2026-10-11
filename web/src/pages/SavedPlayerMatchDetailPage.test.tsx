import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedPlayerMatchDetailPage } from './SavedPlayerMatchDetailPage'
import { LanguageProvider } from '../i18n/LanguageContext'

const api = vi.hoisted(() => ({
  getSavedPlayerMatchDetail: vi.fn(), getSavedHomePlayerIdentities: vi.fn(),
}))
vi.mock('../api/client', () => api)
vi.mock('../admin/AdminBranchContext', () => ({
  useAdminBranch: () => ({ selectedBranch: {
    run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'rev'
  }, isLoading: false, error: null }),
}))
vi.mock('../admin/AdminTimeContext', () => ({ useAdminTime: () => ({ mode: 'present' }) }))

function mount() {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={cache}><LanguageProvider><MemoryRouter
    initialEntries={['/admin/runs/run/people/A/matches/event/final']}>
    <Routes><Route path="/admin/runs/:runId/people/:playerId/matches/:eventId/:matchId"
      element={<SavedPlayerMatchDetailPage />} /></Routes>
  </MemoryRouter></LanguageProvider></QueryClientProvider>)
}

function result(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: 'saved_player_match_detail.v1', run_id: 'run',
    branch_id: 'branch', saved_revision_id: 'rev', player_id: 'A',
    source: 'selected_branch_saved_revision',
    match: { event_id: 'event', match_id: 'final', event_name: 'Championship',
      season: '2002/03', week: 17, draw_type: 'main', round_number: 2,
      completion: 'played', scoreline: '3-2', opponent_player_id: 'B', outcome: 'win' },
    winner_player_id: 'A', loser_player_id: 'B',
    player_a_id: 'A', player_b_id: 'B', replay_status: 'available',
    offset: 0, limit: 25, total_rallies: 2, has_more: false,
    rallies: [1, 2].map(i => ({
      rally_index: i, set_number: 1, server_player_id: 'A',
      winner_player_id: 'A', score_a_before: i - 1,
      score_b_before: 0, score_a_after: i, score_b_after: 0,
      sets_a_after: 0, sets_b_after: 0, set_complete: false, match_complete: false,
    })), ...overrides,
  }
}

describe('canonical saved match detail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSavedPlayerMatchDetail.mockResolvedValue(result())
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r: string, _b: string, ids: string[]) => ({
      run_id: 'run', branch_id: 'branch', saved_revision_id: 'rev',
      requested_ids: ids, players: ids.map(id => ({ player_id: id, display_name: id === 'A' ? 'Alpha' : 'Bravo' })),
    }))
  })
  it('steps through archived score frames without simulating', async () => {
    mount()
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    expect(await screen.findByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText(/1\/2/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Další výměna →' }))
    await waitFor(() => expect(screen.getByText(/2\/2/)).toBeInTheDocument())
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledTimes(1)
  })
  it('does not invent a replay when archive missing', async () => {
    api.getSavedPlayerMatchDetail.mockResolvedValueOnce(result({
      replay_status: 'unavailable', player_a_id: null, player_b_id: null,
      total_rallies: 0, rallies: [],
    }))
    mount()
    expect(await screen.findByText(/Ověřený archiv výměn není/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další výměna →' })).not.toBeInTheDocument()
  })
  it('hides a stale saved HEAD rather than exposing a foreign match', async () => {
    api.getSavedPlayerMatchDetail.mockResolvedValueOnce(result({ saved_revision_id: 'foreign' }))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Detail neodpovídá vybrané uložené revizi.')
    expect(screen.queryByText('Championship')).not.toBeInTheDocument()
  })
})

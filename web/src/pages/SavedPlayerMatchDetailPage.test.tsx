import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedPlayerMatchDetailPage } from './SavedPlayerMatchDetailPage'
import { LanguageProvider } from '../i18n/LanguageContext'

const api = vi.hoisted(() => ({
  getSavedPlayerMatchDetail: vi.fn(), getSavedHomePlayerIdentities: vi.fn(),
}))
vi.mock('../api/client', () => api)
const branchContext = vi.hoisted(() => ({
  current: { run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'rev' }
}))
vi.mock('../admin/AdminBranchContext', () => ({
  useAdminBranch: () => ({ selectedBranch: branchContext.current, isLoading: false, error: null }),
}))
vi.mock('../admin/AdminTimeContext', () => ({ useAdminTime: () => ({ mode: 'present' }) }))

function mount() {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const tree = () => <QueryClientProvider client={cache}><LanguageProvider><MemoryRouter
    initialEntries={['/admin/runs/run/people/A/matches/event/final']}>
    <nav aria-label="Replay scope test navigation">
      <Link to="/admin/runs/run/people/A/matches/event/short">Switch match</Link>
      <Link to="/admin/runs/run/people/A/matches/second/final">Switch event</Link>
      <Link to="/admin/runs/run/people/B/matches/event/final">Switch player</Link>
      <Link to="/admin/runs/other-run/people/A/matches/event/final">Switch Run</Link>
    </nav>
    <Routes><Route path="/admin/runs/:runId/people/:playerId/matches/:eventId/:matchId"
      element={<SavedPlayerMatchDetailPage />} /></Routes>
  </MemoryRouter></LanguageProvider></QueryClientProvider>
  const rendered = render(tree())
  return { ...rendered, refreshBranch: () => rendered.rerender(tree()) }
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
    branchContext.current = { run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'rev' }
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


function useLongMatchFixture(): void {
  api.getSavedPlayerMatchDetail.mockImplementation(async (
    runId: string, branchId: string, playerId: string,
    eventId: string, matchId: string, offset: number, limit: number
  ) => {
    const total = runId !== 'run' || branchId !== 'branch' ||
      branchContext.current.saved_head_revision_id !== 'rev' ||
      matchId === 'short' || eventId === 'second' || playerId === 'B' ? 2 : 30
    const original = result()
    return result({
      run_id: runId, branch_id: branchId,
      saved_revision_id: branchContext.current.saved_head_revision_id,
      player_id: playerId, offset, limit, total_rallies: total,
      has_more: offset + limit < total,
      match: { ...original.match, event_id: eventId, match_id: matchId },
      rallies: Array.from({ length: Math.max(0, Math.min(limit, total - offset)) }, (_, i) => {
        const index = offset + i + 1
        return {
          rally_index: index, set_number: 1, server_player_id: playerId,
          winner_player_id: playerId, score_a_before: index - 1,
          score_b_before: 0, score_a_after: index, score_b_after: 0,
          sets_a_after: 0, sets_b_after: 0, set_complete: false, match_complete: false
        }
      })
    })
  })
  api.getSavedHomePlayerIdentities.mockImplementation(async (
    runId: string, branchId: string, ids: string[]
  ) => ({
    run_id: runId, branch_id: branchId,
    saved_revision_id: branchContext.current.saved_head_revision_id,
    requested_ids: ids, players: ids.map(id => ({ player_id: id, display_name: id }))
  }))
}
async function seekSecondPage(): Promise<void> {
  expect(await screen.findByText(/1\/30/)).toBeInTheDocument()
  for (let i = 0; i < 25; i++) {
    fireEvent.click(screen.getByRole('button', { name: 'Další výměna →' }))
  }
  await waitFor(() => expect(screen.getByText(/26\/30/)).toBeInTheDocument())
  expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith(
    'run', 'branch', 'A', 'event', 'final', 25, 25
  )
}

describe('replay identity cursor isolation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    branchContext.current = { run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'rev' }
    useLongMatchFixture()
  })

  it.each([
    ['Switch match', 'run', 'branch', 'A', 'event', 'short'],
    ['Switch event', 'run', 'branch', 'A', 'second', 'final'],
    ['Switch player', 'run', 'branch', 'B', 'event', 'final'],
  ])('resets a page-2 cursor on %s with no stale page-2 request', async (
    link, runId, branchId, playerId, eventId, matchId
  ) => {
    mount()
    await seekSecondPage()
    fireEvent.click(screen.getByRole('link', { name: link }))
    await waitFor(() => expect(screen.getByText(/1\/2/)).toBeInTheDocument())
    expect(screen.queryByText(/V tomto úseku není výměna/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '← Předchozí výměna' })).toBeDisabled()
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith(
      runId, branchId, playerId, eventId, matchId, 0, 25
    )
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalledWith(
      runId, branchId, playerId, eventId, matchId, 25, 25
    )
  })

  it('resets at first render when a new Run is selected, not after the old offset is fetched', async () => {
    mount()
    await seekSecondPage()
    branchContext.current = { run_id: 'other-run', branch_id: 'other-branch', saved_head_revision_id: 'other-rev' }
    fireEvent.click(screen.getByRole('link', { name: 'Switch Run' }))
    await waitFor(() => expect(screen.getByText(/1\/2/)).toBeInTheDocument())
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith(
      'other-run', 'other-branch', 'A', 'event', 'final', 0, 25
    )
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalledWith(
      'other-run', 'other-branch', 'A', 'event', 'final', 25, 25
    )
  })

  it.each([
    ['Branch', 'branch-next', 'rev-next'],
    ['Saved Revision', 'branch', 'rev-next'],
  ])('remounts and begins at first rally when %s changes without navigating', async (
    _label, nextBranch, nextHead
  ) => {
    const view = mount()
    await seekSecondPage()
    branchContext.current = { run_id: 'run', branch_id: nextBranch, saved_head_revision_id: nextHead }
    await act(async () => { view.refreshBranch() })
    await waitFor(() => expect(screen.getByText(/1\/2/)).toBeInTheDocument())
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith(
      'run', nextBranch, 'A', 'event', 'final', 0, 25
    )
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalledWith(
      'run', nextBranch, 'A', 'event', 'final', 25, 25
    )
    expect(screen.getByRole('button', { name: '← Předchozí výměna' })).toBeDisabled()
  })
})

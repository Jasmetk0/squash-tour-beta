import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { RankingCandidateHistory } from '../api/rankingCandidates'
import { MemoryRouter, Route, Routes, Link } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { getRankingCandidates } from '../api/client'
import { AdminRankingCandidatesPage } from './AdminRankingCandidatesPage'
vi.mock('../api/client', async (importOriginal) => ({ ...await importOriginal<typeof import('../api/client')>(), getRankingCandidates: vi.fn() }))
const fetchHistory = vi.mocked(getRankingCandidates)
function show(suffix = '') {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/admin/runs/run/branches/branch/ranking-candidates' + suffix]}><Link to="/admin/runs/run/branches/other/ranking-candidates/0/2">Other Branch</Link><Routes><Route path="/admin/runs/:runId/branches/:branchId/ranking-candidates" element={<AdminRankingCandidatesPage />} /><Route path="/admin/runs/:runId/branches/:branchId/ranking-candidates/:seasonIndex/:week" element={<AdminRankingCandidatesPage />} /></Routes></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  vi.resetAllMocks()
  fetchHistory.mockResolvedValue({ run_id: 'run', branch_id: 'branch', publication_status: 'candidate_only', candidates: [] })
})
it('shows an empty scoped history', async () => {
  show()
  expect(await screen.findByText('No ranking candidates have been prepared for this Branch.')).toBeInTheDocument()
  expect(fetchHistory).toHaveBeenCalledWith('run', 'branch')
})
it('does not substitute a missing week', async () => {
  show('/0/2')
  expect(await screen.findByRole('alert')).toHaveTextContent('No candidate is stored for this week.')
})
it('rejects invalid coordinates without fetching', () => {
  show('/50/62')
  expect(screen.getByRole('alert')).toHaveTextContent('Invalid season or week.')
  expect(fetchHistory).not.toHaveBeenCalled()
})

const populated: RankingCandidateHistory = {
  run_id: 'run', branch_id: 'branch', publication_status: 'candidate_only', candidates: [{
    publication_status: 'candidate_only', fingerprint: 'hash', command_ids: ['command-1'],
    snapshot: { run_id: 'run', branch_id: 'branch', week: { season_index: 0, week: 2 }, policy: { policy_id: 'policy-1', best_n: 15 }, rows: [{ rank: 1, player_id: 'player-a', points: 120, counted_results: [{ edition_id: 'edition-1', qualification_points: 20, main_points: 100, completed_week: { season_index: 0, week: 1 }, first_publication_week: { season_index: 0, week: 2 }, validity_weeks: 61 }] }] },
  }],
}
it('opens a week, counted awards and provenance through read-only controls', async () => {
  fetchHistory.mockResolvedValue(populated)
  show()
  await userEvent.click(await screen.findByRole('link', { name: '2000/01 · Week 2' }))
  expect(await screen.findByText('player-a')).toBeInTheDocument()
  expect(screen.getByText('120')).toBeInTheDocument()
  await userEvent.click(screen.getByText('1 counted results for player-a'))
  expect(screen.getByText('edition-1')).toBeVisible()
  expect(screen.getByText(/20 qualification \+ 100 main/)).toBeVisible()
  await userEvent.click(screen.getByText('Technical provenance'))
  expect(screen.getByText('Commands: command-1')).toBeVisible()
  expect(screen.queryByRole('button', { name: /publish|save|simulate/i })).not.toBeInTheDocument()
})
it('hides the previous branch while the next scope loads', async () => {
  fetchHistory.mockResolvedValueOnce(populated)
  show('/0/2')
  expect(await screen.findByText('player-a')).toBeInTheDocument()
  fetchHistory.mockImplementation(() => new Promise(() => {}))
  await userEvent.click(screen.getByRole('link', { name: 'Other Branch' }))
  expect(screen.getByRole('status')).toHaveTextContent('Loading ranking history')
  expect(screen.queryByText('player-a')).not.toBeInTheDocument()
  expect(fetchHistory).toHaveBeenLastCalledWith('run', 'other')
})
it('reports load failures and retries successfully', async () => {
  fetchHistory.mockRejectedValueOnce(new Error('History unavailable'))
  show()
  expect(await screen.findByRole('alert')).toHaveTextContent('History unavailable')
  await userEvent.click(screen.getByRole('button', { name: 'Retry loading' }))
  expect(await screen.findByText('No ranking candidates have been prepared for this Branch.')).toBeInTheDocument()
})
it('does not show another stored week instead of the requested week', async () => {
  fetchHistory.mockResolvedValue(populated)
  show('/0/3')
  expect(await screen.findByRole('alert')).toHaveTextContent('No candidate is stored for this week.')
  expect(screen.queryByText('player-a')).not.toBeInTheDocument()
})

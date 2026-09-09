import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { getRankingCandidates } from '../api/client'
import { AdminRankingCandidatesPage } from './AdminRankingCandidatesPage'
vi.mock('../api/client', () => ({ getRankingCandidates: vi.fn() }))
const fetchHistory = vi.mocked(getRankingCandidates)
function show(suffix = '') {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/admin/runs/run/branches/branch/ranking-candidates' + suffix]}><Routes><Route path="/admin/runs/:runId/branches/:branchId/ranking-candidates" element={<AdminRankingCandidatesPage />} /><Route path="/admin/runs/:runId/branches/:branchId/ranking-candidates/:seasonIndex/:week" element={<AdminRankingCandidatesPage />} /></Routes></MemoryRouter></QueryClientProvider>)
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

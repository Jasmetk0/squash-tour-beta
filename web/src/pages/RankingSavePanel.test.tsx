import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { previewRankingSave, saveRankingPreparation } from '../api/client'
import { RankingSavePanel } from './RankingSavePanel'
vi.mock('../api/client', async (importOriginal) => ({ ...await importOriginal<typeof import('../api/client')>(), previewRankingSave: vi.fn(), saveRankingPreparation: vi.fn() }))
const preview = { run_id: 'run', branch_id: 'branch', ranking_fingerprint: 'a'.repeat(64), saved_head_revision_id: 'revision', draft_version: 3, has_unsaved_changes: true, can_save: true }
function show() { render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><RankingSavePanel runId="run" branchId="branch" /></QueryClientProvider>) }
beforeEach(() => { vi.resetAllMocks(); vi.mocked(previewRankingSave).mockResolvedValue(preview); vi.mocked(saveRankingPreparation).mockResolvedValue({}) })
it('requires review then explicit save of the reviewed fingerprint', async () => {
  show()
  expect(previewRankingSave).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Review ranking changes' }))
  await screen.findByText('Ranking changes are ready to save.')
  expect(saveRankingPreparation).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Save ranking preparation' }))
  await screen.findByText('Ranking preparation saved.')
  expect(saveRankingPreparation).toHaveBeenCalledWith('run', 'branch', preview)
})
it('does not enable save when unavailable', async () => {
  vi.mocked(previewRankingSave).mockResolvedValue({...preview, can_save:false})
  show(); await userEvent.click(screen.getByRole('button', { name: 'Review ranking changes' }))
  expect(await screen.findByRole('button', { name:'Save ranking preparation' })).toBeDisabled()
})
it('refreshes after conflict without retrying the mutation', async () => {
  vi.mocked(saveRankingPreparation).mockRejectedValue(new Error('Ranking changed'))
  show(); await userEvent.click(screen.getByRole('button', { name:'Review ranking changes' }))
  await userEvent.click(await screen.findByRole('button', { name:'Save ranking preparation' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Ranking changed')
  await waitFor(() => expect(previewRankingSave).toHaveBeenCalledTimes(2))
  expect(saveRankingPreparation).toHaveBeenCalledTimes(1)
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { NativeProspectSourceEpochPanel } from './NativeProspectSourceEpochPanel'

const api = vi.hoisted(() => ({
  previewRunProspectSourceSave: vi.fn(), saveRunProspectSource: vi.fn(),
  previewFutureNativeProspects: vi.fn(), materializeFutureNativeProspects: vi.fn(),
}))
vi.mock('../api/client', () => api)
vi.mock('../api/nativeFutureProspects', () => api)
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

function panel(branchId = 'branch', head = 'head') {
  return <QueryClientProvider client={new QueryClient()}>
    <NativeProspectSourceEpochPanel runId="run" branchId={branchId} head={head}/>
  </QueryClientProvider>
}
const review = () => ({ run_id: 'run', branch_id: 'branch',
  saved_head_revision_id: 'head', draft_version: 3,
  run_prospect_source_fingerprint: 'a'.repeat(64), prospect_count: 12,
  can_save: true, has_unsaved_changes: true, blockers: [] })

beforeEach(() => { vi.resetAllMocks() })

it('recovers materialized shared records after reload through review and explicit separate Save', async () => {
  api.previewRunProspectSourceSave.mockResolvedValue(review())
  api.saveRunProspectSource.mockResolvedValue({ saved_revision: {
    revision_id: 'next-head', content_hash: 'b'.repeat(64),
  } })
  render(panel())
  // No browser-local materialized flag survives a reload or a lost response.
  expect(api.previewRunProspectSourceSave).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '3. Review source-epoch Save' }))
  await screen.findByLabelText('Reviewed prospect source Save')
  expect(screen.getByRole('button', { name: '4. Save immutable source epoch' })).toBeDisabled()
  expect(api.saveRunProspectSource).not.toHaveBeenCalled()
  fireEvent.click(screen.getByLabelText('I explicitly confirm the separate manual Save.'))
  fireEvent.click(screen.getByRole('button', { name: '4. Save immutable source epoch' }))
  await screen.findByRole('status')
  expect(api.saveRunProspectSource).toHaveBeenCalledTimes(1)
  expect(api.saveRunProspectSource).toHaveBeenCalledWith('run', 'branch', {
    expected_draft_version: 3, expected_saved_head_revision_id: 'head',
    expected_run_prospect_source_fingerprint: 'a'.repeat(64),
  })
  expect(api.materializeFutureNativeProspects).not.toHaveBeenCalled()
})

it('discards a delayed recovery review after changing Branch and Saved HEAD', async () => {
  let finish!: (value: ReturnType<typeof review>) => void
  api.previewRunProspectSourceSave.mockReturnValue(new Promise(resolve => { finish = resolve }))
  const mounted = render(panel())
  fireEvent.click(screen.getByRole('button', { name: '3. Review source-epoch Save' }))
  mounted.rerender(panel('other', 'other-head'))
  await act(async () => { finish(review()) })
  expect(screen.queryByLabelText('Reviewed prospect source Save')).not.toBeInTheDocument()
  expect(api.saveRunProspectSource).not.toHaveBeenCalled()
})

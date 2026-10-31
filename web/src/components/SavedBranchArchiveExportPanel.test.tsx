/** Mocked component tests; these do not stand in for a real browser/SQLite export. */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { RunBranch, RunContainer } from '../api/types'
import type { SavedBranchArchivePreview } from '../api/runBranchArchiveExport'
import { LanguageProvider, useLanguage } from '../i18n/LanguageContext'
import { SavedBranchArchiveExportPanel } from './SavedBranchArchiveExportPanel'

const mocks = vi.hoisted(() => ({
  getRunContainer: vi.fn(),
  listRunBranches: vi.fn(),
  getBranchWorkingDraft: vi.fn(),
  previewSavedBranchArchive: vi.fn(),
  downloadSavedBranchArchive: vi.fn()
}))
vi.mock('../api/client', () => ({
  ApiError: class ApiError extends Error { constructor(message: string, public status = 409) { super(message) } },
  getRunContainer: mocks.getRunContainer,
  listRunBranches: mocks.listRunBranches,
  getBranchWorkingDraft: mocks.getBranchWorkingDraft
}))
vi.mock('../api/runBranchArchiveExport', () => ({
  previewSavedBranchArchive: mocks.previewSavedBranchArchive,
  downloadSavedBranchArchive: mocks.downloadSavedBranchArchive
}))
const run = {
  run_id: 'r', display_name: 'Run', storage_kind: 'custom_local', status: 'active', read_only: false
} as RunContainer
const branch = {
  run_id: 'r', branch_id: 'b', display_name: 'Branch A', status: 'active', read_only: false,
  saved_head_revision_id: 'head'
} as RunBranch
const archive = {
  schema_version: 'run_branch_archive_preview.v1', run_id: 'r',
  selected_branch_id: 'b', selected_head_revision_id: 'head',
  run_activation_revision_id: 'head',
  archive_digest: 'a'.repeat(64), archive_size_bytes: 1024,
  scope: 'custom_selected_saved_branch_with_dependency_history',
  format: 'run_branch_archive.v1', minimum_engine: 'engine', display_name: 'Run',
  viewer_branch_id: 'b', audit_event_count: 2, checkpoint_count: 1,
  branches: [
    { branch_id: 'b', display_name: 'Branch A', role: 'selected',
      forked_from_branch_id: null, forked_from_saved_revision_id: null, saved_head_revision_id: 'head' },
    { branch_id: 'dep', display_name: 'Source', role: 'dependency',
      forked_from_branch_id: 'b', forked_from_saved_revision_id: 'previous', saved_head_revision_id: 'previous' }
  ],
  history: [
    {revision_id: 'previous', original_owner_branch_id: 'dep', sequence: 1,
      parent_revision_id: null, content_hash_algorithm: 'sha256',
      content_hash: 'a'.repeat(64), payload_schema_version: 'run_saved_revision_v1'},
    {revision_id: 'head', original_owner_branch_id: 'b', sequence: 2,
      parent_revision_id: 'previous', content_hash_algorithm: 'sha256',
      content_hash: 'b'.repeat(64), payload_schema_version: 'run_saved_revision_v1'}
  ],
  omitted_branch_ids: ['other'], omitted_areas: ['working_drafts'],
  unresolved_package_references: [{revision_id: 'head', reference: {source_package_id: 'missing-package'}}],
  included_components: ['run_package_state'], selected_head_components: ['run_package_state'],
  continuation: 'Use existing operation-scoped preview'
} as SavedBranchArchivePreview

function Toggle(): JSX.Element {
  const { setLanguage, language } = useLanguage()
  return <button onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function mount(props: {run?: RunContainer; branch?: RunBranch | null} = {}) {
  return render(<MemoryRouter><LanguageProvider><Toggle />
    <SavedBranchArchiveExportPanel run={props.run ?? run} branch={props.branch === undefined ? branch : props.branch} />
  </LanguageProvider></MemoryRouter>)
}
describe('Saved Branch archive Admin export panel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mocks.getRunContainer.mockResolvedValue(run)
    mocks.listRunBranches.mockResolvedValue({run_branches: [branch]})
    mocks.getBranchWorkingDraft.mockResolvedValue({
      run_id: 'r', branch_id: 'b', base_saved_revision_id: 'head',
      status: 'clean', change_count: 0
    })
    mocks.previewSavedBranchArchive.mockResolvedValue(archive)
    mocks.downloadSavedBranchArchive.mockResolvedValue(new Blob(['file']))
  })
  afterEach(() => vi.restoreAllMocks())

  it('does not preview or Save on mount, and retains the reviewed export after CS/EN toggle', async () => {
    mount()
    expect(mocks.previewSavedBranchArchive).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', {name: /Stáhnout/})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByText('Source')).toBeInTheDocument()
    expect(screen.getByText(/missing-package/)).toBeInTheDocument()
    expect(screen.getByText(/Počet revizí/)).toBeInTheDocument()
    expect(screen.getByText(/Aktivační revize Runu/)).toBeInTheDocument()
    expect(screen.getByText(/working_drafts/)).toBeInTheDocument()
    expect(screen.getByText('Zahrnuté Saved komponenty (1)')).toBeInTheDocument()
    expect(screen.getByText('Komponenty vybraného HEAD (1)')).toBeInTheDocument()
    expect(screen.getByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    fireEvent.click(screen.getByRole('button', {name: 'Switch language'}))
    expect(screen.getByRole('button', {name: 'Download verified .sqbranch file'})).toBeEnabled()
    expect(mocks.previewSavedBranchArchive).toHaveBeenCalledTimes(1)
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
  })

  it('paginates a long Saved history without mounting all revisions and retains page across language toggle', async () => {
    const history = Array.from({length: 205}, (_, index) => ({
      ...archive.history[0], revision_id: 'revision-' + (index + 1), sequence: index + 1
    }))
    mocks.previewSavedBranchArchive.mockResolvedValueOnce({...archive, history})
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    expect(screen.getByText('Zobrazené revize: 1–100 / 205')).toBeInTheDocument()
    expect(screen.queryByText('revision-101')).not.toBeInTheDocument()
    expect(screen.queryByText('revision-205')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', {name: 'Další revize', hidden: true}))
    expect(screen.getByText('Zobrazené revize: 101–200 / 205')).toBeInTheDocument()
    expect(screen.getByText('revision-101')).toBeInTheDocument()
    expect(screen.queryByText('revision-1')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', {name: 'Další revize', hidden: true}))
    expect(screen.getByText('Zobrazené revize: 201–205 / 205')).toBeInTheDocument()
    expect(screen.getByText('revision-205')).toBeInTheDocument()
    expect(screen.getByRole('button', {name: 'Další revize', hidden: true})).toBeDisabled()
    fireEvent.click(screen.getByRole('button', {name: 'Switch language'}))
    expect(screen.getByText('Showing revisions: 201–205 / 205')).toBeInTheDocument()
    expect(screen.getByText('revision-205')).toBeInTheDocument()
    expect(mocks.previewSavedBranchArchive).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', {name: 'Reload preview'}))
    await waitFor(() => expect(screen.getByText('Showing revisions: 1–2 / 2')).toBeInTheDocument())
    expect(mocks.previewSavedBranchArchive).toHaveBeenCalledTimes(2)
  })

  it('blocks stale HEAD before preview and does not call the export endpoint', async () => {
    mocks.listRunBranches.mockResolvedValueOnce({run_branches: [{...branch, saved_head_revision_id: 'new-head'}]})
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('HEAD')
    expect(mocks.previewSavedBranchArchive).not.toHaveBeenCalled()
  })

  it('offers manual Save navigation when the Viewer draft is dirty; never saves implicitly', async () => {
    mocks.getBranchWorkingDraft.mockResolvedValueOnce({
      run_id: 'r', branch_id: 'b', base_saved_revision_id: 'head',
      status: 'dirty', change_count: 1
    })
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Neuložené změny')
    expect(screen.getByRole('link', {name: /ruční Save/})).toHaveAttribute('href', '/admin/runs/r')
    expect(mocks.previewSavedBranchArchive).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', {name: 'Zrušit export'}))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('invalidates reviewed bytes after an independent selected HEAD change', async () => {
    const view = mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    view.rerender(<MemoryRouter><LanguageProvider><Toggle />
      <SavedBranchArchiveExportPanel run={run} branch={{...branch, saved_head_revision_id: 'new-head'}} />
    </LanguageProvider></MemoryRouter>)
    await waitFor(() => expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument())
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
  })

  it('invalidates reviewed consent when a Run becomes read-only without changing its HEAD', async () => {
    const view = mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    view.rerender(<MemoryRouter><LanguageProvider><Toggle />
      <SavedBranchArchiveExportPanel run={{...run, read_only: true}} branch={branch} />
    </LanguageProvider></MemoryRouter>)
    await waitFor(() => expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument())
    expect(screen.getByRole('button', {name: 'Načíst exportní náhled'})).toBeDisabled()
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
  })

  it('aborts verified bytes when the selected Branch becomes read-only mid-download', async () => {
    let complete!: (result: Blob) => void
    mocks.downloadSavedBranchArchive.mockImplementationOnce(() =>
      new Promise<Blob>(resolve => { complete = resolve }))
    const objectUrl = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', {configurable: true, value: objectUrl})
    const view = mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    fireEvent.click(await screen.findByRole('button', {name: /Stáhnout ověřený/}))
    await waitFor(() => expect(mocks.downloadSavedBranchArchive).toHaveBeenCalledTimes(1))
    const signal = mocks.downloadSavedBranchArchive.mock.calls[0][1] as AbortSignal
    expect(signal.aborted).toBe(false)
    view.rerender(<MemoryRouter><LanguageProvider><Toggle />
      <SavedBranchArchiveExportPanel run={run} branch={{...branch, read_only: true}} />
    </LanguageProvider></MemoryRouter>)
    await waitFor(() => expect(signal.aborted).toBe(true))
    await act(async () => complete(new Blob(['stale bytes'])))
    expect(objectUrl).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument()
  })

  it('invalidates reviewed export when the selected Branch is renamed without a new HEAD', async () => {
    const view = mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    view.rerender(<MemoryRouter><LanguageProvider><Toggle />
      <SavedBranchArchiveExportPanel run={run} branch={{...branch, display_name: 'Renamed Branch'}} />
    </LanguageProvider></MemoryRouter>)
    await waitFor(() => expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument())
    expect(screen.getByText('Renamed Branch')).toBeInTheDocument()
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
  })

  it('blocks a persisted Branch rename discovered at download time before requesting bytes', async () => {
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    mocks.listRunBranches.mockResolvedValueOnce({run_branches: [
      {...branch, display_name: 'Server Renamed Branch'}
    ]})
    fireEvent.click(screen.getByRole('button', {name: /Stáhnout ověřený/}))
    expect(await screen.findByRole('alert')).toHaveTextContent('HEAD')
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument()
  })

  it('blocks a persisted Run rename discovered at download time before requesting bytes', async () => {
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    mocks.getRunContainer.mockResolvedValueOnce({...run, display_name: 'Server Renamed Run'})
    fireEvent.click(screen.getByRole('button', {name: /Stáhnout ověřený/}))
    expect(await screen.findByRole('alert')).toHaveTextContent('HEAD')
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument()
  })

  it('downloads only after a second fresh context check and explicit click', async () => {
    const objectUrl = vi.fn(() => 'blob:test')
    const revoke = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', {configurable: true, value: objectUrl})
    Object.defineProperty(URL, 'revokeObjectURL', {configurable: true, value: revoke})
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    fireEvent.click(await screen.findByRole('button', {name: /Stáhnout ověřený/}))
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1))
    expect(mocks.getRunContainer).toHaveBeenCalledTimes(2)
    expect(mocks.getBranchWorkingDraft).toHaveBeenCalledTimes(2)
    expect(mocks.downloadSavedBranchArchive).toHaveBeenCalledWith(archive, expect.objectContaining({aborted: false}))
    expect(objectUrl).toHaveBeenCalledTimes(1)
  })

  it('rejects a newer persisted HEAD at download time without requesting archive bytes', async () => {
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    mocks.listRunBranches.mockResolvedValueOnce({run_branches: [
      {...branch, saved_head_revision_id: 'newer-saved-head'}
    ]})
    fireEvent.click(screen.getByRole('button', {name: /Stáhnout ověřený/}))
    expect(await screen.findByRole('alert')).toHaveTextContent('HEAD')
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument()
    expect(mocks.previewSavedBranchArchive).toHaveBeenCalledTimes(1)
  })

  it('refuses a newly dirty Viewer draft after review and requires a fresh preview', async () => {
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    mocks.getBranchWorkingDraft.mockResolvedValueOnce({
      run_id: 'r', branch_id: 'b', base_saved_revision_id: 'head',
      status: 'dirty', change_count: 1
    })
    fireEvent.click(screen.getByRole('button', {name: /Stáhnout ověřený/}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Neuložené změny')
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument()
    expect(screen.getByRole('link', {name: /ruční Save/})).toHaveAttribute('href', '/admin/runs/r')
  })

  it('surfaces server preview error with explicit retry, not a fabricated v1 capability', async () => {
    mocks.previewSavedBranchArchive.mockRejectedValueOnce(new Error('unsupported_saved_component'))
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('unsupported_saved_component')
    expect(screen.getByRole('button', {name: 'Zkusit znovu'})).toBeEnabled()
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
  })

  it.each(['completed', 'archived'])('reviews the Saved export of a writable %s Run', async status => {
    const persisted = {...run, status}
    mocks.getRunContainer.mockResolvedValue(persisted)
    mount({run: persisted})
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    expect(mocks.previewSavedBranchArchive).toHaveBeenCalledTimes(1)
  })

  it('requires a fresh review if the persisted Run lifecycle status changes before download', async () => {
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    expect(await screen.findByRole('button', {name: /Stáhnout ověřený/})).toBeEnabled()
    mocks.getRunContainer.mockResolvedValueOnce({...run, status: 'completed'})
    fireEvent.click(screen.getByRole('button', {name: /Stáhnout ověřený/}))
    expect(await screen.findByRole('alert')).toHaveTextContent('HEAD')
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument()
  })

  it('allows the canonical newly created working Run status (archive v1 supported)', () => {
    mount({run: {...run, status: 'working'}})
    expect(screen.getByRole('button', {name: 'Načíst exportní náhled'})).toBeEnabled()
  })

  it('does not allow unsupported, read-only or foreign Run/Branch exports', () => {
    mount({run: {...run, read_only: true}})
    expect(screen.getByRole('button', {name: 'Načíst exportní náhled'})).toBeDisabled()
    expect(mocks.previewSavedBranchArchive).not.toHaveBeenCalled()
  })

  it('actually aborts pending preview transport and ignores the late result after Cancel', async () => {
    let complete!: (result: SavedBranchArchivePreview) => void
    mocks.previewSavedBranchArchive.mockImplementationOnce(() =>
      new Promise<SavedBranchArchivePreview>(resolve => { complete = resolve }))
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    await waitFor(() => expect(mocks.previewSavedBranchArchive).toHaveBeenCalledTimes(1))
    const signal = mocks.previewSavedBranchArchive.mock.calls[0][2] as AbortSignal
    expect(signal.aborted).toBe(false)
    fireEvent.click(screen.getByRole('button', {name: 'Zrušit export'}))
    expect(signal.aborted).toBe(true)
    await act(async () => complete(archive))
    expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument()
    expect(mocks.downloadSavedBranchArchive).not.toHaveBeenCalled()
  })

  it('aborts a pending download on Cancel and does not trigger a delayed file save', async () => {
    let complete!: (result: Blob) => void
    mocks.downloadSavedBranchArchive.mockImplementationOnce(() =>
      new Promise<Blob>(resolve => { complete = resolve }))
    const objectUrl = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', {configurable: true, value: objectUrl})
    mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    fireEvent.click(await screen.findByRole('button', {name: /Stáhnout ověřený/}))
    await waitFor(() => expect(mocks.downloadSavedBranchArchive).toHaveBeenCalledTimes(1))
    const signal = mocks.downloadSavedBranchArchive.mock.calls[0][1] as AbortSignal
    fireEvent.click(screen.getByRole('button', {name: 'Zrušit export'}))
    expect(signal.aborted).toBe(true)
    await act(async () => complete(new Blob(['old bytes'])))
    expect(objectUrl).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', {name: /Stáhnout ověřený/})).not.toBeInTheDocument()
  })

  it('does not apply an old draft status after a scope/head change', async () => {
    let complete!: (result: object) => void
    mocks.getBranchWorkingDraft.mockImplementationOnce(() =>
      new Promise(resolve => { complete = resolve }))
    const view = mount()
    fireEvent.click(screen.getByRole('button', {name: 'Načíst exportní náhled'}))
    await waitFor(() => expect(mocks.getBranchWorkingDraft).toHaveBeenCalledTimes(1))
    view.rerender(<MemoryRouter><LanguageProvider><Toggle />
      <SavedBranchArchiveExportPanel run={run} branch={{...branch, saved_head_revision_id: 'new-head'}} />
    </LanguageProvider></MemoryRouter>)
    await act(async () => complete({
      run_id: 'r', branch_id: 'b', base_saved_revision_id: 'head', status: 'dirty', change_count: 1
    }))
    expect(screen.queryByText(/Neuložené změny blokují export/)).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(mocks.previewSavedBranchArchive).not.toHaveBeenCalled()
  })
})

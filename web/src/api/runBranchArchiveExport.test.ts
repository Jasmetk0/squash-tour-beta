/** Mocked HTTP contract tests only; real HTTP/SQLite/Chromium is a separate gate. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  assertSavedBranchArchivePreview, downloadSavedBranchArchive, previewSavedBranchArchive,
  type SavedBranchArchivePreview
} from './runBranchArchiveExport'

const hash = 'ab'.repeat(32)
const original: SavedBranchArchivePreview = {
  schema_version: 'run_branch_archive_preview.v1',
  archive_digest: hash, archive_size_bytes: 12,
  format: 'run_branch_archive.v1', minimum_engine: 'engine+archive.v1',
  scope: 'custom_selected_saved_branch_with_dependency_history',
  run_id: 'run', display_name: 'Run', selected_branch_id: 'branch',
  selected_head_revision_id: 'head', viewer_branch_id: 'branch',
  branches: [{
    branch_id: 'branch', display_name: 'Main', role: 'selected',
    forked_from_branch_id: null, forked_from_saved_revision_id: null,
    saved_head_revision_id: 'head'
  }],
  history: [{
    revision_id: 'head', original_owner_branch_id: 'branch', sequence: 1,
    parent_revision_id: null, content_hash_algorithm: 'sha256',
    content_hash: 'cd'.repeat(32), payload_schema_version: 'run_saved_revision_v1'
  }],
  included_components: ['run_package_state'], selected_head_components: ['run_package_state'],
  unresolved_package_references: [{ reference: { source_package_id: 'unknown' } }],
  continuation: 'Use existing operation-scoped preview',
  audit_event_count: 1, checkpoint_count: 0, omitted_branch_ids: ['other'],
  omitted_areas: ['working_drafts']
}
const fetchMock = vi.fn()
describe('Saved Branch export-only HTTP boundary', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => vi.unstubAllGlobals())

  it('requires exact requested Run/Branch, selected Saved HEAD and consistent history', () => {
    expect(assertSavedBranchArchivePreview(original, 'run', 'branch')).toEqual(original)
    expect(() => assertSavedBranchArchivePreview(original, 'foreign', 'branch')).toThrow(/scope/)
    expect(() => assertSavedBranchArchivePreview({...original, selected_head_revision_id: 'fake'}, 'run', 'branch')).toThrow()
    expect(() => assertSavedBranchArchivePreview({...original, archive_digest: 'bad'}, 'run', 'branch')).toThrow()
    expect(() => assertSavedBranchArchivePreview({...original, branches: [{...original.branches[0], role: 'dependency'}]}, 'run', 'branch')).toThrow()
    expect(() => assertSavedBranchArchivePreview({...original, history: []}, 'run', 'branch')).toThrow()
  })

  it('preview is a read-only, explicitly requested POST with no subsequent Save', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(original), {
      status: 200, headers: {'Content-Type': 'application/json'}
    }))
    expect(await previewSavedBranchArchive('run', 'branch')).toEqual(original)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/admin/run-archives/export/preview')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({run_id: 'run', branch_id: 'branch'})
  })

  it('sends exact HEAD/digest and rejects changed content before allowing a download', async () => {
    fetchMock.mockResolvedValueOnce(new Response('wrong content', {
      status: 200, headers: {'Content-Type': 'application/vnd.squash.saved-branch+json'}
    }))
    await expect(downloadSavedBranchArchive(original)).rejects.toThrow(/size|digest/)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/admin/run-archives/export')
    expect(JSON.parse(init.body as string)).toEqual({
      run_id: 'run', branch_id: 'branch',
      expected_head_revision_id: 'head', expected_archive_digest: hash
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('rejects stale preview 409 and preserves server reason without retry', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      detail: { code: 'stale_export_preview', message: 'Review again' }
    }), {status: 409}))
    await expect(downloadSavedBranchArchive(original)).rejects.toMatchObject({status: 409})
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('rejects wrong MIME even if the response size matches', async () => {
    fetchMock.mockResolvedValueOnce(new Response('wrong length', {status: 200, headers: {'Content-Type': 'text/html'}}))
    await expect(downloadSavedBranchArchive(original)).rejects.toThrow(/non-archive/)
  })
})

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
  run_activation_revision_id: 'head',
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
    expect(() => assertSavedBranchArchivePreview({
      ...original, run_activation_revision_id: 'missing-witness'
    }, 'run', 'branch')).toThrow(/dependency/)
    expect(() => assertSavedBranchArchivePreview({
      ...original, run_activation_revision_id: ''
    }, 'run', 'branch')).toThrow(/scope/)
  })

  it('refuses a foreign owner, missing parent, missing dependency HEAD or unknown archive format', () => {
    expect(() => assertSavedBranchArchivePreview({
      ...original, format: 'unknown-v999'
    }, 'run', 'branch')).toThrow()
    expect(() => assertSavedBranchArchivePreview({
      ...original, history: [{...original.history[0], original_owner_branch_id: 'foreign'}]
    }, 'run', 'branch')).toThrow(/dependency/)
    expect(() => assertSavedBranchArchivePreview({
      ...original, history: [{...original.history[0], parent_revision_id: 'missing-revision'}]
    }, 'run', 'branch')).toThrow(/dependency/)
    expect(() => assertSavedBranchArchivePreview({
      ...original, viewer_branch_id: 'foreign'
    }, 'run', 'branch')).toThrow(/dependency/)
    expect(() => assertSavedBranchArchivePreview({
      ...original, omitted_branch_ids: ['branch']
    }, 'run', 'branch')).toThrow(/dependency/)
    expect(() => assertSavedBranchArchivePreview({
      ...original, branches: [{...original.branches[0], saved_head_revision_id: 'foreign-head'}]
    }, 'run', 'branch')).toThrow()
  })

  it('accepts an unmodified fork whose selected Saved HEAD still belongs to the source Branch', () => {
    // The v1 archive backend explicitly permits a Branch that shares its
    // source's historical HEAD before it has written a new owned revision.
    const inherited = {
      ...original, selected_head_revision_id: 'source-head', run_activation_revision_id: 'source-head',
      branches: [
        {...original.branches[0], saved_head_revision_id: 'source-head',
          forked_from_branch_id: 'source', forked_from_saved_revision_id: 'source-head'},
        {branch_id: 'source', display_name: 'Source', role: 'dependency' as const,
          saved_head_revision_id: 'source-head', forked_from_branch_id: null,
          forked_from_saved_revision_id: null}
      ],
      history: [{...original.history[0], revision_id: 'source-head',
        original_owner_branch_id: 'source'}]
    }
    expect(assertSavedBranchArchivePreview(inherited, 'run', 'branch')).toEqual(inherited)
  })

  it('accepts a source Branch ending at a historical prefix, not its current live HEAD', () => {
    const ancestor = {...original.history[0], revision_id: 'source-prefix',
      original_owner_branch_id: 'source'}
    const selected = {...original.history[0], revision_id: 'head', sequence: 2,
      parent_revision_id: 'source-prefix'}
    const forked = {
      ...original, run_activation_revision_id: 'source-prefix',
      branches: [
        {...original.branches[0], forked_from_branch_id: 'source',
          forked_from_saved_revision_id: 'source-prefix'},
        {branch_id: 'source', display_name: 'Source', role: 'dependency' as const,
          saved_head_revision_id: 'source-prefix', forked_from_branch_id: null,
          forked_from_saved_revision_id: null}
      ],
      history: [ancestor, selected]
    }
    expect(assertSavedBranchArchivePreview(forked, 'run', 'branch')).toEqual(forked)
    expect(() => assertSavedBranchArchivePreview({
      ...forked, branches: [{...forked.branches[0], forked_from_branch_id: 'absent'},
        forked.branches[1]]
    }, 'run', 'branch')).toThrow(/fork dependency/)
    expect(() => assertSavedBranchArchivePreview({
      ...forked, branches: [{...forked.branches[0], forked_from_saved_revision_id: 'absent'},
        forked.branches[1]]
    }, 'run', 'branch')).toThrow(/fork dependency/)
    expect(() => assertSavedBranchArchivePreview({
      ...forked, branches: [forked.branches[0],
        {...forked.branches[1], forked_from_branch_id: 'branch'}]
    }, 'run', 'branch')).toThrow(/fork cycle/)
    expect(() => assertSavedBranchArchivePreview({
      ...forked, history: [ancestor, {...selected, sequence: 4}]
    }, 'run', 'branch')).toThrow(/noncontiguous/)
    expect(() => assertSavedBranchArchivePreview({
      ...forked, history: [ancestor, selected,
        {...ancestor, revision_id: 'orphan', parent_revision_id: null}]
    }, 'run', 'branch')).toThrow(/unreachable/)
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

  it('accepts only exact SHA-256-verified streamed bytes', async () => {
    const digest = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    const verified = {...original, archive_size_bytes: 3, archive_digest: digest}
    const digestMock = vi.fn(async (_algorithm: string, value: Uint8Array) => {
      expect(_algorithm).toBe('SHA-256')
      expect(Array.from(value)).toEqual([97, 98, 99])
      return Uint8Array.from(digest.match(/../g)!.map(byte => Number.parseInt(byte, 16))).buffer
    })
    vi.stubGlobal('crypto', {subtle: {digest: digestMock}})
    fetchMock.mockResolvedValueOnce(new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(new Uint8Array([97]))
        controller.enqueue(new Uint8Array([98, 99]))
        controller.close()
      }
    }), {status: 200, headers: {'Content-Type': 'application/vnd.squash.saved-branch+json'}}))
    const blob = await downloadSavedBranchArchive(verified)
    expect(blob.type).toBe('application/vnd.squash.saved-branch+json')
    expect(blob.size).toBe(3)
    const content = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = () => reject(reader.error)
      reader.readAsText(blob)
    })
    expect(content).toBe('abc')
    expect(digestMock).toHaveBeenCalledTimes(1)
  })

  it('rejects an oversized response as soon as streamed bytes exceed the reviewed size', async () => {
    const cancelled = vi.fn()
    fetchMock.mockResolvedValueOnce(new Response(new ReadableStream({
      start(controller) { controller.enqueue(new Uint8Array(13)) },
      cancel: cancelled
    }), {status: 200, headers: {'Content-Type': 'application/vnd.squash.saved-branch+json'}}))
    await expect(downloadSavedBranchArchive(original)).rejects.toThrow(/size exceeds/)
    expect(cancelled).toHaveBeenCalledTimes(1)
  })

  it('rejects an incomplete streamed download without calculating a digest or offering a file', async () => {
    const digestMock = vi.fn()
    vi.stubGlobal('crypto', {subtle: {digest: digestMock}})
    fetchMock.mockResolvedValueOnce(new Response('small', {
      status: 200, headers: {'Content-Type': 'application/vnd.squash.saved-branch+json'}
    }))
    await expect(downloadSavedBranchArchive(original)).rejects.toThrow(/size differs/)
    expect(digestMock).not.toHaveBeenCalled()
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

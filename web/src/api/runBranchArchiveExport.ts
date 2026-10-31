/** Export-only boundary for the merged Saved Branch archive v1 API (#1677).
 * No import, Save, mutation or implicit retry is allowed in this module.
 */
import { ApiError } from './client'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const SHA256 = /^[0-9a-f]{64}$/
const MAX_BYTES = 128 * 1024 * 1024

export type IncludedArchiveBranch = {
  branch_id: string
  display_name: string
  role: 'selected' | 'dependency'
  forked_from_branch_id: string | null
  forked_from_saved_revision_id: string | null
  saved_head_revision_id: string
}
export type ArchiveHistoryRevision = {
  revision_id: string
  original_owner_branch_id: string
  sequence: number
  parent_revision_id: string | null
  content_hash_algorithm: string
  content_hash: string
  payload_schema_version: string
}
export type SavedBranchArchivePreview = {
  schema_version: 'run_branch_archive_preview.v1'
  archive_digest: string
  archive_size_bytes: number
  format: string
  minimum_engine: string
  scope: 'custom_selected_saved_branch_with_dependency_history'
  run_id: string
  display_name: string
  selected_branch_id: string
  selected_head_revision_id: string
  viewer_branch_id: string | null
  branches: IncludedArchiveBranch[]
  history: ArchiveHistoryRevision[]
  included_components: string[]
  selected_head_components: string[]
  unresolved_package_references: unknown[]
  continuation: string
  audit_event_count: number
  checkpoint_count: number
  omitted_branch_ids: string[]
  omitted_areas: string[]
}
const record = (data: unknown): data is Record<string, unknown> =>
  typeof data === 'object' && data !== null && !Array.isArray(data)
const strings = (data: unknown): data is string[] =>
  Array.isArray(data) && data.every(item => typeof item === 'string')

/** Fail closed on foreign/partial previews: never authorize a download from an unchecked response. */
export function assertSavedBranchArchivePreview(
  value: unknown, runId: string, branchId: string
): SavedBranchArchivePreview {
  if (!record(value) ||
    value.schema_version !== 'run_branch_archive_preview.v1' ||
    value.scope !== 'custom_selected_saved_branch_with_dependency_history' ||
    value.run_id !== runId || value.selected_branch_id !== branchId ||
    typeof value.selected_head_revision_id !== 'string' || !value.selected_head_revision_id ||
    typeof value.archive_digest !== 'string' || !SHA256.test(value.archive_digest) ||
    !Number.isSafeInteger(value.archive_size_bytes) ||
    (value.archive_size_bytes as number) <= 0 ||
    (value.archive_size_bytes as number) > MAX_BYTES ||
    typeof value.display_name !== 'string' ||
    value.format !== 'run_branch_archive.v1' ||
    typeof value.minimum_engine !== 'string' || !value.minimum_engine ||
    typeof value.continuation !== 'string' || !value.continuation ||
    !Array.isArray(value.branches) || !value.branches.length ||
    !Array.isArray(value.history) || !value.history.length ||
    !strings(value.included_components) || !strings(value.selected_head_components) ||
    !strings(value.omitted_branch_ids) || !strings(value.omitted_areas) ||
    !Array.isArray(value.unresolved_package_references) ||
    !Number.isSafeInteger(value.audit_event_count) || (value.audit_event_count as number) < 0 ||
    !Number.isSafeInteger(value.checkpoint_count) || (value.checkpoint_count as number) < 0 ||
    !(value.viewer_branch_id === null || typeof value.viewer_branch_id === 'string')) {
    throw new Error('Saved Branch archive preview has an invalid or foreign scope.')
  }
  const branches = value.branches as unknown[]
  const history = value.history as unknown[]
  if (branches.some(b => !record(b) || typeof b.branch_id !== 'string' || !b.branch_id ||
      typeof b.display_name !== 'string' ||
      (b.role !== 'selected' && b.role !== 'dependency') ||
      typeof b.saved_head_revision_id !== 'string' || !b.saved_head_revision_id ||
      !(b.forked_from_branch_id === null || typeof b.forked_from_branch_id === 'string') ||
      !(b.forked_from_saved_revision_id === null || typeof b.forked_from_saved_revision_id === 'string')) ||
    branches.filter(b => record(b) && b.role === 'selected' && b.branch_id === branchId).length !== 1 ||
    branches.some(b => record(b) && b.role === 'selected' && b.branch_id !== branchId) ||
    new Set(branches.map(b => (b as IncludedArchiveBranch).branch_id)).size !== branches.length ||
    !branches.some(b => record(b) && b.branch_id === branchId &&
      b.saved_head_revision_id === value.selected_head_revision_id) ||
    history.some(r => !record(r) || typeof r.revision_id !== 'string' || !r.revision_id ||
      typeof r.original_owner_branch_id !== 'string' ||
      !Number.isSafeInteger(r.sequence) || (r.sequence as number) < 1 ||
      !(r.parent_revision_id === null || typeof r.parent_revision_id === 'string') ||
      r.content_hash_algorithm !== 'sha256' || typeof r.content_hash !== 'string' ||
      !SHA256.test(r.content_hash) || typeof r.payload_schema_version !== 'string') ||
    !history.some(r => record(r) && r.revision_id === value.selected_head_revision_id) ||
    new Set(history.map(r => (r as ArchiveHistoryRevision).revision_id)).size !== history.length) {
    throw new Error('Saved Branch archive preview has invalid dependencies or revision history.')
  }
  const includedBranchIds = new Set(branches.map(b => (b as IncludedArchiveBranch).branch_id))
  const revisionIds = new Set(history.map(r => (r as ArchiveHistoryRevision).revision_id))
  const revisionsById = new Map(history.map(r => [
    (r as ArchiveHistoryRevision).revision_id, r as ArchiveHistoryRevision
  ]))
  if (branches.some(b => !revisionIds.has((b as IncludedArchiveBranch).saved_head_revision_id)) ||
    history.some(r => {
      const revision = r as ArchiveHistoryRevision
      return !includedBranchIds.has(revision.original_owner_branch_id) ||
        (revision.parent_revision_id !== null && !revisionIds.has(revision.parent_revision_id))
    }) ||
    (value.viewer_branch_id !== null && !includedBranchIds.has(value.viewer_branch_id)) ||
    new Set(value.omitted_branch_ids).size !== value.omitted_branch_ids.length ||
    value.omitted_branch_ids.some(id => includedBranchIds.has(id))) {
    throw new Error('Saved Branch archive preview contains incomplete or foreign dependency links.')
  }

  // Match the archive v1 closed graph invariants. The dependency Branch may
  // legitimately end at an earlier historical prefix rather than its live HEAD.
  const branchById = new Map((branches as IncludedArchiveBranch[]).map(b => [b.branch_id, b]))
  const reached = new Set<string>()
  for (const branch of branches as IncludedArchiveBranch[]) {
    if ((branch.forked_from_branch_id !== null &&
        !branchById.has(branch.forked_from_branch_id)) ||
      (branch.forked_from_saved_revision_id !== null &&
        !revisionIds.has(branch.forked_from_saved_revision_id))) {
      throw new Error('Saved Branch archive preview has a missing fork dependency.')
    }
    const forkPath = new Set<string>()
    let owner: string | null = branch.branch_id
    while (owner !== null) {
      if (forkPath.has(owner)) throw new Error('Saved Branch archive preview has a Branch fork cycle.')
      forkPath.add(owner)
      owner = branchById.get(owner)?.forked_from_branch_id ?? null
    }
    let revisionId: string | null = branch.saved_head_revision_id
    while (revisionId !== null && !reached.has(revisionId)) {
      reached.add(revisionId)
      const revision = revisionsById.get(revisionId)
      if (!revision) throw new Error('Saved Branch archive preview has a missing revision.')
      const parent = revision.parent_revision_id === null
        ? null : revisionsById.get(revision.parent_revision_id)
      if ((parent === null || parent === undefined) !== (revision.parent_revision_id === null) ||
        (parent && revision.sequence !== parent.sequence + 1) ||
        (!parent && revision.sequence !== 1)) {
        throw new Error('Saved Branch archive preview has noncontiguous revision history.')
      }
      revisionId = revision.parent_revision_id
    }
  }
  if (reached.size !== revisionIds.size) {
    throw new Error('Saved Branch archive preview contains unreachable history.')
  }
  return value as SavedBranchArchivePreview
}

async function archiveResponse(path: string, body: object, signal?: AbortSignal): Promise<Response> {
  const response = await fetch(API_BASE + '/admin/run-archives' + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal
  })
  if (!response.ok) {
    const message = await response.text()
    throw new ApiError(message || 'Saved Branch archive request failed', response.status)
  }
  return response
}

export async function previewSavedBranchArchive(
  runId: string, branchId: string, signal?: AbortSignal
): Promise<SavedBranchArchivePreview> {
  const response = await archiveResponse('/export/preview', { run_id: runId, branch_id: branchId }, signal)
  return assertSavedBranchArchivePreview(await response.json() as unknown, runId, branchId)
}

/** Prove the attachment is the *exact* reviewed bytes, not merely a successful HTTP reply. */
export async function downloadSavedBranchArchive(
  preview: SavedBranchArchivePreview, signal?: AbortSignal
): Promise<Blob> {
  const response = await archiveResponse('/export', {
    run_id: preview.run_id,
    branch_id: preview.selected_branch_id,
    expected_head_revision_id: preview.selected_head_revision_id,
    expected_archive_digest: preview.archive_digest
  }, signal)
  if (!response.headers.get('Content-Type')?.startsWith('application/vnd.squash.saved-branch+json')) {
    throw new Error('Server returned a non-archive attachment.')
  }
  // Do not buffer an arbitrary HTTP payload before checking its size: even
  // a wrong/stale server response must stay within the reviewed byte budget.
  if (!response.body) throw new Error('Server returned an unreadable archive stream.')
  const reader = response.body.getReader()
  const raw = new Uint8Array(preview.archive_size_bytes)
  let received = 0
  try {
    while (true) {
      const chunk = await reader.read()
      if (chunk.done) break
      if (chunk.value.byteLength > raw.byteLength - received) {
        throw new Error('Export size exceeds reviewed preview.')
      }
      raw.set(chunk.value, received)
      received += chunk.value.byteLength
    }
  } catch (cause) {
    await reader.cancel().catch(() => undefined)
    throw cause
  } finally {
    reader.releaseLock()
  }
  if (received !== raw.byteLength) throw new Error('Export size differs from reviewed preview.')
  if (!globalThis.crypto?.subtle) throw new Error('SHA-256 verification is unavailable in this browser.')
  const digest = await globalThis.crypto.subtle.digest('SHA-256', raw)
  const actual = Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, '0')).join('')
  if (actual !== preview.archive_digest) throw new Error('Export digest differs from reviewed preview.')
  return new Blob([raw.buffer], { type: 'application/vnd.squash.saved-branch+json' })
}

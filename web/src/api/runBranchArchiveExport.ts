/** Export-only boundary for Saved archives.
 * No import, Save, mutation or implicit retry is allowed in this module.
 */
import { ApiError } from './client'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const SHA256 = /^[0-9a-f]{64}$/
const MAX_BYTES = 128 * 1024 * 1024
const MAX_ERROR_BYTES = 64 * 1024
const BRANCH_SCOPE = 'custom_selected_saved_branch_with_dependency_history'
const FULL_RUN_SCOPE = 'full_saved_run'
const CUSTOM_SCOPE = 'custom_saved_branches'
const COMPACT_SCOPE = 'compact_saved_branch_snapshot'
const ARCHIVE_MIME = 'application/vnd.squash.saved-branch+json'
const COMPACT_MIME = 'application/vnd.squash.compact-snapshot+json'
export const MAX_CUSTOM_BRANCHES = 128
export type ArchiveExportMode = 'branch' | 'full_run' | 'custom' | 'compact'

export type IncludedArchiveBranch = {
  branch_id: string
  display_name: string
  role: 'selected' | 'dependency' | 'included'
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
  scope: typeof BRANCH_SCOPE | typeof FULL_RUN_SCOPE | typeof CUSTOM_SCOPE
  selected_branch_ids?: string[]
  run_id: string
  display_name: string
  selected_branch_id: string
  selected_head_revision_id: string
  viewer_branch_id: string
  run_activation_revision_id: string
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
/** Master §24.1 scope 3: one Branch's exact Saved HEAD, no technical history. */
export type CompactSnapshotPreview = {
  schema_version: 'run_compact_snapshot_preview.v1'
  archive_digest: string
  archive_size_bytes: number
  format: 'run_compact_snapshot.v1'
  minimum_engine: string
  scope: typeof COMPACT_SCOPE
  run_id: string
  display_name: string
  selected_branch_id: string
  selected_branch_display_name: string
  selected_head_revision_id: string
  selected_head_sequence: number
  selected_head_kind: string
  saved_at: string
  payload_schema_version: string
  content_hash_algorithm: 'sha256'
  content_hash: string
  run_calendar: Record<string, unknown>
  included_components: string[]
  package_provenance: { source_package_ids: string[]; run_local_entity_count: number }
  unresolved_package_references: unknown[]
  kept_references: {
    parent_revision_id: string | null
    forked_from_branch_id: string | null
    forked_from_saved_revision_id: string | null
    viewer_branch_id_signed_at_save: string | null
  }
  omitted_older_revision_count: number
  omitted_areas: string[]
  verified_uses: string[]
  unsupported_uses: string[]
  verification: string
  source_context: {
    viewer_branch_id: string
    selected_is_viewer_branch: boolean
    omitted_branch_count: number
    omitted_older_revision_count: number
  }
}
export type ArchiveExportPreview = SavedBranchArchivePreview | CompactSnapshotPreview
export const isCompactSnapshotPreview = (value: ArchiveExportPreview): value is CompactSnapshotPreview =>
  value.scope === COMPACT_SCOPE
const record = (data: unknown): data is Record<string, unknown> =>
  typeof data === 'object' && data !== null && !Array.isArray(data)
const strings = (data: unknown): data is string[] =>
  Array.isArray(data) && data.every(item => typeof item === 'string')

/** Fail closed on foreign/partial previews: never authorize a download from an unchecked response. */
export function assertSavedBranchArchivePreview(
  value: unknown, runId: string, branchId: string, mode?: ArchiveExportMode,
  requestedIds?: readonly string[]
): SavedBranchArchivePreview {
  const fullRun = record(value) && value.scope === FULL_RUN_SCOPE
  const custom = record(value) && value.scope === CUSTOM_SCOPE
  const scope = custom ? CUSTOM_SCOPE : fullRun ? FULL_RUN_SCOPE : BRANCH_SCOPE
  const format = custom ? 'run_custom_archive.v1' : fullRun ? 'run_full_archive.v1' : 'run_branch_archive.v1'
  const actualMode = custom ? 'custom' : fullRun ? 'full_run' : 'branch'
  const otherRole = fullRun ? 'included' : 'dependency'
  if (!record(value) ||
    value.schema_version !== 'run_branch_archive_preview.v1' ||
    value.scope !== scope || (mode !== undefined && actualMode !== mode) ||
    value.run_id !== runId || value.selected_branch_id !== branchId ||
    typeof value.selected_head_revision_id !== 'string' || !value.selected_head_revision_id ||
    typeof value.archive_digest !== 'string' || !SHA256.test(value.archive_digest) ||
    !Number.isSafeInteger(value.archive_size_bytes) ||
    (value.archive_size_bytes as number) <= 0 ||
    (value.archive_size_bytes as number) > MAX_BYTES ||
    typeof value.display_name !== 'string' ||
    value.format !== format ||
    typeof value.minimum_engine !== 'string' || !value.minimum_engine ||
    typeof value.continuation !== 'string' || !value.continuation ||
    !Array.isArray(value.branches) || !value.branches.length ||
    !Array.isArray(value.history) || !value.history.length ||
    !strings(value.included_components) || !strings(value.selected_head_components) ||
    !strings(value.omitted_branch_ids) || !strings(value.omitted_areas) ||
    (fullRun && value.omitted_branch_ids.length !== 0) ||
    !Array.isArray(value.unresolved_package_references) ||
    !Number.isSafeInteger(value.audit_event_count) || (value.audit_event_count as number) < 0 ||
    !Number.isSafeInteger(value.checkpoint_count) || (value.checkpoint_count as number) < 0 ||
    typeof value.viewer_branch_id !== 'string' || !value.viewer_branch_id ||
    typeof value.run_activation_revision_id !== 'string' || !value.run_activation_revision_id) {
    throw new Error('Saved Branch archive preview has an invalid or foreign scope.')
  }
  const selectedIds = custom ? value.selected_branch_ids : [branchId]
  if (!strings(selectedIds) || !selectedIds.includes(branchId) ||
      (custom && (selectedIds.length < 2 || selectedIds.length > MAX_CUSTOM_BRANCHES)) ||
      new Set(selectedIds).size !== selectedIds.length ||
      (requestedIds && (requestedIds.length !== selectedIds.length ||
        requestedIds.some(id => !selectedIds.includes(id))))) {
    throw new Error('Saved Branch archive preview has a foreign selection.')
  }
  const branches = value.branches as unknown[]
  const history = value.history as unknown[]
  if (branches.some(b => !record(b) || typeof b.branch_id !== 'string' || !b.branch_id ||
      typeof b.display_name !== 'string' ||
      (b.role !== 'selected' && b.role !== otherRole) ||
      typeof b.saved_head_revision_id !== 'string' || !b.saved_head_revision_id ||
      !(b.forked_from_branch_id === null || typeof b.forked_from_branch_id === 'string') ||
      !(b.forked_from_saved_revision_id === null || typeof b.forked_from_saved_revision_id === 'string')) ||
    branches.filter(b => record(b) && b.role === 'selected').length !== selectedIds.length ||
    branches.some(b => record(b) && (b.role === 'selected') !== selectedIds.includes(String(b.branch_id))) ||
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
    !includedBranchIds.has(value.viewer_branch_id) ||
    !revisionIds.has(value.run_activation_revision_id) ||
    new Set(value.omitted_branch_ids).size !== value.omitted_branch_ids.length ||
    value.omitted_branch_ids.some(id => includedBranchIds.has(id))) {
    throw new Error('Saved Branch archive preview contains incomplete or foreign dependency links.')
  }

  // Match archive v1's closed graphs without repeatedly walking the same
  // ancestors. A large Saved export may contain thousands of dependent Branches
  // and revisions; validating each fork from scratch grows quadratically.
  const branchById = new Map((branches as IncludedArchiveBranch[]).map(b => [b.branch_id, b]))
  const checkedForks = new Set<string>()
  const reached = new Set<string>()
  for (const branch of branches as IncludedArchiveBranch[]) {
    if ((branch.forked_from_branch_id !== null &&
        !branchById.has(branch.forked_from_branch_id)) ||
      (branch.forked_from_saved_revision_id !== null &&
        !revisionIds.has(branch.forked_from_saved_revision_id))) {
      throw new Error('Saved Branch archive preview has a missing fork dependency.')
    }
    // Every suffix is examined only once, including a deep fork chain.
    const forkPath = new Set<string>()
    let owner: string | null = branch.branch_id
    while (owner !== null && !checkedForks.has(owner)) {
      if (forkPath.has(owner)) throw new Error('Saved Branch archive preview has a Branch fork cycle.')
      forkPath.add(owner)
      const current = branchById.get(owner)
      if (!current) throw new Error('Saved Branch archive preview has a missing fork dependency.')
      owner = current.forked_from_branch_id
    }
    for (const id of forkPath) checkedForks.add(id)
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

  // Each Saved Revision has exactly one parent: it is a rooted forest.
  // Iterative DFS timestamps make an ancestry proof constant-time per fork,
  // even when the source Branch ends at an earlier historical prefix.
  const children = new Map<string, string[]>()
  const roots: string[] = []
  for (const revision of history as ArchiveHistoryRevision[]) {
    if (revision.parent_revision_id === null) {
      roots.push(revision.revision_id)
    } else {
      const siblings = children.get(revision.parent_revision_id) ?? []
      siblings.push(revision.revision_id)
      children.set(revision.parent_revision_id, siblings)
    }
  }
  const entered = new Map<string, number>()
  const exited = new Map<string, number>()
  let tick = 0
  for (const root of roots) {
    const stack: {id: string; leaving: boolean}[] = [{id: root, leaving: false}]
    while (stack.length) {
      const item = stack.pop()!
      if (item.leaving) {
        exited.set(item.id, ++tick)
        continue
      }
      if (entered.has(item.id)) {
        throw new Error('Saved Branch archive preview has a revision ancestry cycle.')
      }
      entered.set(item.id, ++tick)
      stack.push({id: item.id, leaving: true})
      const descendants = children.get(item.id) ?? []
      for (let i = descendants.length - 1; i >= 0; i--) {
        stack.push({id: descendants[i], leaving: false})
      }
    }
  }
  if (entered.size !== revisionIds.size) {
    throw new Error('Saved Branch archive preview contains unreachable revision ancestry.')
  }
  for (const branch of branches as IncludedArchiveBranch[]) {
    if (branch.forked_from_branch_id === null ||
      branch.forked_from_saved_revision_id === null) continue
    const sourceHead = branchById.get(branch.forked_from_branch_id)?.saved_head_revision_id
    const forkStart = entered.get(branch.forked_from_saved_revision_id)
    const forkEnd = exited.get(branch.forked_from_saved_revision_id)
    const headStart = sourceHead === undefined ? undefined : entered.get(sourceHead)
    const headEnd = sourceHead === undefined ? undefined : exited.get(sourceHead)
    if (forkStart === undefined || forkEnd === undefined ||
      headStart === undefined || headEnd === undefined ||
      !(forkStart <= headStart && forkEnd >= headEnd)) {
      throw new Error('Saved Branch archive preview has a foreign fork source revision.')
    }
  }
  return value as SavedBranchArchivePreview
}

const nullableString = (data: unknown): data is string | null =>
  data === null || (typeof data === 'string' && data.length > 0)

/** Fail closed: a Compact preview must bind this exact Run, Branch, HEAD and digest. */
export function assertCompactSnapshotPreview(
  value: unknown, runId: string, branchId: string
): CompactSnapshotPreview {
  const references = record(value) ? value.kept_references : null
  const packages = record(value) ? value.package_provenance : null
  const source = record(value) ? value.source_context : null
  if (!record(value) || value.schema_version !== 'run_compact_snapshot_preview.v1' ||
    value.scope !== COMPACT_SCOPE || value.format !== 'run_compact_snapshot.v1' ||
    value.run_id !== runId || value.selected_branch_id !== branchId ||
    typeof value.selected_head_revision_id !== 'string' || !value.selected_head_revision_id ||
    typeof value.archive_digest !== 'string' || !SHA256.test(value.archive_digest) ||
    value.content_hash_algorithm !== 'sha256' ||
    typeof value.content_hash !== 'string' || !SHA256.test(value.content_hash) ||
    !Number.isSafeInteger(value.archive_size_bytes) || (value.archive_size_bytes as number) <= 0 ||
    (value.archive_size_bytes as number) > MAX_BYTES ||
    !Number.isSafeInteger(value.selected_head_sequence) || (value.selected_head_sequence as number) < 1 ||
    value.omitted_older_revision_count !== (value.selected_head_sequence as number) - 1 ||
    typeof value.display_name !== 'string' || typeof value.selected_branch_display_name !== 'string' ||
    typeof value.minimum_engine !== 'string' || !value.minimum_engine ||
    typeof value.selected_head_kind !== 'string' || typeof value.saved_at !== 'string' ||
    typeof value.payload_schema_version !== 'string' || typeof value.verification !== 'string' ||
    !record(value.run_calendar) || !strings(value.included_components) ||
    !strings(value.omitted_areas) || !value.omitted_areas.length ||
    !strings(value.verified_uses) || !value.verified_uses.length ||
    !strings(value.unsupported_uses) || !value.unsupported_uses.includes('cold_restore') ||
    !Array.isArray(value.unresolved_package_references) ||
    !record(packages) || !strings(packages.source_package_ids) ||
    !Number.isSafeInteger(packages.run_local_entity_count) ||
    !record(references) || !nullableString(references.parent_revision_id) ||
    (references.parent_revision_id === null) !== (value.selected_head_sequence === 1) ||
    !nullableString(references.forked_from_branch_id) ||
    !nullableString(references.forked_from_saved_revision_id) ||
    !nullableString(references.viewer_branch_id_signed_at_save) ||
    !record(source) || typeof source.viewer_branch_id !== 'string' || !source.viewer_branch_id ||
    source.selected_is_viewer_branch !== (source.viewer_branch_id === branchId) ||
    !Number.isSafeInteger(source.omitted_branch_count) || (source.omitted_branch_count as number) < 0 ||
    source.omitted_older_revision_count !== value.omitted_older_revision_count) {
    throw new Error('Compact snapshot preview has an invalid or foreign scope.')
  }
  return value as CompactSnapshotPreview
}

/** Bound both preview and error JSON without trusting Content-Length alone. */
async function boundedResponseText(
  response: Response, limit: number
): Promise<{ text: string; exceeded: boolean }> {
  const length = response.headers.get('Content-Length')
  if (length !== null && /^\d+$/.test(length) && Number(length) > limit) {
    await response.body?.cancel().catch(() => undefined)
    return { text: '', exceeded: true }
  }
  if (!response.body) return { text: '', exceeded: false }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let received = 0
  let text = ''
  try {
    while (true) {
      const chunk = await reader.read()
      if (chunk.done) return { text: text + decoder.decode(), exceeded: false }
      if (chunk.value.byteLength > limit - received) {
        return { text: '', exceeded: true }
      }
      received += chunk.value.byteLength
      text += decoder.decode(chunk.value, { stream: true })
    }
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}

async function archiveResponse(path: string, body: object, signal?: AbortSignal): Promise<Response> {
  const response = await fetch(API_BASE + '/admin/run-archives' + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal
  })
  if (!response.ok) {
    const errorBody = await boundedResponseText(response, MAX_ERROR_BYTES)
    const message = errorBody.exceeded
      ? 'Saved Branch archive error response exceeded the safe size limit.' : errorBody.text
    throw new ApiError(message || 'Saved Branch archive request failed', response.status)
  }
  return response
}

/** One bounded JSON preview response; the caller validates its exact scope. */
async function previewJson(body: object, label: string, signal?: AbortSignal): Promise<unknown> {
  const response = await archiveResponse('/export/preview', body, signal)
  if (!response.headers.get('Content-Type')?.startsWith('application/json')) {
    throw new Error('Server returned a non-JSON archive preview.')
  }
  const previewBody = await boundedResponseText(response, MAX_BYTES)
  if (previewBody.exceeded) throw new Error(label + ' preview exceeds the safe size limit.')
  return JSON.parse(previewBody.text) as unknown
}

export async function previewSavedBranchArchive(
  runId: string, branchId: string, signal?: AbortSignal, mode: ArchiveExportMode = 'branch',
  selectedIds?: readonly string[]
): Promise<SavedBranchArchivePreview> {
  const selection = { run_id: runId, branch_id: branchId }
  const value = await previewJson({
    ...selection,
    ...(mode === 'branch' ? {} : {mode}),
    ...(mode === 'custom' ? {selected_branch_ids: selectedIds} : {})
  }, 'Saved Branch archive', signal)
  return assertSavedBranchArchivePreview(value, runId, branchId, mode, selectedIds)
}

export async function previewCompactSnapshot(
  runId: string, branchId: string, signal?: AbortSignal
): Promise<CompactSnapshotPreview> {
  const value = await previewJson({run_id: runId, branch_id: branchId, mode: 'compact'},
    'Compact snapshot', signal)
  return assertCompactSnapshotPreview(value, runId, branchId)
}

/** Prove the attachment is the *exact* reviewed bytes, not merely a successful HTTP reply. */
export async function downloadSavedBranchArchive(
  preview: ArchiveExportPreview, signal?: AbortSignal
): Promise<Blob> {
  const compact = isCompactSnapshotPreview(preview)
  const mime = compact ? COMPACT_MIME : ARCHIVE_MIME
  const response = await archiveResponse('/export', {
    run_id: preview.run_id,
    branch_id: preview.selected_branch_id,
    ...(compact ? {mode: 'compact'} : {}),
    ...(preview.scope === FULL_RUN_SCOPE ? {mode: 'full_run'} : {}),
    ...(preview.scope === CUSTOM_SCOPE ? {
      mode: 'custom', selected_branch_ids: preview.selected_branch_ids
    } : {}),
    expected_head_revision_id: preview.selected_head_revision_id,
    expected_archive_digest: preview.archive_digest
  }, signal)
  if (!response.headers.get('Content-Type')?.startsWith(mime)) {
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
  return new Blob([raw.buffer], { type: mime })
}

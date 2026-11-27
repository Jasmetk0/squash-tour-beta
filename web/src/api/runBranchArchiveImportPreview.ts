/** Preview and explicitly confirmed cold restore of one reviewed file. */
import { ApiError } from './client'
import { assertSavedBranchArchivePreview, type SavedBranchArchivePreview } from './runBranchArchiveExport'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
export const MAX_IMPORT_ARCHIVE_BYTES = 128 * 1024 * 1024
const ERROR_BYTES = 64 * 1024
const SHA256 = /^[0-9a-f]{64}$/

export type SavedBranchImportConflict = {
  code: string
  identity: string
  area?: string
}
export type SavedBranchImportPreview = SavedBranchArchivePreview & {
  can_restore: boolean
  preview_fingerprint: string
  conflicts: SavedBranchImportConflict[]
}

export type ArchiveRestoreCommand = {
  commandId: string
  operatorLabel: string
  auditReason: string
}

export class ArchiveRestoreRejected extends ApiError {
  constructor(message: string, status: number, readonly code?: string) {
    super(message, status)
  }
}

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

/** A reply from another file, stale endpoint, or unsupported schema is not review evidence. */
export function assertSavedBranchImportPreview(
  value: unknown, size: number, expectedDigest: string
): SavedBranchImportPreview {
  if (!record(value) || typeof value.run_id !== 'string' ||
    typeof value.selected_branch_id !== 'string' ||
    !SHA256.test(expectedDigest) ||
    value.archive_size_bytes !== size || value.archive_digest !== expectedDigest ||
    !SHA256.test(String(value.preview_fingerprint ?? '')) ||
    typeof value.can_restore !== 'boolean' || !Array.isArray(value.conflicts) ||
    value.conflicts.some(item => !record(item) ||
      typeof item.code !== 'string' || !item.code.trim() ||
      typeof item.identity !== 'string' || !item.identity.trim() ||
      (item.area !== undefined && (typeof item.area !== 'string' || !item.area.trim()))) ||
    value.can_restore !== (value.conflicts.length === 0)) {
    throw new Error('Saved Branch import review does not match the selected file or target conflicts.')
  }
  // Reuse all export v1 lineage, original-owner and reachable-history checks.
  assertSavedBranchArchivePreview(value, value.run_id, value.selected_branch_id)
  return value as SavedBranchImportPreview
}

async function boundedText(response: Response, maxBytes: number): Promise<string> {
  const length = response.headers.get('Content-Length')
  if (length && /^\d+$/.test(length) && Number(length) > maxBytes) {
    await response.body?.cancel().catch(() => undefined)
    throw new Error('Saved Branch import response exceeds its size limit.')
  }
  if (!response.body) throw new Error('Saved Branch import returned an empty response.')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let bytes = 0, output = ''
  try {
    while (true) {
      const {value,done} = await reader.read()
      if (done) return output + decoder.decode()
      if (value.byteLength > maxBytes - bytes) {
        throw new Error('Saved Branch import response exceeds its size limit.')
      }
      bytes += value.byteLength
      output += decoder.decode(value, {stream: true})
    }
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}

/** Verify the same immutable file bytes locally, then send only a read-only preview. */
export async function previewSavedBranchImport(
  file: File, signal?: AbortSignal
): Promise<SavedBranchImportPreview> {
  if (!file || !Number.isSafeInteger(file.size) || file.size < 1 ||
    file.size > MAX_IMPORT_ARCHIVE_BYTES || !/\.sqbranch$/i.test(file.name)) {
    throw new Error('Select a .sqbranch archive up to 128 MiB.')
  }
  if (!globalThis.crypto?.subtle) throw new Error('SHA-256 is unavailable in this browser.')
  const bytes = await file.arrayBuffer()
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError')
  if (bytes.byteLength !== file.size) throw new Error('Selected archive size changed during review.')
  const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes)
  const digest = Array.from(new Uint8Array(hash), n => n.toString(16).padStart(2, '0')).join('')
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError')
  const response = await uploadArchive('/preview', file, signal)
  const raw = await boundedText(response, MAX_IMPORT_ARCHIVE_BYTES)
  return assertSavedBranchImportPreview(JSON.parse(raw) as unknown, file.size, digest)
}

async function uploadArchive(path: string, file: File, signal?: AbortSignal): Promise<Response> {
  const response = await fetch(API_BASE + '/admin/run-archives/import' + path, {
    method: 'POST', headers: {'Content-Type': 'application/octet-stream'},
    body: file, signal
  })
  if (!response.ok) {
    const raw = await boundedText(response, ERROR_BYTES)
    let message = raw
    let code: string | undefined
    try {
      const parsed: unknown = JSON.parse(raw)
      if (record(parsed) && record(parsed.detail) && typeof parsed.detail.message === 'string') {
        message = parsed.detail.message
        if (typeof parsed.detail.code === 'string') code = parsed.detail.code
      }
    } catch { /* Preserve bounded server text when not JSON. */ }
    throw new ArchiveRestoreRejected(message || 'Archive request failed.', response.status, code)
  }
  if (!response.headers.get('Content-Type')?.startsWith('application/json')) {
    throw new Error('Saved Branch import returned non-JSON review data.')
  }
  return response
}

const sameIds = (actual: unknown, expected: string[]): boolean => {
  const expectedIds = new Set(expected)
  return Array.isArray(actual) && actual.length === expectedIds.size &&
    new Set(actual).size === expectedIds.size &&
    actual.every(id => typeof id === 'string' && expectedIds.has(id))
}

/** The existing API binds the immutable file bytes and the review in one atomic command. */
export async function confirmSavedBranchImport(
  file: File, reviewed: SavedBranchImportPreview, command: ArchiveRestoreCommand,
  signal?: AbortSignal
): Promise<void> {
  if (!reviewed.can_restore || reviewed.conflicts.length ||
      file.size !== reviewed.archive_size_bytes || !SHA256.test(reviewed.preview_fingerprint) ||
      !command.commandId.trim() || command.commandId.length > 128 ||
      !command.operatorLabel.trim() || command.operatorLabel.length > 160 ||
      !command.auditReason.trim() || command.auditReason.length > 1000) {
    throw new Error('Restore requires an eligible archive review and audit details.')
  }
  const query = new URLSearchParams({
    command_id: command.commandId,
    expected_preview_fingerprint: reviewed.preview_fingerprint,
    explicit_confirmation: 'true',
    operator_label: command.operatorLabel,
    audit_reason: command.auditReason,
  })
  const response = await uploadArchive('/confirm?' + query, file, signal)
  const value: unknown = JSON.parse(await boundedText(response, MAX_IMPORT_ARCHIVE_BYTES))
  if (response.status !== 201 || !record(value) ||
      value.schema_version !== 'run_branch_archive_restore_receipt.v1' ||
      value.command_id !== command.commandId || value.archive_digest !== reviewed.archive_digest ||
      value.preview_fingerprint !== reviewed.preview_fingerprint ||
      value.run_id !== reviewed.run_id || value.display_name !== reviewed.display_name ||
      value.selected_branch_id !== reviewed.selected_branch_id ||
      value.viewer_branch_id !== reviewed.viewer_branch_id ||
      value.saved_head_revision_id !== reviewed.selected_head_revision_id ||
      !sameIds(value.restored_branch_ids, reviewed.branches.map(branch => branch.branch_id)) ||
      !sameIds(value.restored_revision_ids, reviewed.history.map(revision => revision.revision_id))) {
    throw new Error('The restore receipt does not match the reviewed Run. Retry the same restore to verify it.')
  }
}

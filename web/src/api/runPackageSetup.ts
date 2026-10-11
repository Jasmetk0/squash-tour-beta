/** Contracts for source-backed, Run/Branch-owned Package preview/confirm. */
export type RunSourcePackageKind = 'world' | 'calendar'

export type RunSourcePackagePreview = {
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  draft_version: number
  current_state_fingerprint: string | null
  preview_fingerprint: string
  document: {
    package_type: 'World' | 'Calendar'
    package_id: string
    source_version: number
    entities: unknown[]
  }
  additions: string[]
  unchanged: string[]
  updates: string[]
  not_included: string[]
  unresolved: string[]
  automatically_resolvable: string[]
  invalid: string[]
  conflicts: string[]
}

export type RunSourcePackageConfirm = {
  command_id: string
  expected_head_revision_id: string
  expected_draft_version: number
  expected_state_fingerprint: string | null
  expected_preview_fingerprint: string
  conflict_resolutions: Record<string, 'keep_run' | 'use_source'>
}

export type RunSourcePackageApplied = {
  state: { run_id: string; branch_id: string } | null
  state_fingerprint: string | null
  draft_version: number
  already_applied: boolean
  command_id: string
}

export type RunWorkingDraftSaved = {
  run_id: string
  branch_id: string
  saved_revision: { revision_id: string }
  working_draft: {
    run_id: string
    branch_id: string
    base_saved_revision_id: string
    status: string
  }
}

export function reviewedSourcePackage(
  preview: RunSourcePackagePreview,
  runId: string,
  branchId: string,
  kind: RunSourcePackageKind,
  sourceId: string
): boolean {
  return preview.run_id === runId &&
    preview.branch_id === branchId &&
    Boolean(preview.saved_head_revision_id) &&
    Number.isInteger(preview.draft_version) &&
    preview.draft_version >= 0 &&
    /^[0-9a-f]{64}$/.test(preview.preview_fingerprint) &&
    preview.document.package_type === (kind === 'world' ? 'World' : 'Calendar') &&
    preview.document.package_id === (kind === 'world' ? sourceId : `calendar-${sourceId}`) &&
    Array.isArray(preview.document.entities) &&
    ['additions', 'unchanged', 'updates', 'not_included', 'unresolved', 'invalid', 'conflicts'].every(
      key => Array.isArray(preview[key as keyof RunSourcePackagePreview])
    )
}

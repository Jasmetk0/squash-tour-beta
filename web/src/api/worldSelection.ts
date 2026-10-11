
/** Server-verified, selection-bound World source import. IDs are canonical entity labels. */
export type WorldSelectionRequest = {
  selected_entities: string[]
  conflict_resolutions: Record<string, 'keep_run' | 'use_source'>
}
export type WorldSelectionOption = {
  label: string
  entity_kind: string
  scope: string
  status: 'add' | 'update' | 'unchanged' | 'invalid'
  valid: boolean
  local_divergence: boolean
}
export type WorldSelectionField = { field: string; before: unknown; after: unknown }
export type WorldSelectionChange = {
  label: string
  entity_kind: string
  scope: string
  status: 'add' | 'update' | 'unchanged' | 'keep_run'
  local_divergence: boolean
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  fields: WorldSelectionField[]
}
export type WorldSelectionPreview = {
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  draft_version: number
  current_state_fingerprint: string | null
  preview_fingerprint: string
  selection_fingerprint: string
  source: { package_id: string; source_version: number; source_fingerprint: string }
  available: WorldSelectionOption[]
  selected_entities: string[]
  excluded_entities: string[]
  changes: WorldSelectionChange[]
  blockers: string[]
  can_confirm: boolean
}
export type WorldSelectionConfirm = WorldSelectionRequest & {
  command_id: string
  expected_head_revision_id: string
  expected_draft_version: number
  expected_state_fingerprint: string | null
  expected_preview_fingerprint: string
  expected_selection_fingerprint: string
}
export function isExactWorldSelection(
  p: WorldSelectionPreview, worldId: string, runId: string, branchId: string,
  selected: string[], resolutions: Record<string, 'keep_run' | 'use_source'>
): boolean {
  return p.run_id === runId && p.branch_id === branchId &&
    p.source.package_id === worldId &&
    Boolean(p.saved_head_revision_id) &&
    /^[0-9a-f]{64}$/.test(p.preview_fingerprint) &&
    /^[0-9a-f]{64}$/.test(p.selection_fingerprint) &&
    p.selected_entities.join('|') === [...selected].sort().join('|') &&
    p.available.every(opt => typeof opt.label === 'string') &&
    p.changes.every(change => p.selected_entities.includes(change.label)) &&
    Object.keys(resolutions).every(label => selected.includes(label))
}

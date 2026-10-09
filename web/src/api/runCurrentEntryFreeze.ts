import type { AuthoritativeSimulationPosition } from './types'

export type CurrentEntryDecisionPreview = {
  schema_version: 'pre_alpha_fax_current_entry_decision_preview.v1'
  run_id: string
  branch_id: string
  current_week: { season_index: number; week: number }
  decision_slot_ordinal: number
  event_ids: string[]
  seed: number
  expected_revision_id: string
  expected_position_fingerprint: string
  entry_batch_fingerprint: string
  application_decisions_fingerprint: string
  slot_fingerprint: string
  decision_count: number
  persisted: boolean
  preview_fingerprint: string
}

export type CurrentEntryDecisionApplyResult = {
  schema_version: 'pre_alpha_fax_current_entry_decision_apply.v1'
  run_id: string
  branch_id: string
  current_week: { season_index: number; week: number }
  decision_slot_ordinal: number
  event_ids: string[]
  decision_count: number
  slot_fingerprint: string
  adoption: 'committed' | 'exact_retry'
  validation_required: true
  validation_policy_status: 'automatic_policy_unresolved'
  application_fingerprint: string
}

const sha = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)

export function verifiedCurrentEntryPreview(
  preview: CurrentEntryDecisionPreview | null | undefined,
  position: AuthoritativeSimulationPosition | null | undefined,
  runId: string, branchId: string, eventId: string,
  savedHeadId: string
): preview is CurrentEntryDecisionPreview {
  if (!preview || !position || !savedHeadId ||
    preview.schema_version !== 'pre_alpha_fax_current_entry_decision_preview.v1' ||
    preview.run_id !== runId || preview.branch_id !== branchId ||
    position.run_id !== runId || position.branch_id !== branchId ||
    position.current_slot_kind !== 'entry' ||
    !Number.isInteger(position.slot_ordinal) || position.slot_ordinal! < 1 ||
    preview.decision_slot_ordinal !== position.slot_ordinal ||
    preview.expected_revision_id !== savedHeadId ||
    preview.expected_position_fingerprint !== position.position_fingerprint ||
    !sha(position.position_fingerprint) ||
    !sha(preview.expected_position_fingerprint) ||
    !sha(preview.entry_batch_fingerprint) ||
    !sha(preview.application_decisions_fingerprint) ||
    !sha(preview.slot_fingerprint) ||
    !sha(preview.preview_fingerprint) ||
    preview.current_week.season_index !== position.current_week.season_index ||
    preview.current_week.week !== position.current_week.week ||
    preview.seed !== 12345 ||
    !Number.isInteger(preview.decision_count) || preview.decision_count < 0 ||
    typeof preview.persisted !== 'boolean' ||
    !Array.isArray(preview.event_ids) ||
    !preview.event_ids.includes(eventId)) return false
  return preview.event_ids.length === new Set(preview.event_ids).size &&
    preview.event_ids.every(id => typeof id === 'string' && id.length > 0) &&
    preview.event_ids.every((id, index) => index === 0 || preview.event_ids[index - 1] < id)
}

export function verifiedCurrentEntryApply(
  result: CurrentEntryDecisionApplyResult | null | undefined,
  preview: CurrentEntryDecisionPreview
): boolean {
  return Boolean(result &&
    result.schema_version === 'pre_alpha_fax_current_entry_decision_apply.v1' &&
    result.run_id === preview.run_id && result.branch_id === preview.branch_id &&
    result.current_week.season_index === preview.current_week.season_index &&
    result.current_week.week === preview.current_week.week &&
    result.decision_slot_ordinal === preview.decision_slot_ordinal &&
    result.slot_fingerprint === preview.slot_fingerprint &&
    result.decision_count === preview.decision_count &&
    result.event_ids.length === preview.event_ids.length &&
    result.event_ids.every((id, i) => id === preview.event_ids[i]) &&
    ['committed','exact_retry'].includes(result.adoption) &&
    result.validation_required === true &&
    result.validation_policy_status === 'automatic_policy_unresolved' &&
    sha(result.application_fingerprint))
}

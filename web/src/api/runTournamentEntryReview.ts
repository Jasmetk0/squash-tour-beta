import type {
  AuthoritativeEntryDecisionSlotInspection,
  AuthoritativeExplicitApplicationValidationPayload,
  AuthoritativeSimulationPosition
} from './types'

export type EntryValidationOutcome = {
  outcome: '' | 'valid' | 'invalid'
  reason: string
}

export type ReviewedEntryValidation = {
  runId: string
  branchId: string
  selectedEventId: string
  savedHeadId: string
  slotFingerprint: string
  positionFingerprint: string
  decisionCount: number
  payload: AuthoritativeExplicitApplicationValidationPayload
}

const sha = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)

export const decisionKey = (eventId: string, playerId: string): string =>
  JSON.stringify([eventId, playerId])

export function verifiedFrozenEntrySlot(
  position: AuthoritativeSimulationPosition | null | undefined,
  inspection: AuthoritativeEntryDecisionSlotInspection | null | undefined,
  runId: string, branchId: string, eventId: string
): inspection is AuthoritativeEntryDecisionSlotInspection {
  if (!position || !inspection ||
    position.run_id !== runId || position.branch_id !== branchId ||
    position.current_slot_kind !== 'entry' ||
    !Number.isInteger(position.slot_ordinal) || position.slot_ordinal! < 1 ||
    !sha(position.position_fingerprint) ||
    inspection.run_id !== runId || inspection.branch_id !== branchId ||
    inspection.decision_slot_ordinal !== position.slot_ordinal ||
    inspection.authority.run_id !== runId || inspection.authority.branch_id !== branchId ||
    inspection.authority.decision_slot_ordinal !== position.slot_ordinal ||
    inspection.authority.schema_version !== 'run_entry_decision_slot_authority.v1' ||
    !sha(inspection.slot_fingerprint) ||
    inspection.week.season_index !== position.current_week.season_index ||
    inspection.week.week !== position.current_week.week ||
    inspection.authority.week.season_index !== position.current_week.season_index ||
    inspection.authority.week.week !== position.current_week.week ||
    !Array.isArray(inspection.authority.decisions) ||
    inspection.validation_resolved ||
    inspection.authority.decisions.length === 0 ||
    !inspection.authority.decisions.some(row => row.event_id === eventId)) return false

  const keys = new Set<string>()
  for (const decision of inspection.authority.decisions) {
    if (!decision.event_id || !decision.player_id ||
      !['MAIN', 'QUALIFICATION'].includes(decision.target) ||
      !sha(decision.source_decision_fingerprint)) return false
    const key = decisionKey(decision.event_id, decision.player_id)
    if (keys.has(key)) return false
    keys.add(key)
  }
  return true
}

export function buildReviewedEntryValidation(
  position: AuthoritativeSimulationPosition,
  inspection: AuthoritativeEntryDecisionSlotInspection,
  runId: string, branchId: string, eventId: string, savedHeadId: string,
  outcomes: Record<string, EntryValidationOutcome>,
  operator: string, reason: string, commandId: string
): ReviewedEntryValidation {
  if (!savedHeadId || !operator.trim() || !reason.trim() || !commandId ||
    !verifiedFrozenEntrySlot(position, inspection, runId, branchId, eventId))
    throw new Error('The frozen Run/Branch entry slot and operator review are required.')
  const reviews = inspection.authority.decisions.map(decision => {
    const outcome = outcomes[decisionKey(decision.event_id, decision.player_id)]
    if (!outcome || !['valid', 'invalid'].includes(outcome.outcome))
      throw new Error('Every frozen decision across all simultaneous events must be reviewed.')
    if (outcome.outcome === 'invalid' && !outcome.reason.trim())
      throw new Error('Every rejected application needs an explicit reason.')
    return {
      event_id: decision.event_id, player_id: decision.player_id,
      outcome: outcome.outcome as 'valid' | 'invalid',
      reasons: outcome.outcome === 'invalid' ? [outcome.reason.trim()] : []
    }
  })
  return {
    runId, branchId, selectedEventId: eventId, savedHeadId,
    slotFingerprint: inspection.slot_fingerprint,
    positionFingerprint: position.position_fingerprint,
    decisionCount: reviews.length,
    payload: {
      command_id: commandId, expected_week: position.current_week,
      expected_revision_id: savedHeadId,
      expected_position_fingerprint: position.position_fingerprint,
      decision_slot_ordinal: position.slot_ordinal!,
      expected_entry_slot_fingerprint: inspection.slot_fingerprint,
      operator_label: operator.trim(), reason: reason.trim(), reviews
    }
  }
}

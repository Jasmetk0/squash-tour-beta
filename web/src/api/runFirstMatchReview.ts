import type {
  AuthoritativeMatchReconstructionState,
  AuthoritativeMatchReplayContext,
  AuthoritativeMatchReplayList,
  AuthoritativeSimulationPosition,
  AuthoritativeWeekScheduleInspection
} from './types'

const sha = (v: unknown): v is string =>
  typeof v === 'string' && /^[a-f0-9]{64}$/.test(v)

export type ReviewedFirstMatchEvidence = {
  runId: string
  branchId: string
  eventId: string
  head: string
  draftVersion: number
  positionFingerprint: string
  week: { season_index: number; week: number }
  groupId: string
  matchId: string
  slotId: string
  slotOrdinal: number
  slotStartFingerprint: string
  playerAId: string
  playerBId: string
  drawFingerprint: string
  scheduleFingerprint: string
  commandId: string
}

export function verifiedScheduledMatch(
  position: AuthoritativeSimulationPosition | null | undefined,
  inspection: AuthoritativeMatchReconstructionState | null | undefined,
  schedule: AuthoritativeWeekScheduleInspection | null | undefined,
  runId: string, branchId: string, eventId: string, revisionId: string
): inspection is AuthoritativeMatchReconstructionState {
  if (!position || !inspection || !schedule || !revisionId ||
    position.run_id !== runId || position.branch_id !== branchId ||
    position.current_slot_kind !== 'match' ||
    !Number.isSafeInteger(position.slot_ordinal) || (position.slot_ordinal ?? 0) < 1 ||
    !sha(position.position_fingerprint) ||
    !position.eligible_match_ids.includes(inspection.group_id) ||
    schedule.run_id !== runId || schedule.branch_id !== branchId ||
    !sha(schedule.schedule_fingerprint) ||
    schedule.schedule?.schema_version !== 'week_simulation_schedule.v2' ||
    schedule.schedule.run_id !== runId || schedule.schedule.branch_id !== branchId ||
    schedule.week.season_index !== position.current_week.season_index ||
    schedule.week.week !== position.current_week.week ||
    schedule.schedule.week.season_index !== position.current_week.season_index ||
    schedule.schedule.week.week !== position.current_week.week ||
    inspection.run_id !== runId || inspection.branch_id !== branchId ||
    inspection.event_id !== eventId ||
    inspection.expected_revision_id !== revisionId ||
    inspection.position_fingerprint !== position.position_fingerprint ||
    inspection.week.season_index !== position.current_week.season_index ||
    inspection.week.week !== position.current_week.week ||
    inspection.slot_id !== position.current_slot_id ||
    !sha(inspection.slot_start_fingerprint) ||
    !inspection.match_id || !inspection.group_id ||
    !inspection.player_a_id || !inspection.player_b_id ||
    inspection.player_a_id === inspection.player_b_id) return false

  return schedule.schedule.slots.some(slot =>
    slot.ordinal === position.slot_ordinal &&
    slot.event_id === eventId &&
    slot.group_ids.includes(inspection.group_id) &&
    (slot.draw_phase === 'main' || slot.draw_phase === 'qualification') &&
    (slot.round_number ?? 0) >= 1 &&
    Number.isInteger(slot.match_day_ordinal) &&
    (slot.match_day_ordinal ?? 0) >= 1 &&
    Number.isInteger(slot.match_order) &&
    (slot.match_order ?? 0) >= 1)
}

export function verifiedMatchReplay(
  list: AuthoritativeMatchReplayList | null | undefined,
  context: AuthoritativeMatchReplayContext | null | undefined,
  evidence: ReviewedFirstMatchEvidence
): { winnerId: string; loserId: string; resultFingerprint: string; totalRallies: number } | null {
  if (!list || !context ||
    list.schema_version !== 'authoritative_match_replay_list.v1' ||
    list.run_id !== evidence.runId || list.branch_id !== evidence.branchId ||
    list.read_only !== true ||
    context.schema_version !== 'authoritative_match_replay_context.v1' ||
    context.run_id !== evidence.runId || context.branch_id !== evidence.branchId ||
    context.group_id !== evidence.groupId || context.match_id !== evidence.matchId ||
    context.event_id !== evidence.eventId || context.slot_id !== evidence.slotId ||
    context.summary.player_a_id !== evidence.playerAId ||
    context.summary.player_b_id !== evidence.playerBId ||
    context.verified !== true || context.read_only !== true ||
    context.rng_rerun !== false || context.replay_source !== 'stored_authoritative_events' ||
    !sha(context.result_fingerprint)) return null
  const row = list.matches.find(match =>
    match.group_id === evidence.groupId &&
    match.match_id === evidence.matchId &&
    match.slot_id === evidence.slotId &&
    match.result_fingerprint === context.result_fingerprint &&
    match.replay_available &&
    sha(match.result_fingerprint) &&
    Number.isInteger(match.total_rallies) && match.total_rallies > 0)
  if (!row) return null
  const players = new Set([evidence.playerAId,evidence.playerBId])
  if (!players.has(row.winner_player_id) ||
    !players.has(row.loser_player_id) ||
    row.winner_player_id === row.loser_player_id) return null
  return {
    winnerId: row.winner_player_id,
    loserId: row.loser_player_id,
    resultFingerprint: row.result_fingerprint,
    totalRallies: row.total_rallies
  }
}

import type {
  CanonicalTournamentPreparationState,
  CanonicalTournamentEntryFieldState,
  CanonicalTournamentDrawState,
  CanonicalTournamentDrawAuthority
} from './types'

const sha = (v: unknown): v is string =>
  typeof v === 'string' && /^[0-9a-f]{64}$/.test(v)

export function verifiedDrawInputSource(
  preparation: CanonicalTournamentPreparationState | null | undefined,
  field: CanonicalTournamentEntryFieldState | null | undefined,
  draw: CanonicalTournamentDrawState | null | undefined,
  runId: string, branchId: string, eventId: string
): boolean {
  return Boolean(preparation && field && draw &&
    preparation.schema_version === 'canonical_tournament_preparation_state.v1' &&
    preparation.run_id === runId && preparation.branch_id === branchId &&
    preparation.event_id === eventId &&
    preparation.authority_source === 'run_owned_db_authorities.v1' &&
    preparation.entry_field_ready === true &&
    preparation.ranking_snapshot_ready === true &&
    preparation.next_required_action === 'review_pre_draw_or_commit_draw_input' &&
    !preparation.wild_card_required || false)
}

/** Complete early-fail guard: never show Draw commit on unready Wild Card or stale field. */
export function canReviewInitialDrawInput(
  preparation: CanonicalTournamentPreparationState | null | undefined,
  field: CanonicalTournamentEntryFieldState | null | undefined,
  draw: CanonicalTournamentDrawState | null | undefined,
  runId: string, branchId: string, eventId: string
): boolean {
  return Boolean(preparation && field && draw &&
    preparation.schema_version === 'canonical_tournament_preparation_state.v1' &&
    preparation.authority_source === 'run_owned_db_authorities.v1' &&
    preparation.run_id === runId && preparation.branch_id === branchId &&
    preparation.event_id === eventId &&
    preparation.entry_field_ready === true &&
    preparation.ranking_snapshot_ready === true &&
    preparation.next_required_action === 'review_pre_draw_or_commit_draw_input' &&
    (!preparation.wild_card_required || preparation.wild_card_ready === true) &&
    !preparation.blockers.length &&
    field.schema_version === 'canonical_tournament_entry_field_state.v2' &&
    field.run_id === runId && field.branch_id === branchId && field.event_id === eventId &&
    sha(field.field_fingerprint) && field.field_sequence >= 1 &&
    draw.schema_version === 'canonical_tournament_draw_state.v1' &&
    draw.run_id === runId && draw.branch_id === branchId && draw.event_id === eventId &&
    draw.field_fingerprint === field.field_fingerprint &&
    draw.field_sequence === field.field_sequence &&
    draw.main_draw_capacity === field.main_draw_capacity &&
    draw.effective_main_bye_count === field.effective_main_bye_count &&
    !field.draw_input_committed && !draw.draw_input_committed &&
    !draw.initial_draw_generated &&
    draw.draw_input_fingerprint == null &&
    draw.draw_authority_fingerprint == null)
}

export function verifiedCommittedDrawInput(
  draw: CanonicalTournamentDrawState | null | undefined,
  field: CanonicalTournamentEntryFieldState,
  runId: string, branchId: string, eventId: string,
  seed: number
): boolean {
  return Boolean(draw && draw.schema_version === 'canonical_tournament_draw_state.v1' &&
    draw.run_id === runId && draw.branch_id === branchId && draw.event_id === eventId &&
    draw.field_sequence === field.field_sequence &&
    draw.field_fingerprint === field.field_fingerprint &&
    draw.main_draw_capacity === field.main_draw_capacity &&
    draw.draw_input_committed === true && sha(draw.draw_input_fingerprint) &&
    draw.draw_seed === seed &&
    Number.isInteger(draw.main_seed_count) &&
    Number.isInteger(draw.qualification_seed_count))
}

export function verifiedGeneratedFirstDraw(
  draw: CanonicalTournamentDrawState | null | undefined,
  authority: CanonicalTournamentDrawAuthority | null | undefined,
  field: CanonicalTournamentEntryFieldState,
  expectedDrawInputFingerprint: string,
  runId: string, branchId: string, eventId: string
): boolean {
  if (!draw || !authority ||
    !draw.initial_draw_generated ||
    draw.run_id !== runId || draw.branch_id !== branchId || draw.event_id !== eventId ||
    draw.field_fingerprint !== field.field_fingerprint ||
    draw.field_sequence !== field.field_sequence ||
    draw.draw_input_fingerprint !== expectedDrawInputFingerprint ||
    !sha(draw.draw_authority_fingerprint) ||
    ![ 'tournament_draw_authority.v1','tournament_draw_authority.v2' ].includes(authority.schema_version) ||
    authority.run_id !== runId || authority.branch_id !== branchId ||
    authority.event_id !== eventId ||
    authority.draw_input_fingerprint !== expectedDrawInputFingerprint ||
    ![ 'protected_seed_shuffle.v1','idealized_seed_tiers.v2' ].includes(authority.algorithm_version) ||
    authority.main.bracket_size !== field.main_draw_capacity ||
    authority.main.slots.length !== field.main_draw_capacity ||
    authority.main.bye_slot_indexes.length !== draw.main_bye_count ||
    draw.main_bye_count !== field.effective_main_bye_count ||
    draw.main_slot_count !== field.main_draw_capacity) return false

  const mainIds = authority.main.slots.filter(s => s.entrant_kind === 'player')
    .map(s => s.player_id).filter((s): s is string => typeof s === 'string')
  if (mainIds.length !== new Set(mainIds).size ||
    field.direct_main_player_ids.some(id => !mainIds.includes(id))) return false
  const q = authority.qualification_sections?.length
    ? authority.qualification_sections
    : authority.qualification ? [authority.qualification] : []
  const qIds = q.flatMap(bracket => bracket.slots
    .filter(slot => slot.entrant_kind === 'player')
    .map(slot => slot.player_id)
    .filter((s): s is string => typeof s === 'string'))
  if (qIds.length !== new Set(qIds).size ||
    field.qualification_player_ids.some(id => !qIds.includes(id))) return false
  if (authority.main.slots.filter(slot => slot.entrant_kind === 'bye').length !==
    field.effective_main_bye_count) return false
  return true
}

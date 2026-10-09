import type {
  CanonicalTournamentPreparationState,
  CanonicalTournamentEntryFieldState,
  TournamentEntryField,
  TournamentEntryFieldCapacity
} from './types'

export type ReviewedEntryFieldPreview = {
  preview_only: true
  run_id: string
  branch_id: string
  event_id: string
  field_fingerprint: string
  field: TournamentEntryField
}

const sha = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v)

export function strictCapacity(value: TournamentEntryFieldCapacity): boolean {
  const c = value
  return [c.main_draw_size, c.qualification_draw_size, c.qualifier_spots,
    c.wild_card_slots, c.bye_slots].every(Number.isSafeInteger) &&
    [2,4,8,16,32,64,128].includes(c.main_draw_size) &&
    c.qualification_draw_size >= 0 && c.qualification_draw_size <= 128 &&
    c.qualifier_spots >= 0 && c.wild_card_slots >= 0 && c.bye_slots >= 0 &&
    c.qualifier_spots + c.wild_card_slots + c.bye_slots <= c.main_draw_size
}

export function verifiedEntryFieldSource(
  preparation: CanonicalTournamentPreparationState | null | undefined,
  runId: string, branchId: string, eventId: string
): preparation is CanonicalTournamentPreparationState {
  return Boolean(preparation &&
    preparation.schema_version === 'canonical_tournament_preparation_state.v1' &&
    preparation.authority_source === 'run_owned_db_authorities.v1' &&
    preparation.run_id === runId && preparation.branch_id === branchId &&
    preparation.event_id === eventId &&
    preparation.next_required_action === 'build_entry_field' &&
    preparation.phase === 'entry_field_required' &&
    preparation.entry_source_kind === 'ranking_applications' &&
    preparation.ranking_snapshot_ready === true &&
    !preparation.entry_field_ready &&
    sha(preparation.preparation_fingerprint) &&
    sha(preparation.ranking_authority_fingerprint) &&
    preparation.valid_submission_count != null && preparation.valid_submission_count > 0 &&
    preparation.valid_main_submission_count != null &&
    preparation.valid_qualification_submission_count != null &&
    preparation.valid_main_submission_count +
      preparation.valid_qualification_submission_count === preparation.valid_submission_count &&
    preparation.entry_capacity_suggestion?.source === 'run_owned_calendar_package.v1' &&
    sha(preparation.entry_capacity_suggestion.source_package_fingerprint) &&
    sha(preparation.entry_capacity_suggestion.source_event_fingerprint))
}

export function verifiedReviewedEntryField(
  preview: ReviewedEntryFieldPreview,
  preparation: CanonicalTournamentPreparationState,
  runId: string, branchId: string, eventId: string,
  capacity: TournamentEntryFieldCapacity
): boolean {
  if (!verifiedEntryFieldSource(preparation,runId,branchId,eventId) ||
    preview?.preview_only !== true || preview.run_id !== runId ||
    preview.branch_id !== branchId || preview.event_id !== eventId ||
    !sha(preview.field_fingerprint) ||
    preview.field.schema_version !== 'tournament_entry_field.v1' ||
    preview.field.run_id !== runId || preview.field.branch_id !== branchId ||
    preview.field.event_id !== eventId || preview.field.mode !== 'initial' ||
    (preview.field.source_kind != null && preview.field.source_kind !== 'ranking_applications') ||
    preview.field.tournament_ranking_authority_fingerprint !== preparation.ranking_authority_fingerprint ||
    !sha(preview.field.applications_fingerprint) ||
    !sha(preview.field.ranking_snapshot_fingerprint) ||
    !strictCapacity(capacity) ||
    ![ 'main_draw_size','qualification_draw_size','qualifier_spots','wild_card_slots','bye_slots' ]
      .every(key => (preview.field.capacity as unknown as Record<string,number>)[key] ===
        (capacity as unknown as Record<string,number>)[key]) ||
    preview.field.base_field_fingerprint != null) return false
  const field = preview.field
  const ids = [
    ...field.direct_main_player_ids, ...field.qualification_player_ids,
    ...field.below_qualification_cut_player_ids
  ]
  return ids.length === preparation.valid_submission_count &&
    ids.length === new Set(ids).size &&
    field.direct_main_player_ids.length <= capacity.main_draw_size -
      capacity.qualifier_spots - capacity.wild_card_slots - capacity.bye_slots &&
    field.qualification_player_ids.length <= capacity.qualification_draw_size &&
    field.withdrawn_player_ids.length === 0
}

export function verifiedStoredEntryField(
  stored: CanonicalTournamentEntryFieldState | null | undefined,
  preview: ReviewedEntryFieldPreview
): boolean {
  return Boolean(stored &&
    stored.schema_version === 'canonical_tournament_entry_field_state.v2' &&
    stored.run_id === preview.run_id && stored.branch_id === preview.branch_id &&
    stored.event_id === preview.event_id &&
    stored.field_sequence === 1 && stored.mode === 'initial' &&
    stored.field_fingerprint === preview.field_fingerprint &&
    stored.main_draw_capacity === preview.field.capacity.main_draw_size &&
    stored.direct_main_player_ids.length === preview.field.direct_main_player_ids.length &&
    stored.direct_main_player_ids.every((v,i)=>v===preview.field.direct_main_player_ids[i]) &&
    stored.qualification_player_ids.length === preview.field.qualification_player_ids.length &&
    stored.qualification_player_ids.every((v,i)=>v===preview.field.qualification_player_ids[i]) &&
    stored.below_qualification_cut_player_ids.length === preview.field.below_qualification_cut_player_ids.length &&
    stored.below_qualification_cut_player_ids.every((v,i)=>v===preview.field.below_qualification_cut_player_ids[i]) &&
    stored.withdrawn_player_ids.length === 0)
}

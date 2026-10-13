import type { CanonicalTournamentPreparationState } from '../api/types'

/** Knockout stays the normal workflow; this is an explicit opt-in before Draw Input is frozen. */
export function canOfferPureGroupSetup(
  preparation: CanonicalTournamentPreparationState | null | undefined,
  hasVerifiedEntryField: boolean
): boolean {
  return Boolean(
    hasVerifiedEntryField &&
    preparation?.entry_field_ready &&
    preparation.entry_source_kind === 'ranking_applications' &&
    preparation.next_required_action === 'review_pre_draw_or_commit_draw_input' &&
    !preparation.format_authority_ready &&
    !preparation.draw_input_ready &&
    !preparation.draw_ready
  )
}

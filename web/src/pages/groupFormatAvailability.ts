import type { CanonicalTournamentPreparationState } from '../api/types'

export type GroupFormatReadiness = Pick<
  CanonicalTournamentPreparationState,
  | 'entry_field_ready'
  | 'entry_source_kind'
  | 'next_required_action'
  | 'format_authority_ready'
  | 'draw_input_ready'
  | 'draw_ready'
>

/** Knockout stays the standard path; group opt-in is available only before any draw authority. */
export function canOfferPureGroupSetup(
  preparation: GroupFormatReadiness | null | undefined,
  hasVerifiedEntryField: boolean
): boolean {
  return Boolean(
    hasVerifiedEntryField &&
    preparation?.entry_field_ready === true &&
    preparation.entry_source_kind === 'ranking_applications' &&
    preparation.next_required_action === 'review_pre_draw_or_commit_draw_input' &&
    preparation.format_authority_ready === false &&
    preparation.draw_input_ready === false &&
    preparation.draw_ready === false
  )
}

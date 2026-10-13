import { describe, expect, it } from 'vitest'
import type { CanonicalTournamentPreparationState } from '../api/types'
import { canOfferPureGroupSetup } from './groupFormatAvailability'

const preparation = {
  entry_field_ready: true,
  entry_source_kind: 'ranking_applications',
  next_required_action: 'review_pre_draw_or_commit_draw_input',
  format_authority_ready: false,
  draw_input_ready: false,
  draw_ready: false,
} as CanonicalTournamentPreparationState

describe('explicit pure-group option for ordinary Run tournaments', () => {
  it('offers group setup only with a verified frozen ranking-applications Entry Field', () => {
    expect(canOfferPureGroupSetup(preparation, true)).toBe(true)
    expect(canOfferPureGroupSetup(preparation, false)).toBe(false)
    expect(canOfferPureGroupSetup(null, true)).toBe(false)
    expect(canOfferPureGroupSetup({ ...preparation, entry_field_ready: false }, true)).toBe(false)
    expect(canOfferPureGroupSetup({ ...preparation, entry_source_kind: 'finals_participant_selection' }, true)).toBe(false)
  })

  it('never offers an alternative once a sporting format or draw authority is frozen', () => {
    for (const changes of [
      { format_authority_ready: true },
      { draw_input_ready: true },
      { draw_ready: true },
      { next_required_action: 'generate_draw' },
      { next_required_action: 'generate_tournament_topology' },
    ]) {
      expect(canOfferPureGroupSetup({ ...preparation, ...changes }, true)).toBe(false)
    }
  })
})

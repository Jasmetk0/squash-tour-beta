import { describe, expect, it } from 'vitest'
import { canOfferPureGroupSetup } from './groupFormatAvailability'
import type { GroupFormatReadiness } from './groupFormatAvailability'

const preparation: GroupFormatReadiness = {
  entry_field_ready: true,
  entry_source_kind: 'ranking_applications',
  next_required_action: 'review_pre_draw_or_commit_draw_input',
  format_authority_ready: false,
  draw_input_ready: false,
  draw_ready: false,
}

describe('explicit pure-group option for ordinary Run tournaments', () => {
  it('offers group setup only with verified frozen ranking-applications Entry Field', () => {
    expect(canOfferPureGroupSetup(preparation, true)).toBe(true)
    expect(canOfferPureGroupSetup(preparation, false)).toBe(false)
    expect(canOfferPureGroupSetup(null, true)).toBe(false)
    expect(canOfferPureGroupSetup({ ...preparation, entry_field_ready: false }, true)).toBe(false)
    expect(canOfferPureGroupSetup({ ...preparation, entry_source_kind: 'finals_participant_selection' }, true)).toBe(false)
  })

  it('fails closed for missing readiness values or previously frozen authorities', () => {
    for (const changes of [
      { format_authority_ready: true },
      { draw_input_ready: true },
      { draw_ready: true },
      { draw_input_ready: undefined },
      { draw_ready: undefined },
      { format_authority_ready: undefined },
      { next_required_action: 'generate_draw' as const },
      { next_required_action: 'generate_tournament_topology' as const },
    ]) {
      expect(canOfferPureGroupSetup({ ...preparation, ...changes }, true)).toBe(false)
    }
  })
})

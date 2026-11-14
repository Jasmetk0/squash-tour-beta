import { describe, expect, it } from 'vitest'
import { validSavedPlayerCareer } from './savedPlayerCareer'
import type { SavedPlayerCareer } from './savedPlayerCareer'

const f = 'f'.repeat(64)
const scope = { runId: 'run', branchId: 'branch', savedHead: 'rev-1', playerId: 'P1' }
const ev = (kind: string, week: number | null, extra = {}) => ({
  kind, detail: {}, source: { kind: 'x', fingerprint: f },
  effective_week: week === null ? null : { season_index: 0, week }, ...extra
})
const career = (patch: Partial<SavedPlayerCareer> = {}): SavedPlayerCareer => {
  const timeline = [ev('turn_pro', 2), ev('edition_result', 5)]
  return {
    schema_version: 'native_player_career.v1', run_id: 'run', branch_id: 'branch',
    saved_head_revision_id: 'rev-1', source_tour_fingerprint: f, as_of_ordinal: 6,
    player: { player_id: 'P1', name: 'P', country_code: 'CZE' },
    covered_period: { first_recorded_ranking_ordinal: 1, note: 'Coverage starts with the first ranking.' },
    overview: { status: 'professional', titles: 0, finals: 0, editions_played: 1, career_high_rank: 3, current_rank: 5 },
    milestones: [timeline[0]], timeline, unsupported: ['injury'], ...patch
  } as SavedPlayerCareer
}

describe('native player career contract (pure validator)', () => {
  it('accepts a consistent career and an opening professional without a week', () => {
    expect(validSavedPlayerCareer(career(), scope)).toBe(true)
    const opening = [ev('turn_pro', null)]
    expect(validSavedPlayerCareer(career({ timeline: opening, milestones: opening } as never), scope)).toBe(true)
  })

  it('rejects another Run, Branch, Saved HEAD, player or schema', () => {
    expect(validSavedPlayerCareer(career({ run_id: 'other' }), scope)).toBe(false)
    expect(validSavedPlayerCareer(career({ branch_id: 'sibling' }), scope)).toBe(false)
    expect(validSavedPlayerCareer(career({ saved_head_revision_id: 'rev-2' }), scope)).toBe(false)
    expect(validSavedPlayerCareer(career({ player: { player_id: 'P2', name: 'x', country_code: 'CZE' } }), scope)).toBe(false)
    expect(validSavedPlayerCareer({ ...career(), schema_version: 'native_player_career.v2' } as never, scope)).toBe(false)
    expect(validSavedPlayerCareer(null, scope)).toBe(false)
  })

  it('rejects unknown kinds, missing sources and a weekless non-opening fact', () => {
    expect(validSavedPlayerCareer(career({ timeline: [ev('mystery', 3)] } as never), scope)).toBe(false)
    const noSource = { ...ev('turn_pro', 2), source: { kind: 'x', fingerprint: 'short' } }
    expect(validSavedPlayerCareer(career({ timeline: [noSource], milestones: [] } as never), scope)).toBe(true)
    expect(validSavedPlayerCareer(career({ timeline: [{ ...noSource, source: undefined }], milestones: [] } as never), scope)).toBe(false)
    expect(validSavedPlayerCareer(career({ timeline: [ev('edition_result', null)], milestones: [] } as never), scope)).toBe(false)
  })

  it('rejects a milestone that is not backed by a recorded timeline fact', () => {
    const invented = ev('first_recorded_title', 9, { source: { kind: 'played_edition', fingerprint: 'e'.repeat(64) } })
    expect(validSavedPlayerCareer(career({ milestones: [invented] } as never), scope)).toBe(false)
  })

  it('rejects impossible counts and ranks', () => {
    expect(validSavedPlayerCareer(career({ overview: { ...career().overview, titles: -1 } }), scope)).toBe(false)
    expect(validSavedPlayerCareer(career({ overview: { ...career().overview, career_high_rank: 0 } }), scope)).toBe(false)
    expect(validSavedPlayerCareer(career({ overview: { ...career().overview, status: 'legend' as never } }), scope)).toBe(false)
  })
  it('rejects a title relabelled from an unrelated fact with the same source and week', () => {
    const unrelated = ev('career_high_ranking', 5)
    const invented = { ...unrelated, kind: 'first_recorded_title' }
    expect(validSavedPlayerCareer(career({ timeline: [unrelated], milestones: [invented] }), scope)).toBe(false)
  })

  it('rejects a malformed retired timeline without throwing', () => {
    const data = career({ overview: { ...career().overview, status: 'retired' },
      timeline: [null] as never, milestones: [], retirement_summary: {
        titles: 0, finals: 0, editions_played: 0, career_high_rank: null,
        retired_week: { season_index: 0, week: 6 }, source: { kind: 'week_transition', fingerprint: f }
      } as never })
    expect(validSavedPlayerCareer(data, scope)).toBe(false)
  })

})

import { describe, expect, it } from 'vitest'
import { verifyKnockoutInspection, type KnockoutInspection, type KnockoutSportingState } from './calendarOpeningKnockout'

function fixture(): KnockoutInspection {
  const calendar = { schema_version: 'run_calendar.v1', weeks_per_year: 52, season_start_year_week: 1, start_year: 2030, season_count: 3 }
  const match = (round: string, slot: number, a: string, b: string, winner: string) => ({
    round, slot, seed: 5,
    input_context: { match_id: round, player_a: { player: { player_id: a } }, player_b: { player: { player_id: b } } },
    result: { winner_player_id: winner, loser_player_id: winner === a ? b : a, rally_log: { events: [{}] }, sets_won: {} },
  })
  const states = ['a', 'b', 'c', 'd'].map(player_id => ({ player_id, current_form: 100, match_sharpness: 100, long_term_fatigue: 0 }))
  const sporting: KnockoutSportingState = {
    schema_version: 'calendar_knockout_sporting.v1',
    initial: structuredClone(states), after_semifinals: structuredClone(states), terminal: structuredClone(states),
    effects: ['a', 'b', 'c', 'd', 'a', 'c'].map(player_id => ({
      player_id, match_id: 'm', input_fingerprint: 'c'.repeat(64),
      result_fingerprint: 'd'.repeat(64), source_checkpoint_fingerprint: 'e'.repeat(64),
    })), health_effects_applied: false, annual_development_applied: false,
  }
  return {
    schema_version: 'calendar_opening_knockout_inspection.v1', run_id: 'r', branch_id: 'b',
    saved_head_revision_id: 'head', draft_version: 2, run_calendar: calendar,
    initial_world_fingerprint: 'a'.repeat(64), player_ids: ['a', 'b', 'c', 'd'],
    knockout: { schema_version: 'calendar_opening_knockout.v2', run_id: 'r', branch_id: 'b', match_id: 'ko',
      week: { season_index: 0, week: 1, calendar }, entrant_ids: ['a', 'b', 'c', 'd'], sporting,
      matches: [match('semifinal_1', 1, 'a', 'b', 'a'), match('semifinal_2', 1, 'c', 'd', 'c'), match('final', 2, 'a', 'c', 'a')],
    }, knockout_fingerprint: 'b'.repeat(64), saved: true, prepared_points: null,
  } as KnockoutInspection
}

describe('versioned knockout checkpoint response boundary', () => {
  it('accepts new state and old v1 without silently adding checkpoints', () => {
    const v = fixture()
    expect(verifyKnockoutInspection(v, 'r', 'b', 'head')).toBe(v)
    v.knockout!.schema_version = 'calendar_opening_knockout.v1'
    delete v.knockout!.sporting
    expect(verifyKnockoutInspection(v, 'r', 'b', 'head')).toBe(v)
  })
  it.each(['missing', 'range', 'roster', 'duplicate', 'effects', 'legacy'])('rejects %s state', fault => {
    const v = fixture(), k = v.knockout!, s = k.sporting!
    if (fault === 'missing') delete k.sporting
    if (fault === 'range') s.terminal[0].long_term_fatigue = 101
    if (fault === 'roster') s.after_semifinals[0].player_id = 'foreign'
    if (fault === 'duplicate') s.initial[0].player_id = s.initial[1].player_id
    if (fault === 'effects') s.effects.pop()
    if (fault === 'legacy') k.schema_version = 'calendar_opening_knockout.v1'
    expect(() => verifyKnockoutInspection(v, 'r', 'b', 'head')).toThrow()
  })
})

function healthFixture() {
  const v = fixture(), k = v.knockout!
  k.schema_version = 'calendar_opening_knockout.v3'
  const profiles = k.entrant_ids.map(player_id => ({ player_id, highest_current_severity: 0,
    highest_permanent_limitation: 0, numeric_effect_applied: false as const,
    numeric_calibration_required: false, current_records: [],
  }))
  k.health_source = { schema_version: 'calendar_knockout_health_source.v1',
    source_health_schema: 'calendar_initial_health_state.v1', source_health_fingerprint: 'f'.repeat(64),
    profiles, numeric_effect_applied: false }
  k.matches.forEach(m => { m.effective_health = { numeric_effect_applied: false,
    player_profiles: [m.input_context.player_a, m.input_context.player_b].map(p => profiles.find(x => x.player_id === p.player.player_id)!),
  } })
  return v
}

describe('Saved Health in a played knockout', () => {
  it('accepts descriptive Health without claiming numeric effects', () => {
    const v = healthFixture()
    expect(verifyKnockoutInspection(v, 'r', 'b', 'head')).toBe(v)
  })
  it.each(['missing', 'scope', 'order', 'version'])('rejects %s Health evidence', fault => {
    const v = healthFixture(), k = v.knockout!
    if (fault === 'missing') delete k.health_source
    if (fault === 'scope') k.health_source!.profiles[0].player_id = 'foreign'
    if (fault === 'order') k.matches[0].effective_health!.player_profiles.reverse()
    if (fault === 'version') k.schema_version = 'calendar_opening_knockout.v2'
    expect(() => verifyKnockoutInspection(v, 'r', 'b', 'head')).toThrow()
  })
})

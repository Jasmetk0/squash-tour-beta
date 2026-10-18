import { describe, expect, it } from 'vitest'
import { verifyFollowupKnockout, type ContinuationView, type FollowupScoredCommand, type FollowupKnockoutReceipt } from './calendarContinuation'

const fp = 'a'.repeat(64)
const view: ContinuationView = {
  schema_version: 'calendar_continuation_inspection.v1',
  run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'head', draft_version: 1,
  checkpoint_fingerprint: fp, player_ids: ['a', 'b', 'c', 'd'],
  saved: true, can_play: true, limited_player_ids: [], health_numeric_effect_applied: false,
  matches: [],
}
const command: FollowupScoredCommand = {
  command_id: 'cmd', tournament_id: 't', expected_saved_head: 'head',
  expected_checkpoint_fingerprint: fp, entrant_ids: ['a', 'b', 'c', 'd'],
  seed: 1, operator_label: 'Admin', audit_reason: 'Review real result awards',
  point_policy: { category_label: 'Provisional', champion: 100, finalist: 60, semifinal: 30, validity_weeks: 52 },
  explicit_point_confirmation: true,
}
const match = (id: string, sequence: number, a: string, b: string, winner: string) => ({
  match_id: id, sequence, result: { player_a_id: a, player_b_id: b, winner_player_id: winner },
})
const receipt: FollowupKnockoutReceipt = {
  schema_version: 'calendar_followup_knockout_receipt.v1',
  fingerprint: 'b'.repeat(64), checkpoint_fingerprint: 'c'.repeat(64),
  winner_player_id: 'a', official_ranking_published: false,
  scope: 'sporting_exhibition_knockout_not_official',
  publication_status: 'prepared_not_official', prepared_policy_fingerprint: 'd'.repeat(64),
  prepared_awards: ([
    ['a', 'champion', 100], ['b', 'semifinal', 30],
    ['c', 'finalist', 60], ['d', 'semifinal', 30],
  ] as const).map(([player_id, reached_stage, main_points]) => ({
    player_id, reached_stage, main_points,
    source_tournament_fingerprint: 'e'.repeat(64),
    source_policy_fingerprint: 'd'.repeat(64),
  })),
  tournament: {
    run_id: 'run', branch_id: 'branch', command_id: 'cmd',
    tournament_id: 't', source_saved_head: 'head', source_checkpoint_fingerprint: fp,
    entrant_ids: ['a', 'b', 'c', 'd'],
    matches: [
      match('t:sf1', 1, 'a', 'b', 'a'),
      match('t:sf2', 2, 'c', 'd', 'c'),
      match('t:final', 3, 'a', 'c', 'a'),
    ],
  },
}

describe('prepared-scored real knockout response boundary', () => {
  it('accepts the actual four result-derived placements, never Official publication', () => {
    expect(verifyFollowupKnockout(receipt, command, view)).toBe(receipt)
  })
  it('rejects point substitutions or relabelled champion', () => {
    expect(() => verifyFollowupKnockout({
      ...receipt, prepared_awards: receipt.prepared_awards?.map(a =>
        a.player_id === 'b' ? { ...a, main_points: 500 } : a),
    }, command, view)).toThrow('Prepared points disagree')
    expect(() => verifyFollowupKnockout({
      ...receipt, prepared_awards: receipt.prepared_awards?.map(a =>
        a.player_id === 'c' ? { ...a, reached_stage: 'champion' as const } : a),
    }, command, view)).toThrow('Prepared points disagree')
  })
  it('refuses prepared points on a historical unscored command', () => {
    const { point_policy: _p, explicit_point_confirmation: _c, ...historical } = command
    expect(() => verifyFollowupKnockout(receipt, historical, view)).toThrow('Unscored knockout cannot gain')
  })
  it('rejects swapping a semifinal loser and the actual finalist with matching points', () => {
    const forged = {...receipt, prepared_awards: receipt.prepared_awards!.map(a =>
      a.player_id === 'b' ? {...a, reached_stage: 'finalist' as const, main_points: 60}
        : a.player_id === 'c' ? {...a, reached_stage: 'semifinal' as const, main_points: 30} : a)}
    expect(() => verifyFollowupKnockout(forged, command, view)).toThrow('Prepared points disagree')
  })
  it('rejects a non-participant winner even when the next pairing follows it', () => {
    const {point_policy: _p, explicit_point_confirmation: _c, ...unscored} = command
    const forged = {...receipt, prepared_awards: undefined, publication_status: undefined,
      tournament: {...receipt.tournament, matches: receipt.tournament.matches.map((m, i) =>
        i === 0 ? {...m, result: {...m.result, winner_player_id: 'd'}}
          : i === 2 ? {...m, result: {...m.result, player_a_id: 'd'}} : m)}}
    expect(() => verifyFollowupKnockout(forged, unscored, view)).toThrow('played participants')
  })
})

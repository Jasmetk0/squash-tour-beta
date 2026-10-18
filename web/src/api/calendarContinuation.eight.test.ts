import { describe, expect, it } from 'vitest'
import { verifyEightFollowupKnockout, type ContinuationView, type FollowupEightCommand, type FollowupKnockoutReceipt } from './calendarContinuation'

const hash = (value: string) => value.repeat(64)
const view: ContinuationView = {
  schema_version: 'calendar_continuation_inspection.v1', run_id: 'r', branch_id: 'b',
  saved_head_revision_id: 'head', draft_version: 1, checkpoint_fingerprint: hash('a'),
  player_ids: ['a','b','c','d','e','f','g','h'],
  saved: true, can_play: true, limited_player_ids: [], health_numeric_effect_applied: false,
  matches: [],
}
const cmd: FollowupEightCommand = {
  command_id: 'eight', tournament_id: 'draw', expected_saved_head: 'head',
  expected_checkpoint_fingerprint: hash('a'), entrant_ids: ['a','b','c','d','e','f','g','h'],
  seed: 12, operator_label: 'Admin', audit_reason: 'Actual eight-player knockout',
}
const rounds = [
  ['qf1','a','b','a'],['qf2','c','d','c'],['qf3','e','f','e'],['qf4','g','h','g'],
  ['sf1','a','c','c'],['sf2','e','g','e'],['final','c','e','c'],
] as const
const receipt: FollowupKnockoutReceipt = {
  schema_version: 'calendar_followup_knockout_receipt.v1', fingerprint: hash('b'),
  checkpoint_fingerprint: hash('c'), winner_player_id: 'c', official_ranking_published: false,
  scope: 'sporting_exhibition_knockout_not_official',
  tournament: {
    schema_version: 'calendar_followup_knockout.v3', run_id: 'r', branch_id: 'b',
    command_id: 'eight', tournament_id: 'draw', source_saved_head: 'head',
    source_checkpoint_fingerprint: hash('a'), entrant_ids: cmd.entrant_ids,
    matches: rounds.map(([round,a,b,winner], index) => ({
      match_id: 'draw:'+round, sequence: index+1,
      result: {player_a_id: a, player_b_id: b, winner_player_id: winner},
    })),
  },
}
describe('native eight-player knockout receipt proof', () => {
  it('authenticates the seven frozen quarterfinal/semifinal/final pairings', () => {
    expect(verifyEightFollowupKnockout(receipt, cmd, view)).toBe(receipt)
  })
  it('rejects forged semifinal pairing and forged winner', () => {
    const original = receipt.tournament.matches
    const forge = (index:number,player:string) => ({
      ...receipt, tournament: {...receipt.tournament,
        matches: original.map((m,i)=>i===index ? {...m,result:{...m.result,player_a_id:player}} : m)},
    })
    expect(() => verifyEightFollowupKnockout(forge(4, 'b'), cmd, view)).toThrow('lineage')
    expect(() => verifyEightFollowupKnockout({...receipt,winner_player_id:'a'},cmd,view)).toThrow('lineage')
  })
  it('refuses scored or Official status on the unscored eight-player flow', () => {
    expect(() => verifyEightFollowupKnockout({...receipt,official_ranking_published:true as false},cmd,view)).toThrow('source changed')
    expect(() => verifyEightFollowupKnockout({...receipt,publication_status:'prepared_not_official'},cmd,view)).toThrow('source changed')
  })
})

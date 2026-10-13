import { describe, expect, it } from 'vitest'
import { isScopedCompletedGroupStandings, isScopedGroupTieState, isExactGroupTieResolution } from './tournamentGroupStandings'

const sha = 'a'.repeat(64)
const make = () => ({
  schema_version: 'tournament_group_standings_authority.v2',
  run_id: 'r', branch_id: 'b', event_id: 'e',
  authority_fingerprint: sha, group_match_schedule_fingerprint: sha,
  generated_by_command_id: 'save-one',
  source_results: [{match_id: 'm1', result_kind: 'played'}, {match_id: 'm2', result_kind: 'played'}],
  groups: [{ group_index: 1, rows: ['A','B'].map((player_id, i) => ({
    group_index: 1, position: i+1, player_id, wins: 1-i, losses: i,
    group_points: 4-i*4, played_matches: 1, walkovers_received: 0,
    walkovers_conceded: 0, games_won: 3-i, games_lost: i,
    points_won: 33-i, points_lost: 20+i,
  })) }]
})

describe('canonical group standings response scope', () => {
  it('accepts a complete immutable group table for its owning run and branch', () => {
    expect(isScopedCompletedGroupStandings(make(), 'r', 'b', 'e')).toBe(true)
  })

  it('rejects foreign, forged and partial final tables', () => {
    expect(isScopedCompletedGroupStandings(make(), 'other', 'b', 'e')).toBe(false)
    expect(isScopedCompletedGroupStandings(make(), 'r', 'other', 'e')).toBe(false)
    expect(isScopedCompletedGroupStandings(make(), 'r', 'b', 'other')).toBe(false)
    expect(isScopedCompletedGroupStandings({...make(), groups: []}, 'r', 'b', 'e')).toBe(false)
    expect(isScopedCompletedGroupStandings({...make(), authority_fingerprint: 'fake'}, 'r', 'b', 'e')).toBe(false)
    const row = make()
    row.groups[0].rows[1].position = 1
    expect(isScopedCompletedGroupStandings(row, 'r', 'b', 'e')).toBe(false)
    const duplicate = make()
    duplicate.groups[0].rows[1].player_id = 'A'
    expect(isScopedCompletedGroupStandings(duplicate, 'r', 'b', 'e')).toBe(false)
    const forged = make()
    forged.source_results[1].match_id = 'm1'
    expect(isScopedCompletedGroupStandings(forged, 'r', 'b', 'e')).toBe(false)
  })

  it('never mistakes missing or unresolved tie evidence for a completed table', () => {
    const state = {schema_version: 'tournament_group_tie_resolution_state.v1',
      run_id:'r', branch_id:'b', event_id:'e', unresolved_case_fingerprint: sha,
      unresolved_case:{
        group_index:1,reason:'unresolved',player_ids:['A','B']
      },resolutions:[]}
    expect(isScopedGroupTieState(state,'r','b','e')).toBe(true)
    expect(isScopedCompletedGroupStandings(state,'r','b','e')).toBe(false)
    expect(isScopedGroupTieState({...state,branch_id:'foreign'},'r','b','e')).toBe(false)
    expect(isScopedGroupTieState({...state,unresolved_case:{...state.unresolved_case,player_ids:['A','A']}},'r','b','e')).toBe(false)
  })
  it('rejects a fabricated, absent or mismatched server-side tie fingerprint', () => {
    const tie = {schema_version: 'tournament_group_tie_resolution_state.v1',
      run_id:'r', branch_id:'b', event_id:'e', unresolved_case_fingerprint:sha,
      unresolved_case:{group_index:1,reason:'unresolved',player_ids:['A','B']},
      resolutions:[]}
    expect(isScopedGroupTieState(tie, 'r', 'b', 'e')).toBe(true)
    expect(isScopedGroupTieState({...tie, unresolved_case_fingerprint:undefined}, 'r','b','e')).toBe(false)
    expect(isScopedGroupTieState({...tie, unresolved_case_fingerprint:'not-a-sha'}, 'r','b','e')).toBe(false)
    expect(isScopedGroupTieState({...tie, unresolved_case:{...tie.unresolved_case,player_ids:['B','A']}}, 'r','b','e')).toBe(false)
  })

  it('validates the exact resolution response and refuses mismatched order or operator reason', () => {
    const payload = {command_id:'review-1',case_fingerprint:sha,
      ordered_player_ids:['B','A'],admin_reason:'Reviewed evidence'}
    const response = {schema_version:'tournament_group_tie_resolution_authority.v1',
      run_id:'r',branch_id:'b',event_id:'e',
      resolved_by_command_id:'review-1',authority_fingerprint:sha,
      group_match_schedule_fingerprint:sha,
      decision:{case:{group_index:1,reason:'tied',player_ids:['A','B']},
        ordered_player_ids:['B','A'],admin_reason:'Reviewed evidence'}}
    expect(isExactGroupTieResolution(response,'r','b','e',['A','B'],payload)).toBe(true)
    expect(isExactGroupTieResolution({...response,event_id:'foreign'},'r','b','e',['A','B'],payload)).toBe(false)
    expect(isExactGroupTieResolution({...response,decision:{...response.decision,
      ordered_player_ids:['A','B']}},'r','b','e',['A','B'],payload)).toBe(false)
    expect(isExactGroupTieResolution({...response,decision:{...response.decision,
      admin_reason:'silently changed'}},'r','b','e',['A','B'],payload)).toBe(false)
  })

})
import {describe,expect,it} from 'vitest'
import {filterSavedEditionMatches} from './savedEditionResultDiscovery'
import type {PublishedEditionMatch} from './savedEditionResultDiscovery'

const matches:PublishedEditionMatch[]=[
  {match_id:'final',draw_type:'main',round_number:2,bracket_position:1,
    winner_player_id:'BRNO-1',loser_player_id:'EGY-2',scoreline:'3-0'},
  {match_id:'qual-one',draw_type:'qualification',round_number:1,bracket_position:1,
    winner_player_id:'Q-3',loser_player_id:'Q-4',scoreline:'3-1'},
  {match_id:'group-game',draw_type:'group',round_number:1,bracket_position:2,
    winner_player_id:'CZE-5',loser_player_id:'BRNO-1',scoreline:'3-2'}
]
describe('Saved Edition result search is read-only',()=>{
  it('finds player on either side, match ID and score without changing canonical ordering',()=>{
    const before=JSON.stringify(matches)
    expect(filterSavedEditionMatches(matches,'BRNO-1').map(m=>m.match_id)).toEqual(['final','group-game'])
    expect(filterSavedEditionMatches(matches,'egy-2').map(m=>m.match_id)).toEqual(['final'])
    expect(filterSavedEditionMatches(matches,'  QUAL-ONE  ').map(m=>m.match_id)).toEqual(['qual-one'])
    expect(filterSavedEditionMatches(matches,'3-2').map(m=>m.match_id)).toEqual(['group-game'])
    expect(filterSavedEditionMatches(matches,'unseen')).toEqual([])
    expect(JSON.stringify(matches)).toBe(before)
  })
  it('empty search preserves original order, group records, and replay identity',()=>{
    expect(filterSavedEditionMatches(matches,' ')).toEqual(matches)
    expect(filterSavedEditionMatches(matches,'')[0]).toBe(matches[0])
    expect(filterSavedEditionMatches(matches,'q-3')[0].draw_type).toBe('qualification')
  })
  it('does not mistake a missing opponent ID for a searchable string',()=>{
    const walkover={...matches[0],loser_player_id:null}
    expect(filterSavedEditionMatches([walkover],'null')).toEqual([])
    expect(filterSavedEditionMatches([walkover],'final')).toEqual([walkover])
  })
})

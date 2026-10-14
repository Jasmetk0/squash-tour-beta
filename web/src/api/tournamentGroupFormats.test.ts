import {describe,expect,it} from 'vitest'
import {proposedHybridGroups} from './tournamentGroupFormats'

const ids=[{top:'1:1',bottom:'2:2'},{top:'2:1',bottom:'1:2'}]
describe('exact reviewed hybrid Format contract',()=>{
  it('sends unique group positions to the first knockout round only',()=>{
    expect(proposedHybridGroups('2','2','2',4,ids,'hybrid-command')).toEqual({
      command_id:'hybrid-command',format_kind:'groups_knockout',
      group_count:2,group_size:2,seeded_slots_per_group:0,
      group_seed_placements:[],match_best_of_override:null,
      advancing_per_group:2,knockout_crossings:[
        {match_index:1,top:{group_index:1,finishing_position:1},
          bottom:{group_index:2,finishing_position:2}},
        {match_index:2,top:{group_index:2,finishing_position:1},
          bottom:{group_index:1,finishing_position:2}}
      ]
    })
    expect(proposedHybridGroups('2','2','1',4,[{top:'1:1',bottom:'2:1'}],
      'final').knockout_crossings).toHaveLength(1)
  })
  it('refuses implicit pairing, duplicates, invalid source, odd/oversized knockout and partial field',()=>{
    for(const args of [
      ['2','2','2',4,[]],
      ['2','2','2',4,[{top:'1:1',bottom:'2:2'}, {top:'2:1',bottom:'2:2'}]],
      ['2','2','1',4,[{top:'1:1',bottom:''}]],
      ['2','2','1',4,[{top:'1:1',bottom:'3:1'}]],
      ['2','2','1',4,[{top:'1:1',bottom:'2:2'}]],
      ['3','2','1',6,[{top:'1:1',bottom:'2:1'}]],
      ['2','2','3',4,[{top:'1:1',bottom:'2:1'}]],
      ['2','2','1',6,[{top:'1:1',bottom:'2:1'}]],
      ['2.0','2','1',4,[{top:'1:1',bottom:'2:1'}]],
    ] as Array<[string,string,string,number,{top:string;bottom:string}[]]>){
      expect(()=>proposedHybridGroups(...args,'test')).toThrow()
    }
  })
})

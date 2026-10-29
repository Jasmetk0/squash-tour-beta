import {describe,expect,it} from 'vitest'
import type {CountrySavedMatchRecords,CountrySavedMatch} from '../api/types'
import {countrySavedMatchPageCount,validCountrySavedMatchPage} from './countrySavedMatchListGuard'

const scope={runId:'run',branchId:'branch',revision:'rev',countryCode:'CZE',
  seasonIndex:null,resultKind:'all' as const,outcome:'all' as const,offset:0}
const match=(id:string):CountrySavedMatch=>({
  event_id:'cup',event_name:'Brno Cup',match_id:id,
  season:'2000/2001',season_week:1,draw_type:'main',round_number:2,
  winner_player_id:'A',winner_name:'Alpha',winner_country:'CZE',
  loser_player_id:'B',loser_name:'Bravo',loser_country:'EGY',
  host_country:'CZE',completion:'played',scoreline:'3-1',
})
const full=(patch:Partial<CountrySavedMatchRecords>={}):CountrySavedMatchRecords=>({
  schema_version:'country_saved_match_records.v1',source:'reachable_saved_revision',
  run_id:'run',branch_id:'branch',revision_branch_id:'origin',
  saved_revision_id:'rev',country_code:'CZE',calendar_status:'ready',
  published_event_count:1,total_played_matches:3,total_walkovers:1,
  country_played_wins:3,country_played_losses:0,
  country_walkover_wins:0,country_walkover_losses:0,
  hosted_played_matches:3,hosted_walkovers:0,country_match_count:3,
  available_seasons:[0],season_index:null,result_kind:'all',outcome:'all',
  filtered_match_count:1,offset:0,limit:25,has_more:false,matches:[match('m1')],
  ...patch,
})

describe('Country exact Saved match paging guard',()=>{
  it('accepts authentic full, filtered and truly empty windows',()=>{
    expect(validCountrySavedMatchPage(full(),scope)).toBe(true)
    expect(validCountrySavedMatchPage(full({
      result_kind:'played',outcome:'win',season_index:0,
    }),{...scope,resultKind:'played',outcome:'win',seasonIndex:0})).toBe(true)
    expect(validCountrySavedMatchPage(full({
      filtered_match_count:0,matches:[],
    }),scope)).toBe(true)
    expect(countrySavedMatchPageCount(0)).toBe(0)
    expect(countrySavedMatchPageCount(25)).toBe(1)
    expect(countrySavedMatchPageCount(26)).toBe(2)
  })
  it('rejects foreign Run/Branch/Revision and unsourced API data',()=>{
    const patches:Partial<CountrySavedMatchRecords>[]=[
      {run_id:'other'},{branch_id:'other'},{saved_revision_id:'other'},
      {revision_branch_id:''},{source:'wrong' as CountrySavedMatchRecords['source']},
      {schema_version:'wrong' as CountrySavedMatchRecords['schema_version']},
      {country_code:'ENG'},{offset:25},{limit:20},{outcome:'loss'},
      {season_index:0},{result_kind:'walkover'},
    ]
    for(const patch of patches)
      expect(validCountrySavedMatchPage(full(patch),scope)).toBe(false)
  })
  it('rejects incomplete, duplicate or contradictory result windows',()=>{
    expect(validCountrySavedMatchPage(full({matches:[]}),scope)).toBe(false)
    expect(validCountrySavedMatchPage(full({
      filtered_match_count:2,matches:[match('m1'),match('m1')],
    }),scope)).toBe(false)
    expect(validCountrySavedMatchPage(full({has_more:true}),scope)).toBe(false)
    expect(validCountrySavedMatchPage(full({country_match_count:5}),scope)).toBe(false)
    expect(validCountrySavedMatchPage(full({available_seasons:[0,0]}),scope)).toBe(false)
    expect(validCountrySavedMatchPage(full({filtered_match_count:4}),scope)).toBe(false)
  })
  it('does not treat a walkover as played nor a foreign player as a national match',()=>{
    expect(validCountrySavedMatchPage(full({matches:[
      {...match('m1'),completion:'walkover'},
    ],result_kind:'played'}),{...scope,resultKind:'played'})).toBe(false)
    expect(validCountrySavedMatchPage(full({matches:[{
      ...match('m1'),winner_country:'ENG',loser_country:'EGY',
    }]}),scope)).toBe(false)
    expect(validCountrySavedMatchPage(full({matches:[{
      ...match('m1'),winner_country:'EGY',loser_country:'CZE',
    }],outcome:'win'}),{...scope,outcome:'win'})).toBe(false)
    expect(validCountrySavedMatchPage(full({matches:[{
      ...match('m1'),season:'2001/2002',
    }],season_index:0}),{...scope,seasonIndex:0})).toBe(false)
  })
  it('accepts an empty page after the end but never invents nonempty rows there',()=>{
    const late={...scope,offset:25}
    expect(validCountrySavedMatchPage(full({offset:25,matches:[]}),late)).toBe(true)
    expect(validCountrySavedMatchPage(full({offset:25}),late)).toBe(false)
  })
})

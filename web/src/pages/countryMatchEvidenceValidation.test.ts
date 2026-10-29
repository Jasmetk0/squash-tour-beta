import {describe,expect,it} from 'vitest'
import type {CountryMatchRecordHighlights,CountrySavedMatch} from '../api/types'
import {COUNTRY_EVIDENCE_PAGE_SIZE,validCountryMatchEvidence} from './countryMatchEvidenceValidation'

const scope={
  runId:'run',branchId:'branch',countryCode:'CZE',revision:'rev',
  fromSeason:0,fromWeek:1,toSeason:0,toWeek:9,
  selected:'played_wins' as const,offset:0,
}
const game=(id:string):CountrySavedMatch=>({
  event_id:'cup',match_id:id,event_name:'Brno Cup',season:'2000/01',season_week:2,
  draw_type:'main',round_number:2,winner_player_id:'A',winner_name:'Alpha',
  winner_country:'CZE',loser_player_id:'B',loser_name:'Bravo',loser_country:'ENG',
  host_country:'CZE',completion:'played',scoreline:'3-1',
})
const detail=(patch:Partial<CountryMatchRecordHighlights>={}):CountryMatchRecordHighlights=>({
  schema_version:'country_match_record_highlights.v1',source:'reachable_saved_revision',
  run_id:'run',branch_id:'branch',revision_branch_id:'origin',saved_revision_id:'rev',
  country_code:'CZE',from_season:0,from_week:1,to_season:0,to_week:9,
  period_country_matches:3,period_played_matches:2,period_walkovers:1,
  records:[
    {key:'played_wins',value:2,holders:[{player_id:'A',player_name:'Alpha',value:2}]},
    {key:'played_matches',value:2,holders:[{player_id:'A',player_name:'Alpha',value:2}]},
  ],
  selected_record:'played_wins',evidence_count:2,offset:0,limit:COUNTRY_EVIDENCE_PAGE_SIZE,
  has_more:false,evidence:[game('m1'),game('m2')],...patch,
})

describe('exact Saved Country match record evidence',()=>{
  it('accepts both valid summary and selected-record pages',()=>{
    expect(validCountryMatchEvidence(detail(),scope)).toBe(true)
    expect(validCountryMatchEvidence(detail({
      selected_record:null,evidence_count:0,evidence:[],
    }),{...scope,selected:null})).toBe(true)
  })
  it('rejects foreign source, scope, cursor, record selection or unsupported schema',()=>{
    const errors:Partial<CountryMatchRecordHighlights>[]=[
      {run_id:'other'},{branch_id:'other'},{saved_revision_id:'other'},
      {revision_branch_id:''},{source:'wrong' as CountryMatchRecordHighlights['source']},
      {from_week:2},{country_code:'ENG'},{selected_record:'played_matches'},
      {offset:25},{limit:20},{schema_version:'wrong' as CountryMatchRecordHighlights['schema_version']},
    ]
    for(const mismatch of errors)expect(validCountryMatchEvidence(detail(mismatch),scope)).toBe(false)
  })
  it('checks full-server totals, unique record holders and complete 25-row windows',()=>{
    expect(validCountryMatchEvidence(detail({period_walkovers:9}),scope)).toBe(false)
    expect(validCountryMatchEvidence(detail({evidence_count:3}),scope)).toBe(false)
    expect(validCountryMatchEvidence(detail({evidence:[game('m1'),game('m1')]}),scope)).toBe(false)
    expect(validCountryMatchEvidence(detail({has_more:true}),scope)).toBe(false)
    expect(validCountryMatchEvidence(detail({records:[]}),scope)).toBe(false)
    expect(validCountryMatchEvidence(detail({records:[
      {key:'played_wins',value:2,holders:[]},
      {key:'played_matches',value:2,holders:[{player_id:'A',player_name:'Alpha',value:2}]},
    ]}),scope)).toBe(false)
  })
  it('cannot use walkovers, an unrelated holder, or an out-of-period match as proof',()=>{
    expect(validCountryMatchEvidence(detail({evidence:[
      {...game('m1'),completion:'walkover'},game('m2')]}),scope)).toBe(false)
    expect(validCountryMatchEvidence(detail({evidence:[
      {...game('m1'),winner_player_id:'C'},game('m2')]}),scope)).toBe(false)
    expect(validCountryMatchEvidence(detail({evidence:[
      {...game('m1'),season_week:11},game('m2')]}),scope)).toBe(false)
  })
  it('accepts a genuinely empty page beyond the end, without inventing matching rows',()=>{
    const outside={...scope,offset:25}
    expect(validCountryMatchEvidence(detail({
      offset:25,evidence:[],evidence_count:2,
    }),outside)).toBe(true)
    expect(validCountryMatchEvidence(detail({
      offset:25,evidence:[game('m1')],evidence_count:2,
    }),outside)).toBe(false)
    expect(validCountryMatchEvidence(detail({
      selected_record:null,evidence_count:2,evidence:[game('m1')],
    }),{...scope,selected:null})).toBe(false)
  })
})

import {describe,expect,it} from 'vitest'
import type {CountryPlayerStanding,CountryPlayerStandings} from '../api/types'
import {compareCountryStanding,parseStandingPage,standingsPages,validCountryStandingPage}
  from './countrySavedStandingsNavigation'

const scope={runId:'run',branchId:'branch',countryCode:'CZE',revision:'rev',offset:0}
const player=(position:number):CountryPlayerStanding=>({
  position,player_id:'P'+String(position).padStart(3,'0'),
  player_name:'Player '+position,country_code:'CZE',
  titles:0,runner_up_finishes:0,final_appearances:0,
  played_wins:1,played_losses:0,walkover_wins:0,walkover_losses:0,
})
const data=(patch:Partial<CountryPlayerStandings>={}):CountryPlayerStandings=>({
  schema_version:'country_player_standings.v1',source:'reachable_saved_revision',
  run_id:'run',branch_id:'branch',revision_branch_id:'parent',
  saved_revision_id:'rev',country_code:'CZE',calendar_status:'ready',
  published_event_count:1,country_titles:0,country_runner_up_finishes:0,
  country_played_wins:26,country_played_losses:0,
  country_walkover_wins:0,country_walkover_losses:0,
  total_players:26,offset:0,limit:25,has_more:true,
  players:Array.from({length:25},(_,i)=>player(i+1)),...patch,
})

describe('exact Country standings page contract',()=>{
  it('accepts exactly 25 genuine rows and the final one-row page',()=>{
    expect(validCountryStandingPage(data(),scope)).toBe(true)
    expect(validCountryStandingPage(data({
      offset:25,players:[player(26)],has_more:false,
    }),{...scope,offset:25})).toBe(true)
    expect(standingsPages(0)).toBe(0)
    expect(standingsPages(25)).toBe(1)
    expect(standingsPages(26)).toBe(2)
  })
  it('fails closed on wrong Run, Branch, HEAD, metadata and cursor',()=>{
    for(const patch of [
      {run_id:'other'},{branch_id:'other'},{saved_revision_id:'old'},
      {revision_branch_id:''},{country_code:'EGY'},{offset:25},{limit:20},
      {schema_version:'other'},{source:'other'}, {calendar_status:'other'},
    ] as Partial<CountryPlayerStandings>[]){
      expect(validCountryStandingPage(data(patch),scope)).toBe(false)
    }
  })
  it('rejects incomplete pages, wrong next flag, duplicate or out-of-order rows',()=>{
    expect(validCountryStandingPage(data({players:[player(1)]}),scope)).toBe(false)
    expect(validCountryStandingPage(data({has_more:false}),scope)).toBe(false)
    expect(validCountryStandingPage(data({
      players:[player(1),player(1),...Array.from({length:23},(_,i)=>player(i+3))],
    }),scope)).toBe(false)
    expect(validCountryStandingPage(data({
      players:[player(2),player(1),...Array.from({length:23},(_,i)=>player(i+3))],
    }),scope)).toBe(false)
    expect(validCountryStandingPage(data({
      players:[{...player(1),position:2},...Array.from({length:24},(_,i)=>player(i+2))],
    }),scope)).toBe(false)
  })
  it('verifies nationality, played vs W/O, complete finals and real evidence',()=>{
    const rest=Array.from({length:24},(_,i)=>player(i+2))
    for(const first of [
      {...player(1),country_code:'EGY'},
      {...player(1),final_appearances:1},
      {...player(1),titles:-1},
      {...player(1),played_wins:0},
      {...player(1),player_name:''},
    ]) expect(validCountryStandingPage(data({players:[first,...rest]}),scope)).toBe(false)
    expect(validCountryStandingPage(data({country_titles:2,published_event_count:1}),scope)).toBe(false)
  })
  it('allows an explicitly empty archive but no fabricated Page 1/1',()=>{
    const empty=data({total_players:0,players:[],has_more:false,
      country_played_wins:0})
    expect(validCountryStandingPage(empty,scope)).toBe(true)
    expect(validCountryStandingPage({...empty,calendar_status:'empty',
      published_event_count:0},scope)).toBe(true)
    expect(validCountryStandingPage(data({calendar_status:'empty'}),scope)).toBe(false)
    expect(validCountryStandingPage(data({offset:50,players:[],has_more:false}),
      {...scope,offset:50})).toBe(true)
    expect(validCountryStandingPage(data({offset:50,players:[player(51)],has_more:false}),
      {...scope,offset:50})).toBe(false)
  })
  it('parses bounded one-based numeric navigation without changing ranking order',()=>{
    expect(parseStandingPage('1',3)).toBe(0)
    expect(parseStandingPage('3',3)).toBe(2)
    for(const raw of ['0','4','01',' 2','1.0','-1','NaN','10000000',''])
      expect(parseStandingPage(raw,3)).toBeNull()
    expect(parseStandingPage('1',0)).toBeNull()
    expect(compareCountryStanding({...player(1),titles:1},player(2))).toBeLessThan(0)
    expect(compareCountryStanding({...player(1),walkover_wins:50},player(2))).toBeLessThan(0)
  })
})

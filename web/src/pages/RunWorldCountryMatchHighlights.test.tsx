import {fireEvent,render,screen,waitFor,within} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router-dom'
import {useState} from 'react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import type {CountryMatchRecordHighlights,CountryMatchRecordKey,CountrySavedMatch} from '../api/types'
import type {CountryPeriodRequest} from './runCountryRecordPeriods'
import {RunWorldCountryMatchHighlights} from './RunWorldCountryMatchHighlights'

const api=vi.hoisted(()=>({getCountryMatchRecordHighlights:vi.fn()}))
vi.mock('../api/client',()=>api)
const request:CountryPeriodRequest={
  mode:'whole',season:0,from:{season:0,week:1},to:{season:0,week:9}
}
const match=(n:number):CountrySavedMatch=>({
  event_id:'event',match_id:'m'+n,event_name:'Cup',season:'2000/01',
  season_week:2,draw_type:'main',round_number:2,winner_player_id:'A',
  winner_name:'Alpha',winner_country:'CZE',loser_player_id:'B',
  loser_name:'Bravo',loser_country:'ENG',host_country:'CZE',
  completion:'played',scoreline:'3-1',
})
const games=Array.from({length:26},(_,i)=>match(i+1))
const summaries=()=>[
  {key:'played_wins' as const,value:26,holders:[{player_id:'A',player_name:'Alpha',value:26}]},
  {key:'played_matches' as const,value:26,holders:[{player_id:'A',player_name:'Alpha',value:26}]},
]
function reply(branch:string,revision:string,selected:CountryMatchRecordKey|null,offset:number,
  patch:Partial<CountryMatchRecordHighlights>={}):CountryMatchRecordHighlights{
  return {
    schema_version:'country_match_record_highlights.v1',source:'reachable_saved_revision',
    run_id:'run',branch_id:branch,revision_branch_id:branch,saved_revision_id:revision,
    country_code:'CZE',from_season:0,from_week:1,to_season:0,to_week:9,
    period_country_matches:27,period_played_matches:26,period_walkovers:1,
    records:summaries(),selected_record:selected,
    evidence_count:selected?26:0,offset,limit:25,
    has_more:Boolean(selected&&offset+25<26),
    evidence:selected?games.slice(offset,offset+25):[],...patch,
  }
}
function mount(){
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})
  function Harness(){
    const [revision,setRevision]=useState('rev-a')
    const [branch,setBranch]=useState('branch-a')
    const [selected,setSelected]=useState<CountryMatchRecordKey|null>(null)
    const [cs,setCs]=useState(false)
    return <>
      <button type="button" onClick={()=>{setBranch('branch-b');setRevision('rev-b')}}>Change saved source</button>
      <button type="button" onClick={()=>setCs(v=>!v)}>Toggle language</button>
      <RunWorldCountryMatchHighlights runId="run" branchId={branch} countryCode="CZE"
        revision={revision} request={request} cs={cs} selected={selected}
        onSelect={setSelected} onClose={()=>setSelected(null)}/>
    </>
  }
  return render(<QueryClientProvider client={client}>
    <MemoryRouter initialEntries={['/admin/runs/run/world/countries/CZE?tab=records']}>
      <Harness />
    </MemoryRouter>
  </QueryClientProvider>)
}
const calls=()=>api.getCountryMatchRecordHighlights.mock.calls

describe('Saved Country record evidence navigation (mocked HTTP)',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    api.getCountryMatchRecordHighlights.mockImplementation(async (
      _r:string,b:string,_c:string,rev:string,
      opts:{recordKey:CountryMatchRecordKey|null;offset:number;limit:number})=>
      reply(b,rev,opts.recordKey,opts.offset))
  })
  it('navigates exact 25-row source pages and keeps query on locale switch',async()=>{
    mount()
    expect(await screen.findByRole('table',{name:'Country period match record leaders'})).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button',{name:'Open evidence'})[0])
    const table=await screen.findByRole('table',{name:'Country match record source matches'})
    expect(within(table).getAllByRole('row')).toHaveLength(26)
    expect(screen.getByText('Page 1 / 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Next →'}))
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    expect(calls()).toContainEqual(['run','branch-a','CZE','rev-a',
      expect.objectContaining({recordKey:'played_wins',offset:25,limit:25})])
    const count=calls().length
    fireEvent.click(screen.getByRole('button',{name:'Toggle language'}))
    expect(screen.getByText('Strana 2 / 2')).toBeInTheDocument()
    expect(calls()).toHaveLength(count)
  })
  it('resets the cursor BEFORE reading another Saved revision or Branch',async()=>{
    mount()
    await screen.findByRole('table',{name:'Country period match record leaders'})
    fireEvent.click(screen.getAllByRole('button',{name:'Open evidence'})[0])
    await screen.findByText('Page 1 / 2')
    fireEvent.click(screen.getByRole('button',{name:'Next →'}))
    await screen.findByText('Page 2 / 2')
    fireEvent.click(screen.getByRole('button',{name:'Change saved source'}))
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    await waitFor(()=>expect(calls()).toContainEqual(['run','branch-b','CZE','rev-b',
      expect.objectContaining({recordKey:'played_wins',offset:0,limit:25})]))
    expect(calls().filter(([,branch])=>branch==='branch-b')
      .every(([, , , ,opts])=>opts.offset===0)).toBe(true)
  })
  it('rejects foreign HEAD and wrong selected record before rendering proof',async()=>{
    api.getCountryMatchRecordHighlights.mockImplementation(async (
      _r:string,b:string,_c:string,rev:string,
      opts:{recordKey:CountryMatchRecordKey|null;offset:number;limit:number})=>
      reply(b,rev,opts.recordKey,opts.offset,opts.recordKey?{selected_record:'played_matches',saved_revision_id:'wrong'}:{}))
    mount()
    await screen.findByRole('table',{name:'Country period match record leaders'})
    fireEvent.click(screen.getAllByRole('button',{name:'Open evidence'})[0])
    expect(await screen.findByRole('alert')).toHaveTextContent('Historical match evidence detail mismatch')
    expect(screen.queryByRole('table',{name:'Country match record source matches'})).not.toBeInTheDocument()
  })
  it('shows no fake page 1/1 when no saved played-record proof exists',async()=>{
    api.getCountryMatchRecordHighlights.mockImplementation(async (
      _r:string,b:string,_c:string,rev:string,
      opts:{recordKey:CountryMatchRecordKey|null;offset:number;limit:number})=>
      reply(b,rev,opts.recordKey,opts.offset,{
        period_country_matches:0,period_played_matches:0,period_walkovers:0,
        records:[
          {key:'played_wins',value:0,holders:[]},
          {key:'played_matches',value:0,holders:[]},
        ],evidence_count:0,evidence:[],has_more:false,
      }))
    mount()
    await screen.findByRole('table',{name:'Country period match record leaders'})
    fireEvent.click(screen.getAllByRole('button',{name:'Open evidence'})[0])
    expect(await screen.findByText('Page 0 / 0')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Next →'})).toBeDisabled()
    expect(screen.getByRole('status',{name:''})).toBeInTheDocument()
  })
  it('preserves exact branch/revision/return origin on immutable match links',async()=>{
    mount()
    await screen.findByRole('table',{name:'Country period match record leaders'})
    fireEvent.click(screen.getAllByRole('button',{name:'Open evidence'})[0])
    const t=await screen.findByRole('table',{name:'Country match record source matches'})
    const href=within(t).getByRole('link',{name:'Cup · m1'}).getAttribute('href')!
    const url=new URL(href,'http://example.test')
    expect(url.pathname).toBe('/admin/runs/run/tour/calendar/event/matches/m1')
    expect(url.searchParams.get('revision')).toBe('rev-a')
    expect(url.searchParams.get('branch')).toBe('branch-a')
    expect(url.searchParams.get('fromCountry')).toContain('#country-match-record-played_wins')
  })
})

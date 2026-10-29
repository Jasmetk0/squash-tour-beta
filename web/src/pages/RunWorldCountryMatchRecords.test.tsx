import {fireEvent,render,screen,waitFor,within} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router-dom'
import {useState} from 'react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import type {CountrySavedMatchRecords,CountrySavedMatch} from '../api/types'
import {RunWorldCountryMatchRecords} from './RunWorldCountryMatchRecords'

const api=vi.hoisted(()=>({getCountrySavedMatchRecords:vi.fn()}))
vi.mock('../api/client',()=>api)
const game=(i:number):CountrySavedMatch=>({
  event_id:'cup',match_id:'m'+i,event_name:'Brno Cup',
  season:'2000/2001',season_week:1,draw_type:'main',round_number:2,
  winner_player_id:'A',winner_name:'Alpha',winner_country:'CZE',
  loser_player_id:'B',loser_name:'Bravo',loser_country:'EGY',
  host_country:'CZE',completion:'played',scoreline:'3-1',
})
const all=Array.from({length:26},(_,i)=>game(i+1))
type Options={seasonIndex:number|null;resultKind:'all'|'played'|'walkover';
  outcome:'all'|'win'|'loss';offset:number;limit:number}
function reply(run:string,branch:string,country:string,rev:string,opts:Options,
  patch:Partial<CountrySavedMatchRecords>={}):CountrySavedMatchRecords{
  const available=opts.resultKind!=='walkover'&&opts.outcome!=='loss'&&
    (opts.seasonIndex===null||opts.seasonIndex===0)
  const filtered=available?all:[]
  return {
    schema_version:'country_saved_match_records.v1',source:'reachable_saved_revision',
    run_id:run,branch_id:branch,revision_branch_id:branch,saved_revision_id:rev,
    country_code:country,calendar_status:'ready',published_event_count:1,
    total_played_matches:26,total_walkovers:0,
    country_played_wins:26,country_played_losses:0,
    country_walkover_wins:0,country_walkover_losses:0,
    hosted_played_matches:26,hosted_walkovers:0,country_match_count:26,
    available_seasons:[0],season_index:opts.seasonIndex,result_kind:opts.resultKind,
    outcome:opts.outcome,filtered_match_count:filtered.length,
    offset:opts.offset,limit:opts.limit,
    has_more:opts.offset+opts.limit<filtered.length,
    matches:filtered.slice(opts.offset,opts.offset+opts.limit),...patch,
  }
}
function mount(){
  function Harness(){
    const [rev,setRev]=useState('rev-a')
    const [branch,setBranch]=useState('branch-a')
    const [country,setCountry]=useState('CZE')
    const [historical,setHistorical]=useState(false)
    const [cs,setCs]=useState(false)
    return <>
      <button type="button" onClick={()=>{setRev('rev-b');setBranch('branch-b')}}>
        Switch revision and Branch</button>
      <button type="button" onClick={()=>{setCountry('ENG');setRev('rev-c')}}>
        Switch country</button>
      <button type="button" onClick={()=>setHistorical(true)}>Open historical mode</button>
      <button type="button" onClick={()=>setCs(v=>!v)}>Switch language</button>
      <RunWorldCountryMatchRecords runId="run" branchId={branch} countryCode={country}
        savedRevisionId={rev} historical={historical} cs={cs}/>
    </>
  }
  return render(<QueryClientProvider client={new QueryClient({
    defaultOptions:{queries:{retry:false,gcTime:0}},
  })}><MemoryRouter initialEntries={['/admin/runs/run/world/countries/CZE?tab=records']}>
    <Harness />
  </MemoryRouter></QueryClientProvider>)
}
describe('Country lifetime Saved matches (mocked API)',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    api.getCountrySavedMatchRecords.mockImplementation(async (
      run:string,branch:string,country:string,rev:string,opts:Options,
    )=>reply(run,branch,country,rev,opts))
  })
  it('paginates 25 real rows, preserves them on CS/EN, and keeps server totals',async()=>{
    mount()
    const t=await screen.findByRole('table',{name:'Country canonical saved matches'})
    expect(within(t).getAllByRole('row')).toHaveLength(26)
    expect(screen.getByText('Page 1 / 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Next →'}))
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    expect(api.getCountrySavedMatchRecords).toHaveBeenCalledWith('run','branch-a','CZE',
      'rev-a',expect.objectContaining({offset:25,limit:25}))
    const calls=api.getCountrySavedMatchRecords.mock.calls.length
    fireEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByText('Strana 2 / 2')).toBeInTheDocument()
    expect(api.getCountrySavedMatchRecords).toHaveBeenCalledTimes(calls)
  })
  it('resets old page and filters before reading another branch/revision',async()=>{
    mount()
    await screen.findByText('Page 1 / 2')
    fireEvent.change(screen.getByRole('combobox',{name:'Country match completion'}),
      {target:{value:'played'}})
    await waitFor(()=>expect(api.getCountrySavedMatchRecords).toHaveBeenCalledWith(
      'run','branch-a','CZE','rev-a',expect.objectContaining({resultKind:'played',offset:0})))
    fireEvent.click(screen.getByRole('button',{name:'Next →'}))
    await screen.findByText('Page 2 / 2')
    fireEvent.click(screen.getByRole('button',{name:'Switch revision and Branch'}))
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    const called=api.getCountrySavedMatchRecords.mock.calls.filter(([,branch])=>branch==='branch-b')
    expect(called.length).toBeGreaterThan(0)
    expect(called.every(([, , , ,opts])=>opts.offset===0&&opts.resultKind==='all')).toBe(true)
  })
  it('fails closed on foreign Source/HEAD instead of displaying stale winners',async()=>{
    api.getCountrySavedMatchRecords.mockImplementation(async (
      r:string,b:string,c:string,v:string,opts:Options,
    )=>reply(r,b,c,v,opts,{saved_revision_id:'foreign'}))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Match response does not match')
    expect(screen.queryByRole('table',{name:'Country canonical saved matches'})).not.toBeInTheDocument()
  })
  it('shows an honest empty filter and Page 0 / 0',async()=>{
    mount()
    await screen.findByText('Page 1 / 2')
    fireEvent.change(screen.getByRole('combobox',{name:'Country match completion'}),
      {target:{value:'walkover'}})
    expect(await screen.findByText('Page 0 / 0')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Next →'})).toBeDisabled()
    expect(screen.getByText('No saved matches match these filters in the selected revision.')).toBeInTheDocument()
  })
  it('links a historical row to its immutable Edition/Match and preserves country return',async()=>{
    mount()
    await screen.findByText('Page 1 / 2')
    fireEvent.click(screen.getByRole('button',{name:'Open historical mode'}))
    const link=await screen.findByRole('link',{name:'Saved match m1'})
    const url=new URL(link.getAttribute('href')!,'http://unit.test')
    expect(url.pathname).toBe('/admin/runs/run/tour/calendar/cup/matches/m1')
    expect(url.searchParams.get('revision')).toBe('rev-a')
    expect(url.searchParams.get('branch')).toBe('branch-a')
    expect(url.searchParams.get('season')).toBe('0')
    expect(url.searchParams.get('fromCountry')).toContain('revision=rev-a')
    expect(screen.queryByRole('link',{name:'Alpha'})).not.toBeInTheDocument()
  })
})

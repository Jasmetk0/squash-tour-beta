import {fireEvent,render,screen,waitFor,within} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter,useNavigate} from 'react-router-dom'
import {useState} from 'react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import type {SavedInventoryPlayer,SavedPlayersInventory} from '../api/types'
import {RunWorldCountrySavedPlayers} from './RunWorldCountrySavedPlayers'
import {writeCountryRosterPermalink} from './countrySavedRosterPermalink'

const api=vi.hoisted(()=>({getSavedPlayersInventory:vi.fn()}))
vi.mock('../api/client',()=>api)
type Filters={search:string;country_code:string;status_filter:string;
  include_prepared:boolean;offset:number;limit:number}
const saved=(i:number):SavedInventoryPlayer=>({
  player_id:'p-'+String(i).padStart(3,'0'),
  display_name:(i<=30?'Alpha':'Beta')+' Player '+String(i).padStart(3,'0'),
  country_code:'CZE',identity_source:'initial_world',
  status:i%2===0?'active':'inactive',age:null,ovr:null,potential_ovr:null,
  ranking_status:'unpublished',rank:null,
})
const basePlayers=Array.from({length:55},(_,i)=>saved(i+1))
const prepared:SavedInventoryPlayer={
  player_id:'future-1',display_name:'Alpha Future',country_code:'CZE',
  identity_source:'run_prospect',status:'prepared',age:null,ovr:null,
  potential_ovr:null,ranking_status:'unpublished',rank:null,
}
const other:SavedInventoryPlayer={
  ...saved(70),player_id:'foreign',country_code:'ENG',display_name:'Alpha English',
}
function response(run:string,branch:string,head:string,f:Filters):SavedPlayersInventory {
  const needle=f.search.trim().toLowerCase()
  const status=f.status_filter.trim().toLowerCase()
  const rows=[...basePlayers,...(f.include_prepared?[prepared]:[]),other].filter(p=>
    p.country_code===f.country_code&&
    (!needle||p.player_id.toLowerCase().includes(needle)||
      p.display_name.toLowerCase().includes(needle))&&
    (!status||p.status?.toLowerCase()===status))
    .sort((a,b)=>a.display_name.localeCompare(b.display_name)||a.player_id.localeCompare(b.player_id))
  return {schema_version:'saved_players_inventory.v1',
    source:'selected_branch_saved_revision',time_context:'present',
    run_id:run,branch_id:branch,saved_revision_id:head,
    ranking_week_ordinal:null,search:f.search,country_code:f.country_code,
    status_filter:f.status_filter,include_prepared:f.include_prepared,
    offset:f.offset,limit:f.limit,total:rows.length,
    has_more:f.offset+f.limit<rows.length,players:rows.slice(f.offset,f.offset+f.limit)}
}
function mount(entry='/admin/runs/run/world/countries/CZE?tab=players&year=2025'){
  function Harness(){
    const [head,setHead]=useState<string|null>('rev-a')
    const [branch,setBranch]=useState('branch-a')
    const [country,setCountry]=useState('CZE')
    const [language,setLanguage]=useState<'en'|'cs'>('en')
    const navigate=useNavigate()
    const bookmark=writeCountryRosterPermalink(
      new URLSearchParams('tab=players&year=2025'),JSON.stringify([
        'run','branch-a','rev-a','CZE',
      ]),{search:'Alpha',status:'',includePrepared:false,page:1})
    return <>
      <button type="button" onClick={()=>{setHead('rev-b');setBranch('branch-b')}}>Change source</button>
      <button type="button" onClick={()=>setCountry('ENG')}>Change country</button>
      <button type="button" onClick={()=>setHead(null)}>Clear Saved HEAD</button>
      <button type="button" onClick={()=>setLanguage(l=>l==='en'?'cs':'en')}>Switch language</button>
      <button type="button" onClick={()=>navigate('/admin/runs/run/world/countries/CZE?'+
        bookmark.toString())}>Open same-route bookmark</button>
      <button type="button" onClick={()=>navigate(-1)}>Browser Back</button>
      <RunWorldCountrySavedPlayers runId="run" branchId={branch} savedHead={head}
        countryCode={country} selectedWorldYear={2025} language={language}/>
    </>
  }
  render(<QueryClientProvider client={new QueryClient({
    defaultOptions:{queries:{retry:false,gcTime:0}},
  })}><MemoryRouter initialEntries={[entry]}><Harness/></MemoryRouter></QueryClientProvider>)
}
const calls=()=>api.getSavedPlayersInventory.mock.calls
const apply=()=>fireEvent.click(screen.getByRole('button',{name:'Apply filters'}))

describe('Country Saved roster server-side filters (mock HTTP)',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    api.getSavedPlayersInventory.mockImplementation(async (
      run:string,branch:string,head:string,filters:Filters,
    )=>response(run,branch,head,filters))
  })

  it('searches all 55 saved players by name/ID BEFORE pagination, not 25 local rows',async()=>{
    mount()
    expect(await screen.findByText('Page 1 / 3')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Next →'}))
    expect(await screen.findByText('Page 2 / 3')).toBeInTheDocument()
    const before=calls().length
    fireEvent.change(screen.getByRole('searchbox',{name:'Country roster search'}),
      {target:{value:'Alpha'}})
    // Edits in progress are only drafts: no backend request until explicit Apply.
    expect(calls()).toHaveLength(before)
    apply()
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    await waitFor(()=>expect(calls().some(([, , ,f])=>f.search==='Alpha'&&
      f.offset===0&&f.limit===25)).toBe(true))
    expect(calls().filter(([, , ,f])=>f.search==='Alpha')
      .every(([, , ,f])=>f.offset===0)).toBe(true)
    const list=screen.getByRole('table',{name:'Saved country roster'})
    expect(within(list).getAllByRole('row')).toHaveLength(26)
    fireEvent.click(screen.getByRole('button',{name:'Next →'}))
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    expect(screen.getByText('Alpha Player 030')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox',{name:'Country roster search'}),
      {target:{value:'p-055'}})
    apply()
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Beta Player 055'})).toBeInTheDocument()
  })

  it('combines exact status with the search and can clear only the filters',async()=>{
    mount()
    await screen.findByText('Page 1 / 3')
    fireEvent.change(screen.getByRole('searchbox',{name:'Country roster search'}),
      {target:{value:'Alpha'}})
    fireEvent.change(screen.getByRole('textbox',{name:'Country roster status'}),
      {target:{value:'active'}})
    apply()
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    expect(calls().some(([, , ,f])=>f.search==='Alpha'&&f.status_filter==='active'&&
      f.offset===0)).toBe(true)
    const list=screen.getByRole('table',{name:'Saved country roster'})
    expect(within(list).getAllByRole('row')).toHaveLength(16)
    expect(screen.queryByRole('link',{name:'Alpha Player 001'})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Clear filters'}))
    expect(await screen.findByText('Page 1 / 3')).toBeInTheDocument()
    expect(screen.getByRole('searchbox',{name:'Country roster search'})).toHaveValue('')
    expect(screen.getByRole('textbox',{name:'Country roster status'})).toHaveValue('')
  })

  it('keeps prepared future prospects opt-in and resets the filtered cursor',async()=>{
    mount()
    await screen.findByText('Page 1 / 3')
    fireEvent.change(screen.getByRole('searchbox',{name:'Country roster search'}),
      {target:{value:'future'}})
    apply()
    expect(await screen.findByText('Page 0 / 0')).toBeInTheDocument()
    expect(screen.queryByText('Alpha Future')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox'))
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Alpha Future'})).toBeInTheDocument()
    expect(calls().some(([, , ,f])=>f.search==='future'&&f.include_prepared&&f.offset===0)).toBe(true)
  })

  it('switches Run source without carrying search, status, opt-in or old offset',async()=>{
    mount()
    await screen.findByText('Page 1 / 3')
    fireEvent.change(screen.getByRole('searchbox',{name:'Country roster search'}),
      {target:{value:'Alpha'}})
    fireEvent.change(screen.getByRole('textbox',{name:'Country roster status'}),
      {target:{value:'active'}})
    apply()
    await screen.findByText('Page 1 / 1')
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button',{name:'Change source'}))
    expect(await screen.findByText('Page 1 / 3')).toBeInTheDocument()
    expect(screen.getByRole('searchbox',{name:'Country roster search'})).toHaveValue('')
    expect(screen.getByRole('textbox',{name:'Country roster status'})).toHaveValue('')
    expect(screen.getByRole('checkbox')).not.toBeChecked()
    await waitFor(()=>expect(calls().some(([,branch,rev,f])=>branch==='branch-b'&&
      rev==='rev-b'&&!f.include_prepared&&f.search===''&&f.status_filter===''&&
      f.offset===0)).toBe(true))
    expect(calls().filter(([,branch])=>branch==='branch-b')
      .every(([, , ,f])=>f.offset===0)).toBe(true)
    fireEvent.click(screen.getByRole('button',{name:'Change country'}))
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    expect(calls().filter(([, , ,f])=>f.country_code==='ENG')
      .every(([, , ,f])=>f.offset===0&&f.search==='')).toBe(true)
  })

  it('never refetches or loses an applied filter on language change',async()=>{
    mount()
    await screen.findByText('Page 1 / 3')
    fireEvent.change(screen.getByRole('searchbox',{name:'Country roster search'}),
      {target:{value:'Beta'}})
    apply()
    await screen.findByText('Page 1 / 1')
    const requestCount=calls().length
    fireEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByRole('button',{name:'Použít filtry'})).toBeInTheDocument()
    expect(screen.getByRole('searchbox',{name:'Country roster search'})).toHaveValue('Beta')
    expect(calls()).toHaveLength(requestCount)
  })

  it('fails closed for wrong echoed filter and never falls back when HEAD vanishes',async()=>{
    api.getSavedPlayersInventory.mockImplementation(async (
      run:string,branch:string,head:string,f:Filters,
    )=>({...response(run,branch,head,f),search:'foreign'}))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Response scope does not match')
    expect(screen.queryByRole('table',{name:'Saved country roster'})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Clear Saved HEAD'}))
    expect(screen.getByRole('alert')).toHaveTextContent('No authoritative Saved Revision')
    expect(screen.queryByRole('table',{name:'Saved country roster'})).not.toBeInTheDocument()
  })

  it('jumps to the actual global third page and rejects malformed or future pages',async()=>{
    mount()
    await screen.findByText('Page 1 / 3')
    fireEvent.change(screen.getByRole('textbox',{name:'Country roster page number'}),
      {target:{value:'3'}})
    fireEvent.click(screen.getByRole('button',{name:'Go'}))
    expect(await screen.findByText('Page 3 / 3')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Beta Player 055'})).toBeInTheDocument()
    expect(calls()).toContainEqual(['run','branch-a','rev-a',
      expect.objectContaining({offset:50,limit:25,search:''})])
    const before=calls().length
    for(const invalid of ['0','4','01',' 2','2.0','-1','10000000','']) {
      fireEvent.change(screen.getByRole('textbox',{name:'Country roster page number'}),
        {target:{value:invalid}})
      expect(screen.getByRole('button',{name:'Go'})).toBeDisabled()
    }
    expect(calls()).toHaveLength(before)
    fireEvent.click(screen.getByRole('button',{name:'First'}))
    expect(await screen.findByText('Page 1 / 3')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Last'}))
    expect(await screen.findByText('Page 3 / 3')).toBeInTheDocument()
  })

  it('resets a numeric jump on filtered search, explicit prepared toggle and new HEAD',async()=>{
    mount()
    await screen.findByText('Page 1 / 3')
    fireEvent.change(screen.getByRole('textbox',{name:'Country roster page number'}),
      {target:{value:'2'}})
    fireEvent.click(screen.getByRole('button',{name:'Go'}))
    await screen.findByText('Page 2 / 3')
    fireEvent.change(screen.getByRole('searchbox',{name:'Country roster search'}),
      {target:{value:'Alpha'}})
    apply()
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    expect(screen.getByRole('textbox',{name:'Country roster page number'})).toHaveValue('1')
    fireEvent.change(screen.getByRole('textbox',{name:'Country roster page number'}),
      {target:{value:'2'}})
    fireEvent.click(screen.getByRole('button',{name:'Go'}))
    await screen.findByText('Page 2 / 2')
    fireEvent.click(screen.getByRole('checkbox'))
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    expect(screen.getByRole('textbox',{name:'Country roster page number'})).toHaveValue('1')
    fireEvent.click(screen.getByRole('button',{name:'Change source'}))
    expect(await screen.findByText('Page 1 / 3')).toBeInTheDocument()
    expect(screen.getByRole('textbox',{name:'Country roster page number'})).toHaveValue('1')
    expect(calls().filter(([,branch])=>branch==='branch-b')
      .every(([, , ,f])=>f.offset===0&&f.search==='')).toBe(true)
  })

  it('hydrates a bookmarked filtered 2nd page using the exact HEAD and allows a profile return',async()=>{
    const scope=JSON.stringify(['run','branch-a','rev-a','CZE'])
    const params=writeCountryRosterPermalink(
      new URLSearchParams('tab=players&year=2025&q=some-country'),scope,{
        search:'Alpha',status:'',includePrepared:false,page:1,
      })
    mount('/admin/runs/run/world/countries/CZE?'+params.toString())
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    expect(screen.getByRole('searchbox',{name:'Country roster search'})).toHaveValue('Alpha')
    expect(screen.getByRole('link',{name:'Alpha Player 030'})).toBeInTheDocument()
    expect(calls().some(([,branch,rev,f])=>branch==='branch-a'&&rev==='rev-a'&&
      f.search==='Alpha'&&f.offset===25)).toBe(true)
    expect(calls().every(([, , ,f])=>f.offset===25)).toBe(true)
    const href=screen.getByRole('link',{name:'Alpha Player 030'}).getAttribute('href')
    const playerUrl=new URL(href!,'http://test.local')
    const back=playerUrl.searchParams.get('fromCountry')
    expect(playerUrl.pathname).toBe('/admin/runs/run/people/p-030')
    expect(back).not.toBeNull()
    const country=new URL(back!,'http://test.local')
    expect(country.pathname).toBe('/admin/runs/run/world/countries/CZE')
    expect(country.searchParams.get('spSearch')).toBe('Alpha')
    expect(country.searchParams.get('spPage')).toBe('2')
    expect(country.searchParams.get('year')).toBe('2025')
    expect(country.searchParams.get('q')).toBe('some-country')
  })

  it('does not reuse a bookmarked filter, page or prospect opt-in from an old Saved HEAD',async()=>{
    const oldScope=JSON.stringify(['run','branch-a','rev-old','CZE'])
    const params=writeCountryRosterPermalink(
      new URLSearchParams('tab=players&year=2025'),oldScope,{
        search:'future',status:'prepared',includePrepared:true,page:8,
      })
    mount('/admin/runs/run/world/countries/CZE?'+params.toString())
    expect(await screen.findByText('Page 1 / 3')).toBeInTheDocument()
    expect(screen.getByRole('searchbox',{name:'Country roster search'})).toHaveValue('')
    expect(screen.getByRole('textbox',{name:'Country roster status'})).toHaveValue('')
    expect(screen.getByRole('checkbox')).not.toBeChecked()
    expect(calls().every(([, , ,f])=>f.offset===0&&
      f.search===''&&f.status_filter===''&&!f.include_prepared)).toBe(true)
  })

  it('honors a different bookmark on the SAME mounted Country route and Back history',async()=>{
    mount()
    expect(await screen.findByText('Page 1 / 3')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox',{name:'Country roster search'}),
      {target:{value:'Beta'}})
    apply()
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    const before=calls().length
    fireEvent.click(screen.getByRole('button',{name:'Open same-route bookmark'}))
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    expect(screen.getByRole('searchbox',{name:'Country roster search'})).toHaveValue('Alpha')
    expect(screen.getByRole('textbox',{name:'Country roster page number'})).toHaveValue('2')
    expect(screen.getByRole('link',{name:'Alpha Player 030'})).toBeInTheDocument()
    expect(calls().length).toBeGreaterThan(before)
    expect(calls()[calls().length-1][3]).toMatchObject({
      search:'Alpha',status_filter:'',include_prepared:false,offset:25,
    })
    fireEvent.click(screen.getByRole('button',{name:'Browser Back'}))
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    expect(screen.getByRole('searchbox',{name:'Country roster search'})).toHaveValue('Beta')
    expect(screen.queryByRole('link',{name:'Alpha Player 030'})).not.toBeInTheDocument()
  })
})

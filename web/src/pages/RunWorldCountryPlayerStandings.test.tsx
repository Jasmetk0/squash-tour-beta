import {fireEvent,render,screen,waitFor,within} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router-dom'
import {useState} from 'react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import type {CountryPlayerStandings} from '../api/types'
import {RunWorldCountryPlayerStandings} from './RunWorldCountryPlayerStandings'

const api=vi.hoisted(()=>({getCountryPlayerStandings:vi.fn()}))
vi.mock('../api/client',()=>api)
const response=(branch:string,country:string,rev:string,offset:number,
  patch:Partial<CountryPlayerStandings>={}):CountryPlayerStandings=>{
  const total=country==='CZE'?52:1
  const take=Math.max(0,Math.min(25,total-offset))
  return {
    schema_version:'country_player_standings.v1',source:'reachable_saved_revision',
    run_id:'run',branch_id:branch,revision_branch_id:'origin',
    saved_revision_id:rev,country_code:country,calendar_status:'ready',
    published_event_count:total,country_titles:0,
    country_runner_up_finishes:0,country_played_wins:total,country_played_losses:0,
    country_walkover_wins:0,country_walkover_losses:0,
    total_players:total,offset,limit:25,has_more:offset+25<total,
    players:Array.from({length:take},(_,i)=>({
      position:offset+i+1,player_id:'P'+String(offset+i+1).padStart(3,'0'),
      player_name:'Athlete '+(offset+i+1),country_code:country,
      titles:0,runner_up_finishes:0,final_appearances:0,
      played_wins:1,played_losses:0,walkover_wins:0,walkover_losses:0,
    })),...patch,
  }
}
function mount(initialCountry='CZE'){
  const cache=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})
  function Harness(){
    const [branch,setBranch]=useState('branch-a')
    const [rev,setRev]=useState('rev-a')
    const [country,setCountry]=useState(initialCountry)
    const [cs,setCs]=useState(false)
    const [historical,setHistorical]=useState(false)
    return <>
      <button onClick={()=>{setBranch('branch-b');setRev('rev-b')}}>Change Branch and HEAD</button>
      <button onClick={()=>setCountry('ENG')}>Change country</button>
      <button onClick={()=>setCs(v=>!v)}>Switch language</button>
      <button onClick={()=>setHistorical(true)}>Historical source</button>
      <RunWorldCountryPlayerStandings runId="run" branchId={branch}
        countryCode={country} savedRevisionId={rev} historical={historical} cs={cs}/>
    </>
  }
  render(<QueryClientProvider client={cache}><MemoryRouter><Harness/></MemoryRouter></QueryClientProvider>)
}
describe('Country saved standing navigation (mock HTTP)',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    api.getCountryPlayerStandings.mockImplementation(async (
      _run:string,branch:string,country:string,rev:string,offset:number,_limit:number,
    )=>response(branch,country,rev,offset))
  })
  it('browses first, last and validated numeric pages without refetch on locale',async()=>{
    mount()
    const table=await screen.findByRole('table',{name:'Country player standings table'})
    expect(within(table).getAllByRole('row')).toHaveLength(26)
    expect(screen.getByText('Page 1 / 3')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Last'}))
    expect(await screen.findByText('Page 3 / 3')).toBeInTheDocument()
    expect(api.getCountryPlayerStandings).toHaveBeenCalledWith('run','branch-a','CZE','rev-a',50,25)
    expect(within(await screen.findByRole('table',{name:'Country player standings table'}))
      .getAllByRole('row')).toHaveLength(3)
    fireEvent.change(screen.getByRole('textbox',{name:'Country standings page number'}),
      {target:{value:'2'}})
    fireEvent.click(screen.getByRole('button',{name:'Go'}))
    expect(await screen.findByText('Page 2 / 3')).toBeInTheDocument()
    expect(api.getCountryPlayerStandings).toHaveBeenCalledWith('run','branch-a','CZE','rev-a',25,25)
    const calls=api.getCountryPlayerStandings.mock.calls.length
    fireEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByText('Strana 2 / 3')).toBeInTheDocument()
    expect(api.getCountryPlayerStandings).toHaveBeenCalledTimes(calls)
    fireEvent.change(screen.getByRole('textbox',{name:'Country standings page number'}),
      {target:{value:'4'}})
    expect(screen.getByRole('button',{name:'Přejít'})).toBeDisabled()
    fireEvent.click(screen.getByRole('button',{name:'První'}))
    expect(await screen.findByText('Strana 1 / 3')).toBeInTheDocument()
  })
  it('resets the page before any read of a different Branch, HEAD or country',async()=>{
    mount()
    await screen.findByText('Page 1 / 3')
    fireEvent.click(screen.getByRole('button',{name:'Last'}))
    await screen.findByText('Page 3 / 3')
    fireEvent.click(screen.getByRole('button',{name:'Change Branch and HEAD'}))
    expect(await screen.findByText('Page 1 / 3')).toBeInTheDocument()
    await waitFor(()=>expect(api.getCountryPlayerStandings).toHaveBeenCalledWith(
      'run','branch-b','CZE','rev-b',0,25))
    expect(api.getCountryPlayerStandings.mock.calls
      .filter(([,branch])=>branch==='branch-b').every(([, , , ,offset])=>offset===0)).toBe(true)
    fireEvent.click(screen.getByRole('button',{name:'Change country'}))
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    expect(api.getCountryPlayerStandings).toHaveBeenCalledWith(
      'run','branch-b','ENG','rev-b',0,25)
  })
  it('fails closed on a foreign Saved revision or incomplete source rows',async()=>{
    api.getCountryPlayerStandings.mockImplementation(async (
      _run:string,b:string,c:string,r:string,offset:number,
    )=>response(b,c,r,offset,{saved_revision_id:'elsewhere'}))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Leaderboard evidence differs')
    expect(screen.queryByRole('table',{name:'Country player standings table'})).not.toBeInTheDocument()
  })
  it('does not render a fabricated first page for no saved sporting evidence',async()=>{
    api.getCountryPlayerStandings.mockImplementation(async (
      _run:string,b:string,c:string,r:string,offset:number,
    )=>response(b,c,r,offset,{
      total_players:0,players:[],has_more:false,
      country_played_wins:0,
    }))
    mount()
    expect(await screen.findByText('Page 0 / 0')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Next →'})).toBeDisabled()
    expect(screen.queryByRole('table',{name:'Country player standings table'})).not.toBeInTheDocument()
  })
  it('never links a historical standings identity to the present player profile',async()=>{
    mount()
    await screen.findByRole('table',{name:'Country player standings table'})
    fireEvent.click(screen.getByRole('button',{name:'Historical source'}))
    expect(screen.getByText('Athlete 1')).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Athlete 1'})).not.toBeInTheDocument()
    expect(screen.getByText(/P001/)).toBeInTheDocument()
  })
})

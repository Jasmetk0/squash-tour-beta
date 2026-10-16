import {act,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {RunCalendarInitialHealthControls} from './RunCalendarInitialHealthControls'
import {clock} from '../api/calendarInitialPool.fixture'
import type {InitialHealthRequest} from '../api/calendarInitialHealth'
const api=vi.hoisted(()=>({getCalendarInitialHealth:vi.fn(),reviewCalendarInitialHealth:vi.fn(),confirmCalendarInitialHealth:vi.fn(),savePlayerHealthRevision:vi.fn()}))
vi.mock('../api/client',()=>api)
vi.mock('../utils/apiErrors',()=>({formatApiError:(e:unknown)=>String(e)}))
vi.mock('./RunNavigationSafeguard',()=>({acknowledgeSavedRunForm:vi.fn()}))
const fp='a'.repeat(64),hp='b'.repeat(64),component='c'.repeat(64)
const empty={schema_version:'calendar_initial_health_view.v1',run_id:'run',branch_id:'branch',saved_head_revision_id:'head',
  population_fingerprint:fp,run_calendar:clock,player_count:1,state:null,health_fingerprint:null,health_component_fingerprint:null,saved:false,draft_version:2,draft_status:'clean'}
function state(request:InitialHealthRequest){return {schema_version:'calendar_initial_health_state.v1',run_id:'run',branch_id:'branch',week:{calendar:clock,season_index:0,week:1},
  players:[{player_id:'p1',records:[],permanent_consequences:[]}],source_initial_world_fingerprint:fp,predecessor_fingerprint:null,
  ...request,request_fingerprint:'d'.repeat(64)}}
function mount(){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const element=(head='head')=><QueryClientProvider client={client}><RunCalendarInitialHealthControls runId="run" branchId="branch" head={head} clock={clock} population={fp} playerIds={['p1']} locale="en"/></QueryClientProvider>
  const view=render(element());return {...view,client,changeHead:()=>view.rerender(element('other'))}
}
async function review(){const b=await screen.findByRole('button',{name:'Review initial health'});await waitFor(()=>expect(b).toBeEnabled());fireEvent.click(b);return screen.findByRole('button',{name:'Create initial health'})}
describe('calendar initial health explicit commands',()=>{
  beforeEach(()=>{
    vi.clearAllMocks();api.getCalendarInitialHealth.mockResolvedValue(empty)
    api.reviewCalendarInitialHealth.mockImplementation(async(_r,_b,request)=>({schema_version:'calendar_initial_health_review.v1',request,state:state(request),health_fingerprint:hp}))
    api.confirmCalendarInitialHealth.mockImplementation(async(_r,_b,request)=>{
      const installed={...empty,state:state(request),health_fingerprint:hp,health_component_fingerprint:component,draft_version:3,draft_status:'dirty'}
      api.getCalendarInitialHealth.mockResolvedValue(installed);return installed
    })
    api.savePlayerHealthRevision.mockResolvedValue({saved_revision:{revision_id:'saved',run_id:'run',branch_id:'branch',payload:{content:{player_health_state:{fingerprint:component}}}},
      working_draft:{run_id:'run',branch_id:'branch',status:'clean',base_saved_revision_id:'saved'}})
  })
  it('requires separate consent for confirmation and manual Save',async()=>{
    mount();const confirm=await review();expect(confirm).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm initial health'));fireEvent.click(confirm)
    const save=await screen.findByRole('button',{name:'Save initial health'});expect(save).toBeDisabled()
    expect(api.savePlayerHealthRevision).not.toHaveBeenCalled()
    fireEvent.click(screen.getByLabelText('Confirm health Save'));await waitFor(()=>expect(save).toBeEnabled());fireEvent.click(save)
    await waitFor(()=>expect(api.savePlayerHealthRevision).toHaveBeenCalledWith('run','branch',{expected_draft_version:3,expected_player_health_fingerprint:component}))
  })
  it('recovers an installed baseline after response loss without confirming twice',async()=>{
    const install=api.confirmCalendarInitialHealth.getMockImplementation()!
    api.confirmCalendarInitialHealth.mockImplementation(async(...args)=>{await install(...args);throw Error('Connection lost')})
    mount();const confirm=await review();fireEvent.click(screen.getByLabelText('Confirm initial health'));fireEvent.click(confirm)
    expect(await screen.findByRole('button',{name:'Save initial health'})).toBeDisabled()
    expect(api.confirmCalendarInitialHealth).toHaveBeenCalledTimes(1)
    expect(api.savePlayerHealthRevision).not.toHaveBeenCalled()
  })
  it('discards an asynchronous review when the Saved head changes',async()=>{
    let finish!:(v:unknown)=>void
    api.reviewCalendarInitialHealth.mockReturnValue(new Promise(resolve=>{finish=resolve}))
    const view=mount();const button=await screen.findByRole('button',{name:'Review initial health'});fireEvent.click(button)
    await waitFor(()=>expect(api.reviewCalendarInitialHealth).toHaveBeenCalledTimes(1))
    const request=api.reviewCalendarInitialHealth.mock.calls[0][2];view.changeHead()
    await act(async()=>finish({schema_version:'calendar_initial_health_review.v1',request,state:state(request),health_fingerprint:hp}))
    expect(screen.queryByRole('button',{name:'Create initial health'})).not.toBeInTheDocument()
  })
  it('rejects a wrong-population inspection without offering mutation',async()=>{
    api.getCalendarInitialHealth.mockResolvedValue({...empty,population_fingerprint:'e'.repeat(64)})
    mount();expect(await screen.findByRole('alert')).toHaveTextContent('proof changed')
    expect(screen.queryByRole('button',{name:'Review initial health'})).not.toBeInTheDocument()
  })
  it('does not accept a Save receipt for different content',async()=>{
    api.savePlayerHealthRevision.mockResolvedValue({saved_revision:{run_id:'run',branch_id:'branch',revision_id:'other',payload:{content:{player_health_state:{fingerprint:'bad'}}}}})
    mount();const confirm=await review();fireEvent.click(screen.getByLabelText('Confirm initial health'));fireEvent.click(confirm)
    const save=await screen.findByRole('button',{name:'Save initial health'});fireEvent.click(screen.getByLabelText('Confirm health Save'))
    await waitFor(()=>expect(save).toBeEnabled());fireEvent.click(save)
    expect(await screen.findByRole('alert')).toHaveTextContent('Save receipt differs')
    expect(screen.getByLabelText('Confirm health Save')).not.toBeChecked()
  })
})

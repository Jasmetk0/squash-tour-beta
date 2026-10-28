import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter,Route,Routes} from 'react-router-dom'
import {beforeEach,describe,it,expect,vi} from 'vitest'
import {SavedTourMatchDetailPage} from './SavedTourMatchDetailPage'
import type {SavedTourMatchDetail} from '../api/savedTour'

const api=vi.hoisted(()=>({getSavedTourMatchDetail:vi.fn()}))
const state=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'new-head'},
  mode:'present',timeLoading:false,timeError:null as string|null,
  branchLoading:false,branchError:null as string|null,language:'en'
}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error{}}))
vi.mock('../admin/AdminBranchContext',()=>({useAdminBranch:()=>({
  selectedBranch:state.branch,isLoading:state.branchLoading,error:state.branchError
})}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>({
  mode:state.mode,isLoading:state.timeLoading,error:state.timeError
})}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:state.language})}))
const url='/admin/runs/run-a/tour/calendar/event-x/matches/final'
  +'?branch=branch-a&revision=old-rev&season=2&country=CZE&view=list&tab=results'
function fixture(offset:number):SavedTourMatchDetail{
  const frames=Array.from({length:30},(_,i)=>({
    rally_index:i+1,set_number:1,server_player_id:'A',
    winner_player_id:'A',score_a_before:i,score_b_before:0,
    score_a_after:i+1,score_b_after:0,sets_a_after:0,sets_b_after:0,
    set_complete:false,match_complete:i===29
  }))
  return {
    schema_version:'run_saved_tour_match_detail.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:'branch-a',revision_branch_id:'ancestor',
    saved_revision_id:'old-rev',season_index:2,event_id:'event-x',match_id:'final',
    match:{match_id:'final',draw_type:'main',round_number:2,
      bracket_position:1,winner_player_id:'A',loser_player_id:'B',scoreline:'3-2'},
    replay_status:'available',player_a_id:'A',player_b_id:'B',
    offset,limit:25,total_rallies:30,has_more:offset+25<30,
    rallies:frames.slice(offset,offset+25)
  }
}
function mount(path=url){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const ui=()=> <QueryClientProvider client={client}>
    <MemoryRouter initialEntries={[path]}><Routes>
      <Route path="/admin/runs/:runId/tour/calendar/:eventId/matches/:matchId"
        element={<SavedTourMatchDetailPage/>}/>
    </Routes></MemoryRouter>
  </QueryClientProvider>
  const view=render(ui())
  return {...view,refresh:()=>view.rerender(ui())}
}
describe('exact historical Edition match replay',()=>{
  beforeEach(()=>{
    vi.clearAllMocks();state.mode='present';state.language='en'
    state.timeLoading=false;state.timeError=null
    state.branchLoading=false;state.branchError=null
    state.branch.branch_id='branch-a';state.branch.run_id='run-a'
    state.branch.saved_head_revision_id='new-head'
    api.getSavedTourMatchDetail.mockImplementation((
      _run:string,_branch:string,_rev:string,_season:number,
      _event:string,_match:string,offset:number
    )=>Promise.resolve(fixture(offset)))
  })
  it('reads old revision, pages archived rallies and preserves Edition filters',async()=>{
    mount()
    expect(await screen.findByRole('heading',{name:'Historical match detail'})).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledWith(
      'run-a','branch-a','old-rev',2,'event-x','final',0,25
    )
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    const back=screen.getByRole('link',{name:'Back to Edition results'})
    expect(back).toHaveAttribute('href',expect.stringContaining('revision=old-rev'))
    expect(back).toHaveAttribute('href',expect.stringContaining('country=CZE'))
    const next=screen.getByRole('button',{name:'Next rally →'})
    for(let i=0;i<25;i++)await userEvent.click(next)
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledWith(
      'run-a','branch-a','old-rev',2,'event-x','final',25,25
    )
  })
  it('does not invent a rally replay when saved authority is missing',async()=>{
    api.getSavedTourMatchDetail.mockResolvedValue({
      ...fixture(0),replay_status:'unavailable',total_rallies:0,
      has_more:false,rallies:[],player_a_id:null,player_b_id:null
    })
    mount()
    expect(await screen.findByText(/No verified rally archive exists/)).toBeInTheDocument()
    expect(screen.getByText('3-2')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Next rally →'})).not.toBeInTheDocument()
  })
  it('hides a loaded replay on checkpoint, loading and failed context without remount',async()=>{
    const view=mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Next rally →'})).toBeInTheDocument()
    const calls=api.getSavedTourMatchDetail.mock.calls.length
    state.mode='checkpoint';view.refresh()
    expect(screen.getByRole('alert')).toHaveTextContent('Checkpoint is not bound')
    expect(screen.queryByText('Rally 1/30')).not.toBeInTheDocument()
    expect(screen.queryByText('3-2')).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Next rally →'})).not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(calls)
    state.mode='present';state.timeLoading=true;view.refresh()
    expect(screen.queryByText('Rally 1/30')).not.toBeInTheDocument()
    state.timeLoading=false;state.timeError='Time context unavailable';view.refresh()
    expect(screen.getByRole('alert')).toHaveTextContent('Time context unavailable')
    expect(screen.queryByRole('button',{name:'Next rally →'})).not.toBeInTheDocument()
    state.timeError=null;state.branchLoading=true;view.refresh()
    expect(screen.queryByText('3-2')).not.toBeInTheDocument()
    state.branchLoading=false;state.branchError='Branch context unavailable';view.refresh()
    expect(screen.getByRole('alert')).toHaveTextContent('Branch context unavailable')
    expect(screen.queryByText('Rally 1/30')).not.toBeInTheDocument()
    state.branchError=null;view.refresh()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
  })
  it('rejects foreign saved revision and mismatched cached rally offset',async()=>{
    api.getSavedTourMatchDetail.mockResolvedValueOnce({...fixture(0),saved_revision_id:'foreign'})
    const view=mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByText('3-2')).not.toBeInTheDocument()
    view.unmount()
    api.getSavedTourMatchDetail.mockResolvedValueOnce({...fixture(25),offset:25})
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByRole('button',{name:'Next rally →'})).not.toBeInTheDocument()
  })
  it('never requests current saved HEAD for missing revision or checkpoint',()=>{
    state.mode='checkpoint'
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('Checkpoint is not bound')
    expect(api.getSavedTourMatchDetail).not.toHaveBeenCalled()
  })
  it('translates replay UI without requesting the same Saved page again',async()=>{
    const view=mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    const calls=api.getSavedTourMatchDetail.mock.calls.length
    state.language='cs'
    view.refresh()
    expect(screen.getByText('Výměna 1/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(calls)
  })
  it('returns to the originating Draw tab with the exact encoded URL state',async()=>{
    mount('/admin/runs/run-a/tour/calendar/event-x/matches/final?branch=branch-a&revision=old-rev&season=2&tab=draw&view=list&country=CZE')
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    const back=screen.getByRole('link',{name:'Back to Edition draw'})
    expect(back).toHaveAttribute('href',expect.stringContaining('tab=draw'))
    expect(back).toHaveAttribute('href',expect.stringContaining('revision=old-rev'))
    expect(back).toHaveAttribute('href',expect.stringContaining('view=list'))
    expect(back).toHaveAttribute('href',expect.stringContaining('country=CZE'))
  })
  it('opens current player careers only when match is from the selected Saved HEAD',async()=>{
    state.branch.saved_head_revision_id='old-rev'
    mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'A'})).toHaveAttribute('href','/admin/runs/run-a/people/A?tab=career')
    expect(screen.getByRole('link',{name:'B'})).toHaveAttribute('href','/admin/runs/run-a/people/B?tab=career')
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
  })
  it('keeps archived match participants as IDs, never as current player profile links',async()=>{
    mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'A'})).not.toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'B'})).not.toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Back to Edition results'})).toHaveAttribute('href',
      expect.stringContaining('revision=old-rev'))
  })
  it('jumps from first to last rally and back across archived pages without fabricating frames',async()=>{
    mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'First rally'})).toBeDisabled()
    await userEvent.click(screen.getByRole('button',{name:'Last rally'}))
    expect(await screen.findByText('Rally 30/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenLastCalledWith(
      'run-a','branch-a','old-rev',2,'event-x','final',25,25)
    expect(screen.getByRole('button',{name:'Last rally'})).toBeDisabled()
    await userEvent.click(screen.getByRole('button',{name:'First rally'}))
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('link',{name:'Back to Edition results'})).toHaveAttribute(
      'href',expect.stringContaining('revision=old-rev'))
  })
  it('accepts typed rally jumps only within verified bounds and retains Saved scope',async()=>{
    mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    const input=screen.getByRole('spinbutton',{name:'Archived rally number'})
    const jump=screen.getByRole('button',{name:'Jump to rally'})
    expect(jump).toBeDisabled()
    await userEvent.type(input,'26')
    expect(jump).toBeEnabled()
    await userEvent.click(jump)
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    expect(input).toHaveValue(null)
    expect(api.getSavedTourMatchDetail).toHaveBeenLastCalledWith(
      'run-a','branch-a','old-rev',2,'event-x','final',25,25)
    await userEvent.type(input,'30')
    await userEvent.keyboard('{Enter}')
    expect(await screen.findByText('Rally 30/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(2)
    await userEvent.type(input,'31')
    expect(jump).toBeDisabled()
    expect(screen.getByText('Rally 30/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(2)
  })
  it('shows localized rally jump controls and does not offer navigation without a replay archive',async()=>{
    const view=mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    const count=api.getSavedTourMatchDetail.mock.calls.length
    state.language='cs';view.refresh()
    expect(screen.getByRole('spinbutton',{name:'Číslo archivované výměny'})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Poslední výměna'})).toBeEnabled()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(count)
    view.unmount()
    state.language='en'
    api.getSavedTourMatchDetail.mockResolvedValue({
      ...fixture(0),replay_status:'unavailable',total_rallies:0,
      has_more:false,rallies:[],player_a_id:null,player_b_id:null
    })
    mount()
    expect(await screen.findByText(/No verified rally archive exists/)).toBeInTheDocument()
    expect(screen.queryByRole('spinbutton',{name:'Archived rally number'})).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Jump to rally'})).not.toBeInTheDocument()
  })
  it('allows a failed rally page to recover without changing the saved source',async()=>{
    api.getSavedTourMatchDetail.mockRejectedValueOnce(new Error('offline'))
    mount()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByText('3-2')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Retry match / archive read'}))
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(2)
    expect(api.getSavedTourMatchDetail).toHaveBeenLastCalledWith(
      'run-a','branch-a','old-rev',2,'event-x','final',0,25)
  })

})

import {render,screen,within} from '@testing-library/react'
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
    score_a_after:i+1,score_b_after:0,sets_a_after:i===29?1:0,sets_b_after:0,
    set_complete:i===29,match_complete:i===29
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
  it('shows the verified post-rally scores in source A/B order and advances without an extra read',async()=>{
    mount()
    const board=await screen.findByRole('region',{name:'Archived rally scoreboard'})
    expect(board.closest('[data-run-navigation-readonly]')).not.toBeNull()
    expect(board).toHaveTextContent('Player A: A')
    expect(board).toHaveTextContent('Player B: B')
    expect(within(board).getAllByText('Game points:',{exact:false}).map(node=>node.textContent))
      .toEqual(['Game points: 1','Game points: 0'])
    expect(within(board).getByRole('progressbar')).toHaveAttribute('value','1')
    expect(within(board).getByRole('progressbar')).toHaveAttribute('max','30')
    await userEvent.click(screen.getByRole('button',{name:'Next rally →'}))
    expect(await screen.findByText('Rally 2/30')).toBeInTheDocument()
    const nextBoard=screen.getByRole('region',{name:'Archived rally scoreboard'})
    expect(within(nextBoard).getAllByText('Game points:',{exact:false}).map(node=>node.textContent))
      .toEqual(['Game points: 2','Game points: 0'])
    expect(within(nextBoard).getByRole('progressbar')).toHaveAttribute('value','2')
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
  })
  it('localizes the scoreboard and hides it when the historical scope is invalid',async()=>{
    const view=mount()
    expect(await screen.findByRole('region',{name:'Archived rally scoreboard'})).toBeInTheDocument()
    state.language='cs';view.refresh()
    const board=screen.getByRole('region',{name:'Skóre archivované výměny'})
    expect(within(board).getByRole('progressbar',{name:'Pozice v archivu výměn'})).toHaveAttribute('value','1')
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
    state.mode='checkpoint';view.refresh()
    expect(screen.queryByRole('region',{name:'Skóre archivované výměny'})).not.toBeInTheDocument()
  })
  it('separates match sections without changing the exact replay bookmark or refetching',async()=>{
    mount(url+'&rally=26&q=keep')
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    const nav=screen.getByRole('navigation',{name:'Match sections'})
    await userEvent.click(within(nav).getByRole('button',{name:'Statistics'}))
    const stats=screen.getByRole('region',{name:'Statistics'})
    expect(stats).toHaveTextContent('Total archived rallies: 30')
    expect(stats).toHaveTextContent('Verified page range: 26–30 / 30')
    expect(stats).toHaveTextContent('These are not whole-match statistics.')
    expect(stats).toHaveTextContent('Rallies won by A (A)5')
    expect(stats).toHaveTextContent('Rallies won by B (B)0')
    expect(screen.queryByRole('region',{name:'Archived rally scoreboard'})).not.toBeInTheDocument()
    await userEvent.click(within(nav).getByRole('button',{name:'Overview'}))
    expect(screen.getByRole('region',{name:'Overview'})).toHaveTextContent(
      'Verified rally archive is available.')
    expect(screen.getByText('3-2')).toBeInTheDocument()
    await userEvent.click(within(nav).getByRole('button',{name:'Course & Replay'}))
    expect(screen.getByText('Rally 26/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
    const href=screen.getByRole('link',{name:'Back to Edition results'}).getAttribute('href')!
    expect(href).toContain('q=keep')
    expect(href).toContain('revision=old-rev')
    expect(href).not.toContain('rally=')
  })
  it('keeps localized statistics unavailable when no archive is recorded',async()=>{
    state.language='cs'
    api.getSavedTourMatchDetail.mockResolvedValue({
      ...fixture(0),replay_status:'unavailable',total_rallies:0,
      has_more:false,rallies:[],player_a_id:null,player_b_id:null
    })
    mount()
    const nav=await screen.findByRole('navigation',{name:'Oddíly zápasu'})
    await userEvent.click(within(nav).getByRole('button',{name:'Statistiky'}))
    const stats=screen.getByRole('region',{name:'Statistiky'})
    expect(stats).toHaveTextContent('Pro tuto stránku nejsou ověřené výměny dostupné.')
    expect(stats).not.toHaveTextContent('Archivovaných výměn celkem')
    expect(stats).not.toHaveTextContent('Výměny s vítězem A')
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
  })
  it('hides all match sections when source context becomes invalid',async()=>{
    const view=mount()
    const nav=await screen.findByRole('navigation',{name:'Match sections'})
    await userEvent.click(within(nav).getByRole('button',{name:'Statistics'}))
    expect(screen.getByRole('region',{name:'Statistics'})).toBeInTheDocument()
    state.mode='checkpoint';view.refresh()
    expect(screen.queryByRole('navigation',{name:'Match sections'})).not.toBeInTheDocument()
    expect(screen.queryByRole('region',{name:'Statistics'})).not.toBeInTheDocument()
  })
  it('plays verified rallies across the 25/26 boundary and stops on an explicit pause',async()=>{
    mount(url+'&rally=25')
    expect(await screen.findByText('Rally 25/30')).toBeInTheDocument()
    const playback=screen.getByRole('region',{name:'Replay playback'})
    await userEvent.selectOptions(within(playback).getByRole('combobox',{name:'Playback speed'}),'4')
    await userEvent.click(within(playback).getByRole('button',{name:'Play replay'}))
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Pause replay'}))
    expect(screen.getByRole('button',{name:'Play replay'})).toBeEnabled()
    expect(api.getSavedTourMatchDetail.mock.calls.map(call=>call[6])).toEqual([0,25])
  })
  it('stops at a recorded game end and jumps only to proven game landmarks',async()=>{
    // Two 15-event games: four neutral rallies then eleven scoring rallies.
    api.getSavedTourMatchDetail.mockImplementation((
      _run:string,_branch:string,_rev:string,_season:number,
      _event:string,_match:string,offset:number
    )=>{
      const frames=Array.from({length:30},(_,i)=>{
        const game=Math.floor(i/15)+1,withinGame=i%15
        const end=withinGame===14
        return {rally_index:i+1,set_number:game,server_player_id:'A',
          winner_player_id:withinGame<4?null:'A',
          score_a_before:Math.max(0,withinGame-4),score_b_before:0,
          score_a_after:Math.max(0,withinGame-3),score_b_after:0,
          sets_a_after:game-1+Number(end),sets_b_after:0,
          set_complete:end,match_complete:i===29}
      })
      const original=fixture(offset)
      return Promise.resolve({...original,match:{...original.match,scoreline:'2-0'},
        rallies:frames.slice(offset,offset+25)})
    })
    mount(url+'&rally=14')
    expect(await screen.findByText('Rally 14/30')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Playback speed'}),'4')
    await userEvent.click(screen.getByRole('button',{name:'Play replay'}))
    expect(await screen.findByText('Rally 15/30')).toBeInTheDocument()
    expect(await screen.findByRole('button',{name:'Play replay'})).toBeEnabled()
    expect(screen.getByRole('button',{name:'Game 1 · end · #15'})).toBeDisabled()
    await userEvent.click(screen.getByRole('button',{name:'Game 2 · start · #16'}))
    expect(screen.getByText('Rally 16/30')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Game 2 · end · #30'})).not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
  })
  it('cancels playback after a failed page read and does not restart on retry',async()=>{
    api.getSavedTourMatchDetail.mockImplementation((
      _run:string,_branch:string,_rev:string,_season:number,
      _event:string,_match:string,offset:number
    )=>offset===25?Promise.reject(new Error('offline')):Promise.resolve(fixture(offset)))
    mount(url+'&rally=25')
    expect(await screen.findByText('Rally 25/30')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Playback speed'}),'4')
    await userEvent.click(screen.getByRole('button',{name:'Play replay'}))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Pause replay'})).not.toBeInTheDocument()
    api.getSavedTourMatchDetail.mockResolvedValueOnce(fixture(25))
    await userEvent.click(screen.getByRole('button',{name:'Retry match / archive read'}))
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Play replay'})).toBeEnabled()
    expect(screen.queryByRole('button',{name:'Pause replay'})).not.toBeInTheDocument()
  })
  it('does not offer an unproven game start on a direct later-page bookmark',async()=>{
    mount(url+'&rally=26')
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:/Game 1 · start/})).not.toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Game 1 · end · #30'})).toBeEnabled()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
  })
  it('builds whole-archive counts only after consecutive verified pages have been read',async()=>{
    mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    const nav=screen.getByRole('navigation',{name:'Match sections'})
    await userEvent.click(within(nav).getByRole('button',{name:'Statistics'}))
    expect(screen.queryByRole('region',{name:'Complete archive statistics'})).not.toBeInTheDocument()
    expect(screen.getByText('Complete archive statistics require all consecutive verified pages to be loaded.')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button',{name:'Previous rally page'})).toBeDisabled()
    await userEvent.click(screen.getByRole('button',{name:'Next rally page'}))
    const complete=await screen.findByRole('region',{name:'Complete archive statistics'})
    expect(complete).toHaveTextContent('Rallies won by A (A)30')
    expect(complete).toHaveTextContent('Rallies won by B (B)0')
    expect(complete).toHaveTextContent('No recorded rally winner0')
    expect(screen.getByRole('button',{name:'Next rally page'})).toBeDisabled()
    const games=within(complete).getByRole('table',{name:'Recorded completed games'})
    expect(within(games).getAllByRole('row')).toHaveLength(2)
    await userEvent.click(within(games).getByRole('button',{name:'#30'}))
    expect(await screen.findByText('Rally 30/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail.mock.calls.map(call=>call[6])).toEqual([0,25])
  })
  it('does not treat an isolated later page as the complete archive',async()=>{
    mount(url+'&rally=26')
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Statistics'}))
    expect(screen.queryByRole('region',{name:'Complete archive statistics'})).not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail.mock.calls.map(call=>call[6])).toEqual([25])
  })
  it('rejects complete statistics when two cached pages do not join',async()=>{
    api.getSavedTourMatchDetail.mockImplementation((
      _run:string,_branch:string,_rev:string,_season:number,
      _event:string,_match:string,offset:number
    )=>{
      const original=fixture(offset)
      return Promise.resolve(offset!==25?original:{
        ...original,rallies:original.rallies.map(frame=>({
          ...frame,score_a_before:frame.score_a_before+100,
          score_a_after:frame.score_a_after+100
        }))
      })
    })
    mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Statistics'}))
    await userEvent.click(screen.getByRole('button',{name:'Next rally page'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByRole('region',{name:'Complete archive statistics'})).not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail.mock.calls.map(call=>call[6])).toEqual([0,25])
  })
  it('rejects two independently valid but discontinuous cached archive pages',async()=>{
    api.getSavedTourMatchDetail.mockImplementation((
      _run:string,_branch:string,_rev:string,_season:number,
      _event:string,_match:string,offset:number
    )=>{
      const original=fixture(offset)
      if(offset!==25)return Promise.resolve(original)
      // This entire page has internally consistent, but forged, scoreboard
      // numbers. Without the cached rally-25 check it would look authentic.
      return Promise.resolve({...original,rallies:original.rallies.map(frame=>({
        ...frame,score_a_before:frame.score_a_before+100,
        score_a_after:frame.score_a_after+100
      }))})
    })
    mount()
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Last rally'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByText('Rally 30/30')).not.toBeInTheDocument()
    expect(screen.queryByRole('region',{name:'Archived rally scoreboard'})).not.toBeInTheDocument()
    expect(screen.queryByRole('table',{name:'Verified archived rally page'}))
      .not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(2)
  })
  it('rejects an inconsistent cached page when navigating BACK from a direct bookmark',async()=>{
    api.getSavedTourMatchDetail.mockImplementation((
      _run:string,_branch:string,_rev:string,_season:number,
      _event:string,_match:string,offset:number
    )=>{
      const original=fixture(offset)
      return Promise.resolve(offset!==25?original:{
        ...original,rallies:original.rallies.map(frame=>({
          ...frame,score_a_before:frame.score_a_before+100,
          score_a_after:frame.score_a_after+100
        }))
      })
    })
    mount(url+'&rally=26')
    // The direct link cannot prove unseen earlier evidence, so it reads only page 2.
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'First rally'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByText('Rally 1/30')).not.toBeInTheDocument()
    expect(screen.queryByRole('table',{name:'Verified archived rally page'}))
      .not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(2)
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
    expect(screen.queryByRole('region',{name:'Archived rally scoreboard'})).not.toBeInTheDocument()
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
  it('refuses nonnumeric archived scores without rendering fabricated rally states',async()=>{
    api.getSavedTourMatchDetail.mockResolvedValue({
      ...fixture(0),rallies:[
        {...fixture(0).rallies[0],score_a_after:'1'},
        ...fixture(0).rallies.slice(1)
      ]
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByText('Rally 1/30')).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Jump to rally'})).not.toBeInTheDocument()
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
  it('links historical participants to published finals of their exact Saved season',async()=>{
    mount('/admin/runs/run-a/tour/calendar/event-x/matches/final?branch=branch-a&revision=old-rev&season=2&tab=results&matchSearch=A&week=9&country=CZE&q=keep')
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'A'})).not.toBeInTheDocument()
    for(const id of ['A','B']){
      const link=screen.getByRole('link',{name:'Find published finals for '+id})
      const href=link.getAttribute('href')!
      for(const x of ['revision=old-rev','branch=branch-a','season=2','publication=published','view=list','q=keep','playerId='+id])
        expect(href).toContain(x)
      for(const x of ['week=9','country=CZE','matchSearch'])expect(href).not.toContain(x)
    }
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
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
  it('browses the 25 genuine page frames and selects a bookmarked rally without another fetch',async()=>{
    mount(url+'&q=keep')
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Browse archived rallies',{exact:false}))
    const table=screen.getByRole('table',{name:'Verified archived rally page'})
    expect(within(table).getAllByRole('row')).toHaveLength(26)
    const first=within(table).getByRole('button',{name:'Rally 1'})
    expect(first).toBeDisabled()
    expect(first).toHaveAttribute('aria-current','step')
    expect(within(table).queryByRole('button',{name:'Rally 26'})).not.toBeInTheDocument()
    expect(within(table).getByText('0:0')).toBeInTheDocument()
    await userEvent.click(within(table).getByRole('button',{name:'Rally 20'}))
    expect(await screen.findByText('Rally 20/30')).toBeInTheDocument()
    expect(within(table).getByRole('button',{name:'Rally 20'})).toHaveAttribute('aria-current','step')
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('link',{name:'Back to Edition results'}).getAttribute('href'))
      .not.toContain('rally=')
    await userEvent.click(screen.getByRole('button',{name:'Last rally'}))
    expect(await screen.findByText('Rally 30/30')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Browse archived rallies',{exact:false}))
    const end=screen.getByRole('table',{name:'Verified archived rally page'})
    expect(within(end).getAllByRole('row')).toHaveLength(6)
    expect(within(end).queryByRole('button',{name:'Rally 20'})).not.toBeInTheDocument()
    await userEvent.click(within(end).getByRole('button',{name:'Rally 26'}))
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(2)
  })
  it('does not expose a rally table for a forged page or an unavailable replay',async()=>{
    api.getSavedTourMatchDetail.mockResolvedValue({...fixture(0),saved_revision_id:'other'})
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByRole('table',{name:'Verified archived rally page'})).not.toBeInTheDocument()
    expect(screen.queryByText('Browse archived rallies',{exact:false})).not.toBeInTheDocument()
  })
  it('resolves a shared rally deep link at its true archive offset and clears it on Edition return',async()=>{
    const urlWithRally=url+'&rally=26&q=keep'
    mount(urlWithRally)
    expect(await screen.findByText('Rally 26/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledWith(
      'run-a','branch-a','old-rev',2,'event-x','final',25,25)
    const back=screen.getByRole('link',{name:'Back to Edition results'})
    const href=back.getAttribute('href')!
    expect(href).toContain('revision=old-rev')
    expect(href).toContain('q=keep')
    expect(href).not.toContain('rally=')
    for(const id of ['A','B']){
      expect(screen.getByRole('link',{name:'Find published finals for '+id}))
        .not.toHaveAttribute('href',expect.stringContaining('rally='))
    }
    await userEvent.click(screen.getByRole('button',{name:'First rally'}))
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
  })
  it.each(['0','01','-1','1e3','99999999999999999999999','100001'])(
    'rejects an invalid rally URL %s before making any API call',async raw=>{
      mount(url+'&rally='+raw)
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Invalid archived rally number in link.')
      expect(api.getSavedTourMatchDetail).not.toHaveBeenCalled()
      expect(screen.queryByRole('button',{name:'Next rally →'})).not.toBeInTheDocument()
    }
  )
  it('recovers from a cached out-of-range page to the real final rally',async()=>{
    mount(url+'&rally=51')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Requested rally is outside this Saved archive.')
    await userEvent.click(screen.getByRole('button',{name:'Return to first rally'}))
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Last rally'}))
    expect(await screen.findByText('Rally 30/30')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail.mock.calls.map(call=>call[6])).toEqual([50,0,25])
  })
  it('shows an honest absent-rally error for a valid but out-of-range bookmark',async()=>{
    mount(url+'&rally=90')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Requested rally is outside this Saved archive.')
    expect(screen.queryByText('Rally 90/30')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Return to first rally'}))
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
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
    // A previously visited page may be independently revalidated by React Query.
    expect(api.getSavedTourMatchDetail).toHaveBeenLastCalledWith(
      'run-a','branch-a','old-rev',2,'event-x','final',0,25)
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
    // A new query page replaces the previous input node; inspect the current page.
    const nextInput=screen.getByRole('spinbutton',{name:'Archived rally number'})
    expect(nextInput).toHaveValue(null)
    expect(api.getSavedTourMatchDetail).toHaveBeenLastCalledWith(
      'run-a','branch-a','old-rev',2,'event-x','final',25,25)
    await userEvent.type(nextInput,'30')
    await userEvent.keyboard('{Enter}')
    expect(await screen.findByText('Rally 30/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(2)
    await userEvent.type(nextInput,'31')
    // Check the active query page, not the detached submit button from rally 1.
    expect(screen.getByRole('button',{name:'Jump to rally'})).toBeDisabled()
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

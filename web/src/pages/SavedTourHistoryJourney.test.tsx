/** Route-level integration of the three immutable Saved Tour viewers.
 * Mocked HTTP boundaries: this does not replace real SQLite/Chromium acceptance. */
import {render,screen,within} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter,Route,Routes,useLocation,useNavigate} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import type {SavedTourCalendar,SavedTourEdition,SavedTourMatchDetail,SavedTourEvent} from '../api/savedTour'
import {SavedTourCalendarPage} from './SavedTourCalendarPage'
import {SavedTourEditionPage} from './SavedTourEditionPage'
import {SavedTourMatchDetailPage} from './SavedTourMatchDetailPage'

const api=vi.hoisted(()=>({
  getSavedTourCalendar:vi.fn(),getSavedTourEdition:vi.fn(),getSavedTourMatchDetail:vi.fn()
}))
const context=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'new-head'},
  time:{mode:'present',presentSeason:2,isLoading:false,error:null},
  language:'en'
}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error{}}))
vi.mock('../admin/AdminBranchContext',()=>({useAdminBranch:()=>({
  selectedBranch:context.branch,isLoading:false,error:null
})}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>context.time}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:context.language})}))

const scope='branch=branch-a&revision=rev-old&season=2'
const start='/admin/runs/run-a/tour/calendar?'+scope+'&view=list&country=CZE&week=5&q=keep'
function event(id:string,name:string,week:number,country:string,
  published:boolean,champion:string|null,finalist:string|null):SavedTourEvent{
  return {event_id:id,event_name:name,season:'2002/2003',season_week:week,
    template_id:'tpl',category:'DIAMOND',tour_level:'WORLD',host_country:country,
    host_city:country==='CZE'?'Brno':'Cairo',region:'EUROPE',main_draw_size:16,
    qualification_draw_size:8,seeds_count:4,qualifier_spots:4,wild_cards:2,byes:0,
    ranking_status:'ranked',result_published:published,champion_player_id:champion,
    finalist_player_id:finalist}
}
const brno=event('event-x','Brno Open',5,'CZE',true,'P1','P2')
function calendar():SavedTourCalendar{
  return {schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:'branch-a',revision_branch_id:'ancestor',
    saved_revision_id:'rev-old',season_index:2,season:'2002/2003',week_count:61,
    calendar_status:'ready',edition_count:3,editions:[
      brno,event('event-y','Cairo Open',9,'EGY',true,'P3','P1'),
      // Unpublished labels must never be counted as a player's final result.
      event('future','Future Cup',12,'CZE',false,'P1','P2')
    ]}
}
function edition():SavedTourEdition{
  return {schema_version:'run_saved_tour_edition.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:'branch-a',revision_branch_id:'ancestor',
    saved_revision_id:'rev-old',season_index:2,lifecycle_status:'unavailable',
    edition:brno,
    published_result:{schema_version:'viewer_tournament_result.v1',
      product_run_id:'run-a',viewer_branch_id:'ancestor',event_id:'event-x',
      completed_season_index:2,completed_week:5,champion_player_id:'P1',
      finalist_player_id:'P2',qualification_winner_ids:[],
      players:[{player_id:'P1',draw_type:'main',reached_stage:'champion',wins:1,losses:0}],
      matches:[{match_id:'final',draw_type:'main',round_number:2,bracket_position:1,
        winner_player_id:'P1',loser_player_id:'P2',scoreline:'3-0'}]}
  }
}
function match(offset:number):SavedTourMatchDetail{
  const frames=Array.from({length:30},(_,i)=>({
    rally_index:i+1,set_number:1,server_player_id:'P1',winner_player_id:'P1',
    score_a_before:i,score_b_before:0,score_a_after:i+1,score_b_after:0,
    sets_a_after:i===29?1:0,sets_b_after:0,set_complete:i===29,match_complete:i===29
  }))
  return {schema_version:'run_saved_tour_match_detail.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:'branch-a',revision_branch_id:'ancestor',
    saved_revision_id:'rev-old',season_index:2,event_id:'event-x',match_id:'final',
    match:{match_id:'final',draw_type:'main',round_number:2,bracket_position:1,
      winner_player_id:'P1',loser_player_id:'P2',scoreline:'3-0'},
    replay_status:'available',player_a_id:'P1',player_b_id:'P2',
    offset,limit:25,total_rallies:30,has_more:offset+25<30,
    rallies:frames.slice(offset,offset+25)}
}
function RouteLocation():JSX.Element{
  const location=useLocation(),navigate=useNavigate()
  const move=(revision:string,branch:string)=>{
    const q=new URLSearchParams(location.search)
    q.set('revision',revision)
    q.set('branch',branch)
    q.delete('rally')
    navigate(location.pathname+'?'+q.toString())
  }
  return <>
    <output data-testid="journey-route">{location.pathname+location.search}</output>
    <button type="button" onClick={()=>move('rev-other',context.branch.branch_id)}>
      Open other Saved Revision
    </button>
    <button type="button" onClick={()=>{
      context.branch.branch_id='branch-b'
      move('rev-old','branch-b')
    }}>Switch selected Branch</button>
  </>
}
function mount(path=start){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>
    <RouteLocation/>
    <Routes>
      <Route path="/admin/runs/:runId/tour/calendar" element={<SavedTourCalendarPage/>}/>
      <Route path="/admin/runs/:runId/tour/calendar/:eventId" element={<SavedTourEditionPage/>}/>
      <Route path="/admin/runs/:runId/tour/calendar/:eventId/matches/:matchId"
        element={<SavedTourMatchDetailPage/>}/>
    </Routes>
  </MemoryRouter></QueryClientProvider>)
}

describe('Saved Tour historical navigation across mounted pages',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.branch.run_id='run-a'
    context.branch.branch_id='branch-a'
    context.branch.saved_head_revision_id='new-head'
    context.time.mode='present';context.time.presentSeason=2
    context.time.isLoading=false;context.time.error=null
    context.language='en'
    api.getSavedTourCalendar.mockResolvedValue(calendar())
    api.getSavedTourEdition.mockResolvedValue(edition())
    api.getSavedTourMatchDetail.mockImplementation(
      (_run:string,_branch:string,_revision:string,_season:number,
        _event:string,_match:string,offset:number)=>Promise.resolve(match(offset)))
  })
  it('navigates calendar → published Edition → match replay → same-revision player evidence',async()=>{
    mount()
    expect(await screen.findByRole('link',{name:'Brno Open'})).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Future Cup'})).not.toBeInTheDocument()
    const result=screen.getByRole('link',{name:'View results'})
    await userEvent.click(result)
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    expect(api.getSavedTourEdition).toHaveBeenCalledWith(
      'run-a','branch-a','rev-old',2,'event-x')
    expect(screen.getByRole('button',{name:'Results'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link',{name:'Match detail'}))
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledWith(
      'run-a','branch-a','rev-old',2,'event-x','final',0,25)
    // The historical match must not be represented as a current-HEAD career.
    expect(screen.queryByRole('link',{name:'P1'})).not.toBeInTheDocument()
    const evidence=screen.getByRole('link',{name:'Find published finals for P1'})
    expect(evidence).toHaveAttribute('href',expect.stringContaining('revision=rev-old'))
    await userEvent.click(evidence)
    const list=await screen.findByRole('table',{name:'Saved Tour edition list'})
    expect(within(list).getAllByRole('row')).toHaveLength(3)
    expect(screen.getByRole('link',{name:'Brno Open'})).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Cairo Open'})).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Future Cup'})).not.toBeInTheDocument()
    const route=screen.getByTestId('journey-route').textContent??''
    for(const value of ['branch=branch-a','revision=rev-old','season=2',
      'view=list','publication=published','playerId=P1','q=keep'])expect(route).toContain(value)
    for(const value of ['country=CZE','week=5','tab=results'])expect(route).not.toContain(value)
    expect(api.getSavedTourCalendar.mock.calls.length).toBeGreaterThanOrEqual(2)
    expect(api.getSavedTourCalendar.mock.calls.every(
      (args:unknown[])=>JSON.stringify(args)===JSON.stringify(['run-a','branch-a','rev-old',2]))).toBe(true)
    expect(api.getSavedTourEdition).toHaveBeenCalledTimes(1)
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledTimes(1)
  })

  it('resets the archived rally cursor when the immutable Saved Revision changes in place',async()=>{
    // Two proven revisions can have different recorded match summaries. The previous
    // revision's page 25..29 must never remain visible while the next one loads.
    api.getSavedTourMatchDetail.mockImplementation(
      (_run:string,_branch:string,revision:string,_season:number,
        _event:string,_match:string,offset:number)=>Promise.resolve({
          ...match(offset),saved_revision_id:revision,
          match:{...match(offset).match,scoreline:revision==='rev-other'?'3-1':'3-0'}
        }))
    mount('/admin/runs/run-a/tour/calendar/event-x/matches/final?'+scope+'&tab=results&q=keep')
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Last rally'}))
    expect(await screen.findByText('Rally 30/30')).toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledWith(
      'run-a','branch-a','rev-old',2,'event-x','final',25,25)
    await userEvent.click(screen.getByRole('button',{name:'Open other Saved Revision'}))
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    expect(screen.queryByText('Rally 30/30')).not.toBeInTheDocument()
    expect(screen.getByTestId('journey-route')).toHaveTextContent('revision=rev-other')
    expect(screen.getByTestId('journey-route')).toHaveTextContent('q=keep')
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledWith(
      'run-a','branch-a','rev-other',2,'event-x','final',0,25)
    expect(screen.getByRole('link',{name:'Find published finals for P1'}))
      .toHaveAttribute('href',expect.stringContaining('revision=rev-other'))
    expect(api.getSavedTourMatchDetail.mock.calls.every(
      (args:unknown[])=>args[6]===0||args[6]===25)).toBe(true)
  })

  it('rejects a stale Branch result after switching a selected Branch mid-replay',async()=>{
    mount('/admin/runs/run-a/tour/calendar/event-x/matches/final?'+scope+'&tab=results')
    expect(await screen.findByText('Rally 1/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Last rally'}))
    expect(await screen.findByText('Rally 30/30')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Switch selected Branch'}))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Archived match does not match the selected Run/Branch/revision or rally page.')
    expect(screen.queryByText('Rally 30/30')).not.toBeInTheDocument()
    expect(screen.queryByText('Rally 1/30')).not.toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Find published finals for P1'})).not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledWith(
      'run-a','branch-b','rev-old',2,'event-x','final',0,25)
  })

  it('fails closed at the Edition boundary for a foreign Saved Revision',async()=>{
    api.getSavedTourEdition.mockResolvedValue({...edition(),saved_revision_id:'new-head'})
    mount()
    expect(await screen.findByRole('link',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link',{name:'View results'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid or stale Edition identity.')
    expect(screen.queryByRole('link',{name:'Match detail'})).not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).not.toHaveBeenCalled()
    expect(api.getSavedTourEdition).toHaveBeenCalledWith(
      'run-a','branch-a','rev-old',2,'event-x')
  })

  it('fails closed at the Match boundary without exposing foreign rally authority',async()=>{
    api.getSavedTourMatchDetail.mockImplementation(
      (_run:string,_branch:string,_rev:string,_season:number,
        _event:string,_match:string,offset:number)=>Promise.resolve({
          ...match(offset),saved_revision_id:'new-head'
        }))
    mount()
    expect(await screen.findByRole('link',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link',{name:'View results'}))
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link',{name:'Match detail'}))
    expect(await screen.findByRole('alert')).toHaveTextContent(/does not match/i)
    expect(screen.queryByText('Rally 1/30')).not.toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Find published finals for P1'})).not.toBeInTheDocument()
    expect(api.getSavedTourMatchDetail).toHaveBeenCalledWith(
      'run-a','branch-a','rev-old',2,'event-x','final',0,25)
  })
})

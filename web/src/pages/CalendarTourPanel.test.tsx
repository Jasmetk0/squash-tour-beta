import {act,fireEvent,render,screen} from '@testing-library/react'
import {StrictMode} from 'react'
import {QueryClient,QueryClientProvider,useQuery} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {CalendarTourPanel} from './CalendarTourPanel'
import type {TourCommand,TourPreview,TourView} from '../api/calendarTour'

const api=vi.hoisted(()=>({inspectCalendarTour:vi.fn(),previewCalendarTour:vi.fn(),executeCalendarTour:vi.fn(),saveCalendarTour:vi.fn(),replayCalendarContinuation:vi.fn(),inspectCalendarTourSeason:vi.fn(),inspectCalendarTourRecords:vi.fn()}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error { status=400 }}))
const view=(run='r',branch='b'):TourView=>({schema_version:'calendar_tour_inspection.v1',run_id:run,branch_id:branch,saved_head_revision_id:'head',draft_version:1,checkpoint_fingerprint:'a'.repeat(64),tour_fingerprint:null,saved:false,can_initialize:true,players:[],transition_blockers:['tour_authority_missing'],season_transition_blockers:['tour_authority_missing'],saved_completed_seasons:[],edition_evidence:{},state:null})
const panel=(run='r',branch='b')=><QueryClientProvider client={new QueryClient()}><MemoryRouter><LanguageProvider><CalendarTourPanel runId={run} branchId={branch} head="head"/></LanguageProvider></MemoryRouter></QueryClientProvider>
const preview=(c:TourCommand):TourPreview=>({schema_version:'calendar_tour_command_preview.v1',run_id:'r',branch_id:'b',command:c,preview_fingerprint:'f'.repeat(64),impact:{}})

describe('configured Tour consent (HTTP boundary mocked)',()=>{
  beforeEach(()=>{vi.clearAllMocks();localStorage.setItem('squash-engine-language-v1','en');api.inspectCalendarTour.mockImplementation((r,b)=>Promise.resolve(view(r,b)))})
  it('requires separate explicit command consent and never saves automatically',async()=>{
    api.previewCalendarTour.mockImplementation((_r,_b,c)=>Promise.resolve(preview(c)))
    api.executeCalendarTour.mockResolvedValue({})
    render(panel());await screen.findByLabelText('Tour operation reason')
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'Reviewed native Tour'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Tour initialization'}))
    await screen.findByLabelText('Confirm Tour command')
    expect(screen.getByRole('button',{name:'Execute confirmed operation'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm Tour command'))
    fireEvent.click(screen.getByRole('button',{name:'Execute confirmed operation'}))
    await act(async()=>{})
    expect(api.executeCalendarTour).toHaveBeenCalledTimes(1)
    expect(api.saveCalendarTour).not.toHaveBeenCalled()
  })
  it('drops a delayed review after its decisive input changes',async()=>{
    let resolve!:(p:TourPreview)=>void,cmd!:TourCommand
    api.previewCalendarTour.mockImplementation((_r,_b,c)=>{cmd=c;return new Promise(r=>{resolve=r})})
    render(panel());await screen.findByLabelText('Tour operation reason')
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'First input'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Tour initialization'}))
    await act(async()=>{})
    fireEvent.change(screen.getByLabelText('Tour seed'),{target:{value:'232'}})
    await act(async()=>resolve(preview(cmd)))
    expect(screen.queryByLabelText('Confirm Tour command')).not.toBeInTheDocument()
    expect(api.executeCalendarTour).not.toHaveBeenCalled()
  })
  it('ignores a superseded StrictMode read while a newer command is pending',async()=>{
    let oldRead!:(v:TourView)=>void,finishPreview!:(v:TourPreview)=>void,command!:TourCommand
    api.inspectCalendarTour.mockReturnValueOnce(new Promise(r=>{oldRead=r}))
      .mockImplementation((r,b)=>Promise.resolve(view(r,b)))
    api.previewCalendarTour.mockImplementation((_r,_b,c)=>{command=c;return new Promise(r=>{finishPreview=r})})
    render(<StrictMode>{panel()}</StrictMode>)
    await screen.findByLabelText('Tour operation reason')
    expect(api.inspectCalendarTour.mock.calls[0][2].aborted).toBe(true)
    expect(api.inspectCalendarTour.mock.calls[1][2].aborted).toBe(false)
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'Current review'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Tour initialization'}))
    expect(screen.getByRole('button',{name:'Refresh state'})).toBeDisabled()
    await act(async()=>oldRead({...view(),can_initialize:false}))
    expect(screen.getByRole('button',{name:'Refresh state'})).toBeDisabled()
    await act(async()=>finishPreview(preview(command)))
    await screen.findByLabelText('Confirm Tour command')
    expect(screen.getByRole('button',{name:'Review Tour initialization'})).toBeEnabled()
  })
  it('does not revive responses after switching Run A→B→A',async()=>{
    let resolve!:(v:TourView)=>void
    api.inspectCalendarTour.mockReturnValueOnce(new Promise(r=>{resolve=r})).mockImplementation((r,b)=>Promise.resolve(view(r,b)))
    const page=render(panel());page.rerender(panel('other'));page.rerender(panel())
    await screen.findByLabelText('Tour operation reason')
    await act(async()=>resolve({...view(),can_initialize:false}))
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'Current input'}})
    expect(screen.getByRole('button',{name:'Review Tour initialization'})).toBeEnabled()
  })
  it('loads the full Tour only once after a confirmed Save changes shared HEAD',async()=>{
    let serverHead='head'
    const state={week:{calendar:{schema_version:'run_calendar.v1',weeks_per_year:52,season_start_year_week:35,start_year:2030,season_count:3},season_index:0,week:2},editions:[],rankings:[],transitions:[]}
    api.inspectCalendarTour.mockImplementation(()=>Promise.resolve({...view(),state,tour_fingerprint:'c'.repeat(64),saved:serverHead==='saved',saved_head_revision_id:serverHead}))
    api.saveCalendarTour.mockImplementation(()=>{serverHead='saved';return Promise.resolve({schema_version:'calendar_tour_save_receipt.v1',run_id:'r',branch_id:'b',saved_revision:{revision_id:'saved',run_id:'r',branch_id:'b',content_hash:'d'.repeat(64)}})})
    function Host(){
      const {data}=useQuery({queryKey:['admin-run-branches','r'],queryFn:async()=>({run_branches:[{branch_id:'b',run_id:'r',saved_head_revision_id:serverHead}]})})
      return data?<CalendarTourPanel runId="r" branchId="b" head={data.run_branches[0].saved_head_revision_id}/>:null
    }
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><LanguageProvider><Host/></LanguageProvider></MemoryRouter></QueryClientProvider>)
    await screen.findByLabelText('Confirm Tour Save')
    fireEvent.click(screen.getByLabelText('Confirm Tour Save'))
    fireEvent.click(screen.getByRole('button',{name:'Manual Tour Save'}))
    await screen.findByText(/State: Saved/)
    expect(api.inspectCalendarTour).toHaveBeenCalledTimes(2)
    expect(api.saveCalendarTour).toHaveBeenCalledTimes(1)
  })
  it('reviews and explicitly confirms a terminal Season Transition without implicit Save',async()=>{
    const calendar={schema_version:'run_calendar.v1',weeks_per_year:4,season_start_year_week:2,start_year:2030,season_count:3}
    const terminal:TourView={...view(),tour_fingerprint:'c'.repeat(64),saved:true,
      transition_blockers:['season_transition_required'],season_transition_blockers:[],
      state:{week:{calendar,season_index:0,week:4},editions:[],rankings:[],transitions:[]}}
    api.inspectCalendarTour.mockResolvedValue(terminal)
    api.previewCalendarTour.mockImplementation((_r,_b,c)=>Promise.resolve(preview(c)))
    api.executeCalendarTour.mockResolvedValue({})
    render(panel())
    await screen.findByRole('button',{name:'Review Season Transition'})
    expect(screen.getByRole('button',{name:'Review Week Transition'})).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'End of season 2030'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Season Transition'}))
    await screen.findByLabelText('Confirm Tour command')
    const passed=api.previewCalendarTour.mock.calls[0][2] as TourCommand
    expect(passed.action).toBe('season-transition')
    expect(screen.getByRole('button',{name:'Execute confirmed operation'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm Tour command'))
    fireEvent.click(screen.getByRole('button',{name:'Execute confirmed operation'}))
    await act(async()=>{})
    expect(api.executeCalendarTour).toHaveBeenCalledOnce()
    expect(api.saveCalendarTour).not.toHaveBeenCalled()
  })


  it('plans and explicitly reviews next-season Edition without crossing the Run horizon',async()=>{
    const calendar={schema_version:'run_calendar.v1',weeks_per_year:52,season_start_year_week:1,start_year:2030,season_count:3}
    const state={week:{calendar,season_index:0,week:51},editions:[],rankings:[],transitions:[]}
    api.inspectCalendarTour.mockResolvedValue({...view(),state,tour_fingerprint:'c'.repeat(64),saved:true})
    api.previewCalendarTour.mockImplementation((_r,_b,c)=>Promise.resolve(preview(c)))
    render(panel())
    await screen.findByLabelText('Tour Edition season')
    expect((screen.getByLabelText('Tour Edition season') as HTMLInputElement).value).toBe('2')
    expect((screen.getByLabelText('Tour Edition week') as HTMLInputElement).value).toBe('1')
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'Real next-season calendar'}})
    fireEvent.change(screen.getByLabelText('Tour Edition ID'),{target:{value:'new-season-cup'}})
    fireEvent.change(screen.getByLabelText('Tour Edition name'),{target:{value:'Season 2 Cup'}})
    fireEvent.click(screen.getByRole('button',{name:'Review new Edition'}))
    await screen.findByLabelText('Confirm Tour command')
    const cmd=api.previewCalendarTour.mock.calls[0][2] as TourCommand
    expect(cmd.action).toBe('create-edition')
    const scheduled=cmd.data.week as {season_index:number;week:number}
    const announcement=cmd.data.announcement_week as {season_index:number;week:number}
    expect(scheduled).toMatchObject({season_index:1,week:1})
    expect(announcement).toMatchObject({season_index:0,week:52})
    expect(api.saveCalendarTour).not.toHaveBeenCalled()
  })
  it('prevents Edition review when the future Run horizon has no two available weeks',async()=>{
    const calendar={schema_version:'run_calendar.v1',weeks_per_year:52,season_start_year_week:1,start_year:2030,season_count:1}
    api.inspectCalendarTour.mockResolvedValue({...view(),tour_fingerprint:'c'.repeat(64),saved:true,
      state:{week:{calendar,season_index:0,week:51},editions:[],rankings:[],transitions:[]}})
    render(panel())
    await screen.findByLabelText('Tour Edition season')
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'End of horizon'}})
    fireEvent.change(screen.getByLabelText('Tour Edition ID'),{target:{value:'bad-cup'}})
    fireEvent.change(screen.getByLabelText('Tour Edition name'),{target:{value:'Bad Cup'}})
    expect(screen.getByRole('button',{name:'Review new Edition'})).toBeDisabled()
    expect(api.previewCalendarTour).not.toHaveBeenCalled()
  })


  it('shows only Saved completed seasons and validates provenance before rendering',async()=>{
    const calendar={schema_version:'run_calendar.v1',weeks_per_year:4,season_start_year_week:2,start_year:2030,season_count:3}
    const complete={...view(),tour_fingerprint:'c'.repeat(64),saved:true,saved_completed_seasons:[0],
      state:{week:{calendar,season_index:1,week:1},editions:[],rankings:[],transitions:[]}}
    api.inspectCalendarTour.mockResolvedValue(complete)
    const summary={schema_version:'native_tour_signed_season_summary.v1',run_id:'r',branch_id:'b',source_tour_fingerprint:'c'.repeat(64),
      season_index:0,season_label:'2030/2031',weeks_per_season:4,boundary_command_id:'season-1',next_season_index:1,
      completed_edition_count:1,countries:[{country_code:'CZE',titles:1,finals:0,semifinals:1,quarterfinals:0,awarded_points:130,distinct_players:2,edition_appearances:1}],
      editions:[{edition_id:'cup',name:'Cup',week:3,champion_player_id:'a',champion_name:'Alpha',champion_country:'CZE',finalist_player_id:'b',finalist_name:'Beta',finalist_country:'USA',source_tournament_fingerprint:'d'.repeat(64)}],
      players:[],last_week_published_ranking:{week:4,source_fingerprint:'e'.repeat(64),top_players:[]}}
    api.inspectCalendarTourSeason.mockResolvedValue({schema_version:'calendar_tour_season_comparison.v1',run_id:'r',branch_id:'b',saved_head_revision_id:'head',selected:summary,comparison:null,country_deltas:[]})
    render(panel())
    await screen.findByLabelText('Signed season')
    fireEvent.click(screen.getByRole('button',{name:'Load season summary'}))
    await screen.findByLabelText('Verified season summary')
    expect(screen.getByLabelText('Country season comparison')).toHaveTextContent('CZE')
    expect(screen.getByLabelText('Country season comparison')).toHaveTextContent('130')
    expect(api.inspectCalendarTourSeason).toHaveBeenCalledWith('r','b',0,null)
    expect(api.saveCalendarTour).not.toHaveBeenCalled()
  })
  it('does not present an unsaved or pending season as Signed history',async()=>{
    const calendar={schema_version:'run_calendar.v1',weeks_per_year:4,season_start_year_week:2,start_year:2030,season_count:3}
    api.inspectCalendarTour.mockResolvedValue({...view(),saved:false,saved_completed_seasons:[],tour_fingerprint:'c'.repeat(64),
      state:{week:{calendar,season_index:1,week:1},editions:[],rankings:[],transitions:[]}})
    render(panel())
    await screen.findByLabelText('Tour operation reason')
    expect(screen.queryByLabelText('Signed season')).not.toBeInTheDocument()
    expect(api.inspectCalendarTourSeason).not.toHaveBeenCalled()
  })


  it('reads only Signed career records with selected national and historical filters',async()=>{
    const calendar={schema_version:'run_calendar.v1',weeks_per_year:4,season_start_year_week:2,start_year:2030,season_count:3}
    api.inspectCalendarTour.mockResolvedValue({...view(),saved:true,saved_completed_seasons:[0,1],tour_fingerprint:'c'.repeat(64),
      state:{week:{calendar,season_index:2,week:1},editions:[],rankings:[],transitions:[]}})
    const item=(scope:'player'|'country',metric:'titles'|'finals'|'awarded_points')=>({
      record_id:`native_tour.${scope}.${metric}.v1`,scope,metric,value:metric==='titles'?2:0,
      holders:metric==='titles'?[{entity_id:'player-a',label:'Alpha',country_code:'CZE',titles:2,finals:0,awarded_points:230}]:[],
      holder_history:metric==='titles'?[{season_index:1,season_label:'S2',record_value:2,holder_ids:['player-b'],holder_labels:['Former Champion'],change:'improved',boundary_command_id:'close-1'}]:[],
      leaderboard:metric==='titles'?[{entity_id:'player-a',label:'Alpha',country_code:'CZE',titles:2,finals:0,awarded_points:230,rank:1}]:[],
      leaderboard_total:metric==='titles'?1:0
    })
    api.inspectCalendarTourRecords.mockResolvedValue({
      schema_version:'calendar_tour_signed_records_response.v1',run_id:'r',branch_id:'b',
      saved_head_revision_id:'head',source_tour_fingerprint:'c'.repeat(64),
      as_of_season_index:1,from_season_index:0,country_code:'CZE',leaderboard_limit:20,
      completed_seasons:[0,1],completed_edition_count:2,source_seasons:[],
      records:(['player','country'] as const).flatMap(scope=>(['titles','finals','awarded_points'] as const).map(metric=>item(scope,metric)))
    })
    render(panel())
    await screen.findByLabelText('Records as of season')
    fireEvent.change(screen.getByLabelText('Records country'),{target:{value:'cze'}})
    expect((screen.getByLabelText('Records country') as HTMLInputElement).value).toBe('CZE')
    fireEvent.click(screen.getByRole('button',{name:'Load historical records'}))
    await screen.findByLabelText('Verified career records')
    expect(screen.getByLabelText('Verified career records')).toHaveTextContent('CZE')
    expect(screen.getByLabelText('Verified career records')).toHaveTextContent('Alpha')
    // Former record-holder identity remains readable after the lead changes.
    expect(screen.getByLabelText('Verified career records')).toHaveTextContent('Former Champion')
    expect(api.inspectCalendarTourRecords).toHaveBeenCalledWith('r','b',1,0,'CZE')
    expect(api.saveCalendarTour).not.toHaveBeenCalled()
  })
  it('rejects stale Signed record reads from the wrong immutable Saved HEAD',async()=>{
    const calendar={schema_version:'run_calendar.v1',weeks_per_year:4,season_start_year_week:2,start_year:2030,season_count:3}
    api.inspectCalendarTour.mockResolvedValue({...view(),saved:true,saved_completed_seasons:[0],
      tour_fingerprint:'c'.repeat(64),state:{week:{calendar,season_index:1,week:1},editions:[],rankings:[],transitions:[]}})
    api.inspectCalendarTourRecords.mockResolvedValue({
      schema_version:'calendar_tour_signed_records_response.v1',run_id:'r',branch_id:'b',
      saved_head_revision_id:'foreign',source_tour_fingerprint:'c'.repeat(64),
      as_of_season_index:0,from_season_index:0,country_code:null,leaderboard_limit:20,
      completed_seasons:[0],completed_edition_count:0,source_seasons:[],records:[]
    })
    render(panel())
    await screen.findByLabelText('Records as of season')
    fireEvent.click(screen.getByRole('button',{name:'Load historical records'}))
    await screen.findByRole('alert')
    expect(screen.queryByLabelText('Verified career records')).not.toBeInTheDocument()
  })

  it.each([
    ['season','filter','resolve'],['season','reason','reject'],
    ['records','filter','resolve'],['records','reason','reject'],
  ])('releases busy after a superseded %s read (%s / %s)',async(kind,edit,outcome)=>{
    const calendar={schema_version:'run_calendar.v1',weeks_per_year:4,season_start_year_week:2,start_year:2030,season_count:3}
    api.inspectCalendarTour.mockResolvedValue({...view(),saved:true,saved_completed_seasons:[0,1],tour_fingerprint:'c'.repeat(64),
      state:{week:{calendar,season_index:2,week:1},editions:[],rankings:[],transitions:[]}})
    let resolve!:(v:unknown)=>void,reject!:(e:Error)=>void
    const deferred=new Promise((ok,no)=>{resolve=ok;reject=no})
    if(kind==='season')api.inspectCalendarTourSeason.mockReturnValueOnce(deferred)
    else api.inspectCalendarTourRecords.mockReturnValueOnce(deferred)
    render(panel())
    await screen.findByLabelText('Records as of season')
    fireEvent.click(screen.getByRole('button',{name:kind==='season'?'Load season summary':'Load historical records'}))
    expect(screen.getByRole('button',{name:'Refresh state'})).toBeDisabled()
    if(edit==='reason')fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'Changed during read'}})
    else if(kind==='season')fireEvent.change(screen.getByLabelText('Signed season'),{target:{value:'0'}})
    else fireEvent.change(screen.getByLabelText('Records country'),{target:{value:'CZE'}})
    const response=kind==='season'?{
      schema_version:'calendar_tour_season_comparison.v1',run_id:'r',branch_id:'b',saved_head_revision_id:'head',
      selected:{season_index:1,run_id:'r',branch_id:'b',countries:[],editions:[]},comparison:null,country_deltas:[],
    }:{
      schema_version:'calendar_tour_signed_records_response.v1',run_id:'r',branch_id:'b',saved_head_revision_id:'head',
      as_of_season_index:1,from_season_index:0,country_code:null,completed_seasons:[0,1],source_seasons:[],
      records:Array.from({length:6},()=>({holders:[],holder_history:[],leaderboard:[]})),
    }
    await act(async()=>{if(outcome==='reject')reject(Error('obsolete failure'));else resolve(response)})
    expect(screen.getByRole('button',{name:'Refresh state'})).toBeEnabled()
    expect(screen.queryByLabelText(kind==='season'?'Verified season summary':'Verified career records')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(api.executeCalendarTour).not.toHaveBeenCalled()
    expect(api.saveCalendarTour).not.toHaveBeenCalled()
  })
})

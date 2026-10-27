import {render,screen,within,waitFor} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter,Route,Routes} from 'react-router-dom'
import {beforeEach,describe,it,expect,vi} from 'vitest'
import {SavedTourCalendarPage} from './SavedTourCalendarPage'
import type {SavedTourCalendar} from '../api/savedTour'

const api=vi.hoisted(()=>({getSavedTourCalendar:vi.fn()}))
const context=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'head-a'},
  time:{mode:'present',presentSeason:2,isLoading:false,error:null},
  language:'en'
}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error{}}))
vi.mock('../admin/AdminBranchContext',()=>({useAdminBranch:()=>({
  selectedBranch:context.branch,isLoading:false,error:null
})}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>context.time}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:context.language})}))
function fixture():SavedTourCalendar {
  const event=(id:string,week:number,country:string,category:string,tour:string)=>({
    event_id:id,season:'2002/2003',season_week:week,event_name:id,
    template_id:'tpl',category,tour_level:tour,host_country:country,host_city:null,region:'EUROPE',
    main_draw_size:16,qualification_draw_size:8,seeds_count:4,qualifier_spots:4,
    wild_cards:2,byes:0,ranking_status:'ranked',result_published:false,
    champion_player_id:null,finalist_player_id:null
  })
  return {schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:'branch-a',revision_branch_id:'ancestor',
    saved_revision_id:'rev-old',season_index:2,season:'2002/2003',week_count:61,
    calendar_status:'ready',edition_count:3,editions:[
      event('Brno Open',5,'CZE','DIAMOND','WORLD'),
      event('Egypt Open',5,'EGY','GOLD','WORLD'),
      event('Future Open',9,'CZE','DIAMOND','REGIONAL')
    ]}
}
function mount(path:string){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  return render(<QueryClientProvider client={client}>
    <MemoryRouter initialEntries={[path]}><Routes>
      <Route path="/admin/runs/:runId/tour/calendar" element={<SavedTourCalendarPage/>}/>
    </Routes></MemoryRouter>
  </QueryClientProvider>)
}
describe('Run Saved Tour 61-week calendar',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.branch.run_id='run-a';context.branch.branch_id='branch-a'
    context.branch.saved_head_revision_id='head-a'
    context.time.mode='present';context.time.presentSeason=2;context.language='en'
    api.getSavedTourCalendar.mockResolvedValue(fixture())
  })
  it('shows 61 weeks with simultaneous editions, exact revision links and list/filter alternative',async()=>{
    mount('/admin/runs/run-a/tour/calendar?branch=branch-a&revision=rev-old&season=2&q=keep')
    expect(await screen.findByText('Brno Open')).toBeInTheDocument()
    const weeks=screen.getByLabelText('Saved Tour 61 season weeks')
    expect(within(weeks).getAllByRole('heading',{level:4})).toHaveLength(61)
    expect(screen.getByText('Egypt Open')).toBeInTheDocument()
    expect(api.getSavedTourCalendar).toHaveBeenCalledWith('run-a','branch-a','rev-old',2)
    expect(screen.getByRole('link',{name:'Brno Open'})).toHaveAttribute(
      'href',expect.stringContaining('/tour/calendar/Brno%20Open?'))
    expect(screen.getByRole('link',{name:'Brno Open'})).toHaveAttribute(
      'href',expect.stringContaining('revision=rev-old'))
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Saved Tour view'}),'list')
    const table=screen.getByRole('table',{name:'Saved Tour edition list'})
    expect(within(table).getAllByRole('row')).toHaveLength(4)
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Saved Tour filter country'}),'CZE')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(within(table).queryByText('Egypt Open')).not.toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Brno Open'})).toHaveAttribute(
      'href',expect.stringContaining('country=CZE'))
  })
  it('rejects stale response revisions without displaying any edition',async()=>{
    const f=fixture();f.saved_revision_id='some-other-revision'
    api.getSavedTourCalendar.mockResolvedValue(f)
    mount('/admin/runs/run-a/tour/calendar?branch=branch-a&revision=rev-old&season=2')
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByRole('link',{name:'Brno Open'})).not.toBeInTheDocument()
  })
  it('does not request a guessed saved revision for a checkpoint or wrong branch',async()=>{
    context.time.mode='checkpoint'
    mount('/admin/runs/run-a/tour/calendar?branch=branch-a&revision=rev-old&season=2')
    expect(screen.getByRole('alert')).toHaveTextContent('Checkpoint is not mapped')
    expect(api.getSavedTourCalendar).not.toHaveBeenCalled()
  })
  it.each(['', 'other-branch'])(
    'fails closed for explicitly supplied invalid Branch query value %s',
    async (requested) => {
      mount('/admin/runs/run-a/tour/calendar?branch='+encodeURIComponent(requested)+'&revision=rev-old&season=2')
      expect(await screen.findByRole('alert')).toHaveTextContent('Selected Branch does not match the link.')
      expect(api.getSavedTourCalendar).not.toHaveBeenCalled()
      expect(screen.queryByRole('link',{name:'Brno Open'})).not.toBeInTheDocument()
    }
  )
  it('permits missing Branch parameter when the current selected Branch is authoritative',async()=>{
    mount('/admin/runs/run-a/tour/calendar?revision=rev-old&season=2')
    expect(await screen.findByText('Brno Open')).toBeInTheDocument()
    expect(api.getSavedTourCalendar).toHaveBeenCalledWith('run-a','branch-a','rev-old',2)
  })
  it('pins Saved HEAD when view filters change rather than silently fetching a later HEAD',async()=>{
    api.getSavedTourCalendar.mockResolvedValue({...fixture(),saved_revision_id:'head-a'})
    mount('/admin/runs/run-a/tour/calendar?season=2')
    expect(await screen.findByText('Brno Open')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Saved Tour view'}),'list')
    await waitFor(()=>expect(screen.getByRole('link',{name:'Brno Open'})).toHaveAttribute(
      'href',expect.stringContaining('revision=head-a')))
  })
  it('recovers a failed calendar read explicitly and resets only local filters',async()=>{
    api.getSavedTourCalendar.mockRejectedValueOnce(new Error('offline'))
    mount('/admin/runs/run-a/tour/calendar?branch=branch-a&revision=rev-old&season=2&country=CZE&view=list&q=keep')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Brno Open'})).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Retry calendar read'}))
    expect(await screen.findByRole('link',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Clear filters'}))
    expect(screen.getByRole('link',{name:'Egypt Open'})).toHaveAttribute(
      'href',expect.stringContaining('revision=rev-old'))
    expect(screen.getByRole('link',{name:'Egypt Open'})).toHaveAttribute(
      'href',expect.stringContaining('q=keep'))
    expect(api.getSavedTourCalendar).toHaveBeenCalledTimes(2)
  })
  it('distinguishes an empty saved season from zero matches after filters',async()=>{
    api.getSavedTourCalendar.mockResolvedValue({...fixture(),editions:[],edition_count:0})
    mount('/admin/runs/run-a/tour/calendar?branch=branch-a&revision=rev-old&season=2')
    expect(await screen.findByText('This season has no saved editions.')).toBeInTheDocument()
    expect(screen.queryByText('No saved editions match the selected filters.')).not.toBeInTheDocument()
  })

})

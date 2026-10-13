import {render,screen,within} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter,Route,Routes} from 'react-router-dom'
import {beforeEach,describe,it,expect,vi} from 'vitest'
import {SavedTourEditionPage} from './SavedTourEditionPage'
import type {SavedTourEdition} from '../api/savedTour'

const api=vi.hoisted(()=>({getSavedTourEdition:vi.fn()}))
const context=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'head-a'},
  time:{mode:'present',isLoading:false,error:null},
  language:'en'
}))
vi.mock('../api/client',()=>api)
vi.mock('../admin/AdminBranchContext',()=>({useAdminBranch:()=>({
  selectedBranch:context.branch,isLoading:false,error:null
})}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>context.time}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:context.language})}))
function fixture(published=false):SavedTourEdition{
  return {schema_version:'run_saved_tour_edition.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:'branch-a',revision_branch_id:'ancestor',
    saved_revision_id:'rev-old',season_index:2,lifecycle_status:'unavailable',
    edition:{event_id:'event-x',season:'2002/2003',season_week:5,event_name:'Brno Open',
      template_id:'tpl',category:'DIAMOND',tour_level:'WORLD',host_country:'CZE',
      host_city:'Brno',region:'EUROPE',main_draw_size:16,qualification_draw_size:8,
      seeds_count:4,qualifier_spots:4,wild_cards:2,byes:0,ranking_status:'ranked',
      result_published:published,champion_player_id:published?'P1':null,
      finalist_player_id:published?'P2':null},
    published_result:published?{schema_version:'viewer_tournament_result.v1',
      product_run_id:'run-a',viewer_branch_id:'ancestor',event_id:'event-x',
      completed_season_index:2,completed_week:5,champion_player_id:'P1',
      finalist_player_id:'P2',qualification_winner_ids:['Q1'],
      players:[{player_id:'P1',draw_type:'main',reached_stage:'champion',wins:2,losses:0}],
      matches:[{match_id:'final',draw_type:'main',round_number:2,bracket_position:1,
        winner_player_id:'P1',loser_player_id:'P2',scoreline:'3-0'},
        {match_id:'q-final',draw_type:'qualification',round_number:1,bracket_position:1,
          winner_player_id:'Q1',loser_player_id:'Q2',scoreline:'3-1'}]
    }:null}
}
function mount(path='/admin/runs/run-a/tour/calendar/event-x?branch=branch-a&revision=rev-old&season=2&country=CZE&view=list'){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  return render(<QueryClientProvider client={client}>
    <MemoryRouter initialEntries={[path]}><Routes>
      <Route path="/admin/runs/:runId/tour/calendar/:eventId" element={<SavedTourEditionPage/>}/>
    </Routes></MemoryRouter>
  </QueryClientProvider>)
}
describe('Saved Edition detail',()=>{
  beforeEach(()=>{
    vi.clearAllMocks();context.time.mode='present';context.language='en'
    context.branch.run_id='run-a';context.branch.branch_id='branch-a'
    api.getSavedTourEdition.mockResolvedValue(fixture())
  })
  it('reads exact old revision, has six tabs and preserves filters in return link',async()=>{
    mount()
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    expect(api.getSavedTourEdition).toHaveBeenCalledWith('run-a','branch-a','rev-old',2,'event-x')
    const back=screen.getByRole('link',{name:/Back to calendar/})
    expect(back).toHaveAttribute('href',expect.stringContaining('country=CZE'))
    expect(back).toHaveAttribute('href',expect.stringContaining('revision=rev-old'))
    const sections=screen.getByRole('navigation',{name:'Edition sections'})
    expect(within(sections).getAllByRole('button')).toHaveLength(6)
    expect(screen.getByText(/Authoritative lifecycle status: unavailable/)).toBeInTheDocument()
    expect(screen.getByText(/No canonical result was published/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Results'}))
    expect(screen.getByText(/not published in this revision/)).toBeInTheDocument()
  })
  it('shows real saved results in Main then Qualification; draw-only phase switch',async()=>{
    api.getSavedTourEdition.mockResolvedValue(fixture(true))
    mount()
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Results'}))
    const main=document.getElementById('saved-results-main')!
    const qualification=document.getElementById('saved-results-qualification')!
    expect(within(main).getByText('3-0')).toBeInTheDocument()
    expect(within(qualification).getByText('3-1')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Qualification'})).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Draw / groups'}))
    expect(screen.getByRole('button',{name:'Qualification'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Qualification'}))
    expect(screen.queryByText('q-final')).not.toBeInTheDocument()
    expect(screen.getByText('3-1')).toBeInTheDocument()
  })
  it('fails closed for cross-revision and mismatched event',async()=>{
    api.getSavedTourEdition.mockResolvedValue({...fixture(),saved_revision_id:'new-rev'})
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid or stale Edition identity')
    expect(screen.queryByRole('heading',{name:'Brno Open'})).not.toBeInTheDocument()
  })
  it('does not consult the API with missing exact revision or a checkpoint',async()=>{
    context.time.mode='checkpoint'
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('Checkpoint is not mapped')
    expect(api.getSavedTourEdition).not.toHaveBeenCalled()
  })
})

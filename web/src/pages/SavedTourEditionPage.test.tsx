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
  it('shows saved pending tie audit without inventing final group standings',async()=>{
    const source=fixture(false)
    source.group_schedule={
      schema_version:'run_saved_tour_group_schedule.v1',
      source:'saved_tournament_group_match_schedule_authority.v1',
      run_id:'run-a',revision_branch_id:'ancestor',event_id:'event-x',
      authority_fingerprint:'b'.repeat(64),
      group_count:1,group_size:3,match_day_count:3,
      matches:[
        {match_id:'ab',group_index:1,match_day_ordinal:1,match_order:1,
          top_player_id:'A',bottom_player_id:'B',best_of:3},
        {match_id:'ac',group_index:1,match_day_ordinal:2,match_order:1,
          top_player_id:'A',bottom_player_id:'C',best_of:3},
        {match_id:'bc',group_index:1,match_day_ordinal:3,match_order:1,
          top_player_id:'B',bottom_player_id:'C',best_of:3}
      ]
    }
    source.group_standings=null
    source.pending_group_tie_decisions=[{
      group_index:1,case_fingerprint:'a'.repeat(64),
      ordered_player_ids:['C','A','B'],admin_reason:'Reviewed three-way cycle.'
    }]
    api.getSavedTourEdition.mockResolvedValue(source)
    mount()
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Results'}))
    const audit=screen.getByLabelText('Saved pending group tie decisions')
    expect(within(audit).getByText(/Reviewed three-way cycle/)).toBeInTheDocument()
    expect(within(audit).getByText(/C → A → B/)).toBeInTheDocument()
    expect(within(audit).getByText(/not a published group table/)).toBeInTheDocument()
    expect(screen.queryByRole('table',{name:'Saved group 1 standings'})).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Saved group standings')).not.toBeInTheDocument()
    expect(screen.getByText(/not published in this revision/)).toBeInTheDocument()
  })

  it('shows canonical final group ranks, W/O evidence and exact Admin audit reason',async()=>{
    const source=fixture(false)
    source.group_schedule={
      schema_version:'run_saved_tour_group_schedule.v1',
      source:'saved_tournament_group_match_schedule_authority.v1',
      run_id:'run-a',revision_branch_id:'ancestor',event_id:'event-x',
      authority_fingerprint:'b'.repeat(64),group_count:1,group_size:2,
      match_day_count:1,matches:[{
        match_id:'group-one',group_index:1,match_day_ordinal:1,match_order:1,
        top_player_id:'P1',bottom_player_id:'P2',best_of:3
      }]
    }
    const row=(pos:number,player_id:string,points:number,wo:number)=>({
      position:pos,player_id,wins:pos===1?1:0,losses:pos===1?0:1,
      group_points:points,played_matches:0,walkovers_received:wo,
      walkovers_conceded:pos===2?1:0,games_won:0,games_lost:0,
      points_won:0,points_lost:0
    })
    source.group_standings={
      schema_version:'run_saved_tour_group_standings.v1',
      source:'saved_tournament_group_standings_authority',
      run_id:'run-a',revision_branch_id:'ancestor',event_id:'event-x',
      authority_fingerprint:'c'.repeat(64),
      group_schedule_fingerprint:'b'.repeat(64),
      groups:[{group_index:1,rows:[row(1,'P1',4,1),row(2,'P2',0,0)]}],
      tie_decisions:[{group_index:1,case_fingerprint:'d'.repeat(64),
        ordered_player_ids:['P1','P2'],admin_reason:'Evidence reviewed.'}]
    }
    api.getSavedTourEdition.mockResolvedValue(source)
    mount()
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Results'}))
    const table=screen.getByRole('table',{name:'Saved group 1 standings'})
    expect(within(table).getByText('P1')).toBeInTheDocument()
    expect(within(table).getByText('P2')).toBeInTheDocument()
    expect(within(table).getByText('4')).toBeInTheDocument()
    const evidence=screen.getByLabelText('Saved group tie decisions')
    expect(within(evidence).getByText(/Evidence reviewed/)).toBeInTheDocument()
    expect(screen.getByText(/Saved final tables/)).toBeInTheDocument()
    expect(screen.getByText(/not published in this revision/)).toBeInTheDocument()
  })

  it('renders genuine group Match Days and links only canonically published results',async()=>{
    const source=fixture(false)
    source.group_schedule={
      schema_version:'run_saved_tour_group_schedule.v1',
      source:'saved_tournament_group_match_schedule_authority.v1',
      run_id:'run-a',revision_branch_id:'ancestor',event_id:'event-x',
      authority_fingerprint:'b'.repeat(64),group_count:1,group_size:2,
      match_day_count:1,matches:[{
        match_id:'group-1',group_index:1,match_day_ordinal:1,
        match_order:1,top_player_id:'P1',bottom_player_id:'P2',best_of:3
      }]
    }
    api.getSavedTourEdition.mockResolvedValue(source)
    mount()
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Schedule & matches'}))
    const group=screen.getByRole('table',{name:'Saved group matches'})
    expect(within(group).getByText('P1 – P2')).toBeInTheDocument()
    expect(within(group).getByText('BO3')).toBeInTheDocument()
    expect(within(group).getByText('Not canonically published')).toBeInTheDocument()
    expect(within(group).queryByRole('link',{name:'Match detail'})).not.toBeInTheDocument()
    expect(screen.getByText(/Days are ordinal, not calendar dates/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Qualification'})).not.toBeInTheDocument()
  })

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

  it('displays saved global Match Day order and only canonically published scores',async()=>{
    const item=fixture(true)
    item.match_schedule={
      schema_version:'run_saved_tour_match_schedule.v1',source:'saved_week_simulation_schedule.v2',
      run_id:'run-a',revision_branch_id:'ancestor',event_id:'event-x',
      season_index:2,season_week:5,week_schedule_fingerprint:'b'.repeat(64),
      slots:[
        {global_slot_ordinal:1,match_day_ordinal:1,match_order:1,draw_phase:'main',
          round_number:2,group_id:'g1',match_id:'final'},
        {global_slot_ordinal:3,match_day_ordinal:2,match_order:1,draw_phase:'qualification',
          round_number:1,group_id:'g3',match_id:null},
      ]
    }
    api.getSavedTourEdition.mockResolvedValue(item)
    mount()
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Schedule & matches'}))
    expect(screen.getByText('Authentic Saved Week Simulation Schedule v2.',{exact:false})).toBeInTheDocument()
    const sections=screen.getAllByRole('table',{name:'Saved Match Day order'})[0]
    expect(within(sections).getByText('P1 · 3-0')).toBeInTheDocument()
    expect(screen.getByText('No saved match plan')).toBeInTheDocument()
    expect(screen.getByText(/Match Day is an ordinal, not a date/)).toBeInTheDocument()
    expect(screen.queryByText('Q1 · 3-1')).not.toBeInTheDocument()
  })
  it('shows actual saved Entry partitions and first-round positions without inventing match times',async()=>{
    const source=fixture(true)
    source.entry_field={
      schema_version:'viewer_tournament_entry_field.v1',product_run_id:'run-a',
      viewer_branch_id:'ancestor',event_id:'event-x',field_sequence:2,
      mode:'pre_draw_repair',main_draw_capacity:4,active_main_entrant_count:2,
      effective_main_bye_count:2,direct_main_player_ids:['P1','P2'],
      qualification_player_ids:[],alternate_player_ids:['A1'],withdrawn_player_ids:['W1']
    }
    const slot=(index:number,id:string|null)=>({slot_index:index,
      entrant_kind:(id?'player':'bye') as 'player'|'bye',
      player_id:id,placeholder_id:null,seed_number:index===1?1:null,entry_status:null})
    source.draw={
      schema_version:'viewer_tournament_draw.v1',product_run_id:'run-a',
      viewer_branch_id:'ancestor',event_id:'event-x',revision_count:0,
      main:{draw_type:'main',section_id:null,bracket_size:4,
        slots:[slot(1,'P1'),slot(2,null),slot(3,'P2'),slot(4,null)]},
      qualification_sections:[]
    }
    api.getSavedTourEdition.mockResolvedValue(source)
    mount()
    expect(await screen.findByRole('heading',{name:'Brno Open'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Entries & participants'}))
    expect(screen.getByText(/Authentic saved Entry Field, version:/)).toBeInTheDocument()
    expect(screen.getByRole('heading',{name:'Direct Main entrants (2)'})).toBeInTheDocument()
    expect(screen.getByRole('heading',{name:'Alternates (1)'})).toBeInTheDocument()
    expect(screen.getByText('W1')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Draw / groups'}))
    const bracket=screen.getByRole('table',{name:'Saved draw main'})
    expect(within(bracket).getAllByRole('row')).toHaveLength(5)
    expect(within(bracket).getAllByText('BYE')).toHaveLength(2)
    expect(within(bracket).getByText('P1')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Qualification'}))
    expect(screen.getByText('No saved qualification bracket is available.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Schedule & matches'}))
    expect(screen.getByText(/Match start times are never inferred/)).toBeInTheDocument()
  })
})

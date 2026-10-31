import {screen,within,waitFor} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {renderWithRoute} from '../test/testUtils'
import {SavedStatesComparePage} from './SavedStatesComparePage'

const api=vi.hoisted(()=>({
  listRunBranches:vi.fn(),listSavedRevisionHistory:vi.fn(),
  compareSavedRevisions:vi.fn(),getSavedRevision:vi.fn(),getSavedTourCalendar:vi.fn(),
  getSavedTourEdition:vi.fn()
}))
const locale=vi.hoisted(()=>({current:'en' as 'en'|'cs'}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:locale.current})}))
vi.mock('../api/client',()=>api)

const first={
  revision_id:'old',sequence:1,parent_revision_id:null,kind:'initial_run_creation',
  revision_branch_id:'parent-branch',is_shared_revision:true,is_branch_head:false,
  content_hash:'hash-old',content_hash_algorithm:'sha256',created_at:'2026-10-11 12:00:00',
  payload_schema_version:'run_saved_revision_v1',change_summary:{summary:'Initial'}
}
const second={
  ...first,revision_id:'new',sequence:2,parent_revision_id:'old',
  revision_branch_id:'fork',is_shared_revision:false,is_branch_head:true,
  content_hash:'hash-new',kind:'manual_save',change_summary:{summary:'Changed world'}
}
const history=(branch='fork',entries=[first,second],older=false)=>({
  run_id:'run-a',branch_id:branch,saved_head_revision_id:'new',
  total_count:older?3:entries.length,has_more_older:older,
  next_before_sequence:older?entries[0]?.sequence??null:null,saved_revisions:entries
})
const diff=()=>({
  run_id:'run-a',branch_id:'fork',saved_head_revision_id:'new',
  from_revision:first,to_revision:second,
  run_changes:{display_name:{before:'Run 1',after:'Run 2'}},
  branch_changes:{},
  components:[
    {component_key:'calendar',status:'changed',before_fingerprint:'before',after_fingerprint:'after'},
    {component_key:'ranking',status:'unchanged',before_fingerprint:'same',after_fingerprint:'same'}
  ]
})
function open(query='branch=fork&a=old&b=new'){
  renderWithRoute(<SavedStatesComparePage/>,
    '/admin/runs/run-a/branches/compare'+(query?'?'+query:''))
}
beforeEach(()=>{
  locale.current='en'
  vi.clearAllMocks()
  api.listRunBranches.mockResolvedValue({run_branches:[
    {run_id:'run-a',branch_id:'fork',display_name:'Timeline 2'},
    {run_id:'run-a',branch_id:'other',display_name:'Timeline 3'}
  ]})
  api.listSavedRevisionHistory.mockImplementation(async (_run:string,branch:string)=>
    history(branch))
  api.compareSavedRevisions.mockResolvedValue(diff())
  api.getSavedTourCalendar.mockImplementation(async (_run:string,branch:string,revision:string,season:number)=>({
    schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:branch,revision_branch_id:revision==='old'?'parent-branch':'fork',
    saved_revision_id:revision,season_index:season,
    season:(2000+season)+'/'+(2001+season),week_count:61,
    calendar_status:'empty',edition_count:0,editions:[]
  }))
  api.getSavedTourEdition.mockImplementation(async (run:string,branch:string,
    rev:string,season:number,eventId:string)=>{
    const calendar=await api.getSavedTourCalendar(run,branch,rev,season)
    const edition=calendar.editions.find((item:{event_id:string})=>item.event_id===eventId)
    return {
      schema_version:'run_saved_tour_edition.v1',source:'reachable_saved_revision',
      run_id:run,branch_id:branch,revision_branch_id:rev==='old'?'parent-branch':'fork',
      saved_revision_id:rev,season_index:season,edition,
      published_result:null,lifecycle_status:'unavailable'
    }
  })
  api.getSavedRevision.mockImplementation(async (_run:string,branch:string,rev:string)=>({
    ...((rev==='old')?first:second),branch_id:branch,run_id:'run-a',
    payload:{content:{example:'immutable'}}
  }))
})

describe('Dedicated read-only Compare States A/B',()=>{
  it('loads explicit same-Branch A/B and filters without mutating any Run state',async()=>{
    open()
    const selection=await screen.findByLabelText('Compare Saved Revision selection')
    expect(await within(selection).findByLabelText('Compare Branch')).toHaveValue('fork')
    await waitFor(()=>expect(within(selection).getByLabelText('Compare state A')).toHaveValue('old'))
    expect(within(selection).getByLabelText('Compare state B')).toHaveValue('new')
    const results=await screen.findByLabelText('Compare Saved Revision results')
    const table=await within(results).findByRole('table',{name:'Saved State A B comparison table'})
    expect(table).toHaveTextContent('calendar')
    expect(table).toHaveTextContent('display_name')
    expect(table).not.toHaveTextContent('ranking')
    expect(within(results).getByLabelText('Compare Saved Revision totals')).toHaveTextContent('2')
    expect(api.compareSavedRevisions).toHaveBeenCalledWith('run-a','fork','old','new')
    await userEvent.selectOptions(within(results).getByLabelText('Compare display filter'),'all')
    expect(within(results).getByRole('table',{name:'Saved State A B comparison table'}))
      .toHaveTextContent('ranking')
    await userEvent.click(within(results).getByRole('button',{name:'Inspect comparison component:calendar'}))
    const drawer=screen.getByLabelText('Compare read-only detail')
    expect(drawer).toHaveTextContent('Canonical Saved change evidence')
    expect(within(drawer).getByText('"before"')).toBeInTheDocument()
    expect(within(drawer).getByText('"after"')).toBeInTheDocument()
    expect(drawer).toHaveTextContent('NOT reconstructed')
    await userEvent.click(within(drawer).getByRole('button',{name:'Close Compare detail'}))
    expect(screen.queryByLabelText('Compare read-only detail')).not.toBeInTheDocument()
    expect(api.compareSavedRevisions).toHaveBeenCalledTimes(1)
  })
  it('inspects the true Saved payload of A without restore and verifies hash/owner',async()=>{
    open()
    const results=await screen.findByLabelText('Compare Saved Revision results')
    await within(results).findByRole('table',{name:'Saved State A B comparison table'})
    await userEvent.click(within(results).getByRole('button',{name:'Inspect state A read-only'}))
    const drawer=await screen.findByLabelText('Compare read-only detail')
    await waitFor(()=>expect(drawer).toHaveTextContent('immutable'))
    expect(drawer).toHaveTextContent('parent-branch')
    expect(drawer).toHaveTextContent('hash-old')
    expect(api.getSavedRevision).toHaveBeenCalledWith('run-a','fork','old')
  })
  it('blocks cross-Branch switching with stale A/B; no silent compare fallback',async()=>{
    open()
    const results=await screen.findByLabelText('Compare Saved Revision results')
    await within(results).findByRole('table',{name:'Saved State A B comparison table'})
    await userEvent.selectOptions(screen.getByLabelText('Compare Branch'),'other')
    expect(screen.getByLabelText('Compare state A')).toHaveValue('')
    expect(screen.getByLabelText('Compare state B')).toHaveValue('')
    expect(screen.queryByLabelText('Compare Saved Revision results')).not.toBeInTheDocument()
    expect(api.compareSavedRevisions).toHaveBeenCalledTimes(1)
  })
  it('does not compare unreachable revisions, foreign Branches or identical state selections',async()=>{
    open('branch=fork&a=unknown&b=new')
    expect(await screen.findByText(/Requested state is not in the loaded reachable history/))
      .toBeInTheDocument()
    expect(api.compareSavedRevisions).not.toHaveBeenCalled()
  })
  it('does not compare a malformed or cross-owner response',async()=>{
    api.compareSavedRevisions.mockResolvedValue({...diff(),from_revision:{...first,
      revision_branch_id:'foreign'}})
    open()
    expect(await screen.findByText(/identity\/content hashes disagree/)).toBeInTheDocument()
    expect(screen.queryByRole('table',{name:'Saved State A B comparison table'}))
      .not.toBeInTheDocument()
  })
  it('shows true season-specific Edition field edits, added events and side evidence from two Saved A/B states',async()=>{
    const event=(event_id:string,season_week:number,extra:Record<string,unknown>={})=>({
      event_id,season:'2000/2001',season_week,event_name:event_id+' Cup',
      template_id:'template',category:'Bronze',tour_level:'World Tour',
      host_country:'CZE',host_city:'Brno',region:'Europe',
      main_draw_size:8,qualification_draw_size:0,seeds_count:2,qualifier_spots:0,
      wild_cards:0,byes:0,ranking_status:'unpublished',result_published:false,
      champion_player_id:null,finalist_player_id:null,...extra
    })
    api.getSavedTourCalendar.mockImplementation(async (_run:string,branch:string,
      rev:string,season:number)=>{
      const events=rev==='old'?[
        event('Kept',9),event('Moved',61,{host_country:'USA'})]:
        [event('Kept',9),event('Moved',1,{host_country:'CZE'}),event('Added',12)]
      return {
        schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
        run_id:'run-a',branch_id:branch,revision_branch_id:rev==='old'?'parent-branch':'fork',
        saved_revision_id:rev,season_index:season,season:'2000/2001',week_count:61,
        calendar_status:'ready',edition_count:events.length,editions:events
      }
    })
    open()
    const section=await screen.findByLabelText('Compare saved season Editions')
    const stats=await within(section).findByLabelText('Compare saved Edition totals')
    expect(stats).toHaveTextContent('1')
    const table=within(section).getByRole('table',{name:'Compared Saved Edition changes'})
    expect(table).toHaveTextContent('Added Cup')
    expect(table).toHaveTextContent('Moved Cup')
    expect(table).not.toHaveTextContent('Kept Cup')
    await userEvent.click(within(section).getByRole('button',{name:'Inspect Saved Edition Moved'}))
    const drawer=screen.getByLabelText('Saved Edition A B detail')
    expect(drawer).toHaveTextContent('season_week, host_country')
    expect(drawer).toHaveTextContent('"USA"')
    expect(drawer).toHaveTextContent('"CZE"')
    expect(drawer).toHaveTextContent('parent-branch')
    await userEvent.click(within(drawer).getByRole('button',{name:'Close Edition comparison'}))
    await userEvent.selectOptions(within(section).getByLabelText('Compare Edition display filter'),'all')
    expect(within(section).getByRole('table',{name:'Compared Saved Edition changes'}))
      .toHaveTextContent('Kept Cup')
    await userEvent.selectOptions(within(section).getByLabelText('Compare Edition season'),'1')
    expect(api.getSavedTourCalendar).toHaveBeenCalledWith('run-a','fork','old',1)
    expect(api.getSavedTourCalendar).toHaveBeenCalledWith('run-a','fork','new',1)
    expect(api.compareSavedRevisions).toHaveBeenCalledTimes(1)
  })
  it('loads exact published match A/B changes only on inspecting a real common Edition',async()=>{
    const edition={
      event_id:'Cup',season:'2000/2001',season_week:9,event_name:'Test Cup',
      template_id:'template',category:'Bronze',tour_level:'World Tour',
      host_country:'CZE',host_city:'Brno',region:'Europe',
      main_draw_size:4,qualification_draw_size:0,seeds_count:2,
      qualifier_spots:0,wild_cards:0,byes:0,ranking_status:'published',
      result_published:true,champion_player_id:'p1',finalist_player_id:'p2'
    }
    api.getSavedTourCalendar.mockImplementation(async (_run:string,branch:string,
      rev:string,season:number)=>({
      schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
      run_id:'run-a',branch_id:branch,
      revision_branch_id:rev==='old'?'parent-branch':'fork',
      saved_revision_id:rev,season_index:season,season:'2000/2001',
      week_count:61,calendar_status:'ready',edition_count:1,editions:[edition]
    }))
    api.getSavedTourEdition.mockImplementation(async (_run:string,branch:string,
      rev:string,season:number)=>({
      schema_version:'run_saved_tour_edition.v1',source:'reachable_saved_revision',
      run_id:'run-a',branch_id:branch,
      revision_branch_id:rev==='old'?'parent-branch':'fork',
      saved_revision_id:rev,season_index:season,edition,
      published_result:{
        schema_version:'viewer_tournament_result.v1',product_run_id:'run-a',
        viewer_branch_id:rev==='old'?'parent-branch':'fork',
        event_id:'Cup',completed_season_index:0,completed_week:9,
        champion_player_id:'p1',finalist_player_id:'p2',
        qualification_winner_ids:[],players:[],
        matches:rev==='old'?[
          {match_id:'same',draw_type:'main',round_number:1,bracket_position:1,
            winner_player_id:'p1',loser_player_id:'p2',scoreline:'3-0'},
          {match_id:'changed',draw_type:'main',round_number:1,bracket_position:2,
            winner_player_id:'p1',loser_player_id:'p2',scoreline:'3-1'}
        ]:[
          {match_id:'same',draw_type:'main',round_number:1,bracket_position:1,
            winner_player_id:'p1',loser_player_id:'p2',scoreline:'3-0'},
          {match_id:'changed',draw_type:'main',round_number:1,bracket_position:2,
            winner_player_id:'p2',loser_player_id:'p1',scoreline:'3-2'},
          {match_id:'added',draw_type:'main',round_number:2,bracket_position:1,
            winner_player_id:'p1',loser_player_id:'p2',scoreline:'3-1'}
        ]
      },
      lifecycle_status:'unavailable'
    }))
    open()
    const section=await screen.findByLabelText('Compare saved season Editions')
    await within(section).findByLabelText('Compare saved Edition totals')
    expect(api.getSavedTourEdition).not.toHaveBeenCalled()
    await userEvent.selectOptions(within(section).getByLabelText('Compare Edition display filter'),'all')
    await userEvent.click(within(section).getByRole('button',{name:'Inspect Saved Edition Cup'}))
    const panel=await screen.findByLabelText('Compare exact published Saved matches')
    const table=await within(panel).findByRole('table',{name:'Compared published Saved matches'})
    expect(table).toHaveTextContent('changed')
    expect(table).toHaveTextContent('3-1 → 3-2')
    expect(table).toHaveTextContent('added')
    expect(table).not.toHaveTextContent('same')
    expect(api.getSavedTourEdition).toHaveBeenCalledWith('run-a','fork','old',0,'Cup')
    expect(api.getSavedTourEdition).toHaveBeenCalledWith('run-a','fork','new',0,'Cup')
    await userEvent.click(within(panel).getByRole('button',{name:'Inspect published match changed'}))
    const matchDetail=within(panel).getByLabelText('Exact published match A B detail')
    expect(matchDetail).toHaveTextContent('"p1"')
    expect(matchDetail).toHaveTextContent('"p2"')
    await userEvent.click(within(matchDetail).getByRole('button',{name:'Close match evidence'}))
    await userEvent.selectOptions(within(panel).getByLabelText('Compare published match display filter'),'all')
    expect(within(panel).getByRole('table',{name:'Compared published Saved matches'}))
      .toHaveTextContent('same')
  })
  it('fails closed when State B calendar comes from the wrong original owner',async()=>{
    api.getSavedTourCalendar.mockImplementation(async (_run:string,branch:string,
      rev:string,season:number)=>({
        schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
        run_id:'run-a',branch_id:branch,revision_branch_id:'foreign',
        saved_revision_id:rev,season_index:season,
        season:(2000+season)+'/'+(2001+season),week_count:61,
        calendar_status:'empty',edition_count:0,editions:[]
      }))
    open()
    expect(await screen.findByText(/Saved Edition identity, source Branch or calendar evidence is inconsistent/))
      .toBeInTheDocument()
    expect(screen.queryByRole('table',{name:'Compared Saved Edition changes'}))
      .not.toBeInTheDocument()
  })
  it('can load an older ancestor before comparing the URL-selected A/B',async()=>{
    api.listSavedRevisionHistory.mockImplementation(async (_run:string,branch:string,options:{
      beforeSequence?:number})=>{
      if(options.beforeSequence===2)return {...history(branch,[first]),total_count:2}
      return {...history(branch,[second],true),total_count:2}
    })
    open()
    expect(await screen.findByText(/Requested state is not in the loaded reachable history/))
      .toBeInTheDocument()
    expect(api.compareSavedRevisions).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button',{name:'Load older revisions for Compare'}))
    expect(await screen.findByRole('table',{name:'Saved State A B comparison table'}))
      .toHaveTextContent('calendar')
    expect(api.listSavedRevisionHistory).toHaveBeenCalledWith('run-a','fork',{
      limit:50,beforeSequence:2
    })
  })
  it('switches History/Compare headings, controls and accessible names to Czech without mutations',async()=>{
    locale.current='cs'
    open()
    const selection=await screen.findByLabelText('Výběr uložených revizí pro porovnání')
    expect(await within(selection).findByLabelText('Větev porovnání')).toHaveValue('fork')
    await waitFor(()=>expect(within(selection).getByLabelText('Porovnat stav A')).toHaveValue('old'))
    expect(within(selection).getByLabelText('Porovnat stav B')).toHaveValue('new')
    expect(screen.getByText('Porovnání uložených stavů A/B')).toBeInTheDocument()
    const results=await screen.findByLabelText('Výsledky porovnání uložených revizí')
    expect(within(results).getByLabelText('Filtr porovnání')).toHaveValue('differences')
    expect(within(results).getByLabelText('Tabulka porovnání uložených stavů A/B'))
      .toHaveTextContent('změněno')
    expect(api.compareSavedRevisions).toHaveBeenCalledWith('run-a','fork','old','new')
    await userEvent.click(within(results).getByRole('button',{name:'Prohlédnout stav A jen pro čtení'}))
    expect(await screen.findByText('Zdrojová větev:')).toBeInTheDocument()
    expect(screen.queryByText('Source Branch:')).not.toBeInTheDocument()
  })

})

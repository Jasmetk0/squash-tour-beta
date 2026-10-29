import {fireEvent,render,screen} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter,Routes,Route} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {RunWorldCountrySavedPlayers} from './RunWorldCountrySavedPlayers'
import {SavedPlayerIdentityPage} from './SavedPlayerIdentityPage'
import {writeCountryRosterPermalink} from './countrySavedRosterPermalink'

const ctx=vi.hoisted(()=>({branch:'branch-a',head:'rev-a'}))
const api=vi.hoisted(()=>({getSavedPlayersInventory:vi.fn(),getSavedPlayerProfile:vi.fn()}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error{}}))
vi.mock('../admin/AdminBranchContext',()=>({useAdminBranch:()=>({
  selectedBranch:{run_id:'run',branch_id:ctx.branch,saved_head_revision_id:ctx.head},
  isLoading:false,error:null,
})}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>({
  mode:'present',viewCheckpointId:null,isLoading:false,error:null,
})}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
vi.mock('./SavedPlayerMatchesPanel',()=>({SavedPlayerMatchesPanel:()=>null}))

const players=Array.from({length:30},(_,i)=>({
  player_id:'p-'+String(i+1).padStart(3,'0'),
  display_name:'Alpha '+String(i+1).padStart(3,'0'),
  country_code:'CZE',identity_source:'initial_world' as const,
  status:'active',age:null,ovr:null,potential_ovr:null,
  ranking_status:'unpublished' as const,rank:null,
}))
const params=writeCountryRosterPermalink(new URLSearchParams('tab=players&year=2025'),
  JSON.stringify(['run','branch-a','rev-a','CZE']),{
    search:'Alpha',status:'',includePrepared:false,page:1,
  })
const initial='/admin/runs/run/world/countries/CZE?'+params.toString()
function mount(entry=initial){
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})
  const ui=<QueryClientProvider client={client}>
    <MemoryRouter initialEntries={[entry]}><Routes>
      <Route path="/admin/runs/:runId/world/countries/:countryCode" element={
        <RunWorldCountrySavedPlayers runId="run" branchId={ctx.branch}
          savedHead={ctx.head} countryCode="CZE" language="en"
          selectedWorldYear={2025}/>}/>
      <Route path="/admin/runs/:runId/people/:playerId" element={
        <SavedPlayerIdentityPage/>}/>
    </Routes></MemoryRouter>
  </QueryClientProvider>
  return render(ui)
}
describe('Saved Country roster → verified player profile → exact-filter return',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    ctx.branch='branch-a';ctx.head='rev-a'
    api.getSavedPlayersInventory.mockImplementation(async (
      run:string,branch:string,head:string,
      f:{search:string;country_code:string;status_filter:string;
        include_prepared:boolean;offset:number;limit:number},
    )=>({
      schema_version:'saved_players_inventory.v1',source:'selected_branch_saved_revision',
      time_context:'present',run_id:run,branch_id:branch,saved_revision_id:head,
      ranking_week_ordinal:null,search:f.search,country_code:f.country_code,
      status_filter:f.status_filter,include_prepared:f.include_prepared,
      offset:f.offset,limit:f.limit,total:players.length,
      has_more:f.offset+f.limit<players.length,players:players.slice(f.offset,f.offset+f.limit),
    }))
    api.getSavedPlayerProfile.mockImplementation(async (run:string,branch:string,id:string)=>({
      schema_version:'saved_player_profile.v1',run_id:run,branch_id:branch,
      saved_revision_id:ctx.head,player_id:id,source:'selected_branch_saved_revision',
      identity:{player_id:id,display_name:players.find(p=>p.player_id===id)?.display_name||id,
        country_code:'CZE',identity_source:'initial_world'},
      ranking_status:'unpublished',ranking_week_ordinal:null,
      rank:null,points:null,titles:0,final_appearances:0,
      total_tournament_results:0,tournament_results:[],
    }))
  })

  it('actually navigates to a verified player profile and returns to page 2 with search',async()=>{
    mount()
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link',{name:'Alpha 030'}))
    expect(await screen.findByRole('heading',{name:'Alpha 030'})).toBeInTheDocument()
    const back=screen.getByRole('link',{name:'← Back to filtered country roster'})
    expect(back.getAttribute('href')).toContain('spPage=2')
    fireEvent.click(back)
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    expect(screen.getByRole('searchbox',{name:'Country roster search'})).toHaveValue('Alpha')
    expect(api.getSavedPlayersInventory.mock.calls.every(([,branch,head,f])=>
      branch==='branch-a'&&head==='rev-a'&&f.search==='Alpha'&&f.offset===25)).toBe(true)
  })

  it('rejects an obsolete Branch even when the verified nationality still matches',async()=>{
    ctx.branch='branch-b'
    mount('/admin/runs/run/people/p-030?'+new URLSearchParams({
      fromCountry:initial,
    }))
    expect(await screen.findByRole('heading',{name:'Alpha 030'})).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'← Back to filtered country roster'})).not.toBeInTheDocument()
  })

  it('rejects a retired Saved HEAD despite the same Run, Branch and Country',async()=>{
    ctx.head='rev-b'
    mount('/admin/runs/run/people/p-030?'+new URLSearchParams({
      fromCountry:initial,
    }))
    expect(await screen.findByRole('heading',{name:'Alpha 030'})).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'← Back to filtered country roster'})).not.toBeInTheDocument()
  })

  it('refuses a foreign Country return URL and keeps the generic Players backlink',async()=>{
    const other='/admin/runs/run/world/countries/ENG?tab=players&spScope='+
      encodeURIComponent(JSON.stringify(['run','branch-a','rev-a','ENG']))
    mount('/admin/runs/run/people/p-030?'+new URLSearchParams({
      fromCountry:other,
    }))
    expect(await screen.findByRole('heading',{name:'Alpha 030'})).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'← Back to filtered country roster'})).not.toBeInTheDocument()
    expect(screen.getByRole('link',{name:'← Back to Players'})).toBeInTheDocument()
  })
})

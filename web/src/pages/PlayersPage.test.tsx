import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PlayersPage } from './PlayersPage'

const api=vi.hoisted(()=>({getSavedPlayersInventory:vi.fn()}))
const context=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'a',display_name:'Timeline A',saved_head_revision_id:'head-a'},
  time:{mode:'present',viewCheckpointId:null}
}))
vi.mock('../api/client',()=>api)
vi.mock('../admin/AdminBranchContext',()=>({
  useAdminBranch:()=>({selectedBranch:context.branch,isLoading:false,error:null})
}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>context.time}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
const player=(id:string)=>({
  player_id:id,display_name:'Player '+id,country_code:'CZE',
  identity_source:'initial_world',age:null,status:'active',
  ovr:null,potential_ovr:null,ranking_status:'unpublished',rank:null
})
function mount():void {
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
    <MemoryRouter initialEntries={['/admin/runs/run-a/players']}><Routes>
      <Route path="/admin/runs/:runId/players" element={<PlayersPage/>}/>
    </Routes></MemoryRouter>
  </QueryClientProvider>)
}
type Filters={offset:number;limit:number;search:string;country_code:string;status_filter:string;include_prepared:boolean}
const response=(filters:Filters,head='head-a')=>({
  schema_version:'saved_players_inventory.v1',run_id:'run-a',branch_id:'a',
  saved_revision_id:head,source:'selected_branch_saved_revision',time_context:'present',
  ranking_week_ordinal:null, ...filters,total:1001,has_more:filters.offset+filters.limit<1001,
  players:[player('p'+filters.offset)]
})
describe('Canonical Run Players',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.branch.saved_head_revision_id='head-a'
    context.time.mode='present'
    api.getSavedPlayersInventory.mockImplementation(async (_r:string,_b:string,head:string,filters:Filters)=>response(filters,head))
  })
  it('uses Branch HEAD and real server pagination, never legacy API',async()=>{
    mount()
    expect(await screen.findByRole('link',{name:/Player p0/})).toHaveAttribute('href','/admin/runs/run-a/people/p0')
    expect(screen.getAllByText('—').length).toBeGreaterThan(1)
    expect(screen.queryByText('NR')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Next →'}))
    await waitFor(()=>expect(screen.getByRole('link',{name:/Player p50/})).toBeInTheDocument())
    expect(api.getSavedPlayersInventory).toHaveBeenLastCalledWith('run-a','a','head-a',expect.objectContaining({offset:50,limit:50}))
    fireEvent.change(screen.getByRole('textbox',{name:'Player search'}),{target:{value:'Olivia'}})
    await waitFor(()=>expect(api.getSavedPlayersInventory).toHaveBeenLastCalledWith('run-a','a','head-a',expect.objectContaining({offset:0,search:'Olivia'})))
  })
  it('shows the exact saved ranking week index without assuming a 61-week calendar',async()=>{
    api.getSavedPlayersInventory.mockImplementation(async (_r:string,_b:string,_h:string,filters:Filters)=>({
      ...response(filters),ranking_week_ordinal:78,
    }))
    mount()
    expect(await screen.findByText(/Ranking publication · week index 78/)).toBeInTheDocument()
    expect(screen.queryByText(/Ranking W18/)).not.toBeInTheDocument()
  })
  it('rejects a foreign Saved Revision response instead of displaying stale player',async()=>{
    api.getSavedPlayersInventory.mockImplementation(async (_r:string,_b:string,_h:string,filters:Filters)=>response(filters,'foreign'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Response does not belong')
    expect(screen.queryByRole('link',{name:/Player p0/})).not.toBeInTheDocument()
  })
  it('disables present-time fetch and shows no fake historical roster',async()=>{
    context.time.mode='checkpoint'
    mount()
    expect(screen.getByText(/Historical player projection is not supported/)).toBeInTheDocument()
    expect(api.getSavedPlayersInventory).not.toHaveBeenCalled()
  })
  it('requires explicit reveal before showing prepared prospects',async()=>{
    mount()
    await screen.findByRole('link',{name:/Player p0/})
    expect(api.getSavedPlayersInventory).toHaveBeenCalledWith('run-a','a','head-a',expect.objectContaining({include_prepared:false}))
    fireEvent.click(screen.getByRole('checkbox',{name:/explicitly reveal saved prepared prospects/}))
    await waitFor(()=>expect(api.getSavedPlayersInventory).toHaveBeenLastCalledWith('run-a','a','head-a',expect.objectContaining({include_prepared:true})))
  })
})

import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedPlayerIdentityPage } from './SavedPlayerIdentityPage'

const api=vi.hoisted(()=>({getSavedPlayerProfile:vi.fn()}))
const context=vi.hoisted(()=>({time:{mode:'present',viewCheckpointId:null},language:'en'}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error{}}))
vi.mock('../admin/AdminBranchContext',()=>({useAdminBranch:()=>({
  selectedBranch:{run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'head-a'},
  isLoading:false,error:null
})}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>context.time}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:context.language})}))
vi.mock('./SavedPlayerMatchesPanel',()=>({SavedPlayerMatchesPanel:()=> <div data-testid="saved-matches">Real saved matches panel</div>}))
function mount(){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const ui=()=> <QueryClientProvider client={client}>
    <MemoryRouter initialEntries={['/admin/runs/run-a/people/p1']}><Routes>
      <Route path="/admin/runs/:runId/people/:playerId" element={<SavedPlayerIdentityPage/>}/>
    </Routes></MemoryRouter>
  </QueryClientProvider>
  const view=render(ui())
  return {...view,refresh:()=>view.rerender(ui())}
}
const profile={
  schema_version:'saved_player_profile.v1',run_id:'run-a',branch_id:'branch-a',
  saved_revision_id:'head-a',player_id:'p1',source:'selected_branch_saved_revision',
  identity:{player_id:'p1',display_name:'Sample Player',country_code:'CZE',identity_source:'initial_world'},
  ranking_status:'unpublished',ranking_week_ordinal:null,rank:null,points:null,
  titles:0,final_appearances:0,total_tournament_results:0,tournament_results:[]
}
describe('Saved player three-tab profile',()=>{
  beforeEach(()=>{vi.clearAllMocks();context.time.mode='present';context.language='en';api.getSavedPlayerProfile.mockResolvedValue(profile)})
  it('starts read-only with overview; career/matches open on explicit tab',async()=>{
    mount()
    expect(await screen.findByRole('heading',{name:'Sample Player'})).toBeInTheDocument()
    expect(screen.getByRole('tab',{name:'Overview'})).toHaveAttribute('aria-selected','true')
    expect(screen.queryByTestId('saved-matches')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab',{name:'Attributes'}))
    expect(screen.getByText(/not available in this saved-player read contract yet/)).toBeInTheDocument()
    expect(screen.queryByText('0–200', {exact:true})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab',{name:'Career & results'}))
    expect(screen.getByTestId('saved-matches')).toBeInTheDocument()
  })
  it('refuses historical mode instead of querying the current profile',()=>{
    context.time.mode='checkpoint'
    mount()
    expect(screen.getByText(/Historical player profile for this checkpoint is not supported/)).toBeInTheDocument()
    expect(api.getSavedPlayerProfile).not.toHaveBeenCalled()
  })
  it('keeps the published ranking ordinal without fabricating a 2000-based season or W61 date',async()=>{
    api.getSavedPlayerProfile.mockResolvedValue({
      ...profile,ranking_status:'ranked',ranking_week_ordinal:78,rank:3,points:42,
    })
    mount()
    expect(await screen.findByText('Latest publication · week index: 78')).toBeInTheDocument()
    expect(screen.queryByText(/2001\/02/)).not.toBeInTheDocument()
    expect(screen.queryByText(/W18/)).not.toBeInTheDocument()
  })
  it('does not render foreign-branch profile',async()=>{
    api.getSavedPlayerProfile.mockResolvedValue({...profile,saved_revision_id:'foreign'})
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Profile does not match')
    expect(screen.queryByRole('tab',{name:'Career & results'})).not.toBeInTheDocument()
  })
  it('hides a formerly verified profile when a later Retry fails',async()=>{
    api.getSavedPlayerProfile.mockResolvedValueOnce(profile)
    api.getSavedPlayerProfile.mockRejectedValueOnce(new Error('offline'))
    mount()
    expect(await screen.findByRole('heading',{name:'Sample Player'})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Retry profile read'}))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByRole('heading',{name:'Sample Player'})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Retry profile read'}))
    expect(await screen.findByRole('heading',{name:'Sample Player'})).toBeInTheDocument()
    expect(api.getSavedPlayerProfile).toHaveBeenCalledTimes(3)
  })
  it('recovers an unavailable Saved profile via explicit read-only Retry',async()=>{
    api.getSavedPlayerProfile.mockRejectedValueOnce(new Error('offline'))
    mount()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByText('Sample Player')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Retry profile read'}))
    expect(await screen.findByRole('heading',{name:'Sample Player'})).toBeInTheDocument()
    expect(api.getSavedPlayerProfile).toHaveBeenCalledTimes(2)
  })
  it('preserves true zero ranking points rather than replacing it with missing data',async()=>{
    api.getSavedPlayerProfile.mockResolvedValue({
      ...profile,ranking_status:'ranked',ranking_week_ordinal:0,rank:1,points:0
    })
    mount()
    expect(await screen.findByText(/0.*points/)).toBeInTheDocument()
  })

  it('does not refetch Saved player history merely for a language change',async()=>{
    const view=mount()
    expect(await screen.findByRole('heading',{name:'Sample Player'})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab',{name:'Career & results'}))
    const reads=api.getSavedPlayerProfile.mock.calls.length
    context.language='cs'
    view.refresh()
    expect(screen.getByRole('tab',{name:'Kariéra a výsledky'})).toHaveAttribute('aria-selected','true')
    expect(api.getSavedPlayerProfile).toHaveBeenCalledTimes(reads)
  })
})

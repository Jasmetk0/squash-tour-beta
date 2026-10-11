import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunPlayerGeneratorPage } from './RunPlayerGeneratorPage'

const api=vi.hoisted(()=>({getRunContainer:vi.fn()}))
const context=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'saved-a'},
  time:{mode:'present',isLoading:false,error:null}
}))
vi.mock('../api/client',()=>api)
vi.mock('../admin/AdminBranchContext',()=>({useAdminBranch:()=>({
  selectedBranch:context.branch,isLoading:false,error:null
})}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>context.time}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
vi.mock('../components/RunInitialWorldSetupPanel',()=>({
  RunInitialWorldSetupPanel:({run,branch}:{run:{run_id:string},branch:{branch_id:string}})=>
    <output data-testid="production-generator">{run.run_id}/{branch.branch_id}</output>
}))
function mount():void {
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
    <MemoryRouter initialEntries={['/admin/runs/run-a/players/generate']}>
      <Routes><Route path="/admin/runs/:runId/players/generate"
        element={<RunPlayerGeneratorPage/>}/></Routes>
    </MemoryRouter>
  </QueryClientProvider>)
}
describe('single Run Players Generate entry',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.time.mode='present';context.time.error=null
    context.branch.run_id='run-a'
    api.getRunContainer.mockResolvedValue({run_id:'run-a'})
  })
  it('mounts the real shared production flow for a matching current Run/Branch',async()=>{
    mount()
    expect(await screen.findByTestId('production-generator')).toHaveTextContent('run-a/branch-a')
    expect(screen.getByRole('heading',{name:'Generate players'})).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'← Back to Players'})).toHaveAttribute('href','/admin/runs/run-a/players')
  })
  it('never permits generation against historical checkpoints',async()=>{
    context.time.mode='checkpoint'
    mount()
    expect(screen.getByText(/Historical checkpoints are read-only/)).toBeInTheDocument()
    expect(screen.queryByTestId('production-generator')).not.toBeInTheDocument()
  })
  it('blocks a foreign or stale Run scope instead of silently switching',async()=>{
    context.branch.run_id='another-run'
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Select a valid Active Admin Branch')
    expect(screen.queryByTestId('production-generator')).not.toBeInTheDocument()
  })
})

import {act,render,screen,waitFor,within} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {MemoryRouter,Route,Routes} from 'react-router-dom'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {beforeEach,describe,it,expect,vi} from 'vitest'
import {SavedCrossRunComparePage} from './SavedCrossRunComparePage'
import {a,b,response,revision} from './crossSavedCompareFixture'
const api=vi.hoisted(()=>({listRunContainers:vi.fn(),listRunBranches:vi.fn(),listSavedRevisionHistory:vi.fn(),compareCrossSavedRevisions:vi.fn(),ApiError:class extends Error{}}))
vi.mock('../api/client',()=>api)
vi.mock('../api/crossSavedCompare',()=>api)
const locale=vi.hoisted(()=>({language:'en'}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>locale}))
const route='/admin/compare-runs?run_a=run-a&branch_a=branch-a&rev_a=rev-a&run_b=run-b&branch_b=branch-b&rev_b=rev-b'
const mount=(url='/admin/compare-runs')=>render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
  <MemoryRouter initialEntries={[url]}><Routes><Route path="/admin/compare-runs" element={<SavedCrossRunComparePage/>}/></Routes></MemoryRouter>
</QueryClientProvider>)
beforeEach(()=>{
  vi.resetAllMocks();locale.language='en'
  api.listRunContainers.mockResolvedValue({run_containers:[{run_id:a.runId,display_name:'World A'},{run_id:b.runId,display_name:'World B'}]})
  api.listRunBranches.mockImplementation(async(run:string)=>({run_branches:[{run_id:run,branch_id:run==='run-a'?a.branchId:b.branchId,display_name:'Timeline 1'}]}))
  api.listSavedRevisionHistory.mockImplementation(async(run:string,branch:string)=>({run_id:run,branch_id:branch,
    saved_head_revision_id:run==='run-a'?a.head:b.head,saved_revisions:[run==='run-a'?a.revision:b.revision],
    total_count:1,has_more_older:false,next_before_sequence:null}))
  api.compareCrossSavedRevisions.mockResolvedValue(response())
})
describe('Read-only Cross-Run selection',()=>{
  it('requires explicit source choices and Compare, without raw ID entry',async()=>{
    mount();expect(await screen.findAllByRole('option',{name:'World A'})).toHaveLength(2)
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(api.compareCrossSavedRevisions).not.toHaveBeenCalled()
    for(const [side,run,branch,rev] of [['A',a.runId,a.branchId,a.head],['B',b.runId,b.branchId,b.head]]){
      await userEvent.selectOptions(screen.getByLabelText(side+' Run'),run)
      await waitFor(()=>expect(screen.getByLabelText(side+' Branch')).not.toBeDisabled())
      await userEvent.selectOptions(screen.getByLabelText(side+' Branch'),branch)
      await waitFor(()=>expect(screen.getByLabelText(side+' Saved Revision')).not.toBeDisabled())
      await userEvent.selectOptions(screen.getByLabelText(side+' Saved Revision'),rev)
    }
    expect(api.compareCrossSavedRevisions).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button',{name:'Compare'}))
    expect(await screen.findByRole('heading',{name:'Changes overview'})).toBeInTheDocument()
    expect(api.compareCrossSavedRevisions).toHaveBeenCalledWith(a.runId,a.branchId,a.head,b.runId,b.branchId,b.head)
  })
  it('verifies shared-link sources before rendering and filters locally',async()=>{
    mount(route);expect(await screen.findByRole('heading',{name:'Changes overview'})).toBeInTheDocument()
    let table=screen.getByRole('table',{name:'Cross-Run comparison table'})
    expect(table).not.toHaveTextContent('same')
    const calls=api.compareCrossSavedRevisions.mock.calls.length
    await userEvent.selectOptions(screen.getByLabelText('Cross-Run display filter'),'all')
    table=screen.getByRole('table',{name:'Cross-Run comparison table'});expect(table).toHaveTextContent('same')
    expect(api.compareCrossSavedRevisions).toHaveBeenCalledTimes(calls)
    await userEvent.click(screen.getByRole('button',{name:'Inspect run:missing'}))
    const detail=screen.getByLabelText('Cross-Run difference detail')
    expect(within(detail).getByText('Missing')).toBeInTheDocument()
    expect(within(detail).getByText('null')).toBeInTheDocument()
  })
  it('hides prior results on unsent swap and clears dependent branch/revision when Run changes',async()=>{
    mount(route);await screen.findByRole('heading',{name:'Changes overview'})
    const count=api.compareCrossSavedRevisions.mock.calls.length
    await userEvent.click(screen.getByRole('button',{name:'Swap A/B'}))
    expect(screen.getByLabelText('A Run')).toHaveValue(b.runId)
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(api.compareCrossSavedRevisions).toHaveBeenCalledTimes(count)
    await userEvent.selectOptions(screen.getByLabelText('A Run'),a.runId)
    expect(screen.getByLabelText('A Branch')).toHaveValue('')
    expect(screen.getByLabelText('A Saved Revision')).toHaveValue('')
  })
  it('rejects a response for another Run or stale HEAD instead of showing cached evidence',async()=>{
    api.compareCrossSavedRevisions.mockResolvedValue({...response(),from_source:{...response().from_source,run_id:'foreign'}})
    mount(route)
    expect(await screen.findByRole('alert')).toHaveTextContent('does not match')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
  it('blocks foreign Branches before requesting any revision/comparison',async()=>{
    api.listRunBranches.mockImplementation(async(run:string)=>({run_branches:[{run_id:'foreign',branch_id:run==='run-a'?a.branchId:b.branchId}]}))
    mount(route)
    await waitFor(()=>expect(api.listRunBranches).toHaveBeenCalledTimes(2))
    expect(api.listSavedRevisionHistory).not.toHaveBeenCalled()
    expect(api.compareCrossSavedRevisions).not.toHaveBeenCalled()
  })
  it('loads an older page explicitly and keeps its original source identity',async()=>{
    const old=revision('older','branch-a','e');old.is_branch_head=false
    api.listSavedRevisionHistory.mockImplementation(async(run:string,branch:string,options:{beforeSequence?:number})=>({
      run_id:run,branch_id:branch,saved_head_revision_id:run==='run-a'?a.head:b.head,
      saved_revisions:run==='run-a'?[options.beforeSequence?old:{...a.revision,sequence:2,parent_revision_id:'older'}]:[b.revision],
      total_count:run==='run-a'?2:1,has_more_older:run==='run-a'&&!options.beforeSequence,
      next_before_sequence:run==='run-a'&&!options.beforeSequence?2:null}))
    api.compareCrossSavedRevisions.mockResolvedValue({...response(),from_source:{...response().from_source,revision:old}})
    mount(route.replace('rev_a=rev-a','rev_a=older'))
    expect(await screen.findByRole('button',{name:'Load older revisions'})).toBeInTheDocument()
    expect(api.compareCrossSavedRevisions).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button',{name:'Load older revisions'}))
    await waitFor(()=>expect(api.listSavedRevisionHistory).toHaveBeenCalledWith(a.runId,a.branchId,{limit:50,beforeSequence:2}))
    expect(await screen.findByRole('heading',{name:'Changes overview'})).toBeInTheDocument()
  })
  it('does not display a late response after the selected source changes',async()=>{
    let deliver!:(value:ReturnType<typeof response>)=>void
    api.compareCrossSavedRevisions.mockImplementation(()=>new Promise(resolve=>{deliver=resolve}))
    mount(route)
    await waitFor(()=>expect(api.compareCrossSavedRevisions).toHaveBeenCalledTimes(1))
    await userEvent.selectOptions(screen.getByLabelText('A Run'),b.runId)
    await act(async()=>deliver(response()))
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByText('Selections changed. Press Compare to read this pair.')).toBeInTheDocument()
  })
  it('fails closed on malformed Run inventories without unscoped GETs',async()=>{
    api.listRunContainers.mockResolvedValue({run_containers:[null]})
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid Run inventory')
    expect(api.listRunBranches).not.toHaveBeenCalled()
    expect(api.compareCrossSavedRevisions).not.toHaveBeenCalled()
  })
  it('renders Czech source controls and errors',async()=>{
    locale.language='cs';api.listRunContainers.mockRejectedValue(new Error('503 catalog'))
    mount();expect(screen.getByRole('heading',{name:'Porovnání uložených stavů mezi Runy'})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Porovnat'})).toBeDisabled()
    expect(await screen.findByRole('alert')).toHaveTextContent('503 catalog')
  })
})

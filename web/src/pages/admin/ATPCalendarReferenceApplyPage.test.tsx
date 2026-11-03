import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../../i18n/LanguageContext'
import { ATPCalendarReferenceApplyPage } from './ATPCalendarReferenceApplyPage'

const hash=(s:string)=>s.repeat(64)
const ctx=vi.hoisted(()=>({
  draftVersion:0,
  stateFingerprint:null as string|null,
  savedHead:'r0',
  staged:false,
  sourceFingerprint:'a'.repeat(64),
  previewHead:'r0',
  previewConflicts:[] as string[]
}))
const api=vi.hoisted(()=>({
  getATPCalendarReferenceCatalog:vi.fn(),
  listRunContainers:vi.fn(),
  listRunBranches:vi.fn(),
  getBranchWorkingDraft:vi.fn(),
  getRunPackageState:vi.fn(),
  previewATPCalendarReference:vi.fn(),
  confirmATPCalendarReference:vi.fn(),
  saveRunPackageWorkingDraft:vi.fn()
}))
vi.mock('../../api/client',()=>api)

function mount():void {
  render(<QueryClientProvider client={new QueryClient({
    defaultOptions:{queries:{retry:false}}
  })}><MemoryRouter initialEntries={['/admin/packages/atp-tour-calendar-reference']}>
    <LanguageProvider><Routes>
      <Route path="/admin/packages/atp-tour-calendar-reference" element={<ATPCalendarReferenceApplyPage/>}/>
    </Routes></LanguageProvider>
  </MemoryRouter></QueryClientProvider>)
}
function source(){
  return {
    package_id:'atp_tour_1990_2026_calendar_reference_setup',
    package_type:'Setup',source_version:1,source_fingerprint:ctx.sourceFingerprint,
    reference_span:{from:1990,to:2026},provisional_years:[2026],
    dated_years:[2025,2026],undated_years:Array.from({length:35},(_,i)=>1990+i),
    usage:'source_reference_only_no_playable_calendar',
    children:[
      {package_id:'atp_tour_1990_2026_category',package_type:'Category',
        source_version:1,source_fingerprint:hash('b'),entity_count:11},
      {package_id:'atp_tour_1990_2026_series',package_type:'Series',
        source_version:1,source_fingerprint:hash('c'),entity_count:164},
      {package_id:'atp_tour_1990_2026_calendar',package_type:'Calendar',
        source_version:1,source_fingerprint:hash('d'),entity_count:150}
    ]
  }
}
function preview(){
  return {
    run_id:'run/1',branch_id:'branch/1',saved_head_revision_id:ctx.previewHead,
    draft_version:ctx.draftVersion,current_state_fingerprint:ctx.stateFingerprint,
    preview_fingerprint:hash('d'),
    document_identity:{package_id:'atp_tour_1990_2026_calendar_reference_setup',
      package_type:'Setup',source_version:1,source_fingerprint:hash('a')},
    additions:['atp_tour_1990_2026_category/atp_250'],unchanged:[],updates:[],
    not_included:[],unresolved:[],automatically_resolvable:[],invalid:[],
    conflicts:ctx.previewConflicts
  }
}
describe('ATP reference Apply UI — guarded, explicit Run Save',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    localStorage.clear()
    Object.assign(ctx,{draftVersion:0,stateFingerprint:null,savedHead:'r0',
      staged:false,sourceFingerprint:hash('a'),previewHead:'r0',previewConflicts:[]})
    api.getATPCalendarReferenceCatalog.mockImplementation(async()=>source())
    api.listRunContainers.mockResolvedValue({run_containers:[{
      run_id:'run/1',display_name:'Custom Run',storage_kind:'custom_local',
      read_only:false,status:'working'
    }]})
    api.listRunBranches.mockImplementation(async()=>({run_branches:[{
      run_id:'run/1',branch_id:'branch/1',display_name:'Main',status:'active',
      read_only:false,saved_head_revision_id:ctx.savedHead
    }]}))
    api.getBranchWorkingDraft.mockImplementation(async()=>({
      run_id:'run/1',branch_id:'branch/1',
      draft_version:ctx.draftVersion,base_saved_revision_id:ctx.savedHead,
      status:ctx.staged?'dirty':'clean'
    }))
    api.getRunPackageState.mockImplementation(async()=>({
      fingerprint:ctx.stateFingerprint,
      state:ctx.staged?{
        run_id:'run/1',branch_id:'branch/1',
        package_versions:[{package_id:'atp_tour_1990_2026_calendar_reference_setup',
          source_fingerprint:ctx.sourceFingerprint}]
      }:null
    }))
    api.previewATPCalendarReference.mockImplementation(async()=>preview())
    api.confirmATPCalendarReference.mockImplementation(async()=>{
      ctx.draftVersion=1;ctx.staged=true;ctx.stateFingerprint=hash('e')
      return {state:{run_id:'run/1',branch_id:'branch/1'},
        state_fingerprint:hash('e'),draft_version:1,already_applied:false,
        command_id:'atp-confirm'}
    })
    api.saveRunPackageWorkingDraft.mockImplementation(async()=>{
      ctx.staged=false;ctx.savedHead='r1'
      return {run_id:'run/1',branch_id:'branch/1',
        saved_revision:{revision_id:'r1'},
        working_draft:{run_id:'run/1',branch_id:'branch/1',
          status:'clean',base_saved_revision_id:'r1'}}
    })
  })
  async function selectTarget(){
    await screen.findByRole('option',{name:'Custom Run'})
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Target Run'}),'run/1')
    await screen.findByRole('option',{name:'Main'})
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Target Branch'}),'branch/1')
    await screen.findByText(/Přidávané:/)
  }

  it('shows a non-playable source and keeps all writes behind confirm and Save',async()=>{
    mount()
    expect(await screen.findByText(/11 položek/)).toBeInTheDocument()
    expect(screen.getByText(/164 položek/)).toBeInTheDocument()
    expect(screen.getByText(/150 položek/)).toBeInTheDocument()
    expect(screen.getByText(/2026 předběžný/)).toBeInTheDocument()
    expect(api.previewATPCalendarReference).not.toHaveBeenCalled()
    await selectTarget()
    expect(api.previewATPCalendarReference).toHaveBeenCalledWith('run/1','branch/1')
    expect(api.confirmATPCalendarReference).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
    const button=screen.getByRole('button',{name:'Potvrdit do Working Draftu'})
    expect(button).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox'))
    await waitFor(()=>expect(button).toBeEnabled())
    await userEvent.click(button)
    await waitFor(()=>expect(api.confirmATPCalendarReference).toHaveBeenCalledTimes(1))
    expect(api.confirmATPCalendarReference.mock.calls[0][2]).toMatchObject({
      expected_head_revision_id:'r0',expected_draft_version:0,
      expected_state_fingerprint:null,expected_preview_fingerprint:hash('d'),
      conflict_resolutions:{}
    })
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
    const saveButton=await screen.findByRole('button',{name:'Uložit Saved Revision'})
    await waitFor(()=>expect(saveButton).toBeEnabled())
    await userEvent.click(saveButton)
    await waitFor(()=>expect(api.saveRunPackageWorkingDraft).toHaveBeenCalledWith(
      'run/1','branch/1',1
    ))
  })

  it('blocks stale Saved Head or mismatched source fingerprint',async()=>{
    ctx.previewHead='old-revision'
    mount();await selectTarget()
    expect(screen.getByRole('button',{name:'Potvrdit do Working Draftu'})).toBeDisabled()
    expect(api.confirmATPCalendarReference).not.toHaveBeenCalled()
  })

  it('requires an explicit decision for locally diverged Category data',async()=>{
    ctx.previewConflicts=['atp_tour_1990_2026_category/atp_250:local_divergence']
    mount();await selectTarget()
    const button=screen.getByRole('button',{name:'Potvrdit do Working Draftu'})
    expect(button).toBeDisabled()
    await userEvent.selectOptions(
      screen.getByRole('combobox',{name:'Resolve atp_tour_1990_2026_category/atp_250'}),
      'keep_run'
    )
    await userEvent.click(screen.getByRole('checkbox'))
    await userEvent.click(button)
    await waitFor(()=>expect(api.confirmATPCalendarReference).toHaveBeenCalledTimes(1))
    expect(api.confirmATPCalendarReference.mock.calls[0][2].conflict_resolutions).toEqual({
      'atp_tour_1990_2026_category/atp_250':'keep_run'
    })
  })
})

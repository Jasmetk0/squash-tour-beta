import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../../i18n/LanguageContext'
import { ATPCalendarReferenceApplyPage } from './ATPCalendarReferenceApplyPage'
import {
  validATPCalendarCatalog, validSavedATPRunWeekPreview,
} from '../../api/atpCalendarReferencePackages'

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
  getATPCalendarReferenceYear:vi.fn(),
  getSavedATPRunWeekPreview:vi.fn(),
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
    dated_years:Array.from({length:37},(_,i)=>1990+i),
    undated_years:[],
    usage:'source_reference_only_no_playable_calendar',
    children:[
      {package_id:'atp_tour_1990_2026_category',package_type:'Category',
        source_version:1,source_fingerprint:hash('b'),entity_count:11},
      {package_id:'atp_tour_1990_2026_series',package_type:'Series',
        source_version:1,source_fingerprint:hash('c'),entity_count:164},
      {package_id:'atp_tour_1990_2026_calendar',package_type:'Calendar',
        source_version:1,source_fingerprint:hash('d'),entity_count:2444}
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

function savedWeekPreview() {
  return {
    schema_version:'atp_earth_run_week_preview.v1',
    run_id:'run/1',branch_id:'branch/1',saved_head_revision_id:'r1',
    saved_run_calendar_verified:true,saved_package_source_verified:true,
    uses_saved_run_package_snapshot:true,no_sporting_install:true,run_mutated:false,
    calendar:{weeks_per_year:52},selected_atp_years:[2025],
    source_tour_bindings:{verified_occurrences:2407,selected_occurrences:{
      atp_2025_chengdu:{series_name:'Chengdu Open',historical_category_label:'ATP Tour 250'},
      atp_2025_brisbane:{series_name:'Brisbane International',historical_category_label:'ATP Tour 250'},
    }},
    events:[{
      source_identity:'atp_2025_chengdu',source_start_date:'2025-09-17',source_end_date:'2025-09-23',
      review_flags:['single_week_majority_precedes_finish_week'],
      run_weeks:[{calendar_year:2025,year_week:38,season_index:0,season_week:2}],
      source_finish_run_week:{calendar_year:2025,year_week:39,season_index:0,season_week:3},
    }],
    outside_horizon:[{
      source_identity:'atp_2025_brisbane',source_start_date:'2024-12-29',source_end_date:'2025-01-05',
      review_flags:['cross_iso_year'],
      outside_year_weeks:[{calendar_year:2025,year_week:1}],
    }],
  }
}
describe('ATP reference Apply UI — guarded, explicit Run Save',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    localStorage.clear()
    Object.assign(ctx,{draftVersion:0,stateFingerprint:null,savedHead:'r0',
      staged:false,sourceFingerprint:hash('a'),previewHead:'r0',previewConflicts:[]})
    api.getATPCalendarReferenceCatalog.mockImplementation(async()=>source())
    api.getATPCalendarReferenceYear.mockImplementation(async(year:number)=>
      year===2026?{
        year,package_id:'atp_tour_1990_2026_calendar',
        source_fingerprint:hash('d'),read_only:true,run_mutated:false,
        coverage:{atp_season_year:year,roster_series_count:56,dated_series_count:1,
          undated_series_ids:[],known_not_held_series_ids:[],
          date_coverage_state:'provisional_complete_named_schedule',
          year_source_status:'provisional_published_schedule',year_source_url:null},
        events:[{series_id:'brisbane',category_id:'atp_250',
          start_date:'2026-01-04',end_date:'2026-01-11',
          start_year_week:{iso_year:2026,iso_week:1},
          end_year_week:{iso_year:2026,iso_week:2},
          iso_weeks_occupied:[{iso_year:2026,iso_week:1},{iso_year:2026,iso_week:2}],
          source_url:'https://www.atptour.com/en/scores/results-archive?year=2026',
          year_source_state:'provisional_published_schedule'}]
      }:{
        year,package_id:'atp_tour_1990_2026_calendar',
        source_fingerprint:hash('d'),read_only:true,run_mutated:false,
        coverage:{atp_season_year:year,roster_series_count:75,dated_series_count:1,
          undated_series_ids:[],known_not_held_series_ids:[],
          date_coverage_state:'verified_complete_archive_dates_with_alternate_finals_window',
          year_source_status:'verified_atp_results_archive_with_separate_finals_historical_window',
          year_source_url:'https://www.atptour.com/en/scores/results-archive?year=1990'},
        events:[{series_id:'brisbane',category_id:'atp_world_series',
          start_date:'1990-01-01',end_date:'1990-01-07',
          start_year_week:{iso_year:1990,iso_week:1},
          end_year_week:{iso_year:1990,iso_week:1},
          iso_weeks_occupied:[{iso_year:1990,iso_week:1}],
          source_url:'https://www.atptour.com/en/scores/results-archive?year=1990',
          year_source_state:'verified_atp_results_archive_with_separate_finals_historical_window'}]
      })

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

  it('validates all 37 calendar years as one non-overlapping source partition',()=>{
    const original=source()
    expect(validATPCalendarCatalog(original)).toBe(true)
    expect(validATPCalendarCatalog({...original,
      dated_years:[...original.dated_years,2026]})).toBe(false)
    expect(validATPCalendarCatalog({...original,
      undated_years:[1990]})).toBe(false)
    expect(validATPCalendarCatalog({...original,
      children:[...original.children.slice(0,2),
        {...original.children[2],entity_count:0}]})).toBe(false)
  })

  it('accepts version 2 only with its separate frozen sporting Category',()=>{
    const original=source()
    const current={...original,source_version:2,
      usage:'saved_reference_calendar_with_explicit_squash_sporting_profiles',
      children:[...original.children,{package_id:'atp_squash_sporting_profiles',package_type:'Category',
        source_version:1,source_fingerprint:hash('e'),entity_count:2}]}
    expect(validATPCalendarCatalog(current)).toBe(true)
    expect(validATPCalendarCatalog({...current,children:original.children})).toBe(false)
    expect(validATPCalendarCatalog({...current,source_version:'2'})).toBe(false)
    expect(validATPCalendarCatalog({...current,usage:original.usage})).toBe(false)
  })

  it('renders sourced ISO year/week dates for earliest ATP 1990 source',async()=>{
    mount()
    await screen.findByText('2026/W01')
    expect(screen.getByText('2026/W02')).toBeInTheDocument()
    expect(screen.getByText('2026-01-04')).toBeInTheDocument()
    await userEvent.selectOptions(
      screen.getByRole('combobox',{name:'ATP Calendar Year'}),'1990')
    expect(await screen.findByText('1990-01-01')).toBeInTheDocument()
    expect(api.confirmATPCalendarReference).not.toHaveBeenCalled()
  })

  it('shows a non-playable source and keeps all writes behind confirm and Save',async()=>{
    mount()
    expect(await screen.findByText(/11 položek/)).toBeInTheDocument()
    expect(screen.getByText(/164 položek/)).toBeInTheDocument()
    expect(screen.getByText(/2444 položek/)).toBeInTheDocument()
    expect(screen.getAllByText(/1990–2026/).length).toBeGreaterThan(0)
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

  it('reads projected weeks from the chosen Saved head and lists outside tournaments separately',async()=>{
    ctx.savedHead='r1'
    ctx.previewHead='r1'
    api.getSavedATPRunWeekPreview.mockResolvedValue(savedWeekPreview())
    mount();await selectTarget()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'ATP ročník pro Run'}),'2025')
    expect(api.getSavedATPRunWeekPreview).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button',{name:'Načíst týdny z uloženého ATP balíčku'}))
    expect(await screen.findByText('2025/W38 (S1/W02)')).toBeInTheDocument()
    expect(screen.getByText('2025/W39 (S1/W03)')).toBeInTheDocument()
    expect(screen.getByText('Turnaje mimo rozsah Runu (1)')).toBeInTheDocument()
    expect(api.getSavedATPRunWeekPreview).toHaveBeenCalledWith('run/1','branch/1','r1',2025)
    expect(api.confirmATPCalendarReference).not.toHaveBeenCalled()
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
  })

  it('rejects a different Saved head and invalid Run week in a preview response',()=>{
    const data=savedWeekPreview()
    expect(validSavedATPRunWeekPreview(data,'run/1','branch/1','r1',2025)).toBe(true)
    expect(validSavedATPRunWeekPreview(data,'run/1','branch/1','r0',2025)).toBe(false)
    data.events[0].run_weeks[0].year_week=53
    expect(validSavedATPRunWeekPreview(data,'run/1','branch/1','r1',2025)).toBe(false)
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

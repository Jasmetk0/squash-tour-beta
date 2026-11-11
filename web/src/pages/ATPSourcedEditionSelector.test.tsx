import {fireEvent,render,screen} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {ATPSourcedEditionSelector} from './ATPSourcedEditionSelector'
import type {TourWeek} from '../api/calendarTour'

const api=vi.hoisted(()=>({inspectATPSourcedEditions:vi.fn()}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error {status=400}}))
const clock:TourWeek={calendar:{schema_version:'run_calendar.v1',weeks_per_year:52,season_start_year_week:43,start_year:2025,season_count:2},season_index:0,week:1}
const catalog=()=>({run_id:'r',branch_id:'b',saved_head_revision_id:'head',entries:[{
  profile:{occurrence_id:'atp_2025_atp_finals',name:'ATP Finals 2025',source_start_date:'2025-11-09',source_end_date:'2025-11-16',group_count:2,group_size:4,ranked:true,played_group_win_points:200,native_announcement_lead_weeks:1,entrant_selection:'admin_selected_no_automatic_race_or_age'},
  profile_fingerprint:'a'.repeat(64),calendar_projection:{run_weeks:[{season_index:0,season_week:4}],run_ordinals:[3],source_finish_after_mapped_occupancy:false},
}]})
const panel=(onSelect=vi.fn(),head='head')=><LanguageProvider><ATPSourcedEditionSelector runId="r" branchId="b" head={head} clock={clock} existing={[]} disabled={false} onSelect={onSelect}/></LanguageProvider>

describe('Saved ATP sporting profile selection',()=>{
  beforeEach(()=>localStorage.setItem('squash-engine-language-v1','en'))
  it('loads only on request and selects the stored occurrence',async()=>{
    api.inspectATPSourcedEditions.mockClear().mockResolvedValue(catalog())
    const select=vi.fn()
    render(panel(select))
    expect(api.inspectATPSourcedEditions).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:/Load ATP tournaments/}))
    fireEvent.click(await screen.findByRole('button',{name:'Review import ATP Finals 2025'}))
    expect(select).toHaveBeenCalledWith('atp_2025_atp_finals')
    expect(screen.getByText(/Points per group win/)).toHaveTextContent('200')
  })
  it('refuses a catalog from a different Saved head',async()=>{
    api.inspectATPSourcedEditions.mockResolvedValue({...catalog(),saved_head_revision_id:'foreign'})
    render(panel())
    fireEvent.click(screen.getByRole('button',{name:/Load ATP tournaments/}))
    expect(await screen.findByRole('alert')).toHaveTextContent('ATP source changed')
    expect(screen.queryByRole('button',{name:'Review import ATP Finals 2025'})).not.toBeInTheDocument()
  })
  it('leaves outside-horizon sources visible without enabling import',async()=>{
    const data=catalog()
    data.entries[0].calendar_projection={run_weeks:[],run_ordinals:[],source_finish_after_mapped_occupancy:false}
    api.inspectATPSourcedEditions.mockResolvedValue(data)
    render(panel())
    fireEvent.click(screen.getByRole('button',{name:/Load ATP tournaments/}))
    expect(await screen.findByRole('button',{name:'Review import ATP Finals 2025'})).toBeDisabled()
  })
  it('shows verified knockout capacity without offering an executable import',async()=>{
    const data=catalog()
    Object.assign(data.entries[0].profile,{schema_version:'atp_squash_knockout_profile.v1',occurrence_id:'atp_2025_rotterdam',name:'Rotterdam 2025',main_entrants:32,qualification_entrants:16,qualifier_spots:4})
    Object.assign(data.entries[0],{execution_supported:false})
    api.inspectATPSourcedEditions.mockResolvedValue(data)
    render(panel())
    fireEvent.click(screen.getByRole('button',{name:/Load ATP tournaments/}))
    expect(await screen.findByRole('button',{name:'Review import Rotterdam 2025'})).toBeDisabled()
    expect(screen.getByText(/Qualification.*16/)).toHaveTextContent('32')
    expect(screen.getByText(/Simulation awaits/)).toBeInTheDocument()
  })
  it.each(['en','cs'])('shows sourced v2 Qualification dates without enabling play (%s)',async(language)=>{
    localStorage.setItem('squash-engine-language-v1',language)
    const data=catalog()
    Object.assign(data.entries[0].profile,{
      schema_version:'atp_squash_knockout_profile.v2',occurrence_id:'atp_2025_rotterdam',name:'Rotterdam 2025',
      source_start_date:'2025-02-03',source_end_date:'2025-02-09',
      main_entrants:32,qualification_entrants:16,qualifier_spots:4,qualification_date_status:'verified',
      qualification_date_evidence:{start_date:'2025-02-01',end_date:'2025-02-02',
        source_urls:['https://www.abnamro-open.nl/news/qualification'],published_dates:['2025-01-29']},
    })
    Object.assign(data.entries[0],{execution_supported:false})
    api.inspectATPSourcedEditions.mockResolvedValue(data)
    render(panel())
    fireEvent.click(screen.getByRole('button',{name:language==='cs'?/Načíst ATP turnaje/:/Load ATP tournaments/}))
    const label=language==='cs'?'Zkontrolovat import Rotterdam 2025':'Review import Rotterdam 2025'
    expect(await screen.findByRole('button',{name:label})).toBeDisabled()
    expect(screen.getByText(/2025-02-01 – 2025-02-02/)).toBeInTheDocument()
    expect(screen.getByText(language==='cs'?/Simulace tohoto formátu zatím není dostupná/:/Simulation of this format is not available yet/)).toBeInTheDocument()
  })
  it('rejects a v2 response that claims verification without its source evidence',async()=>{
    const data=catalog()
    Object.assign(data.entries[0].profile,{schema_version:'atp_squash_knockout_profile.v2',qualification_date_status:'verified'})
    Object.assign(data.entries[0],{execution_supported:false})
    api.inspectATPSourcedEditions.mockResolvedValue(data)
    render(panel())
    fireEvent.click(screen.getByRole('button',{name:/Load ATP tournaments/}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid Saved ATP Qualification date evidence')
    expect(screen.queryByRole('button',{name:'Review import ATP Finals 2025'})).not.toBeInTheDocument()
  })
  it.each(['atp_squash_knockout_profile.v1','atp_squash_knockout_profile.v3'])('rejects false or unsupported date knowledge (%s)',async(schema_version)=>{
    const data=catalog()
    Object.assign(data.entries[0].profile,{schema_version,qualification_date_status:'verified'})
    Object.assign(data.entries[0],{execution_supported:false})
    api.inspectATPSourcedEditions.mockResolvedValue(data)
    render(panel())
    fireEvent.click(screen.getByRole('button',{name:/Load ATP tournaments/}))
    expect(await screen.findByRole('alert')).toHaveTextContent(schema_version.endsWith('.v1')?'Historical ATP profile':'Unsupported Saved ATP')
    expect(screen.queryByRole('button',{name:'Review import ATP Finals 2025'})).not.toBeInTheDocument()
  })
})

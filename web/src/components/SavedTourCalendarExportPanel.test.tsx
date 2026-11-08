import {fireEvent,render,screen,within} from '@testing-library/react'
import {beforeEach,afterEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import type {SavedTourCalendar,SavedTourEvent} from '../api/savedTour'
import {SavedTourCalendarExportPanel} from './SavedTourCalendarExportPanel'

const event=(id:string,week:number,published=false):SavedTourEvent=>({
  event_id:id,event_name:'Cup '+id,season:'2002/2003',season_week:week,
  template_id:'tpl',category:'GOLD',tour_level:'WORLD',host_country:'CZE',
  host_city:'Brno',region:'EUROPE',main_draw_size:16,qualification_draw_size:8,
  seeds_count:4,qualifier_spots:4,wild_cards:2,byes:0,ranking_status:'ranked',
  result_published:published,champion_player_id:published?'winner':null,
  finalist_player_id:published?'runner':null,
})
const fixture=(events:SavedTourEvent[]=[event('a',5,true),event('b',9)]):SavedTourCalendar=>({
  schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
  run_id:'run-a',branch_id:'branch-a',revision_branch_id:'ancestor',
  saved_revision_id:'rev-old',season_index:2,season:'2002/2003',week_count:61,
  calendar_status:events.length?'ready':'empty',edition_count:events.length,editions:events,
})
const filters={
  tour:'',category:'',country:'',search:'',publication:'all' as const,
  playerId:'',playerOutcome:'any' as const,
}
function mount(model:SavedTourCalendar=fixture(),runId='run-a',focusedWeek:number|null=null){
  return render(<LanguageProvider><SavedTourCalendarExportPanel
    model={model} runId={runId} branchId="branch-a" revisionId="rev-old"
    seasonIndex={2} filters={filters} focusedWeek={focusedWeek}/>
  </LanguageProvider>)
}

describe('Saved Tour calendar read-only downloads',()=>{
  beforeEach(()=>{
    localStorage.setItem('squash-engine-language-v1','en')
    Object.defineProperty(URL,'createObjectURL',{configurable:true,writable:true,
      value:vi.fn().mockReturnValue('blob:http://localhost/export')})
    Object.defineProperty(URL,'revokeObjectURL',{configurable:true,writable:true,
      value:vi.fn()})
    vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{})
  })
  afterEach(()=>{vi.restoreAllMocks();localStorage.clear()})

  it('offers separately selected full and filtered Saved exports, never a simulation action',()=>{
    mount(fixture(), 'run-a',5)
    const region=screen.getByRole('region',{name:'Export exact Saved season'})
    expect(within(region).getByText(/Editions in export: 2/)).toBeVisible()
    expect(within(region).getByText(/Published finals: 1/)).toBeVisible()
    expect(within(region).getByText(/rev-old/)).toBeVisible()
    fireEvent.change(screen.getByRole('combobox',{name:'Export scope'}),{
      target:{value:'filtered'}
    })
    expect(within(region).getByText(/Editions in export: 1/)).toBeVisible()
    expect(screen.getByRole('button',{name:'Download JSON with source and filters'})).toBeEnabled()
    expect(screen.getByRole('button',{name:'Download CSV for spreadsheets'})).toBeEnabled()
    expect(within(region).queryByRole('button',{name:/Approve|Save|Play|Start|Resume/}))
      .not.toBeInTheDocument()
  })
  it('downloads a file only on an explicit user click and revokes its URL',()=>{
    mount()
    expect(URL.createObjectURL).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Download JSON with source and filters'}))
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledTimes(1)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/export')
    fireEvent.click(screen.getByRole('button',{name:'Download CSV for spreadsheets'}))
    expect(URL.createObjectURL).toHaveBeenCalledTimes(2)
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledTimes(2)
  })
  it('fails closed for a foreign Run, never offering an unverified download',()=>{
    mount(fixture(),'foreign')
    expect(screen.getByRole('alert')).toHaveTextContent(/source scope is invalid/)
    expect(screen.getByRole('button',{name:'Download JSON with source and filters'}))
      .toBeDisabled()
    expect(screen.getByRole('button',{name:'Download CSV for spreadsheets'}))
      .toBeDisabled()
    expect(URL.createObjectURL).not.toHaveBeenCalled()
  })
  it('keeps empty Signed seasons exportable as JSON but not unscoped CSV',()=>{
    mount(fixture([]))
    expect(screen.getByRole('button',{name:'Download JSON with source and filters'}))
      .toBeEnabled()
    expect(screen.getByRole('button',{name:'Download CSV for spreadsheets'}))
      .toBeDisabled()
    expect(screen.getByText(/CSV is unavailable for an empty selection/)).toBeVisible()
    fireEvent.click(screen.getByRole('button',{name:'Download JSON with source and filters'}))
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
  })
  it('renders Czech labels and disclosure, with no inferred outcomes',()=>{
    localStorage.setItem('squash-engine-language-v1','cs')
    mount()
    expect(screen.getByRole('region',{name:'Export přesné uložené sezony'})).toBeVisible()
    expect(screen.getByRole('combobox',{name:'Rozsah exportu'})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Stáhnout CSV pro tabulku'})).toBeEnabled()
    expect(screen.getByText(/Naplánovaná Edition není důkazem odehrání/)).toBeVisible()
  })
})

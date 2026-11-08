import {fireEvent,render,screen,within} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import type {TourView,TourEdition,TourWeek} from '../api/calendarTour'
import {NativeTourOperatorQueue} from './NativeTourOperatorQueue'

const calendar={schema_version:'run_calendar.v1',weeks_per_year:80,season_start_year_week:80,start_year:2030,season_count:3}
const date=(week:number):TourWeek=>({calendar,week,season_index:0})
const edition=(id:string,week:number):TourEdition=>({
  edition:{edition_id:id,name:'Cup '+id,week:date(week),announcement_week:date(1),
    start_slot:1,main_entrant_count:4,point_table:{champion:100},validity_weeks:80},
  submissions:[],field:null,draw:null,tournament_fingerprint:null,result_confirmed:false
})
function view(editions:TourEdition[],saved=true):TourView{
  return{
    schema_version:'calendar_tour_inspection.v1',
    run_id:'run',branch_id:'branch',saved_head_revision_id:'abcde0123456789',
    draft_version:2,checkpoint_fingerprint:'a'.repeat(64),
    tour_fingerprint:'b'.repeat(64),saved,can_initialize:false,
    players:[],transition_blockers:[],season_transition_blockers:[],
    saved_completed_seasons:[],edition_evidence:{},
    state:{week:date(40),editions,rankings:[],transitions:[]},
  }
}
function mount(v:TourView,runId='run'){
  return render(<MemoryRouter><LanguageProvider>
    <NativeTourOperatorQueue view={v} runId={runId} branchId="branch"/>
  </LanguageProvider></MemoryRouter>)
}
describe('CS/EN native Tour operator queue',()=>{
  beforeEach(()=>{localStorage.clear();localStorage.setItem('squash-engine-language-v1','en')})
  it('shows exact source, stage, Save caveat and in-page anchor without mutation controls',()=>{
    mount(view([edition('present',40)],false))
    const region=screen.getByRole('region',{name:'Tour operator queue'})
    expect(within(region).getByText(/Working Draft: observed stages may include unsaved/)).toBeVisible()
    expect(within(region).getByText(/Total: 1/)).toBeVisible()
    expect(within(region).getByText(/Review applications/)).toBeVisible()
    expect(within(region).getByRole('link',{name:'Go to Edition controls'}))
      .toHaveAttribute('href','#native-tour-edition-0')
    expect(within(region).queryByRole('button',{name:/Save|Play|Resume|Approve/})).not.toBeInTheDocument()
  })
  it('supports 80 Editions with bounded pagination and search to last exact index',()=>{
    const v=view(Array.from({length:80},(_,i)=>edition('E'+String(i+1).padStart(3,'0'),i+1)))
    mount(v)
    expect(screen.getByText(/Total: 80/)).toBeVisible()
    expect(screen.getAllByRole('link',{name:'Go to Edition controls'})).toHaveLength(12)
    fireEvent.click(screen.getByRole('button',{name:'Next'}))
    expect(screen.getByText(/Page 2 \/ 7/)).toBeInTheDocument()
    expect(screen.getAllByRole('link',{name:'Go to Edition controls'})).toHaveLength(12)
    fireEvent.change(screen.getByRole('searchbox',{name:'Search Edition'}),{target:{value:'E080'}})
    expect(screen.getAllByRole('link',{name:'Go to Edition controls'})).toHaveLength(1)
    expect(screen.getByRole('link',{name:'Go to Edition controls'})).toHaveAttribute(
      'href','#native-tour-edition-79'
    )
    expect(screen.queryByRole('button',{name:'Next'})).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox',{name:'Search Edition'}),{target:{value:''}})
    fireEvent.change(screen.getByRole('combobox',{name:'Show Editions'}),{target:{value:'current'}})
    expect(screen.getAllByRole('link',{name:'Go to Edition controls'})).toHaveLength(1)
    expect(screen.getByText('Cup E040')).toBeVisible()
  })
  it('filters confirmed results without confusing draft stages or preserving stale evidence',()=>{
    const first=edition('finished',40)
    first.result_confirmed=true
    const second=edition('unfinished',40)
    mount(view([first,second]))
    fireEvent.change(screen.getByRole('combobox',{name:'Show Editions'}),{target:{value:'reviewed'}})
    expect(screen.getByText('Cup finished')).toBeVisible()
    expect(screen.queryByText('Cup unfinished')).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox',{name:'Show Editions'}),{target:{value:'unfinished'}})
    expect(screen.queryByText('Cup finished')).not.toBeInTheDocument()
    expect(screen.getByText('Cup unfinished')).toBeVisible()
  })
  it('supports Czech descriptions without inventing a valid permission or Save',()=>{
    localStorage.setItem('squash-engine-language-v1','cs')
    mount(view([edition('first',40)],false))
    expect(screen.getByRole('region',{name:'Fronta operátora Tour'})).toBeVisible()
    expect(screen.getByText(/není to kontrola způsobilosti/)).toBeVisible()
    expect(screen.getByRole('link',{name:'Přejít k ovládání Edition'}))
      .toHaveAttribute('href','#native-tour-edition-0')
    expect(screen.getByRole('searchbox',{name:'Hledat Edition'})).toBeInTheDocument()
  })
  it('fails closed on a foreign Run or invalid duplicate IDs instead of showing guessed items',()=>{
    const v=view([edition('same',40),edition('same',50)])
    mount(v)
    expect(screen.getByRole('alert')).toHaveTextContent(/duplicate Edition/)
    expect(screen.queryByRole('link',{name:'Go to Edition controls'})).not.toBeInTheDocument()
  })
  it('does not treat an empty source list as completed 80-Edition readiness',()=>{
    mount(view([]))
    expect(screen.getByText('No Editions are present in this Tour yet.')).toBeVisible()
    expect(screen.queryByRole('link',{name:'Go to Edition controls'})).not.toBeInTheDocument()
  })
})

import {act,fireEvent,render,screen} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {CalendarTourPanel} from './CalendarTourPanel'
import type {TourCommand,TourPreview,TourView} from '../api/calendarTour'

const api=vi.hoisted(()=>({inspectCalendarTour:vi.fn(),previewCalendarTour:vi.fn(),executeCalendarTour:vi.fn(),saveCalendarTour:vi.fn(),replayCalendarContinuation:vi.fn()}))
vi.mock('../api/client',()=>api)
const view=(run='r',branch='b'):TourView=>({schema_version:'calendar_tour_inspection.v1',run_id:run,branch_id:branch,saved_head_revision_id:'head',draft_version:1,checkpoint_fingerprint:'a'.repeat(64),tour_fingerprint:null,saved:false,can_initialize:true,players:[],transition_blockers:['tour_authority_missing'],edition_evidence:{},state:null})
const panel=(run='r',branch='b')=><QueryClientProvider client={new QueryClient()}><MemoryRouter><LanguageProvider><CalendarTourPanel runId={run} branchId={branch} head="head"/></LanguageProvider></MemoryRouter></QueryClientProvider>
const preview=(c:TourCommand):TourPreview=>({schema_version:'calendar_tour_command_preview.v1',run_id:'r',branch_id:'b',command:c,preview_fingerprint:'f'.repeat(64),impact:{}})

describe('configured Tour consent (HTTP boundary mocked)',()=>{
  beforeEach(()=>{vi.clearAllMocks();localStorage.setItem('squash-engine-language-v1','en');api.inspectCalendarTour.mockImplementation((r,b)=>Promise.resolve(view(r,b)))})
  it('requires separate explicit command consent and never saves automatically',async()=>{
    api.previewCalendarTour.mockImplementation((_r,_b,c)=>Promise.resolve(preview(c)))
    api.executeCalendarTour.mockResolvedValue({})
    render(panel());await screen.findByLabelText('Tour operation reason')
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'Reviewed native Tour'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Tour initialization'}))
    await screen.findByLabelText('Confirm Tour command')
    expect(screen.getByRole('button',{name:'Execute confirmed operation'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm Tour command'))
    fireEvent.click(screen.getByRole('button',{name:'Execute confirmed operation'}))
    await act(async()=>{})
    expect(api.executeCalendarTour).toHaveBeenCalledTimes(1)
    expect(api.saveCalendarTour).not.toHaveBeenCalled()
  })
  it('drops a delayed review after its decisive input changes',async()=>{
    let resolve!:(p:TourPreview)=>void,cmd!:TourCommand
    api.previewCalendarTour.mockImplementation((_r,_b,c)=>{cmd=c;return new Promise(r=>{resolve=r})})
    render(panel());await screen.findByLabelText('Tour operation reason')
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'First input'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Tour initialization'}))
    await act(async()=>{})
    fireEvent.change(screen.getByLabelText('Tour seed'),{target:{value:'232'}})
    await act(async()=>resolve(preview(cmd)))
    expect(screen.queryByLabelText('Confirm Tour command')).not.toBeInTheDocument()
    expect(api.executeCalendarTour).not.toHaveBeenCalled()
  })
  it('does not revive responses after switching Run A→B→A',async()=>{
    let resolve!:(v:TourView)=>void
    api.inspectCalendarTour.mockReturnValueOnce(new Promise(r=>{resolve=r})).mockImplementation((r,b)=>Promise.resolve(view(r,b)))
    const page=render(panel());page.rerender(panel('other'));page.rerender(panel())
    await screen.findByLabelText('Tour operation reason')
    await act(async()=>resolve({...view(),can_initialize:false}))
    fireEvent.change(screen.getByLabelText('Tour operation reason'),{target:{value:'Current input'}})
    expect(screen.getByRole('button',{name:'Review Tour initialization'})).toBeEnabled()
  })
})

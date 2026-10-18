import { act, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { CalendarContinuationPanel } from './CalendarContinuationPanel'
import type { ContinuationView } from '../api/calendarContinuation'
const api = vi.hoisted(() => ({ inspectCalendarContinuation: vi.fn(), simulateCalendarContinuation: vi.fn(),
  previewCalendarSportingWeek: vi.fn(), commitCalendarSportingWeek: vi.fn(), saveCalendarContinuation: vi.fn(), replayCalendarContinuation: vi.fn(), ApiError: class ApiError extends Error {} }))
vi.mock('../api/client', () => api)
const fp = 'a'.repeat(64)
const view = (head='head'): ContinuationView => ({ schema_version:'calendar_continuation_inspection.v1',
  run_id:'r', branch_id:'b', saved_head_revision_id:head, draft_version:2, checkpoint_fingerprint:fp,
  player_ids:['a','b','c'], saved:true, can_play:true, limited_player_ids:[], health_numeric_effect_applied:false, matches:[] })
const unsaved = (): ContinuationView => ({ ...view(), checkpoint_fingerprint:'b'.repeat(64), saved:false, can_play:false,
  matches:[{ match_id:'match', sequence:1, fingerprint:'c'.repeat(64), player_ids:['a','b'], winner_player_id:'a', rally_count:50, saved:false }] })
const client = new QueryClient()
const panel=(head='head')=><QueryClientProvider client={client}><LanguageProvider><CalendarContinuationPanel
  runId="r" branchId="b" head={head} onChange={()=>{}} /></LanguageProvider></QueryClientProvider>

describe('continuation interaction (HTTP boundary mocked)',()=>{
  beforeEach(()=>{vi.clearAllMocks();localStorage.setItem('squash-engine-language-v1','en')})
  it('requires consent and binds play to the inspected Saved checkpoint',async()=>{
    api.inspectCalendarContinuation.mockResolvedValueOnce(view()).mockResolvedValue(unsaved())
    api.simulateCalendarContinuation.mockResolvedValue({fingerprint:'c'.repeat(64),checkpoint_fingerprint:'b'.repeat(64),match:{
      source_saved_head:'head',source_checkpoint_fingerprint:fp,sequence:1,
      input_context:{player_a:{player:{player_id:'a'}},player_b:{player:{player_id:'b'}}},canonical_projections:[{long_term_fatigue:8},{long_term_fatigue:0}]}})
    render(panel()); await screen.findByLabelText('Continuation reason')
    expect(screen.getByRole('combobox', {name:'Continuation player A'})).toHaveAccessibleName('Continuation player A')
    expect(screen.getByRole('combobox', {name:'Continuation player B'})).toHaveAccessibleName('Continuation player B')
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Continue actual state'}})
    expect(screen.getByRole('button',{name:'Play continuation match'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm playing from this Saved checkpoint.'))
    fireEvent.click(screen.getByRole('button',{name:'Play continuation match'}))
    await screen.findByText('Consumed fatigue A / B: 8 / 0')
    expect(api.simulateCalendarContinuation).toHaveBeenCalledWith('r','b',expect.objectContaining({
      expected_saved_head:'head',expected_checkpoint_fingerprint:fp,player_a_id:'a',player_b_id:'b'}))
    expect(screen.getByRole('button',{name:'Play continuation match'})).toBeDisabled()
  })
  it('requires fresh Save review and separate confirmation',async()=>{
    api.inspectCalendarContinuation.mockResolvedValue(unsaved());api.saveCalendarContinuation.mockResolvedValue({})
    render(panel()); await screen.findByText('Played, awaiting manual Save.')
    fireEvent.click(screen.getByRole('button',{name:'Review continuation Save'}))
    await screen.findByRole('button',{name:'Save continued state'})
    expect(screen.getByRole('button',{name:'Save continued state'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm saving the continued state.'))
    fireEvent.click(screen.getByRole('button',{name:'Save continued state'}))
    await act(async()=>{})
    expect(api.saveCalendarContinuation).toHaveBeenCalledWith('r','b',2,'b'.repeat(64))
  })
  it('replays an event called save without interpreting its ID as a UI action',async()=>{
    const v=unsaved();v.matches[0].match_id='save'
    api.inspectCalendarContinuation.mockResolvedValue(v)
    api.replayCalendarContinuation.mockResolvedValue({match_id:'save',fingerprint:'c'.repeat(64),winner_player_id:'a',rally_count:50,exact_replay:true})
    render(panel());await screen.findByRole('button',{name:'Verify continuation replay'})
    fireEvent.click(screen.getByRole('button',{name:'Verify continuation replay'}))
    await screen.findByText('Exact replay verified.')
    expect(api.replayCalendarContinuation).toHaveBeenCalledWith('r','b','save')
    expect(api.saveCalendarContinuation).not.toHaveBeenCalled()
  })
  it('drops A→B→A responses and old Save consent',async()=>{
    let resolve!:(v:ContinuationView)=>void
    api.inspectCalendarContinuation.mockReturnValueOnce(new Promise(r=>{resolve=r})).mockImplementation((_r:string,_b:string)=>Promise.resolve({...unsaved(),saved_head_revision_id:'A'}))
    const mounted=render(panel('A'));mounted.rerender(panel('B'));mounted.rerender(panel('A'))
    await screen.findByText('Played, awaiting manual Save.')
    fireEvent.click(screen.getByRole('button',{name:'Review continuation Save'}));await screen.findByLabelText('Confirm saving the continued state.')
    fireEvent.click(screen.getByLabelText('Confirm saving the continued state.'))
    mounted.rerender(panel('B'))
    await act(async()=>{resolve(view('A'))})
    expect(api.saveCalendarContinuation).not.toHaveBeenCalled()
    expect(screen.queryByRole('button',{name:'Save continued state'})).not.toBeInTheDocument()
  })
  it('reviews a sporting week without mutation, requires separate consent and manual Save',async()=>{
    const w={calendar:{weeks_per_year:52,season_start_year_week:52,start_year:2030,season_count:3},season_index:0,week:1}
    const before={...view(),sporting_week:w,weekly_advance_count:0,weekly_advances:[]}
    const after={...before,sporting_week:{...w,week:2},checkpoint_fingerprint:'d'.repeat(64),saved:false,can_play:false,
      weekly_advance_count:1,weekly_advances:[{command_id:'advance',fingerprint:'e'.repeat(64),completed_week:1,target_week:2,saved:false}]}
    api.inspectCalendarContinuation.mockResolvedValueOnce(before).mockResolvedValue(after)
    api.previewCalendarSportingWeek.mockImplementation((_r,_b,c)=>Promise.resolve({schema_version:'calendar_sporting_week_preview.v1',
      preview_fingerprint:'f'.repeat(64),advance_fingerprint:'e'.repeat(64),checkpoint_fingerprint:'d'.repeat(64),
      player_count:3,changed_player_count:0,attribute_change_count:0,changes:[],advance:{run_id:'r',branch_id:'b',
        command_id:c.command_id,source_saved_head:'head',source_checkpoint_fingerprint:fp,completed_week:w,target_week:{...w,week:2},
        policy:{policy_id:'calendar-annual-development.provisional.v1'},scope:'sporting_only_exhibition_timeline'}}))
    api.commitCalendarSportingWeek.mockImplementation(async()=>api.previewCalendarSportingWeek.mock.results[0].value)
    render(panel());await screen.findByRole('button',{name:'Review sporting week preparation'})
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Prepare another sporting week'}})
    fireEvent.click(screen.getByRole('button',{name:'Review sporting week preparation'}))
    await screen.findByText('Changed players / attributes: 0 / 0')
    expect(api.commitCalendarSportingWeek).not.toHaveBeenCalled()
    expect(screen.getByRole('button',{name:'Prepare sporting week'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm this sporting-only weekly preparation.'))
    fireEvent.click(screen.getByRole('button',{name:'Prepare sporting week'}))
    await screen.findByText('Sporting preparation awaiting manual Save.')
    expect(api.commitCalendarSportingWeek).toHaveBeenCalledWith('r','b',expect.objectContaining({expected_saved_head:'head',expected_checkpoint_fingerprint:fp}),'f'.repeat(64))
    expect(api.saveCalendarContinuation).not.toHaveBeenCalled()
    expect(screen.getByRole('button',{name:'Play continuation match'})).toBeDisabled()
    expect(screen.getByRole('button',{name:'Review continuation Save'})).toBeEnabled()
  })
  it('clears weekly consent and preview when the reason changes',async()=>{
    const w={calendar:{weeks_per_year:52,season_start_year_week:1,start_year:2030,season_count:3},season_index:0,week:1}
    api.inspectCalendarContinuation.mockResolvedValue({...view(),sporting_week:w,weekly_advance_count:0,weekly_advances:[]})
    api.previewCalendarSportingWeek.mockImplementation((_r,_b,c)=>Promise.resolve({schema_version:'calendar_sporting_week_preview.v1',
      preview_fingerprint:'f'.repeat(64),advance_fingerprint:'e'.repeat(64),checkpoint_fingerprint:'d'.repeat(64),
      player_count:3,changed_player_count:0,attribute_change_count:0,changes:[],advance:{run_id:'r',branch_id:'b',command_id:c.command_id,
        source_saved_head:'head',source_checkpoint_fingerprint:fp,completed_week:w,target_week:{...w,week:2},
        policy:{policy_id:'calendar-annual-development.provisional.v1'},scope:'sporting_only_exhibition_timeline'}}))
    render(panel());await screen.findByLabelText('Continuation reason')
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'First'}})
    fireEvent.click(screen.getByRole('button',{name:'Review sporting week preparation'}))
    await screen.findByLabelText('Confirm this sporting-only weekly preparation.')
    fireEvent.click(screen.getByLabelText('Confirm this sporting-only weekly preparation.'))
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Changed'}})
    expect(screen.queryByRole('button',{name:'Prepare sporting week'})).not.toBeInTheDocument()
    expect(api.commitCalendarSportingWeek).not.toHaveBeenCalled()
  })

})

import { act, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { CalendarContinuationPanel } from './CalendarContinuationPanel'
import type { ContinuationView } from '../api/calendarContinuation'
const api = vi.hoisted(() => ({ inspectCalendarContinuation: vi.fn(), simulateCalendarContinuation: vi.fn(), simulateCalendarFollowupKnockout: vi.fn(), simulateCalendarScoredFollowupKnockout: vi.fn(), simulateCalendarEightFollowupKnockout: vi.fn(), simulateCalendarEightScoredFollowupKnockout: vi.fn(), closeNativeCalendarTournamentResult: vi.fn(),
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


  it('plays a real later-week four-person bracket from the exact Saved source and requires consent', async()=>{
    const w={calendar:{weeks_per_year:52,season_start_year_week:52,start_year:2030,season_count:3},season_index:0,week:2}
    const source:ContinuationView={...view(),player_ids:['a','b','c','d'],sporting_week:w,
      weekly_advance_count:1, weekly_advances:[{command_id:'advance',fingerprint:'e'.repeat(64),completed_week:1,target_week:2,saved:true}],tournaments:[]}
    let after:ContinuationView=source
    api.inspectCalendarContinuation.mockImplementationOnce(async()=>source).mockImplementation(async()=>after)
    api.simulateCalendarFollowupKnockout.mockImplementation(async(_r:string,_b:string,cmd:{
      command_id:string;tournament_id:string;expected_saved_head:string;expected_checkpoint_fingerprint:string;entrant_ids:string[]})=>{
      const ids=['sf1','sf2','final'].map(s=>cmd.tournament_id+':'+s)
      const stages=[
        {match_id:ids[0],sequence:1,result:{player_a_id:'a',player_b_id:'b',winner_player_id:'a'}},
        {match_id:ids[1],sequence:2,result:{player_a_id:'c',player_b_id:'d',winner_player_id:'c'}},
        {match_id:ids[2],sequence:3,result:{player_a_id:'a',player_b_id:'c',winner_player_id:'a'}},
      ]
      after={...source,saved:false,can_play:false,checkpoint_fingerprint:'b'.repeat(64),
        tournaments:[{tournament_id:cmd.tournament_id,command_id:cmd.command_id,
          fingerprint:'c'.repeat(64),week:2,entrant_ids:cmd.entrant_ids,
          winner_player_id:'a',match_ids:ids,saved:false,scope:'sporting_exhibition_knockout_not_official'}],
        matches:stages.map(m=>({match_id:m.match_id,sequence:m.sequence,
          fingerprint:'d'.repeat(64),player_ids:[m.result.player_a_id,m.result.player_b_id] as [string,string],
          winner_player_id:m.result.winner_player_id,rally_count:99,saved:false}))}
      return {schema_version:'calendar_followup_knockout_receipt.v1',fingerprint:'c'.repeat(64),
        checkpoint_fingerprint:'b'.repeat(64),winner_player_id:'a',official_ranking_published:false,
        scope:'sporting_exhibition_knockout_not_official',
        tournament:{run_id:'r',branch_id:'b',source_saved_head:'head',source_checkpoint_fingerprint:fp,
          command_id:cmd.command_id,tournament_id:cmd.tournament_id,entrant_ids:cmd.entrant_ids,matches:stages}}
    })
    render(panel());await screen.findByRole('button',{name:'Play next four-player knockout'})
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Actual next knockout'}})
    expect(screen.getByRole('button',{name:'Play next four-player knockout'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm playing all three matches from this Save.'))
    fireEvent.click(screen.getByRole('button',{name:'Play next four-player knockout'}))
    await screen.findByRole('table',{name:'Later-week knockout history'})
    expect(api.simulateCalendarFollowupKnockout).toHaveBeenCalledWith('r','b',expect.objectContaining({
      expected_saved_head:'head',expected_checkpoint_fingerprint:fp,entrant_ids:['a','b','c','d'],
    }))
    expect(screen.getAllByRole('button',{name:'Verify continuation replay'})).toHaveLength(3)
    expect(screen.getByRole('button',{name:'Review continuation Save'})).toBeEnabled()
  })


  it('requires independent prepared-point consent before a real scored knockout', async () => {
    const w={calendar:{weeks_per_year:52,season_start_year_week:52,start_year:2030,season_count:3},season_index:0,week:2}
    const source:ContinuationView={...view(),player_ids:['a','b','c','d'],sporting_week:w,
      weekly_advance_count:1,weekly_advances:[{command_id:'week',fingerprint:'e'.repeat(64),completed_week:1,target_week:2,saved:true}],tournaments:[]}
    let after:ContinuationView=source
    api.inspectCalendarContinuation.mockImplementationOnce(async()=>source).mockImplementation(async()=>after)
    api.simulateCalendarScoredFollowupKnockout.mockImplementation(async(_r:string,_b:string,cmd:{
      command_id:string;tournament_id:string;entrant_ids:string[]
      point_policy: { category_label:string; champion:number; finalist:number; semifinal:number; validity_weeks:number }})=>{
      const matchIds=['sf1','sf2','final'].map(s=>cmd.tournament_id+':'+s)
      const matches=[
        {match_id:matchIds[0],sequence:1,result:{player_a_id:'a',player_b_id:'b',winner_player_id:'a'}},
        {match_id:matchIds[1],sequence:2,result:{player_a_id:'c',player_b_id:'d',winner_player_id:'c'}},
        {match_id:matchIds[2],sequence:3,result:{player_a_id:'a',player_b_id:'c',winner_player_id:'a'}},
      ]
      const awards=([['a','champion',100],['b','semifinal',30],['c','finalist',60],['d','semifinal',30]] as const)
        .map(([player_id,reached_stage,main_points])=>({player_id,reached_stage,main_points,
          source_policy_fingerprint:'d'.repeat(64),source_tournament_fingerprint:'e'.repeat(64)}))
      after={...source,saved:false,can_play:false,checkpoint_fingerprint:'b'.repeat(64),
        tournaments:[{tournament_id:cmd.tournament_id,command_id:cmd.command_id, fingerprint:'c'.repeat(64),
          week:2,entrant_ids:cmd.entrant_ids,winner_player_id:'a',match_ids:matchIds,saved:false,
          scope:'sporting_exhibition_knockout_not_official',prepared_points_status:'prepared_not_official',
          prepared_policy:cmd.point_policy,prepared_awards:awards}],
        matches:matches.map(m=>({match_id:m.match_id,sequence:m.sequence,fingerprint:'a'.repeat(64),
          player_ids:[m.result.player_a_id,m.result.player_b_id] as [string,string],
          winner_player_id:m.result.winner_player_id,rally_count:99,saved:false}))}
      return {schema_version:'calendar_followup_knockout_receipt.v1',
        fingerprint:'c'.repeat(64),checkpoint_fingerprint:'b'.repeat(64),winner_player_id:'a',
        official_ranking_published:false,scope:'sporting_exhibition_knockout_not_official',
        publication_status:'prepared_not_official',prepared_policy_fingerprint:'d'.repeat(64),
        prepared_awards:awards,tournament:{run_id:'r',branch_id:'b',source_saved_head:'head',
          source_checkpoint_fingerprint:fp,command_id:cmd.command_id,tournament_id:cmd.tournament_id,
          entrant_ids:cmd.entrant_ids,matches},
      }
    })
    render(panel());await screen.findByRole('button',{name:'Play next four-player knockout'})
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Reviewed result points'}})
    fireEvent.click(screen.getByLabelText('Prepare point awards (NOT Official Ranking)'))
    expect(screen.getByRole('button',{name:'Play next four-player knockout'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm playing all three matches from this Save.'))
    expect(screen.getByRole('button',{name:'Play next four-player knockout'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Explicitly confirm prepared points only, not Official publication.'))
    fireEvent.click(screen.getByRole('button',{name:'Play next four-player knockout'}))
    await screen.findByText('a: 100 · b: 30 · c: 60 · d: 30')
    expect(api.simulateCalendarScoredFollowupKnockout).toHaveBeenCalledWith('r','b',expect.objectContaining({
      explicit_point_confirmation:true,
      point_policy:expect.objectContaining({champion:100,finalist:60,semifinal:30,validity_weeks:52}),
    }))
    expect(api.simulateCalendarFollowupKnockout).not.toHaveBeenCalled()
  })


  it('plays seven real eight-player matches only after explicit consent and requires manual Save', async()=>{
    const w={calendar:{weeks_per_year:52,season_start_year_week:52,start_year:2030,season_count:3},season_index:0,week:2}
    const source:ContinuationView={...view(),player_ids:['a','b','c','d','e','f','g','h'],sporting_week:w,
      weekly_advance_count:1,weekly_advances:[{command_id:'week',fingerprint:'e'.repeat(64),completed_week:1,target_week:2,saved:true}],
      tournaments:[]}
    let after:ContinuationView=source
    api.inspectCalendarContinuation.mockImplementationOnce(async()=>source).mockImplementation(async()=>after)
    api.simulateCalendarEightFollowupKnockout.mockImplementation(async(_run:string,_branch:string,cmd:{
      command_id:string;tournament_id:string;entrant_ids:string[]})=>{
      const rounds=[
        ['qf1','a','b','a'],['qf2','c','d','c'],['qf3','e','f','e'],['qf4','g','h','g'],
        ['sf1','a','c','a'],['sf2','e','g','e'],['final','a','e','a'],
      ]
      const matches=rounds.map(([stage,player_a_id,player_b_id,winner_player_id],i)=>({
        match_id:cmd.tournament_id+':'+stage,sequence:i+1,
        result:{player_a_id,player_b_id,winner_player_id},
      }))
      after={...source,saved:false,can_play:false,checkpoint_fingerprint:'b'.repeat(64),
        tournaments:[{tournament_id:cmd.tournament_id,command_id:cmd.command_id,
          fingerprint:'c'.repeat(64),week:2,entrant_ids:cmd.entrant_ids,entrant_count:8,match_count:7,
          winner_player_id:'a',match_ids:matches.map(m=>m.match_id),saved:false,
          scope:'sporting_exhibition_knockout_not_official'}],
        matches:matches.map(m=>({match_id:m.match_id,sequence:m.sequence,fingerprint:'d'.repeat(64),
          player_ids:[m.result.player_a_id,m.result.player_b_id] as [string,string],
          winner_player_id:m.result.winner_player_id,rally_count:80,saved:false}))}
      return {schema_version:'calendar_followup_knockout_receipt.v1',fingerprint:'c'.repeat(64),
        checkpoint_fingerprint:'b'.repeat(64),winner_player_id:'a',official_ranking_published:false,
        scope:'sporting_exhibition_knockout_not_official',
        tournament:{schema_version:'calendar_followup_knockout.v3',
          run_id:'r',branch_id:'b',source_saved_head:'head',source_checkpoint_fingerprint:fp,
          command_id:cmd.command_id,tournament_id:cmd.tournament_id,entrant_ids:cmd.entrant_ids,matches}}
    })
    render(panel());await screen.findByRole('button',{name:'Play eight-player knockout'})
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Seven real matches'}})
    expect(screen.getByRole('button',{name:'Play eight-player knockout'})).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm all seven real matches from the current Saved checkpoint.'))
    fireEvent.click(screen.getByRole('button',{name:'Play eight-player knockout'}))
    await screen.findByRole('table',{name:'Later-week knockout history'})
    expect(api.simulateCalendarEightFollowupKnockout).toHaveBeenCalledWith('r','b',expect.objectContaining({
      expected_saved_head:'head',expected_checkpoint_fingerprint:fp,
      entrant_ids:['a','b','c','d','e','f','g','h'],
    }))
    expect(screen.getAllByRole('button',{name:'Verify continuation replay'})).toHaveLength(7)
    expect(screen.getByRole('button',{name:'Review continuation Save'})).toBeEnabled()
  })

  it('requires a second, invalidated consent for eight-person point awards', async () => {
    const w={calendar:{weeks_per_year:80,season_start_year_week:80,start_year:2030,season_count:3},season_index:0,week:2}
    api.inspectCalendarContinuation.mockResolvedValue({...view(),
      player_ids:['a','b','c','d','e','f','g','h'],sporting_week:w,weekly_advance_count:1,
      weekly_advances:[{command_id:'w2',fingerprint:'b'.repeat(64),completed_week:1,target_week:2,saved:true}],
      tournaments:[],
    })
    render(panel());await screen.findByRole('button',{name:'Play eight-player knockout'})
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Reviewed eight-player prepared awards'}})
    fireEvent.click(screen.getByLabelText('Prepare eight-player points (NOT Official Ranking)'))
    fireEvent.click(screen.getByLabelText('Confirm all seven real matches from the current Saved checkpoint.'))
    const scoredButton=screen.getByRole('button',{name:'Play eight-player prepared-points knockout'})
    expect(scoredButton).toBeDisabled()
    expect(screen.getByLabelText('Quarterfinalist')).toHaveValue(15)
    fireEvent.click(screen.getByLabelText('Confirm eight-player prepared awards, NOT Official publication.'))
    expect(scoredButton).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Quarterfinalist'),{target:{value:'40'}})
    expect(screen.getByLabelText('Confirm eight-player prepared awards, NOT Official publication.')).not.toBeChecked()
    expect(scoredButton).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Quarterfinalist'),{target:{value:'15'}})
    fireEvent.click(screen.getByLabelText('Confirm all seven real matches from the current Saved checkpoint.'))
    fireEvent.click(screen.getByLabelText('Confirm eight-player prepared awards, NOT Official publication.'))
    expect(scoredButton).toBeEnabled()
    expect(api.simulateCalendarEightScoredFollowupKnockout).not.toHaveBeenCalled()
  })

  it('requires fresh closure consent, closes the Saved result and leaves its Save explicit', async () => {
    const rounds = [
      ['qf1','a','b','a'], ['qf2','c','d','c'], ['qf3','e','f','e'], ['qf4','g','h','g'],
      ['sf1','a','c','a'], ['sf2','e','g','e'], ['final','a','e','a'],
    ] as const
    const matches = rounds.map(([id,a,b,winner],i) => ({
      match_id: 'draw:'+id, sequence: i+1, fingerprint: 'b'.repeat(64),
      player_ids: [a,b] as [string,string], winner_player_id: winner, rally_count: 50, saved: true,
    }))
    const stages = ['champion','quarterfinal','semifinal','quarterfinal','finalist','quarterfinal','semifinal','quarterfinal'] as const
    const players = ['a','b','c','d','e','f','g','h'].map((player_id,i) => ({
      player_id, reached_stage: stages[i],
      played_match_ids: matches.filter(m => m.player_ids.includes(player_id)).map(m => m.match_id),
      wins: matches.filter(m => m.winner_player_id === player_id).length,
      losses: player_id === 'a' ? 0 : 1,
      prepared_points: ({champion:100,finalist:60,semifinal:30,quarterfinal:15})[stages[i]],
    }))
    const source: ContinuationView = {...view(), player_ids: players.map(p => p.player_id), matches,
      sporting_week: {calendar:{weeks_per_year:52,season_start_year_week:52,start_year:2030,season_count:3},season_index:0,week:2},
      weekly_advance_count:1, weekly_advances:[{command_id:'week',fingerprint:'e'.repeat(64),completed_week:1,target_week:2,saved:true}],
      tournaments:[{tournament_id:'draw',command_id:'play-draw',fingerprint:'c'.repeat(64),week:2,
        entrant_ids:players.map(p => p.player_id),winner_player_id:'a',match_ids:matches.map(m => m.match_id),saved:true,
        scope:'sporting_exhibition_knockout_not_official',prepared_points_status:'prepared_not_official',
        prepared_policy:{category_label:'Prepared only',champion:100,finalist:60,semifinal:30,quarterfinal:15,validity_weeks:52},
        prepared_awards:players.map(p => ({player_id:p.player_id,reached_stage:p.reached_stage,main_points:p.prepared_points,
          source_policy_fingerprint:'d'.repeat(64),source_tournament_fingerprint:'e'.repeat(64)})),
        result_closed:false,result_closure_saved:false}],closures:[],
    }
    let after = source
    api.inspectCalendarContinuation.mockImplementation(async () => after)
    api.closeNativeCalendarTournamentResult.mockImplementation(async (_r,_b,command) => {
      const closure = {command_id:command.command_id,tournament_id:'draw',fingerprint:'f'.repeat(64),
        source_tournament_fingerprint:'c'.repeat(64),champion_player_id:'a',finalist_player_id:'e',
        scope:'played_native_result_closed_not_official' as const,saved:false,players}
      after = {...source,saved:false,can_play:false,checkpoint_fingerprint:'1'.repeat(64),
        tournaments:source.tournaments!.map(t => ({...t,result_closed:true})),closures:[closure]}
      return {schema_version:'calendar_native_tournament_closure_receipt.v1',
        fingerprint:closure.fingerprint,checkpoint_fingerprint:after.checkpoint_fingerprint,
        official_ranking_published:false,publication_status:'native_result_closed_not_official',
        closure:{...closure,source_saved_head:command.expected_saved_head,
          source_checkpoint_fingerprint:command.expected_checkpoint_fingerprint,
          source_week_event_count:2,source_prepared_awards_fingerprint:'2'.repeat(64),request_fingerprint:'3'.repeat(64)}}
    })
    render(panel()); await screen.findByRole('button',{name:'Close native tournament result'})
    const button = screen.getByRole('button',{name:'Close native tournament result'})
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Review seven actual results'}})
    expect(button).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm closing actual played results, NOT Official publication.'))
    expect(button).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Continuation reason'),{target:{value:'Changed review'}})
    expect(button).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm closing actual played results, NOT Official publication.'))
    fireEvent.click(button)
    await screen.findByRole('table',{name:'Closed tournament results'})
    expect(api.closeNativeCalendarTournamentResult).toHaveBeenCalledWith('r','b',expect.objectContaining({
      expected_saved_head:'head',expected_checkpoint_fingerprint:fp,tournament_id:'draw',
      explicit_result_confirmation:true,audit_reason:'Changed review',
    }))
    expect(api.saveCalendarContinuation).not.toHaveBeenCalled()
    expect(screen.getByRole('button',{name:'Review continuation Save'})).toBeEnabled()
    expect(screen.queryByRole('button',{name:'Close native tournament result'})).not.toBeInTheDocument()
  })
})

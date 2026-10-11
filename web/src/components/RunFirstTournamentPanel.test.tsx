import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RunBranch, RunContainer } from '../api/types'
import {
  firstRunCalendarWeek, isRunCalendarProjection, runCalendarPackageIds
} from '../api/runFirstTournament'
import { RunFirstTournamentPanel } from './RunFirstTournamentPanel'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunPackageState: vi.fn(), getRunOwnedCalendar: vi.fn(),
  getBranchWorkingDraft: vi.fn(),
  getCanonicalTournamentPreparation: vi.fn()
}))
vi.mock('../api/client', () => api)

const sha = (x: string) => x.repeat(64)
const run: RunContainer = {
  run_id:'prod-run', display_name:'Product Run', storage_kind:'custom_local',
  status:'working', read_only:false, timeline_start_season:2000, timeline_end_season:2049,
  world_id:null, world_package_fingerprint:null, config_version:null,
  config_fingerprint:null, global_seed:null, official_branch_id:'timeline-a',
  metadata_json:{}, mapped_simulation_run_count:0
}
const branch: RunBranch = {
  branch_id:'timeline-a', run_id:'prod-run', display_name:'Timeline 1',
  status:'active', read_only:false, saved_head_revision_id:'rev-1',
  branch_seed:null, forked_from_branch_id:null, forked_from_checkpoint_id:null,
  head_checkpoint_id:null, legacy_simulation_run_id:null, metadata_json:{},
  is_official:true
}
const events = [
  {event_id:'later',season:'2000/2001',season_week:5,event_name:'Later',
    template_id:'tpl-l',category:'GOLD',tour_level:'WORLD',host_country:'CZE',
    main_draw_size:16,qualification_draw_size:0},
  {event_id:'week1-b',season:'2000/2001',season_week:1,event_name:'Open B',
    template_id:'tpl-b',category:'SILVER',tour_level:'WORLD',host_country:'SVK',
    main_draw_size:8,qualification_draw_size:0},
  {event_id:'week1-a',season:'2000/2001',season_week:1,event_name:'Open A',
    template_id:'tpl-a',category:'SILVER',tour_level:'WORLD',host_country:'CZE',
    main_draw_size:8,qualification_draw_size:0}
]
const calendar = {
  run_id:'prod-run',branch_id:'timeline-a',package_id:'calendar-2000-2001',
  season:'2000/2001',run_package_state_fingerprint:sha('a'),
  content_fingerprint:sha('b'),fingerprint:sha('c'),
  calendar: {season:'2000/2001',events,validation_errors:[]}
}

beforeEach(() => {
  vi.clearAllMocks()
  api.getRunPackageState.mockResolvedValue({
    state:{run_id:'prod-run',branch_id:'timeline-a',package_versions:[
      {package_id:'fifa_earth',package_type:'World'},
      {package_id:'calendar-2000-2001',package_type:'Calendar'}
    ]},fingerprint:sha('a')
  })
  api.getRunOwnedCalendar.mockResolvedValue(calendar)
  api.getBranchWorkingDraft.mockResolvedValue({run_id:'prod-run',branch_id:'timeline-a',base_saved_revision_id:'rev-1',status:'clean',draft_version:0})
  api.getCanonicalTournamentPreparation.mockImplementation(async (_r:string,_b:string,eventId:string) => ({
    schema_version:'canonical_tournament_preparation_state.v1',
    run_id:'prod-run',branch_id:'timeline-a',event_id:eventId,
    phase:'ranking_snapshot_required',next_required_action:'adopt_ranking_snapshot',
    blockers:['tournament_ranking_snapshot_authority_required'],
    authority_source:'run_owned_db_authorities.v1',
    ready_for_match_schedule:false,effective_draw_fingerprint:null
  }))
})
const show=(runData=run,branchData:RunBranch|null=branch)=>
  renderWithRoute(<RunFirstTournamentPanel run={runData} branch={branchData} />, '/admin/runs/prod-run')

describe('First canonical tournament from Run-owned Calendar', () => {
  it('discovers actual earliest Week events, checks DB preparation and offers scoped handoff', async () => {
    show()
    expect(await screen.findByText('First scheduled week: 1')).toBeInTheDocument()
    expect(api.getRunOwnedCalendar).toHaveBeenCalledWith('prod-run','timeline-a','calendar-2000-2001')
    const select=screen.getByRole('combobox',{name:'First scheduled tournament'})
    expect(select).toHaveValue('week1-a')
    expect(screen.queryByRole('option',{name:/Later/})).not.toBeInTheDocument()
    expect(await screen.findByText(/ranking_snapshot_required/)).toBeInTheDocument()
    const link=screen.getByRole('link',{name:'Open first Run-owned tournament preparation'})
    expect(link).toHaveAttribute('href','/admin/runs/prod-run/calendar/week1-a?branch=timeline-a&calendar=calendar-2000-2001')
    await userEvent.selectOptions(select,'week1-b')
    await waitFor(()=>expect(api.getCanonicalTournamentPreparation).toHaveBeenCalledWith('prod-run','timeline-a','week1-b'))
  })

  it('does not offer a handoff for a stale Package fingerprint or crossed Branch', async () => {
    api.getRunOwnedCalendar.mockResolvedValueOnce({...calendar,run_package_state_fingerprint:sha('d')})
    show()
    expect(await screen.findByText(/Package fingerprint could not be verified/)).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Open first Run-owned tournament preparation'})).not.toBeInTheDocument()
    expect(api.getCanonicalTournamentPreparation).not.toHaveBeenCalled()
  })

  it('refuses a protected selected Branch before any Package read', async () => {
    show(run,{...branch,read_only:true})
    expect(screen.getByText(/writable Active Admin Branch/)).toBeInTheDocument()
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })

  it('blocks tournament handoff if Package changes are not saved in the Branch', async () => {
    api.getBranchWorkingDraft.mockResolvedValueOnce({
      run_id:'prod-run',branch_id:'timeline-a',base_saved_revision_id:'rev-1',
      status:'dirty',draft_version:1
    })
    show()
    expect(await screen.findByText(/Save the current Working Draft before preparing/)).toBeInTheDocument()
    expect(api.getRunOwnedCalendar).not.toHaveBeenCalled()
    expect(api.getCanonicalTournamentPreparation).not.toHaveBeenCalled()
  })

  it('fails closed for foreign and duplicated Calendar events', () => {
    expect(firstRunCalendarWeek(events).map(e=>e.event_id)).toEqual(['week1-a','week1-b'])
    expect(runCalendarPackageIds({package_versions:[{package_type:'World',package_id:'w'},{package_type:'Calendar',package_id:'cal'}]})).toEqual(['cal'])
    expect(isRunCalendarProjection(calendar,'prod-run','timeline-a','calendar-2000-2001')).toBe(true)
    expect(isRunCalendarProjection({...calendar,branch_id:'other'},'prod-run','timeline-a','calendar-2000-2001')).toBe(false)
    expect(isRunCalendarProjection({...calendar,calendar:{...calendar.calendar,events:[events[0],events[0]]}},'prod-run','timeline-a','calendar-2000-2001')).toBe(false)
  })
})

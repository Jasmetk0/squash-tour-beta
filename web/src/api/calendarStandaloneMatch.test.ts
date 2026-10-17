import { describe, expect, it } from 'vitest'
import { validateCalendarMatchView } from './calendarStandaloneMatch'

const clock = { schema_version: 'run_calendar.v1', weeks_per_year: 52, season_start_year_week: 1, start_year: 2030, season_count: 3 }
const valid = {
  schema_version: 'calendar_standalone_match_inspection.v1',
  run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'head',
  draft_version: 2, initial_world_fingerprint: 'a'.repeat(64),
  run_calendar: clock, player_ids: ['a', 'b'], match: null, match_fingerprint: null, saved: false,
}

describe('calendar standalone match Run/Branch/HEAD response', () => {
  it('accepts a real empty verified W52 match surface', () => {
    expect(validateCalendarMatchView(valid, 'run', 'branch', 'head')).toEqual(valid)
  })
  it('rejects stale HEAD and cross-Branch or Run results', () => {
    expect(() => validateCalendarMatchView(valid, 'run', 'branch', 'other')).toThrow()
    expect(() => validateCalendarMatchView(valid, 'another-run', 'branch', 'head')).toThrow()
    expect(() => validateCalendarMatchView(valid, 'run', 'other', 'head')).toThrow()
  })
  it('rejects duplicate players, missing hash and fake Saved claims', () => {
    expect(() => validateCalendarMatchView({...valid, player_ids: ['a','a']}, 'run','branch','head')).toThrow()
    expect(() => validateCalendarMatchView({...valid, initial_world_fingerprint: 'bad'}, 'run','branch','head')).toThrow()
    expect(() => validateCalendarMatchView({...valid, saved: true}, 'run','branch','head')).toThrow()
  })
  it('recognizes a scoped completed W80 match but rejects incorrect calendar', () => {
    const w80 = {...clock, weeks_per_year: 80}
    const match = {
      schema_version: 'calendar_standalone_match.v1', run_id: 'run', branch_id: 'branch',
      match_id: 'opening', command_id: 'play',
      week: {calendar:w80,season_index:0,week:1},
      result: {winner_player_id:'a',loser_player_id:'b',sets_won:{a:3,b:2},sets:[],
        rally_log:{events:[{rally_index:1}]}},
    }
    const view = {...valid,run_calendar:w80,match,match_fingerprint:'b'.repeat(64),saved:true}
    expect(validateCalendarMatchView(view,'run','branch','head')).toEqual(view)
    expect(() => validateCalendarMatchView({...view,run_calendar:clock},'run','branch','head')).toThrow()
  })
})

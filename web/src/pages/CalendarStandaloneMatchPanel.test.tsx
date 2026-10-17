import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { CalendarStandaloneMatchPanel } from './CalendarStandaloneMatchPanel'

const api = vi.hoisted(() => ({
  inspectCalendarStandaloneMatch: vi.fn(),
  simulateCalendarStandaloneMatch: vi.fn(),
  replayCalendarStandaloneMatch: vi.fn(),
  previewCalendarStandaloneMatchSave: vi.fn(),
  saveCalendarStandaloneMatch: vi.fn(),
}))
vi.mock('../api/client', () => api)

const calendar = {
  schema_version: 'run_calendar.v1', weeks_per_year: 52,
  season_start_year_week: 1, start_year: 2030, season_count: 3,
}
const empty = {
  schema_version: 'calendar_standalone_match_inspection.v1',
  run_id: 'r', branch_id: 'b', run_calendar: calendar,
  saved_head_revision_id: 'original-head', draft_version: 2,
  initial_world_fingerprint: 'a'.repeat(64), player_ids: ['player-a', 'player-b'],
  match: null, match_fingerprint: null, saved: false,
}
const match = {
  schema_version: 'calendar_standalone_match.v1', run_id: 'r', branch_id: 'b',
  match_id: 'calendar-opening-exhibition', command_id: 'play',
  week: { calendar, season_index: 0, week: 1 },
  result: { winner_player_id: 'player-a', loser_player_id: 'player-b',
    sets_won: { 'player-a': 3, 'player-b': 1 },
    rally_log: {events: [{rally_index: 1}]},
    sets: [],
  },
}
const played = {...empty,match,match_fingerprint:'b'.repeat(64)}
function mount(head = 'original-head') {
  const client = new QueryClient({defaultOptions:{queries:{retry:false}}})
  return {
    client,
    ...render(<QueryClientProvider client={client}>
      <LanguageProvider><CalendarStandaloneMatchPanel runId="r" branchId="b" savedHead={head} /></LanguageProvider>
    </QueryClientProvider>),
  }
}

describe('Run-calendar MatchEngine Admin CS/EN and immutable Save', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('squash-engine-language-v1', 'cs')
    api.inspectCalendarStandaloneMatch.mockResolvedValue(empty)
  })

  it('requires two different Saved players, an audit reason and explicit match consent', async () => {
    mount()
    expect(await screen.findByRole('heading', {name:'První skutečný zápas podle Run kalendáře'})).toBeInTheDocument()
    await screen.findByRole('button', {name:'Odehrát zápas'})
    const action = screen.getByRole('button', {name:'Odehrát zápas'})
    expect(action).toBeDisabled()
    const selectors = screen.getAllByRole('combobox')
    fireEvent.change(selectors[1], {target:{value:'player-a'}})
    fireEvent.change(screen.getByLabelText('Důvod zásahu'), {target:{value:'Real match'}})
    fireEvent.click(screen.getByLabelText('Potvrzuji odehrání zápasu.'))
    expect(action).toBeDisabled()
    fireEvent.change(selectors[1], {target:{value:'player-b'}})
    expect(action).toBeDisabled() // confirmation is intentionally cleared on changed participants
    fireEvent.click(screen.getByLabelText('Potvrzuji odehrání zápasu.'))
    expect(action).toBeEnabled()
    expect(api.simulateCalendarStandaloneMatch).not.toHaveBeenCalled()
  })

  it('plays the real result then requires a separately reviewed manual Save', async () => {
    api.simulateCalendarStandaloneMatch.mockResolvedValue({match,fingerprint:'b'.repeat(64)})
    api.inspectCalendarStandaloneMatch.mockResolvedValueOnce(empty).mockResolvedValue(played)
    api.previewCalendarStandaloneMatchSave.mockResolvedValue({
      run_id:'r',branch_id:'b',calendar_match_fingerprint:'b'.repeat(64),
      saved_head_revision_id:'original-head',draft_version:2,
      has_unsaved_changes:true,can_save:true,
    })
    api.saveCalendarStandaloneMatch.mockResolvedValue({saved_revision:{revision_id:'new-head'}})
    api.replayCalendarStandaloneMatch.mockResolvedValue({
      match_id:'calendar-opening-exhibition',fingerprint:'b'.repeat(64),
      exact_replay:true,rally_count:1,result:match.result,
    })
    mount()
    await screen.findByRole('button',{name:'Odehrát zápas'})
    fireEvent.change(screen.getByLabelText('Důvod zásahu'),{target:{value:'Reviewed Admin exhibition'}})
    fireEvent.click(screen.getByLabelText('Potvrzuji odehrání zápasu.'))
    fireEvent.click(screen.getByRole('button',{name:'Odehrát zápas'}))
    expect(await screen.findByText(/Neuložený výsledek/)).toBeInTheDocument()
    expect(api.simulateCalendarStandaloneMatch).toHaveBeenCalledWith('r','b',
      expect.objectContaining({
        expected_saved_head:'original-head',
        expected_initial_world_fingerprint:'a'.repeat(64),
        player_a_id:'player-a',player_b_id:'player-b',
        audit_reason:'Reviewed Admin exhibition',
      }))
    fireEvent.click(screen.getByRole('button',{name:'Ověřit přesný replay'}))
    expect(await screen.findByText(/Ověřený replay/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Zkontrolovat ruční Save'}))
    const save = await screen.findByRole('button',{name:'Uložit revizi'})
    expect(save).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Potvrzuji nový Save.'))
    fireEvent.click(save)
    await waitFor(() => expect(api.saveCalendarStandaloneMatch)
      .toHaveBeenCalledWith('r','b',2,'b'.repeat(64)))
  })

  it('has an English real-match entry point without an implicit legacy tournament claim', async () => {
    localStorage.setItem('squash-engine-language-v1','en')
    mount()
    expect(await screen.findByRole('heading',{name:'First real Run-calendar match'})).toBeInTheDocument()
    expect(screen.getByText(/no tournament points, week transition/i)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Play match'})).toBeDisabled()
  })
})

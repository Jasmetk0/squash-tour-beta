import { screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedPlayerMatchesPanel } from './SavedPlayerMatchesPanel'

const api = vi.hoisted(() => ({
  getSavedPlayerMatchHistory: vi.fn(), getSavedHomePlayerIdentities: vi.fn(),
}))
vi.mock('../api/client', () => api)

function mount(entry = '/') {
  let locale:'cs'|'en'='cs'
  const client=new QueryClient({ defaultOptions: {queries:{retry:false,gcTime:0}} })
  const ui=()=> <QueryClientProvider client={client}><MemoryRouter initialEntries={[entry]}><SavedPlayerMatchesPanel
    runId="run" branchId="branch" playerId="A" savedHead="revision"
    locale={locale}
  /></MemoryRouter></QueryClientProvider>
  const view=render(ui())
  return {...view,changeLocale:(next:'cs'|'en')=>{locale=next;view.rerender(ui())}}
}

describe('Saved player match history', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r: string, _b: string, ids: string[]) => ({
      run_id: 'run', branch_id: 'branch', saved_revision_id: 'revision', source: 'selected_branch_saved_revision', requested_ids: ids,
      players: ids.map(id => ({ player_id: id, display_name: 'Opponent '+id }))
    }))
    api.getSavedPlayerMatchHistory.mockImplementation(async (_r: string, _b: string, _id: string,
      season: number | null, offset: number, limit: number) => ({
      schema_version: 'saved_player_match_history.v1',
      run_id: 'run', branch_id: 'branch', saved_revision_id: 'revision', player_id: 'A',
      source: 'selected_branch_saved_revision', status: 'ready',
      season_index: season, offset, limit,
      available_seasons: [2], total_results: season === 0 ? 0 : 1,
      played_wins: season === 0 ? 0 : 1, played_losses: 0, walkovers: 0,
      career_played_wins: 1, career_played_losses: 0, career_walkovers: 0,
      has_more: false, matches: season === 0 ? [] : [{
        event_id: 'event', event_name: 'Championship', match_id: 'match',
        season_index: 2, season: '2002/03', week: 17, draw_type: 'main',
        round_number: 2, opponent_player_id: 'B', outcome: 'win',
        completion: 'played', scoreline: '3-2'
      }],
    }))
  })
  it('renders saved opponents, filtered season and actual scoreline', async () => {
    mount()
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/Opponent B/)).toBeInTheDocument())
    expect(screen.getByText(/3-2/)).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Sezóna zápasů' }), { target: { value: '2' } })
    await waitFor(() => expect(api.getSavedPlayerMatchHistory).toHaveBeenLastCalledWith(
      'run', 'branch', 'A', 2, 0, 20,
    ))
  })
  it('preserves the season selection and does not refetch on CS/EN change',async()=>{
    const view=mount()
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox',{name:'Sezóna zápasů'}),{target:{value:'2'}})
    await waitFor(()=>expect(api.getSavedPlayerMatchHistory).toHaveBeenLastCalledWith(
      'run','branch','A',2,0,20))
    const calls=api.getSavedPlayerMatchHistory.mock.calls.length
    view.changeLocale('en')
    expect(screen.getByRole('combobox',{name:'Match season'})).toHaveValue('2')
    expect(api.getSavedPlayerMatchHistory).toHaveBeenCalledTimes(calls)
  })
  it('keeps career season and page in the match URL for an exact profile return', async () => {
    api.getSavedPlayerMatchHistory.mockImplementation(async (_r: string, _b: string, _id: string,
      season: number | null, offset: number, limit: number) => ({
      schema_version: 'saved_player_match_history.v1',
      run_id: 'run', branch_id: 'branch', saved_revision_id: 'revision', player_id: 'A',
      source: 'selected_branch_saved_revision', status: 'ready',
      season_index: season, offset, limit, available_seasons: [2], total_results: 21,
      played_wins: 21, played_losses: 0, walkovers: 0,
      career_played_wins: 21, career_played_losses: 0, career_walkovers: 0,
      has_more: offset === 0,
      matches: [{ event_id: 'event', event_name: 'Championship',
        match_id: offset === 0 ? 'first' : 'second', season_index: 2, season: '2002/03',
        week: 17, draw_type: 'main', round_number: 2, opponent_player_id: 'B',
        outcome: 'win', completion: 'played', scoreline: '3-2' }],
    }))
    mount()
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', {name: 'Sezóna zápasů'}), {target: {value: '2'}})
    await waitFor(() => expect(api.getSavedPlayerMatchHistory).toHaveBeenLastCalledWith(
      'run', 'branch', 'A', 2, 0, 20))
    await waitFor(() => expect(screen.getByRole('link', {name: 'Detail zápasu →'})).toHaveAttribute('href',
      '/admin/runs/run/people/A/matches/event/first?tab=career&replayBranch=branch&replayHead=revision&careerSeason=2'))
    fireEvent.click(screen.getByRole('button', {name: 'Další →'}))
    await waitFor(() => expect(api.getSavedPlayerMatchHistory).toHaveBeenLastCalledWith(
      'run', 'branch', 'A', 2, 20, 20))
    await waitFor(() => expect(screen.getByRole('link', {name: 'Detail zápasu →'})).toHaveAttribute('href',
      '/admin/runs/run/people/A/matches/event/second?tab=career&replayBranch=branch&replayHead=revision&careerSeason=2&careerPage=1'))
  })
  it('does not render foreign saved HEAD data', async () => {
    api.getSavedPlayerMatchHistory.mockResolvedValueOnce({
      schema_version: 'saved_player_match_history.v1', run_id: 'run', branch_id: 'branch',
      saved_revision_id: 'foreign', player_id: 'A', source: 'selected_branch_saved_revision',
      status: 'ready', season_index: null, offset: 0, limit: 20,
      available_seasons: [], total_results: 1, played_wins: 1, played_losses: 0,
      walkovers: 0, career_played_wins: 1, career_played_losses: 0,
      career_walkovers: 0, has_more: false, matches: [],
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Data patří jiné uložené revizi.')
    expect(screen.queryByText('Championship')).not.toBeInTheDocument()
  })
  it('recovers an error without accepting cached career results',async()=>{
    api.getSavedPlayerMatchHistory.mockRejectedValueOnce(new Error('offline'))
    mount()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByText('Championship')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Obnovit kariéru'}))
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    expect(api.getSavedPlayerMatchHistory).toHaveBeenCalledTimes(2)
  })
  it('falls back to verified raw opponent ID when name lookup belongs to another revision',async()=>{
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r:string,_b:string,ids:string[])=>({
      run_id:'run',branch_id:'branch',saved_revision_id:'foreign',requested_ids:ids,
      players:ids.map(id=>({player_id:id,display_name:'WRONG'}))
    }))
    mount()
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    expect(await screen.findByText(/B · 3-2/)).toBeInTheDocument()
    expect(screen.queryByText('WRONG')).not.toBeInTheDocument()
  })

})

describe('career navigation and filtering (mocked API, not browser acceptance)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r:string,_b:string, ids:string[]) => ({
      run_id:'run', branch_id:'branch',saved_revision_id:'revision',
      source:'selected_branch_saved_revision',requested_ids:ids,
      players:ids.map(id=>({player_id:id, display_name:'Verified '+id})),
    }))
    api.getSavedPlayerMatchHistory.mockImplementation(async (_r:string,_b:string,_p:string,
      season:number|null, offset:number,limit:number) => ({
      schema_version:'saved_player_match_history.v1',source:'selected_branch_saved_revision',
      run_id:'run',branch_id:'branch',saved_revision_id:'revision',player_id:'A',
      status:'ready',season_index:season,offset,limit,available_seasons:[2],
      total_results:21,played_wins:20,played_losses:1,walkovers:1,
      career_played_wins:20,career_played_losses:1,career_walkovers:1,
      has_more:offset===0,
      matches:offset>=21?[]:[{
        event_id:'EV',event_name:'Brno Championship',match_id:offset?'later':'M12',
        season_index:2,season:'2002/03',week:17,draw_type:'main',round_number:2,
        opponent_player_id:'B',outcome:offset?'loss':'win',completion:offset?'walkover':'played',
        scoreline:offset?'W/O':'3-2',
      }],
    }))
  })
  it('rejects malformed URL before any read, and recovers', async () => {
    mount('/?tab=career&careerSeason=050&careerPage=999999')
    expect(screen.getByRole('alert')).toHaveTextContent('Neplatná sezona')
    expect(api.getSavedPlayerMatchHistory).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Platný výběr'}))
    expect(await screen.findByText('Brno Championship')).toBeInTheDocument()
    expect(api.getSavedPlayerMatchHistory).toHaveBeenCalledWith('run','branch','A',null,0,20)
  })
  it('recovers a nonexistent high page without page 1/0 or stale rows', async () => {
    mount('/?tab=career&careerPage=5')
    expect(await screen.findByRole('alert')).toHaveTextContent('Požadovaná stránka kariéry neexistuje.')
    expect(screen.queryByText('Brno Championship')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Poslední platná stránka'}))
    await waitFor(()=>expect(api.getSavedPlayerMatchHistory).toHaveBeenLastCalledWith('run','branch','A',null,20,20))
    expect(await screen.findByText('Brno Championship')).toBeInTheDocument()
    expect(screen.getByText(/Strana 2 \/ 2/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'První stránka'}))
    await waitFor(()=>expect(api.getSavedPlayerMatchHistory).toHaveBeenLastCalledWith('run','branch','A',null,0,20))
  })
  it('searches verified fields, filters only local rows, preserves server career counts', async () => {
    mount()
    expect(await screen.findByText('Brno Championship')).toBeInTheDocument()
    await screen.findByText(/Verified B/)
    fireEvent.change(screen.getByRole('searchbox',{name:'Hledat v načtené stránce'}),{target:{value:'Verified B'}})
    expect(screen.getByText('Brno Championship')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox',{name:'Filtrovat výhry a prohry'}),{target:{value:'loss'}})
    expect(screen.queryByText('Brno Championship')).not.toBeInTheDocument()
    expect(screen.getByText(/žádný zápas neodpovídá lokálním filtrům/)).toBeInTheDocument()
    expect(screen.getAllByText(/20 W \/ 1 L/).length).toBeGreaterThan(0)
    fireEvent.change(screen.getByRole('combobox',{name:'Filtrovat výhry a prohry'}),{target:{value:'win'}})
    expect(screen.getByText('Brno Championship')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox',{name:'Filtrovat odehrané a kontumace'}),{target:{value:'walkover'}})
    expect(screen.queryByText('Brno Championship')).not.toBeInTheDocument()
    expect(api.getSavedPlayerMatchHistory).toHaveBeenCalledTimes(1)
  })
  it('validates numeric jump, keeps local filters and passes source-bound link', async () => {
    mount('/?tab=career&careerOutcome=loss&careerCompletion=walkover&careerQ=W%2FO')
    expect(await screen.findByText(/žádný zápas neodpovídá lokálním filtrům/)).toBeInTheDocument()
    fireEvent.change(screen.getByRole('spinbutton',{name:'Číslo stránky kariéry'}),{target:{value:'3'}})
    expect(screen.getByRole('button',{name:'Přejít'})).toBeDisabled()
    fireEvent.change(screen.getByRole('spinbutton',{name:'Číslo stránky kariéry'}),{target:{value:'2'}})
    fireEvent.click(screen.getByRole('button',{name:'Přejít'}))
    expect(await screen.findByText('Brno Championship')).toBeInTheDocument()
    const link=screen.getByRole('link',{name:'Detail zápasu →'})
    expect(link.getAttribute('href')).toContain('replayHead=revision')
    expect(link.getAttribute('href')).toContain('careerOutcome=loss')
    expect(link.getAttribute('href')).toContain('careerCompletion=walkover')
    expect(link.getAttribute('href')).toContain('careerQ=W%2FO')
  })
  it('shows true empty career without nonsensical page count', async () => {
    api.getSavedPlayerMatchHistory.mockImplementation(async (_r:string,_b:string,_p:string,
      season:number|null,offset:number,limit:number) => ({
        schema_version:'saved_player_match_history.v1',source:'selected_branch_saved_revision',
        run_id:'run',branch_id:'branch',saved_revision_id:'revision',player_id:'A',
        status:'ready',season_index:season,offset,limit,available_seasons:[],total_results:0,
        played_wins:0,played_losses:0,walkovers:0,career_played_wins:0,career_played_losses:0,
        career_walkovers:0,has_more:false,matches:[],
      }))
    mount()
    expect(await screen.findByText(/Hráč nemá žádné uložené/)).toBeInTheDocument()
    expect(screen.queryByText(/Strana 1 \/ 0/)).not.toBeInTheDocument()
  })
})

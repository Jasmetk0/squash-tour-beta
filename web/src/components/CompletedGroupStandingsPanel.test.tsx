import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CompletedGroupStandingsPanel } from './CompletedGroupStandingsPanel'
const locale=vi.hoisted(()=>({current:'en' as 'cs'|'en'}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:locale.current})}))

const api = vi.hoisted(() => ({
  getAdminCompletedGroupStandings: vi.fn(),
  generateAdminCompletedGroupStandings: vi.fn(),
  getAdminGroupTieResolutionState: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) { super(message); this.status = status }
  },
}))
vi.mock('../api/client', () => api)
const sha = 'a'.repeat(64)
const ready = {
  schema_version: 'tournament_group_standings_authority.v2',
  run_id:'r',branch_id:'b',event_id:'e',
  authority_fingerprint:sha,group_match_schedule_fingerprint:sha,
  generated_by_command_id:'command',
  source_results:[{match_id:'m1',result_kind:'played'}],
  groups:[{group_index:1,rows:[
    {group_index:1,position:1,player_id:'A',wins:1,losses:0,group_points:4,played_matches:1,
      walkovers_received:0,walkovers_conceded:0,games_won:3,games_lost:0,points_won:33,points_lost:20},
    {group_index:1,position:2,player_id:'B',wins:0,losses:1,group_points:0,played_matches:1,
      walkovers_received:0,walkovers_conceded:0,games_won:0,games_lost:3,points_won:20,points_lost:33},
  ]}],
}
const emptyTie = {schema_version:'tournament_group_tie_resolution_state.v1',
  run_id:'r',branch_id:'b',event_id:'e',unresolved_case:null,resolutions:[]}
function mount(enabled = true) {
  const queryClient = new QueryClient({defaultOptions:{queries:{retry:false}}})
  return render(<QueryClientProvider client={queryClient}>
    <MemoryRouter><CompletedGroupStandingsPanel
      runId="r" branchId="b" eventId="e" enabled={enabled}/></MemoryRouter>
  </QueryClientProvider>)
}
describe('completed real group standings Admin', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    locale.current='en'
    api.getAdminCompletedGroupStandings.mockRejectedValue(new api.ApiError('Not found',404))
    api.getAdminGroupTieResolutionState.mockResolvedValue(emptyTie)
    api.generateAdminCompletedGroupStandings.mockResolvedValue(ready)
  })
  it('does not send a write without explicit confirmation or when context is blocked', async () => {
    mount()
    const button = await screen.findByRole('button',{name:'Generate canonical group standings'})
    expect(button).toBeDisabled()
    await screen.findByText(/No completed group-table authority/)
    expect(screen.getByRole('link',{name:/Open authoritative Simulation/})).toHaveAttribute(
      'href', '/admin/runs/r/simulate?branch=b')
    expect(api.generateAdminCompletedGroupStandings).not.toHaveBeenCalled()
  })
  it('explicitly generates and displays only the server-owned final table', async () => {
    mount()
    const button = await screen.findByRole('button',{name:'Generate canonical group standings'})
    fireEvent.click(screen.getByLabelText('Confirm generation from all completed canonical group matches'))
    await waitFor(() => expect(button).toBeEnabled())
    fireEvent.click(button)
    await waitFor(() => expect(api.generateAdminCompletedGroupStandings).toHaveBeenCalledTimes(1))
    expect(api.generateAdminCompletedGroupStandings.mock.calls[0].slice(0,3)).toEqual(['r','b','e'])
    expect(await screen.findByRole('table',{name:'Canonical group 1 standings'})).toBeInTheDocument()
    expect(screen.getByText(sha)).toBeInTheDocument()
  })
  it('never invents a tiebreak decision and hides generation on unresolved tied group', async () => {
    api.getAdminGroupTieResolutionState.mockResolvedValue({
      ...emptyTie,unresolved_case:{group_index:1,reason:'unresolved',player_ids:['A','B']}
    })
    mount()
    expect(await screen.findByText(/An explicit audited Admin ordering is required/)).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Confirm generation from all completed canonical group matches'))
    expect(screen.getByRole('button',{name:'Generate canonical group standings'})).toBeDisabled()
    expect(api.generateAdminCompletedGroupStandings).not.toHaveBeenCalled()
  })
  it('shows only already-frozen tables when authority is present',async()=>{
    api.getAdminCompletedGroupStandings.mockResolvedValue(ready)
    mount()
    expect(await screen.findByRole('table',{name:'Canonical group 1 standings'})).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Generate canonical group standings'})).not.toBeInTheDocument()
  })
  it('offers Czech standalone confirmation, result and table labels',async()=>{
    locale.current='cs'
    api.getAdminCompletedGroupStandings.mockResolvedValue(ready)
    mount()
    expect(await screen.findByRole('table',{name:'Konečná tabulka skupiny 1'})).toBeInTheDocument()
    expect(screen.getByText(/Tato tabulka není uloženou revizí/)).toBeInTheDocument()
  })
  it('does not query or write without a verified writable context',()=>{
    mount(false)
    expect(api.getAdminCompletedGroupStandings).not.toHaveBeenCalled()
    expect(api.generateAdminCompletedGroupStandings).not.toHaveBeenCalled()
  })
})

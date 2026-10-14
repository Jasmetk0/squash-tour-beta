import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {HybridKnockoutProgressionPanel} from './HybridKnockoutProgressionPanel'
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
vi.mock('../admin/branchSimulation',()=>({newCommandId:()=>'stable-request'}))
const api=vi.hoisted(()=>({
  getAdminCompletedGroupStandings:vi.fn(),
  getAdminHybridKnockoutEntrants:vi.fn(),generateAdminHybridKnockoutEntrants:vi.fn(),
  getAdminHybridKnockoutBracket:vi.fn(),generateAdminHybridKnockoutBracket:vi.fn(),
  ApiError:class ApiError extends Error{
    status:number
    constructor(message:string,status:number){super(message);this.status=status}
  },
}))
vi.mock('../api/client',()=>api)
const sha='a'.repeat(64),id='b'.repeat(64),br='c'.repeat(64)
const table={run_id:'r',branch_id:'b',event_id:'e',authority_fingerprint:sha,
  groups:[
    {group_index:1,rows:[{player_id:'A',position:1},{player_id:'B',position:2}]},
    {group_index:2,rows:[{player_id:'C',position:1},{player_id:'D',position:2}]},
  ]}
const entrants={run_id:'r',branch_id:'b',event_id:'e',authority_fingerprint:id,
  first_round_matches:[{match_id:'m1',match_index:1,
    top_source:{group_index:1,finishing_position:1},top_player_id:'A',
    bottom_source:{group_index:2,finishing_position:1},bottom_player_id:'C'}]}
const bracket={run_id:'r',branch_id:'b',event_id:'e',
  authority_fingerprint:br,terminal_match_id:'m1',entrant_count:2,round_count:1,
  matches:[{match_id:'m1',round_number:1,match_index:1,participant_sources:['player:A','player:C']}]}
const notFound=()=>Object.assign(new Error('Not found'),{status:404})
function mount(enabled=true){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  return render(<QueryClientProvider client={client}>
    <HybridKnockoutProgressionPanel runId="r" branchId="b" eventId="e" enabled={enabled}/>
  </QueryClientProvider>)
}
beforeEach(()=>{
  vi.clearAllMocks()
  api.getAdminCompletedGroupStandings.mockResolvedValue(table)
  api.getAdminHybridKnockoutEntrants.mockRejectedValue(notFound())
  api.getAdminHybridKnockoutBracket.mockRejectedValue(notFound())
  api.generateAdminHybridKnockoutEntrants.mockResolvedValue(entrants)
  api.generateAdminHybridKnockoutBracket.mockResolvedValue(bracket)
})
describe('real hybrid advancing players + knockout Admin',()=>{
  it('does not generate anything before real final group standings exist',async()=>{
    api.getAdminCompletedGroupStandings.mockRejectedValue(notFound())
    mount()
    expect(await screen.findByText(/Play all canonical group matches/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Generate frozen knockout entrants'})).not.toBeInTheDocument()
    expect(api.generateAdminHybridKnockoutEntrants).not.toHaveBeenCalled()
  })
  it('requires exact group-standings confirmation then shows actual resolved players',async()=>{
    mount()
    const button=await screen.findByRole('button',{name:'Generate frozen knockout entrants'})
    expect(button).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm entrants from exact final group standings'))
    expect(button).toBeEnabled()
    fireEvent.click(button)
    await waitFor(()=>expect(api.generateAdminHybridKnockoutEntrants)
      .toHaveBeenCalledWith('r','b','e',table,'stable-request'))
    const results=await screen.findByRole('table',{name:'Canonical advancing positions'})
    expect(results).toHaveTextContent('A')
    expect(results).toHaveTextContent('C')
  })
  it('requires a second deliberate decision before the immutable bracket exists',async()=>{
    api.getAdminHybridKnockoutEntrants.mockResolvedValue(entrants)
    mount()
    expect(await screen.findByRole('table',{name:'Canonical advancing positions'})).toBeInTheDocument()
    const button=await screen.findByRole('button',{name:'Generate frozen knockout bracket'})
    expect(button).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm bracket from exact frozen entrants'))
    expect(button).toBeEnabled()
    fireEvent.click(button)
    await waitFor(()=>expect(api.generateAdminHybridKnockoutBracket)
      .toHaveBeenCalledWith('r','b','e',entrants,'stable-request'))
    const frozen=await screen.findByRole('table',{name:'Canonical hybrid knockout bracket'})
    expect(frozen).toHaveTextContent('player:A')
    expect(frozen).toHaveTextContent('player:C')
  })
  it('never allows mutation from a historical or unverified branch',()=>{
    mount(false)
    expect(api.getAdminCompletedGroupStandings).not.toHaveBeenCalled()
    expect(api.generateAdminHybridKnockoutEntrants).not.toHaveBeenCalled()
    expect(api.generateAdminHybridKnockoutBracket).not.toHaveBeenCalled()
  })
  it('shows corrupt authority as error instead of inviting overwrite',async()=>{
    api.getAdminHybridKnockoutEntrants.mockRejectedValue(Object.assign(
      new Error('Stale authority'),{status:409}))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Stale authority')
    expect(screen.queryByRole('button',{name:'Generate frozen knockout entrants'})).not.toBeInTheDocument()
  })
})

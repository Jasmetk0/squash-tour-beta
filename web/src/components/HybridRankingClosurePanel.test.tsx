import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {HybridRankingClosurePanel} from './HybridRankingClosurePanel'
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
vi.mock('../admin/branchSimulation',()=>({newCommandId:()=>'reviewed-points-command'}))
const api=vi.hoisted(()=>({
  getAdminHybridRankingPolicy:vi.fn(),configureAdminHybridRankingPolicy:vi.fn(),
  getAdminHybridRankingClosure:vi.fn(),closeAdminHybridRanking:vi.fn(),
  getAuthoritativeMatchReplayContext:vi.fn(),
  ApiError:class ApiError extends Error{status:number
    constructor(message:string,status:number){super(message);this.status=status}},
}))
vi.mock('../api/client',()=>api)
const sha='a'.repeat(64),other='b'.repeat(64)
const bracket={
  run_id:'r',branch_id:'b',event_id:'e',authority_fingerprint:sha,
  round_count:1,entrant_count:2,terminal_match_id:'final',matches:[]
} as any
const table={run_id:'r',branch_id:'b',event_id:'e',authority_fingerprint:other,
  source_results:[{result_kind:'played'}]} as any
const policy={
  run_id:'r',branch_id:'b',event_id:'e',authority_fingerprint:sha,
  configured_by_command_id:'reviewed-points-command',
  played_group_win_points:10,knockout_stage_points:[['champion',100],['finalist',60]],
}
const closure={
  schema_version:'tournament_hybrid_closure_response.v1',
  run_id:'r',branch_id:'b',event_id:'e',source_fingerprint:sha,
  result_fingerprint:sha,award_fingerprint:sha,prize_award_fingerprint:sha,
  prize_configuration_status:'configured',total_ranking_points:180,
}
const missing=()=>Object.assign(new Error('Not Found'),{status:404})
function mount(enabled=true){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  return render(<QueryClientProvider client={client}>
    <HybridRankingClosurePanel runId="r" branchId="b" eventId="e"
      enabled={enabled} bracket={bracket} standings={table}/>
  </QueryClientProvider>)
}
beforeEach(()=>{
  vi.clearAllMocks()
  api.getAdminHybridRankingPolicy.mockRejectedValue(missing())
  api.getAdminHybridRankingClosure.mockRejectedValue(missing())
  api.getAuthoritativeMatchReplayContext.mockRejectedValue(missing())
  api.configureAdminHybridRankingPolicy.mockResolvedValue(policy)
  api.closeAdminHybridRanking.mockResolvedValue(closure)
})
describe('Real hybrid ranking Admin approval and closure',()=>{
  it('never supplies default points and refuses incomplete phase table',async()=>{
    mount()
    const submit=await screen.findByRole('button',{name:'Freeze hybrid ranking points policy'})
    expect(submit).toBeDisabled()
    expect(screen.getByLabelText('Played group win points')).toHaveValue(null)
    fireEvent.change(screen.getByLabelText('Played group win points'),{target:{value:'10'}})
    fireEvent.change(screen.getByLabelText('Hybrid points for champion'),{target:{value:'100'}})
    expect(submit).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Hybrid points for finalist'),{target:{value:'60'}})
    expect(submit).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm exact hybrid ranking point values'))
    expect(submit).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Hybrid points for finalist'),{target:{value:'61'}})
    expect(submit).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Hybrid points for finalist'),{target:{value:'60'}})
    fireEvent.click(screen.getByLabelText('Confirm exact hybrid ranking point values'))
    fireEvent.click(submit)
    await waitFor(()=>expect(api.configureAdminHybridRankingPolicy).toHaveBeenCalledWith(
      'r','b','e',bracket,{command_id:'reviewed-points-command',played_group_win_points:10,
        knockout_stage_points:[['champion',100],['finalist',60]]}
    ))
  })
  it('only allows closing from a verified actually played terminal MatchEngine replay',async()=>{
    api.getAdminHybridRankingPolicy.mockResolvedValue(policy)
    mount()
    const close=await screen.findByRole('button',{name:'Close real hybrid tournament ranking source'})
    expect(close).toBeDisabled()
    expect(api.closeAdminHybridRanking).not.toHaveBeenCalled()
  })
  it('confirms real terminal result and shows immutable award fingerprint after explicit close',async()=>{
    api.getAdminHybridRankingPolicy.mockResolvedValue(policy)
    api.getAuthoritativeMatchReplayContext.mockResolvedValue({
      event_id:'e',match_id:'final',result_fingerprint:sha,
    })
    mount()
    const close=await screen.findByRole('button',{name:'Close real hybrid tournament ranking source'})
    expect(close).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm close from real hybrid match results'))
    expect(close).toBeEnabled()
    fireEvent.click(close)
    await waitFor(()=>expect(api.closeAdminHybridRanking)
      .toHaveBeenCalledWith('r','b','e','reviewed-points-command'))
    expect(await screen.findByText('Canonical tournament source is frozen')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Close real hybrid tournament ranking source'}))
      .not.toBeInTheDocument()
  })
  it('reloaded source is read-only and cannot be recreated',async()=>{
    api.getAdminHybridRankingClosure.mockResolvedValue(closure)
    api.getAdminHybridRankingPolicy.mockResolvedValue(policy)
    mount()
    expect(await screen.findByText('Canonical tournament source is frozen')).toBeInTheDocument()
    expect(screen.queryByLabelText('Played group win points')).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Close real hybrid tournament ranking source'})).not.toBeInTheDocument()
    expect(api.closeAdminHybridRanking).not.toHaveBeenCalled()
  })
  it('historical non-writable scope has no data fetches or mutation',()=>{
    mount(false)
    expect(api.getAdminHybridRankingPolicy).not.toHaveBeenCalled()
    expect(api.closeAdminHybridRanking).not.toHaveBeenCalled()
  })
})

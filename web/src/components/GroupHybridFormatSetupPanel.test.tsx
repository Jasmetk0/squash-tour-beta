import {beforeEach,describe,expect,it,vi} from 'vitest'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {GroupFormatSetupPanel} from './GroupFormatSetupPanel'

vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
const api=vi.hoisted(()=>({
  getAdminGroupRules:vi.fn(),adoptAdminGroupRules:vi.fn(),
  configureAdminPureGroups:vi.fn(),configureAdminHybridGroups:vi.fn(),
  generateAdminGroupTopology:vi.fn(),
}))
vi.mock('../api/client',()=>api)
const effective={
  schema_version:'tournament_group_rules_policy.v1',run_id:'run',
  branch_id:'branch',effective_from_season_index:0,
  default_match_best_of:3,authority_fingerprint:'a'.repeat(64),
}
const props={runId:'run',branchId:'branch',eventId:'cup',
  seasonIndex:0,entrantCount:4,hasQualification:false,hasByes:false} as const
function mount(step:'format'|'topology'='format',overrides:Record<string,unknown>={}){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  return render(<QueryClientProvider client={client}>
    <GroupFormatSetupPanel {...props} {...overrides} kind="groups_knockout" step={step}/>
  </QueryClientProvider>)
}
beforeEach(()=>{
  vi.clearAllMocks()
  api.getAdminGroupRules.mockResolvedValue({
    schema_version:'tournament_group_rules_state.v1',
    run_id:'run',branch_id:'branch',target_season_index:0,
    effective,versions:[effective]
  })
  api.configureAdminHybridGroups.mockResolvedValue({schema_version:'tournament_format_authority.v1'})
  api.generateAdminGroupTopology.mockResolvedValue({schema_version:'tournament_topology_authority.v1'})
})
describe('Real hybrid Group Format Admin UI',()=>{
  it('requires operator selection of every crossing, no hidden automatic pairing',async()=>{
    mount()
    await screen.findByText(/Frozen season group rules: BO3/)
    const submit=screen.getByRole('button',{name:'Configure groups + knockout Format'})
    expect(submit).toBeDisabled()
    expect(screen.getByLabelText('Group count')).toHaveValue(2)
    expect(screen.getByLabelText('Players per group')).toHaveValue(2)
    expect(screen.getByLabelText('Advancers per group')).toHaveValue(1)
    fireEvent.change(screen.getByLabelText('Hybrid match 1 top source'),{target:{value:'1:1'}})
    fireEvent.change(screen.getByLabelText('Hybrid match 1 bottom source'),{target:{value:'2:1'}})
    expect(submit).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm exact hybrid Format and crossings'))
    expect(submit).toBeEnabled()
    fireEvent.click(submit)
    await waitFor(()=>expect(api.configureAdminHybridGroups).toHaveBeenCalledTimes(1))
    expect(api.configureAdminHybridGroups).toHaveBeenCalledWith('run','branch','cup',{
      command_id:'admin-ui-hybrid-cup',format_kind:'groups_knockout',
      group_count:2,group_size:2,seeded_slots_per_group:0,
      group_seed_placements:[],match_best_of_override:null,advancing_per_group:1,
      knockout_crossings:[{match_index:1,
        top:{group_index:1,finishing_position:1},
        bottom:{group_index:2,finishing_position:1}}]
    })
    expect(api.configureAdminPureGroups).not.toHaveBeenCalled()
  })
  it('rejects repeated position and invalidates old confirmation after changes',async()=>{
    mount()
    await screen.findByText(/Frozen season group rules: BO3/)
    const send=screen.getByRole('button',{name:'Configure groups + knockout Format'})
    fireEvent.change(screen.getByLabelText('Hybrid match 1 top source'),{target:{value:'1:1'}})
    fireEvent.change(screen.getByLabelText('Hybrid match 1 bottom source'),{target:{value:'1:1'}})
    fireEvent.click(screen.getByLabelText('Confirm exact hybrid Format and crossings'))
    expect(send).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Hybrid match 1 bottom source'),{target:{value:'2:1'}})
    expect(send).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm exact hybrid Format and crossings'))
    expect(send).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Advancers per group'),{target:{value:'2'}})
    expect(send).toBeDisabled()
    expect(screen.getByLabelText('Confirm exact hybrid Format and crossings')).not.toBeChecked()
    expect(screen.getByLabelText('Hybrid match 2 top source')).toHaveValue('')
    expect(api.configureAdminHybridGroups).not.toHaveBeenCalled()
  })
  it('denies corrupted capacity or BYEs and uses hybrid-specific topology validation',async()=>{
    mount('format',{hasByes:true})
    await screen.findByText(/Frozen season group rules: BO3/)
    expect(screen.getByRole('button',{name:'Configure groups + knockout Format'})).toBeDisabled()
    expect(api.configureAdminHybridGroups).not.toHaveBeenCalled()
  })
  it('generates frozen groups+knockout topology under explicit Run and Branch',async()=>{
    mount('topology')
    await screen.findByText(/Frozen season group rules: BO3/)
    const send=screen.getByRole('button',{name:'Generate group Topology'})
    fireEvent.click(screen.getByLabelText('Confirm immutable group Topology'))
    expect(send).toBeEnabled()
    fireEvent.click(send)
    await waitFor(()=>expect(api.generateAdminGroupTopology).toHaveBeenCalledWith(
      'run','branch','cup','admin-ui-group-topology-cup',137,'groups_knockout'
    ))
  })
})

import {beforeEach,describe,expect,it,vi} from 'vitest'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {GroupFormatSetupPanel} from './GroupFormatSetupPanel'
import {proposedPureGroups} from '../api/tournamentGroupFormats'
const locale=vi.hoisted(()=>({current:'en' as 'en'|'cs'}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:locale.current})}))

const api=vi.hoisted(()=>({
  getAdminGroupRules:vi.fn(),adoptAdminGroupRules:vi.fn(),
  configureAdminPureGroups:vi.fn(),generateAdminGroupTopology:vi.fn(),
}))
vi.mock('../api/client',()=>api)
const scope={runId:'run-a',branchId:'branch-a',eventId:'event-1',
  seasonIndex:0,entrantCount:4,hasQualification:false,hasByes:false} as const
const effective={schema_version:'tournament_group_rules_policy.v1',
  run_id:'run-a',branch_id:'branch-a',effective_from_season_index:0,
  default_match_best_of:3,authority_fingerprint:'a'.repeat(64)}
const state=(policy:typeof effective|null)=>({
  schema_version:'tournament_group_rules_state.v1',run_id:'run-a',
  branch_id:'branch-a',target_season_index:0,effective:policy,versions:[]
})
function mount(step:'format'|'topology'='format',override:Partial<{
  runId:string;branchId:string;eventId:string;seasonIndex:number|null
  entrantCount:number;hasQualification:boolean;hasByes:boolean
}>={}){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  return render(<QueryClientProvider client={client}>
    <GroupFormatSetupPanel {...scope} {...override} step={step}/>
  </QueryClientProvider>)
}
describe('real Admin group preparation',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    locale.current='en'
    api.getAdminGroupRules.mockResolvedValue(state(effective))
    api.adoptAdminGroupRules.mockResolvedValue(effective)
    api.configureAdminPureGroups.mockResolvedValue({
      schema_version:'tournament_format_authority.v1',
      run_id:'run-a',branch_id:'branch-a',event_id:'event-1',
      format_kind:'groups',
    })
    api.generateAdminGroupTopology.mockResolvedValue({
      schema_version:'tournament_topology_authority.v1'
    })
  })
  it('configures actual four-player pure groups only after deliberate confirmation',async()=>{
    mount()
    expect(await screen.findByText(/Frozen season group rules: BO3/)).toBeInTheDocument()
    const send=screen.getByRole('button',{name:'Configure pure-groups Format'})
    expect(send).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Group count'),{target:{value:'2'}})
    fireEvent.change(screen.getByLabelText('Players per group'),{target:{value:'2'}})
    fireEvent.click(screen.getByLabelText('Confirm immutable pure-groups Format'))
    expect(send).toBeEnabled()
    fireEvent.click(send)
    await waitFor(()=>expect(api.configureAdminPureGroups).toHaveBeenCalledTimes(1))
    expect(api.configureAdminPureGroups).toHaveBeenCalledWith(
      'run-a','branch-a','event-1',{
        command_id:'admin-ui-pure-groups-event-1',format_kind:'groups',
        group_count:2,group_size:2,seeded_slots_per_group:0,
        group_seed_placements:[],match_best_of_override:null,
        advancing_per_group:0,knockout_crossings:[],
      }
    )
  })
  it('adopts season group rules explicitly when absent; never assumes a default',async()=>{
    let adopted=false
    api.getAdminGroupRules.mockImplementation(async()=>state(adopted?effective:null))
    api.adoptAdminGroupRules.mockImplementation(async()=>{adopted=true;return effective})
    mount()
    const send=await screen.findByRole('button',{name:'Adopt season Group Rules'})
    expect(screen.getByRole('button',{name:'Configure pure-groups Format'})).toBeDisabled()
    expect(send).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Season group-match format'),
      {target:{value:'3'}})
    fireEvent.click(screen.getByLabelText('Confirm immutable season Group Rules'))
    fireEvent.click(send)
    await waitFor(()=>expect(api.adoptAdminGroupRules).toHaveBeenCalledWith(
      'run-a','branch-a',0,3,'admin-ui-group-rules-branch-a-0-bo3'
    ))
    expect(await screen.findByText(/Frozen season group rules: BO3/)).toBeInTheDocument()
  })
  it('blocks partial Entry Fields, BYEs, foreign season and invalid group capacities',async()=>{
    mount('format',{hasByes:true})
    await screen.findByText(/Frozen season group rules/)
    fireEvent.click(screen.getByLabelText('Confirm immutable pure-groups Format'))
    expect(screen.getByRole('button',{name:'Configure pure-groups Format'})).toBeDisabled()
    expect(api.configureAdminPureGroups).not.toHaveBeenCalled()
  })
  it('freezes real group Topology only after an explicit Admin confirmation',async()=>{
    mount('topology')
    const send=await screen.findByRole('button',{name:'Generate group Topology'})
    await screen.findByText(/Frozen season group rules: BO3/)
    expect(send).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm immutable group Topology'))
    fireEvent.click(send)
    await waitFor(()=>expect(api.generateAdminGroupTopology).toHaveBeenCalledWith(
      'run-a','branch-a','event-1','admin-ui-group-topology-event-1',137,'groups'
    ))
  })
  it('refuses missing and fractional topology seeds instead of sending ambiguous authority',async()=>{
    mount('topology')
    await screen.findByRole('button',{name:'Generate group Topology'})
    await screen.findByText(/Frozen season group rules: BO3/)
    fireEvent.click(screen.getByLabelText('Confirm immutable group Topology'))
    const button=screen.getByRole('button',{name:'Generate group Topology'})
    fireEvent.change(screen.getByLabelText('Group Topology seed'),{target:{value:'1.5'}})
    expect(button).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Group Topology seed'),{target:{value:'137'}})
    expect(button).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm immutable group Topology'))
    expect(button).toBeEnabled()
  })
  it('revokes Format approval when exact 1×4 changes to 2×2, even though both are valid',async()=>{
    mount()
    await screen.findByText(/Frozen season group rules/)
    const send=screen.getByRole('button',{name:'Configure pure-groups Format'})
    fireEvent.click(screen.getByLabelText('Confirm immutable pure-groups Format'))
    expect(send).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Group count'),{target:{value:'2'}})
    fireEvent.change(screen.getByLabelText('Players per group'),{target:{value:'2'}})
    expect(send).toBeDisabled()
    expect(screen.getByLabelText('Confirm immutable pure-groups Format')).not.toBeChecked()
    fireEvent.click(send)
    expect(api.configureAdminPureGroups).not.toHaveBeenCalled()
    fireEvent.click(screen.getByLabelText('Confirm immutable pure-groups Format'))
    fireEvent.click(send)
    await waitFor(()=>expect(api.configureAdminPureGroups).toHaveBeenCalledTimes(1))
    expect(api.configureAdminPureGroups.mock.calls[0][3]).toMatchObject({group_count:2,group_size:2})
  })
  it('revokes BO3/BO5 season Rules approval upon changes and requires reconfirmation',async()=>{
    api.getAdminGroupRules.mockResolvedValue(state(null))
    mount()
    const send=await screen.findByRole('button',{name:'Adopt season Group Rules'})
    fireEvent.click(screen.getByLabelText('Confirm immutable season Group Rules'))
    expect(send).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Season group-match format'),{target:{value:'3'}})
    expect(send).toBeDisabled()
    expect(screen.getByLabelText('Confirm immutable season Group Rules')).not.toBeChecked()
    fireEvent.click(send)
    expect(api.adoptAdminGroupRules).not.toHaveBeenCalled()
    fireEvent.click(screen.getByLabelText('Confirm immutable season Group Rules'))
    fireEvent.click(send)
    await waitFor(()=>expect(api.adoptAdminGroupRules).toHaveBeenCalledWith(
      'run-a','branch-a',0,3,'admin-ui-group-rules-branch-a-0-bo3'))
  })
  it('revokes topology approval after seed change, including return to old seed',async()=>{
    mount('topology')
    const send=await screen.findByRole('button',{name:'Generate group Topology'})
    await screen.findByText(/Frozen season group rules: BO3/)
    fireEvent.click(screen.getByLabelText('Confirm immutable group Topology'))
    fireEvent.change(screen.getByLabelText('Group Topology seed'),{target:{value:'123'}})
    expect(send).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Group Topology seed'),{target:{value:'137'}})
    // Returning to a prior value cannot resurrect an old approval.
    expect(send).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm immutable group Topology'))
    expect(send).toBeEnabled()
  })
  it('provides translated Czech labels and validation errors',async()=>{
    locale.current='cs'
    mount()
    await screen.findByText(/Potvrzená skupinová pravidla sezony/)
    expect(screen.getByRole('button',{name:'Nastavit čisté skupiny'})).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Počet skupin'),{target:{value:'2'}})
    expect(screen.getByRole('alert')).toHaveTextContent('Počet skupin × hráči ve skupině')
  })
  it('rejects corrupted or ambiguous numeric fields rather than silently rounding',()=>{
    expect(proposedPureGroups('2','2',4,'cmd').group_count).toBe(2)
    for(const [groups,players,entrants] of [
      ['2.0','2',4],['2','2.5',5],['2','3',4],
      ['0','2',4],['2','1',2],['65','2',130],
    ] as Array<[string,string,number]>){
      expect(()=>proposedPureGroups(groups,players,entrants,'cmd')).toThrow()
    }
  })
})

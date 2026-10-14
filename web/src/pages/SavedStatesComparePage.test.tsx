import {screen,within,waitFor} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {renderWithRoute} from '../test/testUtils'
import {SavedStatesComparePage} from './SavedStatesComparePage'

const api=vi.hoisted(()=>({
  listRunBranches:vi.fn(),listSavedRevisionHistory:vi.fn(),
  compareSavedRevisions:vi.fn(),getSavedRevision:vi.fn()
}))
vi.mock('../api/client',()=>api)

const first={
  revision_id:'old',sequence:1,parent_revision_id:null,kind:'initial_run_creation',
  revision_branch_id:'parent-branch',is_shared_revision:true,is_branch_head:false,
  content_hash:'hash-old',content_hash_algorithm:'sha256',created_at:'2026-10-11 12:00:00',
  payload_schema_version:'run_saved_revision_v1',change_summary:{summary:'Initial'}
}
const second={
  ...first,revision_id:'new',sequence:2,parent_revision_id:'old',
  revision_branch_id:'fork',is_shared_revision:false,is_branch_head:true,
  content_hash:'hash-new',kind:'manual_save',change_summary:{summary:'Changed world'}
}
const history=(branch='fork',entries=[first,second],older=false)=>({
  run_id:'run-a',branch_id:branch,saved_head_revision_id:'new',
  total_count:older?3:entries.length,has_more_older:older,
  next_before_sequence:older?1:null,saved_revisions:entries
})
const diff=()=>({
  run_id:'run-a',branch_id:'fork',saved_head_revision_id:'new',
  from_revision:first,to_revision:second,
  run_changes:{display_name:{before:'Run 1',after:'Run 2'}},
  branch_changes:{},
  components:[
    {component_key:'calendar',status:'changed',before_fingerprint:'before',after_fingerprint:'after'},
    {component_key:'ranking',status:'unchanged',before_fingerprint:'same',after_fingerprint:'same'}
  ]
})
function open(query='branch=fork&a=old&b=new'){
  renderWithRoute(<SavedStatesComparePage/>,
    '/admin/runs/run-a/branches/compare'+(query?'?'+query:''))
}
beforeEach(()=>{
  vi.clearAllMocks()
  api.listRunBranches.mockResolvedValue({run_branches:[
    {run_id:'run-a',branch_id:'fork',display_name:'Timeline 2'},
    {run_id:'run-a',branch_id:'other',display_name:'Timeline 3'}
  ]})
  api.listSavedRevisionHistory.mockImplementation(async (_run:string,branch:string)=>
    history(branch))
  api.compareSavedRevisions.mockResolvedValue(diff())
  api.getSavedRevision.mockImplementation(async (_run:string,branch:string,rev:string)=>({
    ...((rev==='old')?first:second),branch_id:branch,run_id:'run-a',
    payload:{content:{example:'immutable'}}
  }))
})

describe('Dedicated read-only Compare States A/B',()=>{
  it('loads explicit same-Branch A/B and filters without mutating any Run state',async()=>{
    open()
    const selection=await screen.findByLabelText('Compare Saved Revision selection')
    expect(await within(selection).findByLabelText('Compare Branch')).toHaveValue('fork')
    await waitFor(()=>expect(within(selection).getByLabelText('Compare state A')).toHaveValue('old'))
    expect(within(selection).getByLabelText('Compare state B')).toHaveValue('new')
    const results=await screen.findByLabelText('Compare Saved Revision results')
    const table=await within(results).findByRole('table',{name:'Saved State A B comparison table'})
    expect(table).toHaveTextContent('calendar')
    expect(table).toHaveTextContent('display_name')
    expect(table).not.toHaveTextContent('ranking')
    expect(within(results).getByLabelText('Compare Saved Revision totals')).toHaveTextContent('2')
    expect(api.compareSavedRevisions).toHaveBeenCalledWith('run-a','fork','old','new')
    await userEvent.selectOptions(within(results).getByLabelText('Compare display filter'),'all')
    expect(within(results).getByRole('table',{name:'Saved State A B comparison table'}))
      .toHaveTextContent('ranking')
    await userEvent.click(within(results).getByRole('button',{name:'Inspect comparison component:calendar'}))
    const drawer=screen.getByLabelText('Compare read-only detail')
    expect(drawer).toHaveTextContent('Canonical Saved change evidence')
    expect(within(drawer).getByText('before')).toBeInTheDocument()
    expect(within(drawer).getByText('after')).toBeInTheDocument()
    expect(drawer).toHaveTextContent('NOT reconstructed')
    await userEvent.click(within(drawer).getByRole('button',{name:'Close Compare detail'}))
    expect(screen.queryByLabelText('Compare read-only detail')).not.toBeInTheDocument()
    expect(api.compareSavedRevisions).toHaveBeenCalledTimes(1)
  })
  it('inspects the true Saved payload of A without restore and verifies hash/owner',async()=>{
    open()
    const results=await screen.findByLabelText('Compare Saved Revision results')
    await within(results).findByRole('table',{name:'Saved State A B comparison table'})
    await userEvent.click(within(results).getByRole('button',{name:'Inspect state A read-only'}))
    const drawer=await screen.findByLabelText('Compare read-only detail')
    await waitFor(()=>expect(drawer).toHaveTextContent('immutable'))
    expect(drawer).toHaveTextContent('parent-branch')
    expect(drawer).toHaveTextContent('hash-old')
    expect(api.getSavedRevision).toHaveBeenCalledWith('run-a','fork','old')
  })
  it('blocks cross-Branch switching with stale A/B; no silent compare fallback',async()=>{
    open()
    const results=await screen.findByLabelText('Compare Saved Revision results')
    await within(results).findByRole('table',{name:'Saved State A B comparison table'})
    await userEvent.selectOptions(screen.getByLabelText('Compare Branch'),'other')
    expect(screen.getByLabelText('Compare state A')).toHaveValue('')
    expect(screen.getByLabelText('Compare state B')).toHaveValue('')
    expect(screen.queryByLabelText('Compare Saved Revision results')).not.toBeInTheDocument()
    expect(api.compareSavedRevisions).toHaveBeenCalledTimes(1)
  })
  it('does not compare unreachable revisions, foreign Branches or identical state selections',async()=>{
    open('branch=fork&a=unknown&b=new')
    expect(await screen.findByText(/Requested state is not in the loaded reachable history/))
      .toBeInTheDocument()
    expect(api.compareSavedRevisions).not.toHaveBeenCalled()
  })
  it('does not compare a malformed or cross-owner response',async()=>{
    api.compareSavedRevisions.mockResolvedValue({...diff(),from_revision:{...first,
      revision_branch_id:'foreign'}})
    open()
    expect(await screen.findByText(/identity\/content hashes disagree/)).toBeInTheDocument()
    expect(screen.queryByRole('table',{name:'Saved State A B comparison table'}))
      .not.toBeInTheDocument()
  })
  it('can load an older ancestor before comparing the URL-selected A/B',async()=>{
    api.listSavedRevisionHistory.mockImplementation(async (_run:string,branch:string,options:{
      beforeSequence?:number})=>{
      if(options.beforeSequence===1)return {...history(branch,[first]),total_count:2}
      return {...history(branch,[second],true),total_count:2}
    })
    open()
    expect(await screen.findByText(/Requested state is not in the loaded reachable history/))
      .toBeInTheDocument()
    expect(api.compareSavedRevisions).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button',{name:'Load older revisions for Compare'}))
    expect(await screen.findByRole('table',{name:'Saved State A B comparison table'}))
      .toHaveTextContent('calendar')
    expect(api.listSavedRevisionHistory).toHaveBeenCalledWith('run-a','fork',{
      limit:50,beforeSequence:1
    })
  })
})

import {describe,expect,it} from 'vitest'
import {projectSavedStateComparison,validateReachableCompareHistory} from './savedCompareStates'
import type {SavedRevisionHistoryEntry,SavedRevisionComparison,SavedRevisionHistoryPageResponse} from '../api/types'

const item=(id:string,sequence:number,owner='original'):SavedRevisionHistoryEntry=>({
  revision_id:id,sequence,revision_branch_id:owner,
  parent_revision_id:sequence===1?null:'rev-'+(sequence-1),
  kind:'manual_save',payload_schema_version:'run_saved_revision_v1',
  content_hash_algorithm:'sha256',content_hash:'hash-'+id,created_at:null,
  is_shared_revision:owner==='original',is_branch_head:id==='rev-3',
  change_summary:{summary:'Saved '+id}
})
const a=item('rev-1',1),b=item('rev-3',3,'fork')
const page=(items:SavedRevisionHistoryEntry[],cursor:number|null=null):
  SavedRevisionHistoryPageResponse=>({
    run_id:'run',branch_id:'fork',saved_head_revision_id:'rev-3',
    saved_revisions:items,total_count:2,
    has_more_older:cursor!==null,next_before_sequence:cursor
  })
const compare=():SavedRevisionComparison=>({
  run_id:'run',branch_id:'fork',saved_head_revision_id:'rev-3',
  from_revision:a,to_revision:b,
  run_changes:{viewer_branch_id:{before:'origin',after:'fork'}},
  branch_changes:{display_name:{before:'First',after:'Second'}},
  components:[
    {component_key:'calendar',status:'changed',before_fingerprint:'old',after_fingerprint:'new'},
    {component_key:'ranking',status:'unchanged',before_fingerprint:'same',after_fingerprint:'same'},
    {component_key:'player',status:'added',before_fingerprint:null,after_fingerprint:'new'}
  ]
})
describe('Saved Compare A/B source validation',()=>{
  it('checks a true reachable branch including shared ancestors across pages',()=>{
    const history=validateReachableCompareHistory('run','fork',[page([b],2),page([a])])
    expect(history?.entries.map(x=>x.revision_id)).toEqual(['rev-1','rev-3'])
    expect(history?.head).toBe('rev-3')
  })
  it('rejects foreign, duplicate, corrupt and conflicting history pages',()=>{
    expect(validateReachableCompareHistory('run','wrong',[page([a,b])])).toBeNull()
    expect(validateReachableCompareHistory('run','fork',[page([b]),{...page([a]),run_id:'other'}]))
      .toBeNull()
    expect(validateReachableCompareHistory('run','fork',[page([a]),page([a])])).toBeNull()
    expect(validateReachableCompareHistory('run','fork',[page([a]),{...page([b]),saved_head_revision_id:'wrong'}]))
      .toBeNull()
    expect(validateReachableCompareHistory('run','fork',[page([{...a,content_hash:''},b])]))
      .toBeNull()
  })
  it('preserves canonical A→B differences, unchanged components and source fingerprints',()=>{
    const view=projectSavedStateComparison(compare(),'run','fork',a,b,'rev-3')!
    expect(view.changed).toBe(4)
    expect(view.unchanged).toBe(1)
    expect(view.runChanges).toBe(1)
    expect(view.branchChanges).toBe(1)
    expect(view.components).toBe(3)
    expect(view.rows.find(x=>x.id==='run:viewer_branch_id')).toEqual({
      id:'run:viewer_branch_id',section:'run',key:'viewer_branch_id',
      status:'changed',before:'origin',after:'fork'
    })
    expect(view.rows.find(x=>x.id==='component:ranking')?.status).toBe('unchanged')
    expect(view.rows.find(x=>x.id==='component:player')?.before).toBeNull()
  })
  it('fails closed on wrong Run, same state, cross-history hash or altered original owner',()=>{
    expect(projectSavedStateComparison({...compare(),run_id:'foreign'},'run','fork',a,b,'rev-3')).toBeNull()
    expect(projectSavedStateComparison(compare(),'run','fork',a,a,'rev-3')).toBeNull()
    expect(projectSavedStateComparison({...compare(),from_revision:{...a,content_hash:'tampered'}},
      'run','fork',a,b,'rev-3')).toBeNull()
    expect(projectSavedStateComparison({...compare(),from_revision:{...a,revision_branch_id:'fork'}},
      'run','fork',a,b,'rev-3')).toBeNull()
    expect(projectSavedStateComparison(compare(),'run','fork',a,b,'stale-head')).toBeNull()
  })
  it('rejects invented statuses, duplicate components and invalid before/after payloads',()=>{
    const q=compare()
    q.components[0].status='made-up' as 'changed'
    expect(projectSavedStateComparison(q,'run','fork',a,b,'rev-3')).toBeNull()
    const duplicate=compare();duplicate.components.push({...duplicate.components[0]})
    expect(projectSavedStateComparison(duplicate,'run','fork',a,b,'rev-3')).toBeNull()
    const missing=compare();missing.run_changes={bad:{before:'present'} as unknown as {before:unknown;after:unknown}}
    expect(projectSavedStateComparison(missing,'run','fork',a,b,'rev-3')).toBeNull()
  })
})

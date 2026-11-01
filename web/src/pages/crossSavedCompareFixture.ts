import type {SavedRevisionHistoryEntry} from '../api/types'
import type {CrossSavedRevisionComparison} from '../api/crossSavedCompare'
import type {CrossSource} from './crossSavedCompare'
export const revision=(id:string,owner:string,hash:string):SavedRevisionHistoryEntry=>({
  revision_id:id,revision_branch_id:owner,sequence:1,parent_revision_id:null,kind:'initial',
  payload_schema_version:'run_saved_revision_v1',content_hash_algorithm:'sha256',content_hash:hash.repeat(64),
  change_summary:{summary:id},created_at:null,is_shared_revision:false,is_branch_head:true})
export const a:CrossSource={runId:'run-a',branchId:'branch-a',head:'rev-a',revision:revision('rev-a','branch-a','a')}
export const b:CrossSource={runId:'run-b',branchId:'branch-b',head:'rev-b',revision:revision('rev-b','branch-b','b')}
export const response=():CrossSavedRevisionComparison=>({
  from_source:{run_id:a.runId,branch_id:a.branchId,saved_head_revision_id:a.head,revision:a.revision},
  to_source:{run_id:b.runId,branch_id:b.branchId,saved_head_revision_id:b.head,revision:b.revision},
  run_changes:{zero:{before:0,after:false,before_present:true,after_present:true},
    missing:{before:null,after:null,before_present:false,after_present:true}},branch_changes:{},
  components:[{component_key:'same',status:'unchanged',before_fingerprint:'c'.repeat(64),after_fingerprint:'c'.repeat(64)},
    {component_key:'ranking',status:'changed',before_fingerprint:'a'.repeat(64),after_fingerprint:'b'.repeat(64)}]})

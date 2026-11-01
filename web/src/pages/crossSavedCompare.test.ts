import {describe,it,expect} from 'vitest'
import {a,b,response} from './crossSavedCompareFixture'
import {projectCrossSavedStateComparison as project} from './crossSavedCompare'
describe('Cross-Run exact Saved context validation',()=>{
  it('keeps null, absent, zero and false distinct with bounded fingerprints',()=>{
    const result=project(response(),a,b)!
    expect(result.changed).toBe(3)
    expect(result.rows.find(r=>r.key==='zero')).toMatchObject({before:0,after:false})
    expect(result.rows.find(r=>r.key==='missing')).toMatchObject({before:undefined,after:null})
  })
  it.each(['run_id','branch_id','saved_head_revision_id'] as const)('rejects wrong %s on either independent source',field=>{
    for(const side of ['from_source','to_source'] as const){
      const value=response();value[side][field]='foreign';expect(project(value,a,b)).toBeNull()
    }
  })
  it.each(['revision_id','revision_branch_id','content_hash','payload_schema_version','kind'] as const)('rejects altered %s',field=>{
    const value=response();value.to_source={...value.to_source,revision:{...value.to_source.revision,[field]:'altered'}}
    expect(project(value,a,b)).toBeNull()
  })
  it('rejects missing/malformed sources and contradictory component evidence',()=>{
    for(const value of [null,{},[],{from_source:null,to_source:b}])expect(project(value,a,b)).toBeNull()
    const value=response();value.components[1].after_fingerprint=value.components[1].before_fingerprint
    expect(project(value,a,b)).toBeNull()
  })
  it('permits a shared ancestor under the actual selected Branch',()=>{
    const source={...a,branchId:'fork',revision:{...a.revision,is_shared_revision:true}}
    const value=response();value.from_source={...value.from_source,branch_id:'fork',revision:source.revision}
    expect(project(value,source,b)).not.toBeNull()
    expect(project(value,a,b)).toBeNull()
  })
})

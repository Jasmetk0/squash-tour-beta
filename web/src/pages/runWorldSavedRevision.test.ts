import {describe,expect,it} from 'vitest'
import {worldFixture} from './runWorldFixture'
import {historicalRunWorldSnapshot} from './runWorldSavedRevision'
import {projectRunWorld} from './runWorldReadModel'
import type {SavedRevisionHistoryDetail} from '../api/types'

function detail(revisionId:string,origin='branch-a',selected='branch-a',snapshot=worldFixture()):SavedRevisionHistoryDetail {
  if(snapshot.state) snapshot.state.branch_id=origin
  return {
    revision_id:revisionId,sequence:2,parent_revision_id:null,
    kind:'run_saved_revision',payload_schema_version:'run_saved_revision_v1',
    content_hash_algorithm:'sha256',content_hash:'c'.repeat(64),change_summary:{},
    revision_branch_id:origin,created_at:null,is_shared_revision:origin!==selected,is_branch_head:false,
    run_id:'run-a',branch_id:selected,
    payload:{run:{run_id:'run-a'},branch:{branch_id:origin},
      content:{run_package_state:{fingerprint:snapshot.fingerprint,state:snapshot.state}}}
  }
}
describe('historical Saved World source extraction',()=>{
  it('shows different exact World facts in two revisions without changing sources',()=>{
    const older=detail('rev-old')
    const newer=detail('rev-new')
    const other=(newer.payload.content as Record<string,unknown>).run_package_state as {
      fingerprint:string;state:{entities:Record<string,unknown>[]}
    }
    const c=other.state.entities[1].payload as Record<string,unknown>
    c.name='Newly renamed Czechia'
    const before=JSON.stringify([older,newer])
    const old=historicalRunWorldSnapshot(older,'run-a','branch-a','rev-old')
    const next=historicalRunWorldSnapshot(newer,'run-a','branch-a','rev-new')
    expect(projectRunWorld(old.response!,'run-a',old.revisionBranchId,2000)!.countries[0].name).toBe('Czechia')
    expect(projectRunWorld(next.response!,'run-a',next.revisionBranchId,2000)!.countries[0].name)
      .toBe('Newly renamed Czechia')
    expect(JSON.stringify([older,newer])).toBe(before)
  })
  it('keeps the original Branch identity for a reachable shared ancestor',()=>{
    const shared=detail('shared-ancestor','branch-a','branch-b')
    const extracted=historicalRunWorldSnapshot(shared,'run-a','branch-b','shared-ancestor')
    expect(extracted.isShared).toBe(true)
    expect(extracted.revisionBranchId).toBe('branch-a')
    expect(projectRunWorld(extracted.response!,'run-a','branch-a',2000)).not.toBeNull()
    expect(()=>projectRunWorld(extracted.response!,'run-a','branch-b',2000)).toThrow(/ownership/)
  })
  it('fails closed on forged foreign/unreachable identity instead of using live World',()=>{
    const revision=detail('allowed-revision')
    expect(()=>historicalRunWorldSnapshot(revision,'run-a','branch-a','foreign-revision')).toThrow(/scope/)
    expect(()=>historicalRunWorldSnapshot(revision,'run-b','branch-a','allowed-revision')).toThrow(/scope/)
    const shared=detail('shared','branch-a','branch-b')
    shared.is_shared_revision=false
    expect(()=>historicalRunWorldSnapshot(shared,'run-a','branch-b','shared')).toThrow(/source branch/)
    const corrupt=detail('corrupt')
    ;((corrupt.payload.content as Record<string,unknown>).run_package_state as Record<string,unknown>).fingerprint='bad'
    expect(()=>historicalRunWorldSnapshot(corrupt,'run-a','branch-a','corrupt')).toThrow(/invalid/)
  })
  it('reports exact missing historical component rather than substituting current HEAD',()=>{
    const old=detail('empty')
    old.payload.content={}
    const answer=historicalRunWorldSnapshot(old,'run-a','branch-a','empty')
    expect(answer.response).toBeNull()
    expect(answer.revisionId).toBe('empty')
  })
})

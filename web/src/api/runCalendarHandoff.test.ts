import {describe,expect,it} from 'vitest'
import type {RunBranch,RunContainer,ViewerBranchWorkingDraft} from './types'
import {verifiedRunCalendarHandoff} from './runCalendarHandoff'

const run = {
  run_id:'run-a',storage_kind:'custom_local',read_only:false,
  status:'working'
} as RunContainer
const branch = {
  run_id:'run-a',branch_id:'branch-a',status:'active',
  read_only:false,saved_head_revision_id:'rev-a'
} as RunBranch
const draft = {
  run_id:'run-a',branch_id:'branch-a',
  status:'clean',base_saved_revision_id:'rev-a',draft_version:1
} as ViewerBranchWorkingDraft
const check=(r:RunContainer=run,b:RunBranch[]= [branch],d:ViewerBranchWorkingDraft=draft)=>
  verifiedRunCalendarHandoff(r,b,d,'run-a','branch-a')

describe('Detached Calendar handoff at current Saved Revision',()=>{
  it('accepts one exact writable active Product Run Branch and clean matching Draft',()=>{
    expect(check()).toBe(true)
  })
  it('refuses stale Saved Revision or stale Branch cache even with a clean Draft',()=>{
    expect(check(run,[{...branch,saved_head_revision_id:'rev-new'}])).toBe(false)
    expect(check(run,[branch],{...draft,base_saved_revision_id:'old'})).toBe(false)
    expect(check(run,[{...branch,saved_head_revision_id:null}])).toBe(false)
  })
  it('rejects read-only and built-in Runs or inactive/foreign Branches',()=>{
    expect(check({...run,read_only:true})).toBe(false)
    expect(check({...run,storage_kind:'built_in'})).toBe(false)
    expect(check({...run,run_id:'foreign'})).toBe(false)
    expect(check(run,[{...branch,read_only:true}])).toBe(false)
    expect(check(run,[{...branch,status:'archived'}])).toBe(false)
    expect(check(run,[{...branch,run_id:'foreign'}])).toBe(false)
    expect(check(run,[])).toBe(false)
  })
  it('rejects dirty Draft or wrong requested scope without widening authority',()=>{
    expect(check(run,[branch],{...draft,status:'dirty'})).toBe(false)
    expect(check(run,[branch],{...draft,branch_id:'other'})).toBe(false)
    expect(verifiedRunCalendarHandoff(run,[branch],draft,'run-a','other')).toBe(false)
  })
})

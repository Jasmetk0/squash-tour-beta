import {describe,expect,it} from 'vitest'
import {validateWeekExtensionInspection} from './fullSimulationWeekReview'

const h='a'.repeat(64)
const candidate=()=>({
 command_id:'week-command',week:{season_index:0,week:1},
 status:'append_only_proven' as const,reason:'operator_re_review_still_required',
 old_schedule_fingerprint:h,current_schedule_fingerprint:'b'.repeat(64),
 original_slot_count:2,new_slots:[{ordinal:3,group_id:'final',event_id:'event',round_number:1}],
 read_only:true as const, automatic_rebase:false as const
})
const report=(items:unknown)=>({schema_version:'next_week_extension_inspection.v1',run_id:'run',branch_id:'branch',read_only:true,items})
describe('Next Week inspector strict readonly evidence',()=>{
 it('accepts a scoped append-only candidate but grants no authorization',()=>{
   expect(validateWeekExtensionInspection(report([candidate()]),'run','branch')[0].automatic_rebase).toBe(false)
 })
 it('rejects forged approval flags, foreign scope and duplicate child receipts',()=>{
   expect(()=>validateWeekExtensionInspection({...report([candidate()]),run_id:'other'},'run','branch')).toThrow()
   expect(()=>validateWeekExtensionInspection(report([{...candidate(),automatic_rebase:true}]),'run','branch')).toThrow()
   expect(()=>validateWeekExtensionInspection(report([candidate(),candidate()]),'run','branch')).toThrow()
   expect(()=>validateWeekExtensionInspection(report([{...candidate(),status:'blocked'}]),'run','branch')).toThrow()
 })
})

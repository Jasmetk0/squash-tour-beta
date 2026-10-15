import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {afterEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {FullSimulationWeekScheduleReview} from './FullSimulationWeekScheduleReview'

const api=vi.hoisted(()=>({
 getNextWeekExtensionInspection:vi.fn(),approveNextWeekExtension:vi.fn()
}))
vi.mock('../api/fullSimulationWeekReview',()=>api)

const hash=(c:string)=>c.repeat(64)
const candidate=(overrides:Record<string,unknown>={})=>({
 command_id:'week-command',week:{season_index:0,week:1},
 status:'append_only_proven' as const,reason:'operator_re_review_still_required',
 old_schedule_fingerprint:hash('a'),current_schedule_fingerprint:hash('b'),
 original_slot_count:2,receipt_fingerprint:hash('c'),
 new_slots:[{ordinal:3,group_id:'final',event_id:'e1',round_number:1}],
 read_only:true as const,automatic_rebase:false as const,...overrides
})
const scope=(overrides:Record<string,string|number>={})=>({
 runId:'run',branchId:'branch',taskId:'task',taskRevision:1,...overrides
})
function mount(initial=scope()){
 const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})
 const ui=(props:ReturnType<typeof scope>)=><QueryClientProvider client={client}>
  <LanguageProvider><FullSimulationWeekScheduleReview {...props}/></LanguageProvider>
 </QueryClientProvider>
 const view=render(ui(initial))
 return {client,rerender:(props:ReturnType<typeof scope>)=>view.rerender(ui(props))}
}
async function consent(){
 await screen.findByText('week-command')
 fireEvent.change(screen.getByLabelText('Approving operator'),{target:{value:'Admin'}})
 fireEvent.change(screen.getByLabelText('Approval reason'),{target:{value:'Verified real knockout suffix'}})
 fireEvent.click(screen.getByLabelText(/I confirm that committed results/))
 expect(screen.getByRole('button',{name:'Explicitly approve week extension'})).toBeEnabled()
}
const approval=()=>screen.getByRole('button',{name:'Explicitly approve week extension'})
afterEach(()=>{vi.resetAllMocks();localStorage.clear()})
describe('week-extension consent is scoped to rendered evidence (mock HTTP)',()=>{
 it('invalidates the tick on receipt, schedule and new-slot changes, even after reverting',async()=>{
  localStorage.setItem('squash-engine-language-v1','en')
  api.getNextWeekExtensionInspection.mockResolvedValue([candidate()])
  const {client}=mount()
  const key=['next-week-extension-inspection','run','branch']
  const revisions=[
   candidate({receipt_fingerprint:hash('d')}),
   candidate({current_schedule_fingerprint:hash('e')}),
   candidate({new_slots:[{ordinal:4,group_id:'other',event_id:'e2',round_number:2}]}),
  ]
  for(const next of revisions){
   await consent()
   client.setQueryData(key,[next])
   await waitFor(()=>expect(approval()).toBeDisabled())
   expect(screen.getByLabelText(/I confirm that committed results/)).not.toBeChecked()
   client.setQueryData(key,[candidate()])
   await waitFor(()=>expect(approval()).toBeDisabled())
   expect(screen.getByLabelText(/I confirm that committed results/)).not.toBeChecked()
  }
  expect(api.approveNextWeekExtension).not.toHaveBeenCalled()
 })
 it('invalidates consent when task revision, Run, Branch or Task changes',async()=>{
  localStorage.setItem('squash-engine-language-v1','en')
  api.getNextWeekExtensionInspection.mockResolvedValue([candidate()])
  const {rerender}=mount()
  for(const change of [{taskRevision:2},{runId:'elsewhere'},{branchId:'alternate'},{taskId:'different'}]){
   await consent()
   rerender(scope(change))
   await waitFor(()=>expect(approval()).toBeDisabled())
   expect(screen.getByLabelText(/I confirm that committed results/)).not.toBeChecked()
   rerender(scope())
   await waitFor(()=>expect(approval()).toBeDisabled())
  }
  expect(api.approveNextWeekExtension).not.toHaveBeenCalled()
 })
 it('captures the displayed candidate and retries the EXACT original request after lost response and cache drift',async()=>{
  localStorage.setItem('squash-engine-language-v1','en')
  api.getNextWeekExtensionInspection.mockResolvedValue([candidate()])
  api.approveNextWeekExtension.mockRejectedValueOnce(Error('lost response'))
   .mockResolvedValue({schema_version:'next_week_extension_approval.v1',task_revision:2,replayed:true})
  const {client,rerender}=mount()
  await consent()
  fireEvent.click(approval())
  await screen.findByText('lost response')
  const first=api.approveNextWeekExtension.mock.calls[0]
  expect(first[0]).toBe('run')
  expect(first[1]).toBe('branch')
  expect(first[2]).toMatchObject({
   task_id:'task',target_week_command_id:'week-command',expected_task_revision:1,
   expected_receipt_fingerprint:hash('c'),expected_current_schedule_fingerprint:hash('b'),
   operator_label:'Admin',audit_reason:'Verified real knockout suffix'
  })
  client.setQueryData(['next-week-extension-inspection','run','branch'],[
   candidate({receipt_fingerprint:hash('f'),current_schedule_fingerprint:hash('d'),
    new_slots:[{ordinal:4,group_id:'replacement',event_id:'e2',round_number:2}]})
  ])
  rerender(scope({taskRevision:2}))
  await waitFor(()=>expect(screen.getByText(/New knockout slots: 4/)).toBeVisible())
  expect(approval()).toBeDisabled()
  fireEvent.click(screen.getByRole('button',{name:'Retry same request'}))
  await waitFor(()=>expect(api.approveNextWeekExtension).toHaveBeenCalledTimes(2))
  expect(api.approveNextWeekExtension.mock.calls[1]).toEqual(first)
  expect(screen.queryByRole('button',{name:'Explicitly resume server task'})).toBeNull()
  expect(await screen.findByText(/Resuming the server task requires another separate confirmation/)).toBeVisible()
 })
 it('cancelled uncertain request must be reapproved against current evidence',async()=>{
  localStorage.setItem('squash-engine-language-v1','en')
  api.getNextWeekExtensionInspection.mockResolvedValue([candidate()])
  api.approveNextWeekExtension.mockRejectedValueOnce(Error('offline'))
  const {client}=mount()
  await consent()
  fireEvent.click(approval())
  await screen.findByText('offline')
  client.setQueryData(['next-week-extension-inspection','run','branch'],[
   candidate({current_schedule_fingerprint:hash('e')})
  ])
  await waitFor(()=>expect(approval()).toBeDisabled())
  fireEvent.click(screen.getByRole('button',{name:'Cancel request'}))
  await waitFor(()=>expect(approval()).toBeDisabled())
  expect(screen.getByLabelText(/I confirm that committed results/)).not.toBeChecked()
  expect(api.approveNextWeekExtension).toHaveBeenCalledTimes(1)
 })
})

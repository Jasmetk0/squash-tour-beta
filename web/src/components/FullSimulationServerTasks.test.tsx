import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {afterEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {FullSimulationServerTasks,StartServerTask} from './FullSimulationServerTasks'
import {taskExample} from '../api/fullSimulationTasks.fixture'
const api=vi.hoisted(()=>({getServerTasks:vi.fn(),startServerTask:vi.fn(),continueServerTask:vi.fn()}))
const weekReview=vi.hoisted(()=>({getNextWeekExtensionInspection:vi.fn(),approveNextWeekExtension:vi.fn()}))
vi.mock('../api/fullSimulationWeekReview',()=>weekReview)
vi.mock('../api/fullSimulationTasks',async importOriginal=>({...await importOriginal<object>(),...api}))
vi.mock('./FullSimulationSummary',()=>({FullSimulationSummary:()=>null}))
function open(language:'cs'|'en',child:React.ReactNode){
 localStorage.setItem('squash-engine-language-v1',language)
 return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><LanguageProvider>{child}</LanguageProvider></MemoryRouter></QueryClientProvider>)
}
afterEach(()=>vi.resetAllMocks())
describe('server task UI (mock HTTP)',()=>{
 it.each(['cs','en'] as const)('reconnects and retries explicit recovery with unchanged audit/id/revision (%s)',async language=>{
  api.getServerTasks.mockResolvedValue([taskExample()]);api.continueServerTask.mockRejectedValueOnce(Error('offline')).mockResolvedValue({})
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  await screen.findByText('task');expect(screen.getByText('parent')).toBeVisible()
  const op=screen.getByLabelText(language==='cs'?'Operátor úlohy':'Task operator')
  const reason=screen.getByLabelText(language==='cs'?'Důvod akce úlohy':'Task audit reason')
  fireEvent.change(op,{target:{value:'Auditor'}});fireEvent.change(reason,{target:{value:'Explicit recovery'}})
  fireEvent.click(screen.getByRole('button',{name:language==='cs'?'Výslovně obnovit serverovou úlohu':'Explicitly recover server task'}))
  await screen.findByText('offline');expect(op).toBeDisabled()
  fireEvent.click(screen.getByRole('button',{name:language==='cs'?'Zopakovat stejný požadavek':'Retry same request'}))
  await waitFor(()=>expect(api.continueServerTask).toHaveBeenCalledTimes(2))
  expect(api.continueServerTask.mock.calls[0]).toEqual(api.continueServerTask.mock.calls[1])
  expect(api.continueServerTask.mock.calls[0][1]).toMatchObject({action:'recover',expected_revision:1,operator_label:'Auditor',audit_reason:'Explicit recovery'})
  expect(screen.getByRole('link').getAttribute('href')).toContain('branch=branch&task=task')
 })
 it.each(['cs','en'] as const)('keeps a dropped start response retry on the original command (%s)',async language=>{
  api.startServerTask.mockRejectedValueOnce(Error('offline')).mockResolvedValue({task_id:'task',parent_command_id:'parent'})
  open(language,<StartServerTask runId="run" branchId="branch" command={taskExample().original_command} disabled={false} onAccepted={()=>{}}/>)
  fireEvent.click(screen.getByRole('button',{name:language==='cs'?'Spustit jako serverovou úlohu':'Start as server task'}))
  await screen.findByText('offline');fireEvent.click(screen.getByRole('button',{name:language==='cs'?'Zopakovat stejný požadavek':'Retry same request'}))
  await screen.findByText('task');expect(api.startServerTask.mock.calls[0]).toEqual(api.startServerTask.mock.calls[1])
 })
 it.each(['cs','en'] as const)('labels current-week receipts and frozen historical Position honestly (%s)',async language=>{
  const live=taskExample()
  live.progress_evidence.completed_slot_receipts_this_week=1
  live.progress_evidence.committed_group_receipts_this_week=2
  const terminal={...taskExample(),task_id:'ended',state:'stopped',current_week:{season_index:0,week:2},
    progress_evidence:{...taskExample().progress_evidence,kind:'terminal_frozen',week:{season_index:0,week:2},weeks_advanced_since_start:1,
      completed_slot_receipts_this_week:null,committed_group_receipts_this_week:null,receipt_scope:null}}
  api.getServerTasks.mockResolvedValue([live,terminal])
  open(language,<FullSimulationServerTasks/>)
  await screen.findByText('ended')
  const matchLabels=language==='cs'?['Dokončené zápasové sloty: 1','Potvrzené zápasové skupiny: 2']:
    ['Completed match slots: 1','Committed match groups: 2']
  for(const label of matchLabels)expect(screen.getByText((_,element)=>element?.tagName==='P' && (element.textContent??'').includes(label))).toBeVisible()
  expect(screen.getByText(language==='cs'?'Historický koncový týden uložený při ukončení':
    'Historical end week, frozen at termination')).toBeVisible()
 })
 it('shows offline read failure without displaying stale tasks as current',async()=>{
  api.getServerTasks.mockRejectedValue(Error('offline'));open('en',<FullSimulationServerTasks/>)
  expect(await screen.findByRole('alert')).toHaveTextContent('offline');expect(screen.queryByRole('link')).toBeNull()
 })
 it.each(['cs','en'] as const)('identifies changed reviewed weeks without offering unsafe task resume (%s)',async language=>{
  const stale={...taskExample(),state:'awaiting_operator',checkpoint:'week_schedule_review_required',
    needs_operator_action:true,error:null}
  api.getServerTasks.mockResolvedValue([stale])
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  expect(await screen.findByRole('alert')).toHaveTextContent(language==='cs'
    ? 'Původní příkaz nesmí nové zápasy převzít automaticky'
    : 'The original command cannot silently absorb')
  expect(screen.queryByLabelText(language==='cs'?'Operátor úlohy':'Task operator')).toBeNull()
  expect(screen.queryByRole('button',{name:language==='cs'?'Výslovně pokračovat v serverové úloze':'Explicitly resume server task'})).toBeNull()
  expect(api.continueServerTask).not.toHaveBeenCalled()
  expect(screen.getByRole('link').getAttribute('href')).toContain('branch=branch')
 })

 it.each(['cs','en'] as const)('inspects frozen hybrid extension without approving or resuming (%s)',async language=>{
  const stale={...taskExample(),state:'awaiting_operator',checkpoint:'week_schedule_review_required',
    needs_operator_action:true,error:null}
  api.getServerTasks.mockResolvedValue([stale])
  weekReview.getNextWeekExtensionInspection.mockResolvedValue([{
    command_id:'old-week-child',status:'append_only_proven',receipt_fingerprint:'a'.repeat(64),current_schedule_fingerprint:'b'.repeat(64),new_slots:[
      {ordinal:4,group_id:'final',event_id:'event',round_number:1}
    ]
  }])
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  expect(await screen.findByText('old-week-child')).toBeVisible()
  expect(screen.getByText(language==='cs'
    ? /Nové knockout sloty: 4/
    : /New knockout slots: 4/)).toBeVisible()
  expect(weekReview.getNextWeekExtensionInspection).toHaveBeenCalledWith('run','branch')
  expect(screen.queryByRole('button',{name:language==='cs'
    ?'Výslovně pokračovat v serverové úloze':'Explicitly resume server task'})).toBeNull()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })

 it.each(['cs','en'] as const)('requires audited consent before approving only the verified new suffix (%s)',async language=>{
  const original={...taskExample(),state:'awaiting_operator',revision:1,
    checkpoint:'week_schedule_review_required',needs_operator_action:true,error:null}
  api.getServerTasks.mockResolvedValue([original])
  weekReview.getNextWeekExtensionInspection.mockResolvedValue([{
    command_id:'reviewed-week',status:'append_only_proven',receipt_fingerprint:'a'.repeat(64),
    current_schedule_fingerprint:'b'.repeat(64),
    new_slots:[{ordinal:3,group_id:'hybrid-final',event_id:'e1',round_number:1}]
  }])
  weekReview.approveNextWeekExtension.mockResolvedValue({schema_version:'next_week_extension_approval.v1',task_revision:2,replayed:false})
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  await screen.findByText('reviewed-week')
  const approve=screen.getByRole('button',{name:language==='cs'?'Výslovně schválit rozšíření týdne':'Explicitly approve week extension'})
  expect(approve).toBeDisabled()
  fireEvent.change(screen.getByLabelText(language==='cs'?'Schvalující operátor':'Approving operator'),{target:{value:'Operator'}})
  fireEvent.change(screen.getByLabelText(language==='cs'?'Důvod schválení':'Approval reason'),{target:{value:'Reviewed genuine suffix'}})
  fireEvent.click(screen.getByLabelText(language==='cs'?/Potvrzuji, že stávající výsledky/:/I confirm that committed results/))
  expect(approve).not.toBeDisabled()
  fireEvent.click(approve)
  await waitFor(()=>expect(weekReview.approveNextWeekExtension).toHaveBeenCalledTimes(1))
  expect(weekReview.approveNextWeekExtension.mock.calls[0][2]).toMatchObject({
    task_id:'task',expected_task_revision:1,target_week_command_id:'reviewed-week',
    expected_receipt_fingerprint:'a'.repeat(64),
    expected_current_schedule_fingerprint:'b'.repeat(64),
    confirm_committed_work_is_immutable:true,operator_label:'Operator',
    audit_reason:'Reviewed genuine suffix'
  })
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })

 it.each(['cs','en'] as const)('guides unresolved real group phases without fabricating approvals (%s)',async language=>{
  const task={...taskExample(),state:'awaiting_operator',
    checkpoint:'group_phase_review_required',needs_operator_action:true,error:null}
  api.getServerTasks.mockResolvedValue([task])
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  const match=language==='cs'?'skupinovou fázi':'unresolved group phase'
  expect(await screen.findByText((_,node)=>node?.tagName==='P'&&Boolean(node.textContent?.includes(match)))).toBeVisible()
  expect(screen.queryByLabelText(language==='cs'
    ?'Kontrola změněného týdenního rozpisu'
    :'Changed week schedule inspection')).toBeNull()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })

 it.each(['cs','en'] as const)('shows actual driver detail and blockers at current operator checkpoint (%s)',async language=>{
  const task={...taskExample(),state:'awaiting_operator',checkpoint:'week_preparation_required',
   needs_operator_action:true,progress:{
    schema_version:'authoritative_full_simulation_progress.v1',
    checkpoint:'week_preparation_required',status:'blocked',
    detail:'Missing real 2001/02 tournament configuration',blockers:['week_preparation_required','ranking_policy_missing']
   }}
  api.getServerTasks.mockResolvedValue([task])
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  expect(await screen.findByText(/Missing real 2001\/02 tournament configuration/)).toBeVisible()
  const details=screen.getByText(language==='cs'
   ? /Podklady serverového průchodu · Aktuální překážky/
   : /Driver evidence · Current blockers/).closest('details')
  expect(details).toHaveAttribute('open')
  expect(details).toHaveTextContent('ranking_policy_missing')
  expect(screen.getByText(language==='cs'?/Zkontrolujte přípravu týdne/:/Inspect this Branch’s week preparation/)).toBeVisible()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it.each(['cs','en'] as const)('does not mistake a historical checkpoint for a current blocker after task resumes (%s)',async language=>{
  const task={...taskExample(),state:'active',checkpoint:'week_preparation_required',
   needs_operator_action:false,progress:{
    schema_version:'authoritative_full_simulation_progress.v1',checkpoint:'week_preparation_required',
    status:'blocked',detail:'Historical preparation required',blockers:['week_preparation_required']
   }}
  api.getServerTasks.mockResolvedValue([task])
  open(language,<FullSimulationServerTasks/>)
  expect(await screen.findByText('task')).toBeVisible()
  expect(screen.getByText(language==='cs'
   ? 'Poslední zaznamenaný checkpoint (není aktuální překážkou)'
   : 'Last recorded checkpoint (not a current blocker)')).toBeInTheDocument()
  const details=screen.getByText(language==='cs'?'Podklady serverového průchodu':'Driver evidence').closest('details')
  expect(details).not.toHaveAttribute('open')
  expect(screen.queryByText(language==='cs'?/Zkontrolujte přípravu týdne/:/Inspect this Branch’s week preparation/)).toBeNull()
  expect(screen.queryByRole('button',{name:language==='cs'?'Výslovně pokračovat v serverové úloze':'Explicitly resume server task'})).toBeNull()
 })
 it.each(['cs','en'] as const)('shows inspection-specific blocker rather than instructing unsafe Stop (%s)',async language=>{
  const task={...taskExample(),state:'awaiting_operator',checkpoint:'week_schedule_review_required',needs_operator_action:true}
  api.getServerTasks.mockResolvedValue([task])
  weekReview.getNextWeekExtensionInspection.mockResolvedValue([{
   command_id:'blocked-week',status:'blocked',reason:'append_only_prefix_mismatch',
   new_slots:[]
  }])
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  expect(await screen.findByText('append_only_prefix_mismatch')).toBeVisible()
  expect(screen.queryByRole('button',{name:language==='cs'?'Výslovně schválit rozšíření týdne':'Explicitly approve week extension'})).toBeNull()
  expect(screen.queryByText(/Stop that simulation|bezpečně ukončete původní simulaci/)).toBeNull()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })

 it.each(['cs','en'] as const)('offers a safe exact Branch new-season Calendar handoff only for current week preparation (%s)',async language=>{
  const waiting={...taskExample(),state:'awaiting_operator',
   checkpoint:'week_preparation_required',needs_operator_action:true,
   current_week:{season_index:1,week:1},progress_evidence:{
    ...taskExample().progress_evidence,
    week:{season_index:1,week:1},weeks_advanced_since_start:61,
   }}
  api.getServerTasks.mockResolvedValue([waiting])
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  const link=await screen.findByRole('link',{name:language==='cs'
   ?'Prověřit kalendář aktuální sezony ve správě Runu'
   :'Review this season’s Calendar in Run Management'})
  expect(link).toHaveAttribute('href','/admin/runs/run/manage?branch=branch&calendarSeason=2001-2002')
  expect(screen.getByText(language==='cs'?/chybějící kalendář neznamená prázdný týden/:/absent Calendar means an empty week/)).toBeVisible()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it('does not suggest missing Calendar as cause when task has resumed or no preparation checkpoint',async()=>{
  api.getServerTasks.mockResolvedValue([{
   ...taskExample(),state:'active',checkpoint:'week_preparation_required',needs_operator_action:false,
   current_week:{season_index:1,week:1}
  }])
  open('en',<FullSimulationServerTasks/>)
  expect(await screen.findByText('task')).toBeVisible()
  expect(screen.queryByRole('link',{name:'Review this season’s Calendar in Run Management'})).toBeNull()
 })

})

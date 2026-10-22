import {QueryClient,QueryClientProvider,onlineManager} from '@tanstack/react-query'
import {useState} from 'react'
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
const summaryMock=vi.hoisted(()=>({render:vi.fn()}))
vi.mock('./FullSimulationSummary',()=>({FullSimulationSummary:(props:unknown)=>{summaryMock.render(props);return null}}))
function open(language:'cs'|'en',child:React.ReactNode,initialPath='/'){
 localStorage.setItem('squash-engine-language-v1',language)
 return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter initialEntries={[initialPath]}><LanguageProvider>{child}</LanguageProvider></MemoryRouter></QueryClientProvider>)
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
 it('does not fetch every terminal summary until an operator expands its evidence',async()=>{
  const a={...taskExample(),task_id:'completed-one',parent_command_id:'parent-one',
    state:'complete',desired_state:'complete',needs_operator_action:false}
  const b={...taskExample(),task_id:'completed-two',parent_command_id:'parent-two',
    state:'stopped',desired_state:'stopped',needs_operator_action:false}
  api.getServerTasks.mockResolvedValue([a,b])
  open('en',<FullSimulationServerTasks/>)
  await screen.findByText('completed-two')
  expect(summaryMock.render).not.toHaveBeenCalled()
  const terminal=screen.getAllByText('Stored terminal summary').map(el=>el.closest('details')!)
  expect(terminal).toHaveLength(2)
  terminal[0].open=true
  fireEvent(terminal[0],new Event('toggle',{bubbles:true}))
  await waitFor(()=>expect(summaryMock.render).toHaveBeenCalled())
  expect(summaryMock.render.mock.calls.every(([props])=>
    (props as {commandId:string}).commandId==='parent-one'||
    (props as {commandId:string}).commandId==='parent-two')).toBe(true)
  const rendered=summaryMock.render.mock.calls.map(([props])=>(props as {commandId:string}).commandId)
  expect(new Set(rendered).size).toBe(1)
  expect(rendered[0]).toBe(terminal[0].parentElement?.getAttribute('data-task-id')==='completed-one'?'parent-one':'parent-two')
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
  expect(link).toHaveAttribute('href','/admin/runs/run/manage?branch=branch')
  expect(screen.getByText(language==='cs'?/chybějící kalendář neznamená prázdný týden/:/missing Calendar means an empty week/)).toBeVisible()
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

 it('replays a queued start against its original Run, Branch and command after switching context',async()=>{
  api.startServerTask.mockResolvedValue({task_id:'task',parent_command_id:'parent'})
  const initial=taskExample().original_command
  function Switch(){
   const [other,setOther]=useState(false)
   return <><button onClick={()=>setOther(true)}>Switch context</button>
    <StartServerTask runId={other?'run-other':'run'} branchId={other?'branch-other':'branch'}
     command={other?{...initial,command_id:'different-parent'}:initial} disabled={false} onAccepted={()=>{}}/></>
  }
  onlineManager.setOnline(false)
  try{
   open('en',<Switch/>)
   fireEvent.click(screen.getByRole('button',{name:'Start as server task'}))
   fireEvent.click(screen.getByRole('button',{name:'Switch context'}))
   expect(screen.getByRole('button',{name:'Start as server task'})).toBeDisabled()
   expect(screen.getByRole('alert')).toHaveTextContent('different Run, Branch or command')
   onlineManager.setOnline(true)
   await waitFor(()=>expect(api.startServerTask).toHaveBeenCalledTimes(1))
   expect(api.startServerTask.mock.calls[0].slice(0,3)).toEqual(['run','branch','server-start-parent'])
   expect(api.startServerTask.mock.calls[0][3]).toMatchObject({command_id:'parent'})
   expect(screen.queryByText('Server task accepted')).toBeNull()
  }finally{onlineManager.setOnline(true)}
 })
 it('retries a task continuation with the original task identity after a polling revision change',async()=>{
  const first=taskExample()
  const revised={...first,revision:2,events:[...first.events,{...first.events[0],revision:2,previous:first.events[0].fingerprint}]}
  api.getServerTasks.mockResolvedValueOnce([first]).mockResolvedValue([revised])
  api.continueServerTask.mockRejectedValueOnce(Error('connection lost')).mockResolvedValue({})
  open('en',<FullSimulationServerTasks runId="run" branchId="branch"/>)
  await screen.findByText('task')
  fireEvent.change(screen.getByLabelText('Task operator'),{target:{value:'Operator'}})
  fireEvent.change(screen.getByLabelText('Task audit reason'),{target:{value:'Reviewed resume'}})
  fireEvent.click(screen.getByRole('button',{name:'Explicitly recover server task'}))
  await screen.findByText('connection lost')
  fireEvent.click(screen.getByRole('button',{name:'Refresh task evidence'}))
  await waitFor(()=>expect(api.getServerTasks).toHaveBeenCalledTimes(2))
  fireEvent.click(screen.getByRole('button',{name:'Retry same request'}))
  await waitFor(()=>expect(api.continueServerTask).toHaveBeenCalledTimes(2))
  expect(api.continueServerTask.mock.calls[0]).toEqual(api.continueServerTask.mock.calls[1])
  expect(api.continueServerTask.mock.calls[1][0].revision).toBe(1)
  expect(api.continueServerTask.mock.calls[1][1].expected_revision).toBe(1)
 }) 
 it.each(['cs','en'] as const)('surfaces actual action-required tasks first without claiming a healthy worker (%s)',async language=>{
  const active={...taskExample(),task_id:'queued-other',state:'active',
    needs_operator_action:false,checkpoint:null,heartbeat_health:'stale'}
  const blocked={...taskExample(),task_id:'needs-decision',state:'awaiting_operator',
    checkpoint:'week_preparation_required',needs_operator_action:true}
  api.getServerTasks.mockResolvedValue([active,blocked])
  open(language,<FullSimulationServerTasks/>)
  await screen.findByText('needs-decision')
  const items=screen.getAllByRole('listitem').filter(node=>node.hasAttribute('data-task-id'))
  expect(items[0]).toHaveAttribute('data-task-id','needs-decision')
  const activeItem=items.find(item=>item.getAttribute('data-task-id')==='queued-other')!
  expect(activeItem).toHaveTextContent(language==='cs'
   ? 'Aktivní stav úlohy (zdraví workeru nepotvrzeno)'
   : 'Active task state (worker health unverified)')
  const counts=screen.getByRole('status')
  expect(counts).toHaveTextContent(language==='cs'?'Vyžaduje zásah operátora: 1':'Operator action required: 1')
  expect(counts).toHaveTextContent(language==='cs'?'zdraví procesu nepotvrzeno':'health unconfirmed')
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it.each(['cs','en'] as const)('does not offer a resume action for a lease owned by another server (%s)',async language=>{
  const task={...taskExample(),state:'ownership_unverified',heartbeat_health:'stale',
    needs_operator_action:false,lease_expires_at_unix:2000000000}
  api.getServerTasks.mockResolvedValue([task])
  open(language,<FullSimulationServerTasks/>)
  await screen.findByText('task')
  expect(screen.getByText(language==='cs'
    ? /Lease vlastní jiná instance serveru/:/Another server instance owns the lease/)).toBeInTheDocument()
  expect(screen.queryByLabelText(language==='cs'?'Operátor úlohy':'Task operator')).toBeNull()
  expect(screen.queryByRole('button',{name:language==='cs'
    ? 'Výslovně obnovit serverovou úlohu':'Explicitly recover server task'})).toBeNull()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it.each(['cs','en'] as const)('filters stored tasks by actual operator action, non-actionable activity and exact parent identity (%s)',async language=>{
  const needs={...taskExample(),task_id:'needs-approval',parent_command_id:'parent-review',
    state:'awaiting_operator',checkpoint:'week_preparation_required',needs_operator_action:true}
  const active={...taskExample(),task_id:'task-running',parent_command_id:'parent-live',
    state:'active',needs_operator_action:false,heartbeat_health:'stale'}
  const done={...taskExample(),task_id:'task-complete',parent_command_id:'parent-complete',
    state:'complete',needs_operator_action:false}
  api.getServerTasks.mockResolvedValue([done,active,needs])
  open(language,<FullSimulationServerTasks/>)
  await screen.findByText('needs-approval')
  const label=language==='cs'?'Kategorie úloh':'Task category'
  const searchLabel=language==='cs'?'Najít serverovou úlohu':'Find a server task'
  const visible=()=>screen.getAllByRole('listitem').filter(node=>node.hasAttribute('data-task-id'))
    .map(node=>node.getAttribute('data-task-id'))
  expect(visible()).toEqual(['needs-approval','task-running','task-complete'])
  fireEvent.change(screen.getByRole('combobox',{name:label}),{target:{value:'attention'}})
  expect(visible()).toEqual(['needs-approval'])
  fireEvent.change(screen.getByRole('combobox',{name:label}),{target:{value:'live'}})
  expect(visible()).toEqual(['task-running'])
  fireEvent.change(screen.getByRole('combobox',{name:label}),{target:{value:'other'}})
  expect(visible()).toEqual(['task-complete'])
  fireEvent.change(screen.getByRole('combobox',{name:label}),{target:{value:'all'}})
  fireEvent.change(screen.getByRole('searchbox',{name:searchLabel}),{target:{value:'PARENT-LIVE'}})
  expect(visible()).toEqual(['task-running'])
  fireEvent.change(screen.getByRole('combobox',{name:label}),{target:{value:'attention'}})
  expect(screen.queryByRole('listitem')).toBeNull()
  expect(screen.getByText(language==='cs'
    ? /Hledání a kategorie neodpovídá žádná úloha/
    : /No tasks match the current search and category/)).toBeVisible()
  fireEvent.click(screen.getByRole('button',{name:language==='cs'?'Zrušit filtry':'Clear filters'}))
  expect(visible()).toEqual(['needs-approval','task-running','task-complete'])
  expect(screen.getByRole('combobox',{name:label})).toHaveValue('all')
  expect(screen.getByRole('searchbox',{name:searchLabel})).toHaveValue('')
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it('keeps the exact deep-linked task visible even if operator filters exclude it',async()=>{
  const active={...taskExample(),task_id:'current-link',parent_command_id:'other-parent',
    state:'active',needs_operator_action:false}
  const attention={...taskExample(),task_id:'another',parent_command_id:'another-parent',
    state:'awaiting_operator',needs_operator_action:true}
  api.getServerTasks.mockResolvedValue([active,attention])
  open('en',<FullSimulationServerTasks runId="run" branchId="branch"/>,
    '/admin/runs/run/simulate?branch=branch&task=current-link')
  await screen.findByText('Task selected from the link:',{exact:false})
  fireEvent.change(screen.getByRole('combobox',{name:'Task category'}),{target:{value:'attention'}})
  fireEvent.change(screen.getByRole('searchbox',{name:'Find a server task'}),{target:{value:'another-parent'}})
  const cards=screen.getAllByRole('listitem').filter(node=>node.hasAttribute('data-task-id'))
  expect(cards.map(node=>node.getAttribute('data-task-id'))).toEqual(['current-link','another'])
  expect(cards[0]).toHaveAttribute('aria-current','location')
  expect(screen.getByText('Linked task stays visible regardless of filters.')).toBeInTheDocument()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it.each(['cs','en'] as const)('does not fall back to global task inventory when scoped Branch is unresolved (%s)',async language=>{
  api.getServerTasks.mockResolvedValue([taskExample()])
  open(language,<FullSimulationServerTasks runId="run" branchId=""/>)
  expect(screen.getByRole('alert')).toHaveTextContent(language==='cs'
    ? 'Před zobrazením úloh vyberte platný Run a větev'
    : 'Select a valid Run and Branch')
  expect(screen.queryByText('task')).toBeNull()
  expect(screen.queryByText(language==='cs'?'Načítám serverové úlohy…':'Loading server tasks…')).toBeNull()
  const refresh=screen.getByRole('button',{name:language==='cs'?'Obnovit údaje úloh':'Refresh task evidence'})
  expect(refresh).toBeDisabled()
  fireEvent.click(refresh)
  expect(api.getServerTasks).not.toHaveBeenCalled()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it('fails closed if both scope parameters are present but empty',async()=>{
  api.getServerTasks.mockResolvedValue([taskExample()])
  open('en',<FullSimulationServerTasks runId="" branchId=""/>)
  expect(screen.getByRole('alert')).toHaveTextContent('No global inventory was requested')
  expect(screen.getByRole('button',{name:'Refresh task evidence'})).toBeDisabled()
  expect(api.getServerTasks).not.toHaveBeenCalled()
 })
 it('preserves the intentional unscoped Global Task Center inventory request',async()=>{
  api.getServerTasks.mockResolvedValue([taskExample()])
  open('en',<FullSimulationServerTasks/>)
  expect(await screen.findByText('task')).toBeInTheDocument()
  expect(api.getServerTasks).toHaveBeenCalledWith(undefined,undefined)
  expect(screen.queryByText(/No global inventory was requested/)).toBeNull()
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it.each(['cs','en'] as const)('opens the exact linked task first without inventing an action (%s)',async language=>{
  const other={...taskExample(),task_id:'other',parent_command_id:'other-parent'}
  api.getServerTasks.mockResolvedValue([other,taskExample()])
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>,
   '/admin/runs/run/simulate?branch=branch&task=task')
  await screen.findByText(language==='cs'?/Úloha vybraná z odkazu/:/Task selected from the link/)
  const tasks=screen.getAllByRole('listitem').filter(node=>node.hasAttribute('data-task-id'))
  expect(tasks[0]).toHaveAttribute('data-task-id','task')
  expect(tasks[0]).toHaveAttribute('aria-current','location')
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it.each(['cs','en'] as const)('does not label a paused task historical blocker as current (%s)',async language=>{
  const historical={...taskExample(),state:'paused',desired_state:'paused',
    checkpoint:'week_preparation_required',needs_operator_action:false}
  const safe={...taskExample(),task_id:'safe-pause',state:'paused',desired_state:'paused',
    checkpoint:'operator_paused',needs_operator_action:false}
  api.getServerTasks.mockResolvedValue([historical,safe])
  open(language,<FullSimulationServerTasks runId="run" branchId="branch"/>)
  await screen.findByText('safe-pause')
  const cards=screen.getAllByRole('listitem').filter(el=>el.hasAttribute('data-task-id'))
  const past=cards.find(el=>el.getAttribute('data-task-id')==='task')!
  const current=cards.find(el=>el.getAttribute('data-task-id')==='safe-pause')!
  expect(past).toHaveTextContent(language==='cs'?'Poslední zaznamenaný checkpoint':'Last recorded checkpoint')
  expect(past).not.toHaveTextContent(language==='cs'?'Aktuální checkpoint operátora':'Current operator checkpoint')
  expect(current).toHaveTextContent(language==='cs'?'Aktuální checkpoint bezpečného pozastavení':'Current safe-pause checkpoint')
  expect(current).not.toHaveTextContent(language==='cs'?'Aktuální checkpoint operátora':'Current operator checkpoint')
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it('does not carry an unfinished operator form into a different Branch with the same task ID',async()=>{
  api.getServerTasks.mockImplementation(async(_run:string,branch:string)=>[
   {...taskExample(),branch_id:branch,branch_name:branch}
  ])
  function Switch(){
   const [branch,setBranch]=useState('branch')
   return <><button type="button" onClick={()=>setBranch('other-branch')}>Change branch</button>
    <FullSimulationServerTasks runId="run" branchId={branch}/></>
  }
  open('en',<Switch/>)
  const operator=await screen.findByLabelText('Task operator')
  fireEvent.change(operator,{target:{value:'Operator from previous Branch'}})
  expect(operator).toHaveValue('Operator from previous Branch')
  fireEvent.change(screen.getByRole('searchbox',{name:'Find a server task'}),{target:{value:'task'}})
  fireEvent.change(screen.getByRole('combobox',{name:'Task category'}),{target:{value:'attention'}})
  fireEvent.click(screen.getByRole('button',{name:'Change branch'}))
  await waitFor(()=>expect(screen.getByText('World / other-branch')).toBeVisible())
  expect(screen.getByLabelText('Task operator')).toHaveValue('')
  expect(screen.getByLabelText('Task audit reason')).toHaveValue('')
  expect(screen.getByRole('searchbox',{name:'Find a server task'})).toHaveValue('')
  expect(screen.getByRole('combobox',{name:'Task category'})).toHaveValue('all')
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
 it('reports a deep link to a missing task without acting on another one',async()=>{
  api.getServerTasks.mockResolvedValue([taskExample()])
  open('en',<FullSimulationServerTasks runId="run" branchId="branch"/>,
   '/admin/runs/run/simulate?branch=branch&task=unknown')
  expect(await screen.findByRole('alert')).toHaveTextContent('linked task was not found')
  expect(api.continueServerTask).not.toHaveBeenCalled()
 })
})

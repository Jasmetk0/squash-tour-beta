import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {afterEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {FullSimulationServerTasks,StartServerTask} from './FullSimulationServerTasks'
import {taskExample} from '../api/fullSimulationTasks.fixture'
const api=vi.hoisted(()=>({getServerTasks:vi.fn(),startServerTask:vi.fn(),continueServerTask:vi.fn()}))
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
})

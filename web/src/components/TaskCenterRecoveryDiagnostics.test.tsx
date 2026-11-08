import {fireEvent,render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import type {ServerTask} from '../api/fullSimulationTasks'
import type {GlobalFullSimulationOperations} from '../api/types'
import {LanguageProvider} from '../i18n/LanguageContext'
import {TaskCenterRecoveryDiagnostics} from './TaskCenterRecoveryDiagnostics'

const task={
  run_id:'run /A',branch_id:'branch B',task_id:'task: 12',parent_command_id:'start-command',
  run_name:'Example run',branch_name:'Timeline 2',state:'awaiting_operator',
  desired_state:'paused',revision:2,checkpoint:'native_entry_review_required',
  heartbeat_health:'inactive',heartbeat_unix:1700000000,lease_expires_at_unix:null,
  needs_operator_action:true,current_week:{season_index:1,week:30},
  progress_evidence:{kind:'live_branch'},
  original_command:{private_api_key:'this-is-private'},events:[]
} as unknown as ServerTask
const receipts={
  schema_version:'global_full_simulation_operations.v1',
  visibility:'durable_receipts_only',pending_count:1,legacy_pending_count:0,
  operations:[{run_id:'run /A',branch_id:'branch B',command_id:'start-command',
    control_state:'paused',lease_state:'absent'}]
} as unknown as GlobalFullSimulationOperations

function mount(opts:{tasks?:readonly ServerTask[]|null;inventory?:GlobalFullSimulationOperations|null;fresh?:boolean}={}) {
  return render(<MemoryRouter><LanguageProvider>
    <TaskCenterRecoveryDiagnostics
      tasks={opts.tasks===undefined?[task]:opts.tasks}
      inventory={opts.inventory===undefined?receipts:opts.inventory}
      fresh={opts.fresh??true}
    />
  </LanguageProvider></MemoryRouter>)
}
describe('global Task Center CS/EN recovery evidence',()=>{
  beforeEach(()=>{localStorage.clear()})
  it('shows a truthful summary and never creates a mutation button',()=>{
    mount()
    expect(screen.getByRole('region',{name:'Diagnostika obnovy Full Simulation'}))
      .toBeInTheDocument()
    expect(screen.getByText(/Vyžadují operátora: 1/)).toBeVisible()
    expect(screen.getByText(/Nejednoznačné přiřazení: 0/)).toBeVisible()
    expect(screen.getByRole('button',{name:'Stáhnout diagnostiku JSON'})).toBeEnabled()
    expect(screen.queryByRole('button',{name:/Resume|Pokračovat|Save|Stop/})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Zobrazit podrobnosti'}))
    expect(screen.getByText('Example run / Timeline 2')).toBeVisible()
    expect(screen.getAllByText(/Vyžaduje rozhodnutí operátora/).length).toBeGreaterThan(0)
    expect(screen.getByRole('link',{name:'Otevřít řízení ve správné Branch'})).toHaveAttribute(
      'href','/admin/runs/run%20%2FA/simulate?branch=branch%20B&task=task%3A%2012')
  })
  it('shows English with exact same persisted identities',()=>{
    localStorage.setItem('squash-engine-language-v1','en')
    mount()
    expect(screen.getByRole('region',{name:'Full Simulation recovery diagnostics'})).toBeVisible()
    fireEvent.click(screen.getByRole('button',{name:'Show details'}))
    expect(screen.getByRole('link',{name:'Open controls in exact Branch'}))
      .toHaveAttribute('href','/admin/runs/run%20%2FA/simulate?branch=branch%20B&task=task%3A%2012')
  })
  it('removes old evidence and export when either independent query is fetching',()=>{
    const view=mount()
    expect(screen.getByRole('button',{name:'Stáhnout diagnostiku JSON'})).toBeVisible()
    view.rerender(<MemoryRouter><LanguageProvider>
      <TaskCenterRecoveryDiagnostics tasks={[task]} inventory={receipts} fresh={false}/>
    </LanguageProvider></MemoryRouter>)
    expect(screen.queryByRole('button',{name:'Stáhnout diagnostiku JSON'})).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('nelze ověřit')
  })
  it('blocks incomplete/corrupt inventory, never treats it as an empty task center',()=>{
    mount({inventory:{...receipts,pending_count:100}})
    expect(screen.getByRole('alert')).toHaveTextContent('Záznamy nejsou vzájemně důvěryhodné')
    expect(screen.queryByRole('button',{name:'Stáhnout diagnostiku JSON'})).not.toBeInTheDocument()
  })
  it('preserves the task priority filter while avoiding extra network requests',()=>{
    mount({tasks:[task,{...task,task_id:'other',parent_command_id:'another',
      needs_operator_action:false,heartbeat_health:'recent',state:'active'}]})
    fireEvent.click(screen.getByRole('button',{name:'Zobrazit podrobnosti'}))
    expect(screen.getAllByRole('link',{name:'Otevřít řízení ve správné Branch'})).toHaveLength(2)
    fireEvent.change(screen.getByRole('combobox',{name:'Signál'}),{
      target:{value:'operator_action'}
    })
    expect(screen.getAllByRole('link',{name:'Otevřít řízení ve správné Branch'})).toHaveLength(1)
    expect(screen.queryByText('another')).not.toBeInTheDocument()
  })
  it('exports only bounded evidence without original command payload',()=>{
    const create=vi.fn(()=> 'blob:task-debug')
    const revoke=vi.fn()
    vi.stubGlobal('URL',{createObjectURL:create,revokeObjectURL:revoke})
    try{
      const spy=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{})
      mount()
      fireEvent.click(screen.getByRole('button',{name:'Stáhnout diagnostiku JSON'}))
      expect(create).toHaveBeenCalledTimes(1)
      expect(revoke).toHaveBeenCalledWith('blob:task-debug')
      expect(spy).toHaveBeenCalledOnce()
      spy.mockRestore()
    }finally{vi.unstubAllGlobals()}
  })
})

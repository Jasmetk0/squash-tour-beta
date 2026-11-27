import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminSimulationMonitor } from './AdminSimulationMonitor'
import { taskExample } from '../api/fullSimulationTasks.fixture'

const api=vi.hoisted(()=>({getServerTasks:vi.fn()}))
vi.mock('../api/fullSimulationTasks',()=>api)
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))

function mount(client=new QueryClient({defaultOptions:{queries:{retry:false}}})){
  return render(<QueryClientProvider client={client}><MemoryRouter>
    <AdminSimulationMonitor/>
  </MemoryRouter></QueryClientProvider>)
}
function active(){
  return {...taskExample(),run_id:'run/A',branch_id:'branch B',task_id:'task:1',
    run_name:'Simulation world',branch_name:'Simulation branch',state:'active',
    needs_operator_action:false,heartbeat_health:'recent'}
}

describe('Admin simulation monitor',()=>{
  beforeEach(()=>{
    sessionStorage.clear()
    vi.clearAllMocks()
    api.getServerTasks.mockResolvedValue([active()])
  })
  it('does not read global tasks until opted in; uses exact encoded task link',async()=>{
    const view=mount()
    const button=screen.getByRole('button',{name:'Monitor simulations'})
    expect(button).toHaveAttribute('aria-pressed','false')
    expect(api.getServerTasks).not.toHaveBeenCalled()
    await userEvent.click(button)
    expect(await screen.findByText('Simulation world / Simulation branch')).toBeInTheDocument()
    const region=screen.getByRole('region',{name:'Simulation monitor'})
    expect(region).toHaveTextContent('Active task state')
    expect(region).toHaveTextContent('S1 W1')
    expect(region).toHaveTextContent('not proof of a running process')
    expect(within(region).getByRole('link',{name:'Open exact task'})).toHaveAttribute(
      'href','/admin/runs/run%2FA/simulate?branch=branch%20B&task=task%3A1')
    expect(api.getServerTasks).toHaveBeenCalledTimes(1)
    view.unmount()
    mount()
    expect(screen.getByRole('button',{name:'Disable monitoring'})).toHaveAttribute('aria-pressed','true')
    await screen.findByText('Simulation world / Simulation branch')
    await userEvent.click(screen.getByRole('button',{name:'Disable monitoring'}))
    expect(screen.queryByRole('link',{name:'Open exact task'})).not.toBeInTheDocument()
    expect(sessionStorage.getItem('squash-engine-simulation-monitor-v1')).toBe('off')
  })
  it('does not arbitrarily choose between candidate active tasks',async()=>{
    api.getServerTasks.mockResolvedValue([active(),{...active(),task_id:'other',run_id:'other-run'}])
    mount()
    await userEvent.click(screen.getByRole('button',{name:'Monitor simulations'}))
    expect(await screen.findByText(/Multiple candidate active tasks/)).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Open exact task'})).not.toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Open Task Center'})).toHaveAttribute('href','/admin/operations')
  })
  it('offers the exact paused task without implying worker activity',async()=>{
    api.getServerTasks.mockResolvedValue([{...active(),state:'paused',needs_operator_action:true,heartbeat_health:'inactive'}])
    mount()
    await userEvent.click(screen.getByRole('button',{name:'Monitor simulations'}))
    expect(await screen.findByText('Tasks requiring action: 1')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Open exact task'})).toHaveAttribute('href',
      '/admin/runs/run%2FA/simulate?branch=branch%20B&task=task%3A1')
    expect(screen.queryByText(/Active task state/)).not.toBeInTheDocument()
  })
  it('reuses the existing global cache and hides evidence after a failed refresh',async()=>{
    const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
    client.setQueryData(['server-simulation-tasks',null,null],[active()])
    api.getServerTasks.mockRejectedValue(new Error('offline'))
    mount(client)
    await userEvent.click(screen.getByRole('button',{name:'Monitor simulations'}))
    expect(await screen.findByText('Simulation world / Simulation branch')).toBeInTheDocument()
    expect(api.getServerTasks).not.toHaveBeenCalled()
    void client.invalidateQueries({queryKey:['server-simulation-tasks',null,null]})
    await waitFor(()=>expect(screen.getByText('Simulation evidence unavailable.')).toBeInTheDocument())
    expect(screen.queryByRole('link',{name:'Open exact task'})).not.toBeInTheDocument()
    expect(screen.queryByText(/Last read contains no active/)).not.toBeInTheDocument()
  })
})

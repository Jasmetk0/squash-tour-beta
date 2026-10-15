const linkedServerTasks=vi.hoisted(()=>({data:[] as {run_id:string;branch_id:string;parent_command_id:string;task_id:string}[]}))
vi.mock('../components/FullSimulationServerTasks',()=>({
 FullSimulationServerTasks:()=>null,
 useServerTasks:()=>({isSuccess:true,data:linkedServerTasks.data})
}))
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../i18n/LanguageContext'
import { GlobalSimulationTaskCenterPage } from './GlobalSimulationTaskCenterPage'

const api = vi.hoisted(() => ({
  getGlobalFullSimulationOperations: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../api/client', () => api)

const example = {
  schema_version: 'global_full_simulation_operations.v1',
  visibility: 'durable_receipts_only',
  pending_count: 3,
  legacy_pending_count: 1,
  operations: [
    {
      run_id: 'run/alpha', run_name: 'Alfa svět',
      run_status: 'working', run_read_only: false,
      branch_id: 'branch with space', branch_name: 'A timeline',
      branch_status: 'active', branch_read_only: false,
      command_id: 'first-command', control_state: 'paused',
      start_week: {season_index: 3, week: 11},
      final_week: {season_index: 49, week: 61},
      completed_season_count: 5, final_completed_week_count: 1,
      review_fingerprint: 'a'.repeat(64), worker_activity: 'unknown',
      lease_state: 'absent', lease_expires_at_unix: null
    },
    {
      run_id: 'run-beta', run_name: 'Beta world',
      run_status: 'working', run_read_only: false,
      branch_id: 'b-two', branch_name: 'B timeline',
      branch_status: 'active', branch_read_only: false,
      command_id: 'other-command', control_state: 'running',
      start_week: {season_index: 4, week: 7},
      final_week: {season_index: 49, week: 61},
      completed_season_count: 4, final_completed_week_count: 0,
      review_fingerprint: 'b'.repeat(64), worker_activity: 'unknown',
      lease_state: 'matching_active', lease_expires_at_unix: 2000000000
    },
    {
      run_id: 'run-gamma', run_name: 'Gamma world',
      run_status: 'archived', run_read_only: true,
      branch_id: 'c-three', branch_name: 'C timeline',
      branch_status: 'archived', branch_read_only: true,
      command_id: 'pause-request', control_state: 'pause_requested',
      start_week: {season_index: 2, week: 8},
      final_week: {season_index: 49, week: 61},
      completed_season_count: 1, final_completed_week_count: 0,
      review_fingerprint: 'c'.repeat(64), worker_activity: 'unknown',
      lease_state: 'matching_expired', lease_expires_at_unix: 1000000000
    }
  ]
}

function renderPage(): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={queryClient}>
    <MemoryRouter initialEntries={['/admin/operations']}>
      <LanguageProvider><GlobalSimulationTaskCenterPage /></LanguageProvider>
    </MemoryRouter>
  </QueryClientProvider>)
}

describe('global Full Simulation Task Center', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    linkedServerTasks.data=[]
    localStorage.clear()
    api.getGlobalFullSimulationOperations.mockResolvedValue(example)
  })

  it('displays only persisted state, progress, legacy visibility and exact encoded scoped links', async () => {
    renderPage()
    const list = await screen.findByRole('list', {name: 'Centrum simulací'})
    expect(within(list).getAllByRole('listitem')).toHaveLength(3)
    expect(screen.getByText(/Obnovitelné záznamy:/)).toHaveTextContent('3')
    expect(screen.getByText(/Starší záznamy bez ověřitelného příkazu/)).toHaveTextContent('1')
    expect(screen.getByText(/Jde o uložené záznamy postupu/)).toBeInTheDocument()
    expect(within(list).getAllByText(/Skutečná aktivita workeru není potvrzena/)).toHaveLength(3)
    expect(within(list).getByText(/Platná lease této simulace/)).toBeInTheDocument()
    expect(within(list).getByText(/Expirovaná lease této simulace/)).toBeInTheDocument()
    expect(within(list).getByText(/Bez aktuální execution lease/)).toBeInTheDocument()
    const alpha = within(list).getByText('Alfa svět / A timeline').closest('li')!
    expect(within(alpha).getByText('Dokončené sezony:').parentElement).toHaveTextContent('5')
    expect(within(alpha).getByText('Dokončené týdny poslední sezony:').parentElement).toHaveTextContent('1')
    expect(within(alpha).getByRole('link', {name: 'Otevřít detail a ovládání'})).toHaveAttribute(
      'href', '/admin/runs/run%2Falpha/simulate?branch=branch%20with%20space'
    )
    const readonly = within(list).getByText('Gamma world / C timeline').closest('li')!
    expect(within(readonly).getByText(/Jen pro čtení/)).toBeInTheDocument()
    expect(within(list).getByText('Povoleno – aktivita procesu nepotvrzena')).toBeInTheDocument()
    expect(api.getGlobalFullSimulationOperations).toHaveBeenCalledTimes(1)
  })

  it('filters by saved control state and command or Run identity without changing the server', async () => {
    renderPage()
    const list = await screen.findByRole('list', {name: 'Centrum simulací'})
    await userEvent.selectOptions(screen.getByRole('combobox', {name: 'Stav uložené operace'}), 'paused')
    expect(within(list).getAllByRole('listitem')).toHaveLength(1)
    expect(within(list).getByText('Alfa svět / A timeline')).toBeInTheDocument()
    await userEvent.type(screen.getByRole('searchbox', {name: 'Hledat Run, větev nebo ID příkazu'}), 'other-command')
    expect(screen.getByText('Zadaným filtrům neodpovídá žádná uložená simulace.')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox', {name: 'Stav uložené operace'}), 'all')
    expect(await screen.findByText('Beta world / B timeline')).toBeInTheDocument()
    expect(screen.queryByText('Alfa svět / A timeline')).not.toBeInTheDocument()
    expect(api.getGlobalFullSimulationOperations).toHaveBeenCalledTimes(1)
  })

  it('refreshes server evidence only on explicit click and recovers a selected Run on link click', async () => {
    renderPage()
    const list = await screen.findByRole('list', {name: 'Centrum simulací'})
    const alpha = within(list).getByText('Alfa svět / A timeline').closest('li')!
    await userEvent.click(within(alpha).getByRole('link', {name: 'Otevřít detail a ovládání'}))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run/alpha')
    await userEvent.click(screen.getByRole('button', {name: 'Obnovit údaje'}))
    await waitFor(() => expect(api.getGlobalFullSimulationOperations).toHaveBeenCalledTimes(2))
  })

  it('distinguishes empty durable evidence and legacy count from API failure', async () => {
    api.getGlobalFullSimulationOperations.mockResolvedValue({
      ...example, operations: [], pending_count: 0, legacy_pending_count: 2
    })
    renderPage()
    expect(await screen.findByText('Nejsou uložené žádné obnovitelné Full Simulation.')).toBeInTheDocument()
    expect(screen.getByText(/Starší záznamy bez ověřitelného příkazu/)).toHaveTextContent('2')
    expect(screen.queryByRole('list', {name: 'Centrum simulací'})).not.toBeInTheDocument()
  })

  it('fails visibly without claiming empty or enabling recovered operations when inventory is unavailable', async () => {
    api.getGlobalFullSimulationOperations.mockRejectedValue(new Error('Corrupt server receipt'))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Corrupt server receipt')
    expect(screen.queryByRole('list', {name: 'Centrum simulací'})).not.toBeInTheDocument()
    expect(screen.queryByText('Nejsou uložené žádné obnovitelné Full Simulation.')).not.toBeInTheDocument()
    expect(screen.getByRole('link', {name: 'Otevřít seznam Runů'})).toHaveAttribute('href', '/admin/runs')
  })
 it('links an original pending receipt to its single server task and collapses duplicate metadata',async()=>{
  linkedServerTasks.data=[{
   run_id:'run-beta',branch_id:'b-two',parent_command_id:'other-command',task_id:'server-task-42'
  }]
  renderPage()
  const list=await screen.findByRole('list',{name:'Centrum simulací'})
  const beta=within(list).getByText('Beta world / B timeline').closest('li')!
  expect(within(beta).getByText(/Tento původní příkaz už patří serverové úloze/)).toHaveTextContent('server-task-42')
  const receipt=within(beta).getByText('Zobrazit původní pending receipt').closest('details')
  expect(receipt).not.toHaveAttribute('open')
  expect(receipt).toHaveTextContent('other-command')
  expect(within(beta).getAllByRole('link',{name:'Otevřít detail a ovládání'})).toHaveLength(1)
  const alpha=within(list).getByText('Alfa svět / A timeline').closest('li')!
  expect(within(alpha).queryByText(/Tento původní příkaz už patří/)).toBeNull()
  expect(within(alpha).getByText('Dokončené sezony:')).toBeVisible()
 })

})

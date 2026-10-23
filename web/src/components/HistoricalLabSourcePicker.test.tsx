import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'

import { LanguageProvider } from '../i18n/LanguageContext'
import { HistoricalLabSourcePicker } from './HistoricalLabSourcePicker'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn(),
  listRunBranches: vi.fn(),
  listSavedRevisionHistory: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../api/client', () => api)

function StatefulPicker({initial}:{initial?:{run:string;branch:string;revision:string}}): JSX.Element {
  const [selection, setSelection] = useState(initial??{run: '', branch: '', revision: ''})
  return <HistoricalLabSourcePicker lab="Match Lab" {...selection}
    onChange={(run, branch, revision) => setSelection({run, branch, revision})} />
}
function mount(initial?:{run:string;branch:string;revision:string}): void {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}})
  render(<QueryClientProvider client={client}><LanguageProvider>
    <StatefulPicker initial={initial} />
  </LanguageProvider></QueryClientProvider>)
}

describe('historical Lab source inventory states', () => {
  beforeEach(() => {
    localStorage.setItem('squash-engine-language-v1', 'cs')
    vi.clearAllMocks()
    api.listRunContainers.mockResolvedValue({run_containers: []})
    api.listRunBranches.mockResolvedValue({run_branches: []})
    api.listSavedRevisionHistory.mockResolvedValue({saved_revisions: []})
  })

  it('distinguishes a genuinely empty Run inventory without fabricating a historical source', async () => {
    mount()
    await userEvent.click(screen.getByText('Vybrat uložený historický zdroj'))
    expect(await screen.findByText('Žádné Runy v inventáři.')).toBeInTheDocument()
    expect(api.listRunContainers).toHaveBeenCalledTimes(1)
    expect(api.listRunBranches).not.toHaveBeenCalled()
    expect(api.listSavedRevisionHistory).not.toHaveBeenCalled()
  })

  it('shows API failures as alerts, never as an empty inventory', async () => {
    api.listRunContainers.mockRejectedValue(new Error('inventory offline'))
    mount()
    await userEvent.click(screen.getByText('Vybrat uložený historický zdroj'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Nepodařilo se načíst seznam Runů.')
    expect(screen.queryByText('Žádné Runy v inventáři.')).not.toBeInTheDocument()
  })

  it('recovers failed Run inventory through an explicit read-only retry', async () => {
    api.listRunContainers.mockRejectedValueOnce(new Error('transient Runs outage'))
      .mockResolvedValue({run_containers: [{run_id: 'season1', display_name: 'Season 1'}]})
    mount()
    await userEvent.click(screen.getByText('Vybrat uložený historický zdroj'))
    expect(await screen.findByRole('alert')).toHaveTextContent('transient Runs outage')
    await userEvent.click(screen.getByRole('button', {name: 'Znovu načíst Runy'}))
    expect(await screen.findByRole('option', {name: 'Season 1'})).toHaveValue('season1')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(api.listRunContainers).toHaveBeenCalledTimes(2)
    expect(api.listRunBranches).not.toHaveBeenCalled()
    expect(api.listSavedRevisionHistory).not.toHaveBeenCalled()
  })

  it('retries Branch and Saved Revision inventory without changing the selection', async () => {
    api.listRunContainers.mockResolvedValue({run_containers: [{run_id: 'season1', display_name: 'Season 1'}]})
    api.listRunBranches.mockRejectedValueOnce(new Error('transient Branch outage'))
      .mockResolvedValue({run_branches: [{branch_id: 'main', display_name: 'Main'}]})
    api.listSavedRevisionHistory.mockRejectedValueOnce(new Error('transient Revision outage'))
      .mockResolvedValue({saved_revisions: [{revision_id: 'rev1', sequence: 1}]})
    mount()
    await userEvent.click(screen.getByText('Vybrat uložený historický zdroj'))
    await userEvent.selectOptions(await screen.findByRole('combobox', {name: 'Match Lab source Run'}), 'season1')
    expect(await screen.findByRole('alert')).toHaveTextContent('transient Branch outage')
    await userEvent.click(screen.getByRole('button', {name: 'Znovu načíst větve'}))
    await userEvent.selectOptions(await screen.findByRole('combobox', {name: 'Match Lab source Branch'}), 'main')
    expect(await screen.findByRole('alert')).toHaveTextContent('transient Revision outage')
    await userEvent.click(screen.getByRole('button', {name: 'Znovu načíst revize'}))
    expect(await screen.findByRole('option', {name: '#1 · rev1'})).toHaveValue('rev1')
    expect(screen.getByRole('combobox', {name: 'Match Lab source Run'})).toHaveValue('season1')
    expect(screen.getByRole('combobox', {name: 'Match Lab source Branch'})).toHaveValue('main')
    expect(api.listSavedRevisionHistory).toHaveBeenCalledWith('season1', 'main', {limit: 200})
  })

  it('preserves an older manually entered revision that is outside the returned 200 items', async () => {
    api.listRunContainers.mockResolvedValue({run_containers: [{run_id:'season1',display_name:'Season 1'}]})
    api.listRunBranches.mockResolvedValue({run_branches: [{branch_id:'main',display_name:'Main'}]})
    api.listSavedRevisionHistory.mockResolvedValue({saved_revisions:[
      {revision_id:'recent-rev',sequence:200}
    ],has_more_older:true})
    mount({run:'season1',branch:'main',revision:'old-rev'})
    await userEvent.click(screen.getByText('Vybrat uložený historický zdroj'))
    expect(await screen.findByRole('option',{name:'Ručně zadaná revize – mimo seznam · old-rev'})).toBeInTheDocument()
    expect(screen.getByRole('combobox',{name:'Match Lab source Saved Revision'})).toHaveValue('old-rev')
    expect(screen.getByText('Starší revizi lze zadat jejím ID.')).toBeInTheDocument()
    expect(api.listSavedRevisionHistory).toHaveBeenCalledWith('season1','main',{limit:200})
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Match Lab source Saved Revision'}),'recent-rev')
    expect(screen.getByRole('combobox',{name:'Match Lab source Saved Revision'})).toHaveValue('recent-rev')
    expect(screen.queryByText(/Ručně zadaná revize/)).not.toBeInTheDocument()
  })

  it('labels manually entered Run and Branch IDs as unverified rather than dropping their selections', async () => {
    api.listRunContainers.mockResolvedValue({run_containers:[]})
    api.listRunBranches.mockResolvedValue({run_branches:[]})
    mount({run:'legacy-run',branch:'legacy-branch',revision:''})
    await userEvent.click(screen.getByText('Vybrat uložený historický zdroj'))
    expect(await screen.findByRole('option',{name:'Ručně zadaný Run – mimo seznam · legacy-run'})).toBeInTheDocument()
    expect(await screen.findByRole('option',{name:'Ručně zadaná větev – mimo seznam · legacy-branch'})).toBeInTheDocument()
    expect(screen.getByRole('combobox',{name:'Match Lab source Run'})).toHaveValue('legacy-run')
    expect(screen.getByRole('combobox',{name:'Match Lab source Branch'})).toHaveValue('legacy-branch')
    expect(api.listRunContainers).toHaveBeenCalledTimes(1)
    expect(api.listRunBranches).toHaveBeenCalledWith('legacy-run')
  })

  it('uses existing inventory queries in English without writing anything', async () => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    mount()
    await userEvent.click(screen.getByText('Choose a saved historical source'))
    expect(await screen.findByText('No Runs in the source inventory.')).toBeInTheDocument()
    expect(api.listRunBranches).not.toHaveBeenCalled()
  })
})

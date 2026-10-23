import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../i18n/LanguageContext'
import { HistoricalLabSourcePicker } from './HistoricalLabSourcePicker'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn(),
  listRunBranches: vi.fn(),
  listSavedRevisionHistory: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../api/client', () => api)

function mount(): void {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}})
  render(<QueryClientProvider client={client}><LanguageProvider>
    <HistoricalLabSourcePicker lab="Match Lab" run="" branch="" revision="" onChange={vi.fn()} />
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

  it('uses existing inventory queries in English without writing anything', async () => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    mount()
    await userEvent.click(screen.getByText('Choose a saved historical source'))
    expect(await screen.findByText('No Runs in the source inventory.')).toBeInTheDocument()
    expect(api.listRunBranches).not.toHaveBeenCalled()
  })
})

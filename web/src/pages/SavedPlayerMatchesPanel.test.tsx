import { screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedPlayerMatchesPanel } from './SavedPlayerMatchesPanel'

const api = vi.hoisted(() => ({
  getSavedPlayerMatchHistory: vi.fn(), getSavedHomePlayerIdentities: vi.fn(),
}))
vi.mock('../api/client', () => api)

function mount() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: {
    queries: { retry: false, gcTime: 0 }
  } })}><MemoryRouter><SavedPlayerMatchesPanel
    runId="run" branchId="branch" playerId="A" savedHead="revision"
    locale="cs"
  /></MemoryRouter></QueryClientProvider>)
}

describe('Saved player match history', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r: string, _b: string, ids: string[]) => ({
      run_id: 'run', branch_id: 'branch', saved_revision_id: 'revision', requested_ids: ids,
      players: ids.map(id => ({ player_id: id, display_name: 'Opponent '+id }))
    }))
    api.getSavedPlayerMatchHistory.mockImplementation(async (_r: string, _b: string, _id: string,
      season: number | null, offset: number, limit: number) => ({
      schema_version: 'saved_player_match_history.v1',
      run_id: 'run', branch_id: 'branch', saved_revision_id: 'revision', player_id: 'A',
      source: 'selected_branch_saved_revision', status: 'ready',
      season_index: season, offset, limit,
      available_seasons: [2], total_results: season === 0 ? 0 : 1,
      played_wins: season === 0 ? 0 : 1, played_losses: 0, walkovers: 0,
      career_played_wins: 1, career_played_losses: 0, career_walkovers: 0,
      has_more: false, matches: season === 0 ? [] : [{
        event_id: 'event', event_name: 'Championship', match_id: 'match',
        season_index: 2, season: '2002/03', week: 17, draw_type: 'main',
        round_number: 2, opponent_player_id: 'B', outcome: 'win',
        completion: 'played', scoreline: '3-2'
      }],
    }))
  })
  it('renders saved opponents, filtered season and actual scoreline', async () => {
    mount()
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/Opponent B/)).toBeInTheDocument())
    expect(screen.getByText(/3-2/)).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Sezóna zápasů' }), { target: { value: '2' } })
    await waitFor(() => expect(api.getSavedPlayerMatchHistory).toHaveBeenLastCalledWith(
      'run', 'branch', 'A', 2, 0, 20,
    ))
  })
  it('does not render foreign saved HEAD data', async () => {
    api.getSavedPlayerMatchHistory.mockResolvedValueOnce({
      schema_version: 'saved_player_match_history.v1', run_id: 'run', branch_id: 'branch',
      saved_revision_id: 'foreign', player_id: 'A', source: 'selected_branch_saved_revision',
      status: 'ready', season_index: null, offset: 0, limit: 20,
      available_seasons: [], total_results: 1, played_wins: 1, played_losses: 0,
      walkovers: 0, career_played_wins: 1, career_played_losses: 0,
      career_walkovers: 0, has_more: false, matches: [],
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Data patří jiné uložené revizi.')
    expect(screen.queryByText('Championship')).not.toBeInTheDocument()
  })
})

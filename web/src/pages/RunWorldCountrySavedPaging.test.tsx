import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState, type ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunWorldCountrySavedPlayers } from './RunWorldCountrySavedPlayers'
import { RunWorldCountryPlayerStandings } from './RunWorldCountryPlayerStandings'

const api = vi.hoisted(() => ({ getSavedPlayersInventory: vi.fn(), getCountryPlayerStandings: vi.fn() }))
vi.mock('../api/client', () => api)

function mount(content: ReactNode) {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{content}</MemoryRouter>
  </QueryClientProvider>)
}
const totalFor = (country: string) => country === 'CZE' ? 50 : 1

describe('Country Saved Revision paging source changes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSavedPlayersInventory.mockImplementation(async (
      runId: string, branchId: string, revision: string,
      options: { country_code: string; search: string; status_filter: string; include_prepared: boolean;
        offset: number; limit: number }
    ) => {
      const total = totalFor(options.country_code)
      return {
        schema_version: 'saved_players_inventory.v1',
        source: 'selected_branch_saved_revision', time_context: 'present',
        run_id: runId, branch_id: branchId, saved_revision_id: revision,
        ranking_week_ordinal: null, country_code: options.country_code,
        search: options.search, status_filter: options.status_filter,
        include_prepared: options.include_prepared, offset: options.offset, limit: options.limit,
        total, has_more: options.offset + options.limit < total,
        players: [{
          player_id: options.country_code + '-one', country_code: options.country_code,
          display_name: 'Saved Player', status: 'active', age: 23, ovr: 75,
          potential_ovr: 80, ranking_status: 'unranked', rank: null,
        }],
      }
    })
    api.getCountryPlayerStandings.mockImplementation(async (
      runId: string, branchId: string, countryCode: string, savedRevisionId: string,
      offset: number, limit: number
    ) => {
      const total = totalFor(countryCode)
      return {
        schema_version: 'country_player_standings.v1',
        source: 'reachable_saved_revision',
        run_id: runId, branch_id: branchId, country_code: countryCode,
        saved_revision_id: savedRevisionId, revision_branch_id: branchId,
        calendar_status: 'ready', published_event_count: total,
        country_titles: 0, country_runner_up_finishes: 0,
        country_played_wins: total, country_played_losses: 0,
        country_walkover_wins: 0, country_walkover_losses: 0,
        offset, limit, total_players: total, has_more: offset + limit < total,
        players: Array.from({ length: Math.max(0, Math.min(limit, total - offset)) },
          (_, i) => ({
            player_id: countryCode + '-' + String(offset + i + 1).padStart(3, '0'),
            player_name: 'Saved Player ' + (offset + i + 1),
            country_code: countryCode, position: offset + i + 1,
            titles: 0, final_appearances: 0, runner_up_finishes: 0,
            played_wins: 1, played_losses: 0, walkover_wins: 0, walkover_losses: 0,
          })),
      }
    })
  })

  it('resets country inventory offset synchronously when country and HEAD revision change', async () => {
    function Harness() {
      const [country, setCountry] = useState('CZE')
      const [head, setHead] = useState('rev-a')
      return <>
        <button onClick={() => { setCountry('ENG'); setHead('rev-b') }}>Switch saved source</button>
        <RunWorldCountrySavedPlayers runId="run-a" branchId="branch-a" savedHead={head}
          countryCode={country} selectedWorldYear={2028} language="en" />
      </>
    }
    mount(<Harness />)
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    expect(api.getSavedPlayersInventory).toHaveBeenCalledWith('run-a', 'branch-a', 'rev-a',
      expect.objectContaining({ country_code: 'CZE', offset: 25, limit: 25 }))

    fireEvent.click(screen.getByRole('button', { name: 'Switch saved source' }))
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    expect(api.getSavedPlayersInventory).toHaveBeenCalledWith('run-a', 'branch-a', 'rev-b',
      expect.objectContaining({ country_code: 'ENG', offset: 0, limit: 25 }))
    const newSourceCalls = api.getSavedPlayersInventory.mock.calls
      .filter(([, , revision]) => revision === 'rev-b')
    expect(newSourceCalls.length).toBeGreaterThan(0)
    expect(newSourceCalls.every(([, , , options]) => options.offset === 0)).toBe(true)
  })

  it('resets saved standings page before querying a different revision or country', async () => {
    function Harness() {
      const [country, setCountry] = useState('CZE')
      const [revision, setRevision] = useState('rev-a')
      return <>
        <button onClick={() => setRevision('rev-b')}>Change revision</button>
        <button onClick={() => setCountry('ENG')}>Change country</button>
        <RunWorldCountryPlayerStandings runId="run-a" branchId="branch-a"
          countryCode={country} savedRevisionId={revision} historical={false} cs={false} />
      </>
    }
    mount(<Harness />)
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Change revision' }))
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    expect(api.getCountryPlayerStandings).toHaveBeenCalledWith('run-a', 'branch-a', 'CZE', 'rev-b', 0, 25)
    expect(api.getCountryPlayerStandings.mock.calls.filter(([, , , revision]) => revision === 'rev-b')
      .every(([, , , , offset]) => offset === 0)).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: 'Change country' }))
    expect(await screen.findByText('Page 1 / 1')).toBeInTheDocument()
    expect(api.getCountryPlayerStandings).toHaveBeenCalledWith('run-a', 'branch-a', 'ENG', 'rev-b', 0, 25)
    expect(api.getCountryPlayerStandings.mock.calls.filter(([, , country]) => country === 'ENG')
      .every(([, , , , offset]) => offset === 0)).toBe(true)
  })

  it('continues to reset the inventory page after the explicit prepared-prospects toggle', async () => {
    mount(<RunWorldCountrySavedPlayers runId="run-a" branchId="branch-a" savedHead="rev-a"
      countryCode="CZE" selectedWorldYear={2028} language="en" />)
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(await screen.findByText('Page 2 / 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox'))
    await waitFor(() => expect(api.getSavedPlayersInventory).toHaveBeenCalledWith(
      'run-a', 'branch-a', 'rev-a',
      expect.objectContaining({ include_prepared: true, offset: 0, limit: 25 })
    ))
    expect(await screen.findByText('Page 1 / 2')).toBeInTheDocument()
  })
})

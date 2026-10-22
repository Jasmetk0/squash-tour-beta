import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PlayerCareerPage } from './PlayerCareerPage'

const api = vi.hoisted(() => ({
  getRunPlayerCareerHistory: vi.fn(),
  getRunPlayerCareerPerformance: vi.fn(),
  getRunPlayerTournamentResults: vi.fn(),
}))
vi.mock('../api/client', () => api)

const career = {
  requested_run_id: 'run x/y', player_id: 'player/one', player_name: 'Actual Player',
  country_code: 'CZE', entries: [{
    run_id: 'source-run', season: 2028, age: 22, overall: 72,
    technique: 75, movement: 77, physical: 71, mental: 70,
    origin_source_type: 'planner_generated', origin_quality_band: 'A',
    origin_season: 2028, origin_override_id: null,
    source_type: 'planner_generated', quality_band: 'A',
  }],
}
const performance = {
  requested_run_id: 'run x/y', player_id: 'player/one', entries: [{
    run_id: 'source-run', season: 2028, ranking_position: 2, race_position: 3,
    tournaments_played: 8, titles: 1, finals: 2, semifinals: 2,
    quarterfinals: 3, wins: 18, losses: 6,
  }],
}
const results = {
  requested_run_id: 'run x/y', player_id: 'player/one', entries: [{
    run_id: 'source-run', season: 2028, week: 10, event_sequence: 3,
    event_id: 'event-1', event_name: 'Actual Open', event_category: 'DIAMOND',
    finish: 'CHAMPION', is_title: true, wins: 4, losses: 0, ranking_points_awarded: 100,
  }],
}
function mount(path = '/runs/run%20x%2Fy/players/player%2Fone/career') {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[path]}>
      <Routes><Route path="/runs/:runId/players/:playerId/career" element={<PlayerCareerPage />} /></Routes>
    </MemoryRouter>
  </QueryClientProvider>)
}

describe('Legacy Career independent API identity checks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRunPlayerCareerHistory.mockResolvedValue(career)
    api.getRunPlayerCareerPerformance.mockResolvedValue(performance)
    api.getRunPlayerTournamentResults.mockResolvedValue(results)
  })

  it('keeps actual linked-Run career history and exact navigation unchanged', async () => {
    mount()
    expect(await screen.findByText(/Actual Player/)).toBeInTheDocument()
    expect(await screen.findByText('Actual Open')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to players explorer/ })).toHaveAttribute(
      'href', '/runs/run%20x%2Fy/players'
    )
    expect(api.getRunPlayerCareerHistory).toHaveBeenCalledWith('run x/y', 'player/one')
    expect(api.getRunPlayerCareerPerformance).toHaveBeenCalledWith('run x/y', 'player/one')
    expect(api.getRunPlayerTournamentResults).toHaveBeenCalledWith('run x/y', 'player/one')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it.each([
    ['career', 'foreign Run', 'requested_run_id', 'another-run'],
    ['career', 'foreign player', 'player_id', 'another-player'],
    ['performance', 'foreign Run', 'requested_run_id', 'another-run'],
    ['performance', 'foreign player', 'player_id', 'another-player'],
    ['results', 'foreign Run', 'requested_run_id', 'another-run'],
    ['results', 'foreign player', 'player_id', 'another-player'],
  ] as const)('blocks a %s response identifying a %s', async (section, _, key, value) => {
    if (section === 'career') {
      api.getRunPlayerCareerHistory.mockResolvedValue({ ...career, [key]: value, player_name: 'Wrong Player' })
    } else if (section === 'performance') {
      api.getRunPlayerCareerPerformance.mockResolvedValue({ ...performance, [key]: value,
        entries: [{ ...performance.entries[0], season: 2099 }] })
    } else {
      api.getRunPlayerTournamentResults.mockResolvedValue({ ...results, [key]: value,
        entries: [{ ...results.entries[0], event_name: 'Foreign Open' }] })
    }
    mount()
    const alerts = await screen.findAllByRole('alert')
    expect(alerts).toHaveLength(1)
    if (section === 'career') {
      expect(alerts[0]).toHaveTextContent('Career history does not match')
      expect(screen.queryByText('Wrong Player')).not.toBeInTheDocument()
      expect(screen.queryByText(/Seasons tracked:/)).not.toBeInTheDocument()
      expect(screen.getByText('—')).toBeInTheDocument()
      expect(await screen.findByText('Actual Open')).toBeInTheDocument()
    } else if (section === 'performance') {
      expect(alerts[0]).toHaveTextContent('Season performance does not match')
      expect(screen.queryByText('2099')).not.toBeInTheDocument()
      expect(await screen.findByText(/Actual Player/)).toBeInTheDocument()
      expect(await screen.findByText('Actual Open')).toBeInTheDocument()
    } else {
      expect(alerts[0]).toHaveTextContent('Tournament results do not match')
      expect(screen.queryByText('Foreign Open')).not.toBeInTheDocument()
      expect(await screen.findByText(/Actual Player/)).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'Tournament results timeline' })).toBeInTheDocument()
    }
  })
})

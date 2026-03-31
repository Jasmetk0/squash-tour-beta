import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunPage } from './RunPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
  getRun: vi.fn(),
  getFinalsSummary: vi.fn(),
  getLatestRollover: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  simulateWorldTourFinals: vi.fn(),
  rolloverNextSeason: vi.fn(),
  simulateNextTournament: vi.fn(),
  simulateNextWeek: vi.fn(),
  simulateFullSeason: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('RunPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2025, seed: 3, next_event_index: 1, total_events: 4, completed_event_ids: ['E1'] },
      season_state: { season: 2025, next_event_index: 1, completed_event_ids: ['E1'], ordered_events: [] }
    })
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2025,
      qualification: { run_id: 'run-a', season: 2025, source_as_of_season: 2025, source_as_of_week: 40, qualification: {} },
      result: null
    })
    api.getLatestRollover.mockResolvedValue({
      rollover: { run_id: 'run-a', from_season: 2025, to_season: 2026, transitioned_players: 128, metadata: {} }
    })
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'bootstrap',
        parent_run_id: 'run-parent',
        source_rollover_run_id: 'run-parent',
        source_rollover_from_season: 2025,
        source_rollover_to_season: 2026
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'bootstrap',
          parent_run_id: 'run-parent',
          source_rollover_run_id: 'run-parent',
          source_rollover_from_season: 2025,
          source_rollover_to_season: 2026
        },
        children: ['run-child-1', 'run-child-2']
      }
    })
    api.listEvents.mockResolvedValue({
      events: [
        { event_sequence: 3, event_id: 'E3', season: 2025, week: 11, template_id: null, tournament_result: null },
        { event_sequence: 1, event_id: 'E1', season: 2025, week: 9, template_id: null, tournament_result: null },
        { event_sequence: 2, event_id: 'E2', season: 2025, week: 10, template_id: null, tournament_result: null },
        { event_sequence: 4, event_id: 'E4', season: 2025, week: 12, template_id: null, tournament_result: null }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} },
        { snapshot_sequence: 8, snapshot_kind: 'TOURNAMENT', source_event_id: null, payload: {} },
        { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 11, snapshot_kind: 'WEEK', source_event_id: 'E4', payload: {} }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} },
        { snapshot_sequence: 5, snapshot_kind: 'TOURNAMENT', source_event_id: null, payload: {} },
        { snapshot_sequence: 6, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 8, snapshot_kind: 'WEEK', source_event_id: 'E4', payload: {} }
      ]
    })
    api.simulateWorldTourFinals.mockResolvedValue({
      finals: {
        run_id: 'run-a',
        season: 2025,
        event_id: 'WTF-2025',
        already_simulated: false,
        result: { champion_id: 'p-1' }
      }
    })
    api.rolloverNextSeason.mockResolvedValue({
      rollover: {
        run_id: 'run-a',
        from_season: 2025,
        to_season: 2026,
        transitioned_players: 128,
        metadata: {},
        already_persisted: false
      }
    })
    api.simulateNextTournament.mockResolvedValue({ step: { mode: 'simulate_next_tournament' } })
    api.simulateNextWeek.mockResolvedValue({ step: { mode: 'simulate_next_week' } })
    api.simulateFullSeason.mockResolvedValue({ step: { mode: 'simulate_full_season' } })
  })

  it('calls finals quick action endpoint from run detail', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    await userEvent.click(await screen.findByRole('button', { name: 'Simulate World Tour Finals' }))

    await waitFor(() => expect(api.simulateWorldTourFinals).toHaveBeenCalledWith('run-a'))
    expect(await screen.findByText('Finals simulation complete.')).toBeInTheDocument()
  })

  it('calls rollover quick action endpoint from run detail', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    await userEvent.click(await screen.findByRole('button', { name: 'Roll over to next season' }))

    await waitFor(() => expect(api.rolloverNextSeason).toHaveBeenCalledWith('run-a'))
    expect(await screen.findByText('Rollover complete for season 2026.')).toBeInTheDocument()
  })

  it('shows readable quick action errors', async () => {
    api.simulateWorldTourFinals.mockRejectedValueOnce(new api.ApiError('finals blocked', 409))
    api.rolloverNextSeason.mockRejectedValueOnce(new api.ApiError('rollover blocked', 409))

    renderWithRoute(<RunPage />, '/runs/run-a')

    await userEvent.click(await screen.findByRole('button', { name: 'Simulate World Tour Finals' }))
    expect(await screen.findByText('Could not simulate Finals: finals blocked')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Roll over to next season' }))
    expect(await screen.findByText('Could not execute rollover: rollover blocked')).toBeInTheDocument()
  })

  it('calls each simulation endpoint', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    await userEvent.click(await screen.findByRole('button', { name: 'Simulate next tournament' }))
    await waitFor(() => expect(api.simulateNextTournament).toHaveBeenCalledWith('run-a'))

    await userEvent.click(screen.getByRole('button', { name: 'Simulate next week' }))
    await waitFor(() => expect(api.simulateNextWeek).toHaveBeenCalledWith('run-a'))

    await userEvent.click(screen.getByRole('button', { name: 'Simulate full season' }))
    await waitFor(() => expect(api.simulateFullSeason).toHaveBeenCalledWith('run-a'))
  })

  it('renders navigation links for finals, rollover, and bootstrap lineage', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByRole('link', { name: /View World Tour Finals/i })).toHaveAttribute('href', '/runs/run-a/finals')
    expect(await screen.findByRole('link', { name: /View season rollover/i })).toHaveAttribute('href', '/runs/run-a/rollover')
    expect(await screen.findByRole('link', { name: /View bootstrap and lineage/i })).toHaveAttribute(
      'href',
      '/runs/run-a/bootstrap-lineage'
    )
  })

  it('renders finals overview from finals summary data', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('World Tour Finals overview')).toBeInTheDocument()
    expect(screen.getByText('Available')).toBeInTheDocument()
    expect(screen.getByText('Not simulated yet')).toBeInTheDocument()
  })

  it('renders latest rollover overview from rollover api data', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('Latest rollover overview')).toBeInTheDocument()
    expect(screen.getByText('From season')).toBeInTheDocument()
    expect(screen.getByText('To season')).toBeInTheDocument()
    expect(screen.getByText('2026')).toBeInTheDocument()
    expect(screen.getByText('128')).toBeInTheDocument()
  })

  it('renders source and lineage overview from source + lineage data', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('Run source and lineage overview')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'run-parent' })).toHaveAttribute('href', '/runs/run-parent')
    expect(screen.getByText('Child run count')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'run-child-1' })).toHaveAttribute('href', '/runs/run-child-1')
    expect(screen.getByRole('link', { name: 'run-child-2' })).toHaveAttribute('href', '/runs/run-child-2')
  })

  it('renders readable not-found empty states for rollover and lineage metadata', async () => {
    api.getLatestRollover.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.getRunSource.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.getRunLineage.mockRejectedValueOnce({ status: 404, message: 'not found' })

    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('No rollover yet for this run.')).toBeInTheDocument()
    expect(await screen.findByText('No source metadata available for this run.')).toBeInTheDocument()
    expect(await screen.findByText('No lineage metadata available for this run.')).toBeInTheDocument()
  })

  it('refreshes overview queries after quick actions succeed', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    await screen.findByText('World Tour Finals overview')
    expect(api.getFinalsSummary).toHaveBeenCalledTimes(1)
    expect(api.getLatestRollover).toHaveBeenCalledTimes(1)
    expect(api.getRunSource).toHaveBeenCalledTimes(1)
    expect(api.getRunLineage).toHaveBeenCalledTimes(1)
    expect(api.listEvents).toHaveBeenCalledTimes(1)
    expect(api.listRankingSnapshots).toHaveBeenCalledTimes(1)
    expect(api.listRaceSnapshots).toHaveBeenCalledTimes(1)

    await userEvent.click(screen.getByRole('button', { name: 'Simulate World Tour Finals' }))

    await waitFor(() => expect(api.getFinalsSummary).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getLatestRollover).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getRunSource).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getRunLineage).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.listEvents).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.listRankingSnapshots).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.listRaceSnapshots).toHaveBeenCalledTimes(2))

    await userEvent.click(screen.getByRole('button', { name: 'Roll over to next season' }))

    await waitFor(() => expect(api.getFinalsSummary).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(api.getLatestRollover).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(api.getRunSource).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(api.getRunLineage).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(api.listEvents).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(api.listRankingSnapshots).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(api.listRaceSnapshots).toHaveBeenCalledTimes(3))
  })

  it('refreshes overview queries after simulation succeeds', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    await screen.findByText('World Tour Finals overview')
    expect(api.getFinalsSummary).toHaveBeenCalledTimes(1)
    expect(api.getLatestRollover).toHaveBeenCalledTimes(1)
    expect(api.getRunSource).toHaveBeenCalledTimes(1)
    expect(api.getRunLineage).toHaveBeenCalledTimes(1)
    expect(api.listEvents).toHaveBeenCalledTimes(1)
    expect(api.listRankingSnapshots).toHaveBeenCalledTimes(1)
    expect(api.listRaceSnapshots).toHaveBeenCalledTimes(1)

    await userEvent.click(screen.getByRole('button', { name: 'Simulate next tournament' }))

    await waitFor(() => expect(api.getFinalsSummary).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getLatestRollover).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getRunSource).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getRunLineage).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.listEvents).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.listRankingSnapshots).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.listRaceSnapshots).toHaveBeenCalledTimes(2))
  })

  it('renders recent history previews in API order with correct links', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    const eventsPreview = await screen.findByRole('list', { name: 'Recent events preview' })
    const eventRows = within(eventsPreview).getAllByRole('listitem')
    expect(eventRows).toHaveLength(3)
    expect(eventRows[0]).toHaveTextContent('E3')
    expect(eventRows[1]).toHaveTextContent('E1')
    expect(eventRows[2]).toHaveTextContent('E2')

    const rankingPreview = await screen.findByRole('list', { name: 'Recent ranking snapshots preview' })
    const rankingRows = within(rankingPreview).getAllByRole('listitem')
    expect(rankingRows).toHaveLength(3)
    expect(rankingRows[0]).toHaveTextContent('Seq 10')
    expect(rankingRows[1]).toHaveTextContent('Seq 8')
    expect(rankingRows[2]).toHaveTextContent('Seq 9')

    const racePreview = await screen.findByRole('list', { name: 'Recent race snapshots preview' })
    const raceRows = within(racePreview).getAllByRole('listitem')
    expect(raceRows).toHaveLength(3)
    expect(raceRows[0]).toHaveTextContent('Seq 7')
    expect(raceRows[1]).toHaveTextContent('Seq 5')
    expect(raceRows[2]).toHaveTextContent('Seq 6')

    expect(screen.getByRole('link', { name: 'View all events' })).toHaveAttribute('href', '/runs/run-a/events')
    expect(screen.getByRole('link', { name: 'View all ranking snapshots' })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/ranking'
    )
    expect(screen.getByRole('link', { name: 'View all race snapshots' })).toHaveAttribute('href', '/runs/run-a/snapshots/race')

    expect(within(eventsPreview).getByRole('link', { name: /E3/i })).toHaveAttribute(
      'href',
      '/runs/run-a/events?selectedEventId=E3'
    )
    expect(within(rankingPreview).getByRole('link', { name: /Seq 10 • WEEK/i })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/ranking?selectedSequence=10'
    )
    expect(within(racePreview).getByRole('link', { name: /Seq 7 • WEEK/i })).toHaveAttribute(
      'href',
      '/runs/run-a/snapshots/race?selectedSequence=7'
    )
  })

  it('renders readable empty and error states per preview section', async () => {
    api.listEvents.mockResolvedValueOnce({ events: [] })
    api.listRankingSnapshots.mockRejectedValueOnce(new Error('ranking unavailable'))
    api.listRaceSnapshots.mockResolvedValueOnce({ snapshots: [] })

    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('No events are available for this run yet.')).toBeInTheDocument()
    expect(await screen.findByText('Failed to load recent ranking snapshots: ranking unavailable')).toBeInTheDocument()
    expect(await screen.findByText('No race snapshots are available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Simulation controls' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Simulate next tournament' })).toBeInTheDocument()
  })
})

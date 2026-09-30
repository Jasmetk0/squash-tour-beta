import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  expectNoForbiddenViewerActions,
  renderWithViewerProviders
} from '../../../test/viewerTestUtils'
import { ViewerRunWeekPage } from '../../ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerCompletedTournaments: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  listRaceSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)

function renderWeek(route = '/viewer/runs/run%20alpha/weeks/5'): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/weeks/:week" element={<ViewerRunWeekPage />} />
      <Route path="/viewer/runs/:runId/week-missing" element={<ViewerRunWeekPage />} />
    </Routes>,
    { route, legacySimulationRunId: 'legacy-run-alpha' }
  )
}

function event(eventId: string, week: number) {
  return {
    event_id: eventId,
    season: 2028,
    season_week: week,
    calendar_year: 2028,
    year_week: 30 + week,
    template_id: week === 5 ? 'WT-PLAT' : 'ET-GOLD',
    event_name: week === 5 ? 'World Platinum' : 'Elite Gold',
    category: week === 5 ? 'Platinum' : 'Gold',
    tour_level: week === 5 ? 'WORLD_TOUR' : 'ELITE_TOUR',
    host_country: 'CZE',
    host_city: 'Brno',
    region: 'Europe',
    duration_in_season_weeks: 1,
    start_season_week: week,
    end_season_week: week,
    status: 'planned',
    main_draw_size: 32,
    qualification_draw_size: 16,
    seeds_count: 8,
    qualifier_spots: 4,
    wild_cards: 2,
    byes: 0,
    prestige: 8.5
  }
}

describe('ViewerRunWeekPage canonical publication read model', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getViewerRunCalendar.mockResolvedValue({
      schema_version: 'viewer_run_calendar.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      season_count: 1,
      event_count: 2,
      seasons: [{
        season: 2028,
        event_count: 2,
        events: [event('EVENT/1', 5), event('EVENT/10', 6)]
      }]
    })
    api.getViewerCompletedTournaments.mockResolvedValue({
      schema_version: 'viewer_completed_tournaments.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 1,
      tournaments: [{
        event_id: 'EVENT/1',
        completed_season_index: 28,
        completed_week: 5,
        champion_player_id: 'PLAYER-CHAMP',
        finalist_player_id: 'PLAYER-FINAL',
        qualification_winner_ids: [],
        player_count: 32,
        match_count: 31
      }]
    })
    api.listViewerOfficialRankingHistory.mockResolvedValue({
      schema_version: 'viewer_official_ranking_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      public_head_ordinal: 1712,
      publication_count: 2,
      publications: [
        {
          season_index: 28,
          week: 5,
          week_ordinal: 1712,
          snapshot_fingerprint: 'a'.repeat(64),
          policy_id: 'official-weekly',
          best_n: 12,
          row_count: 64
        },
        {
          season_index: 28,
          week: 4,
          week_ordinal: 1711,
          snapshot_fingerprint: 'b'.repeat(64),
          policy_id: 'official-weekly',
          best_n: 12,
          row_count: 64
        }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'legacy-run-alpha',
      snapshots: [{
        snapshot_sequence: 9,
        snapshot_kind: 'race',
        source_event_id: 'EVENT/1',
        payload: {}
      }]
    })
  })

  it('joins Saved Calendar, canonical Result and canonical Ranking publication for the week', async () => {
    renderWeek()

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect((await screen.findAllByText('EVENT/1')).length).toBeGreaterThan(0)
    expect(screen.queryByText('EVENT/10')).not.toBeInTheDocument()

    const rankingList = await screen.findByRole('list', { name: 'Week ranking publications' })
    expect(within(rankingList).getByRole('link', { name: 'Ranking publication #1712' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/rankings/1712'
    )
    expect(within(rankingList).getByText('Official · 64 ranked players · official-weekly')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ranking publication #1711' })).not.toBeInTheDocument()

    const raceList = screen.getByRole('list', { name: 'Week race publications' })
    expect(within(raceList).getByRole('link', { name: 'Race publication #9' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/race/9'
    )

    const completed = screen.getByRole('list', { name: 'Viewer week canonical completed tournaments' })
    expect(within(completed).getByText('PLAYER-CHAMP')).toBeInTheDocument()
    expect(within(completed).getByText('PLAYER-FINAL')).toBeInTheDocument()

    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('run alpha')
    expect(api.listRaceSnapshots).toHaveBeenCalledWith('legacy-run-alpha')
    expectNoForbiddenViewerActions()
  })

  it('does not source-match canonical Ranking through event ids', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValueOnce({
      schema_version: 'viewer_official_ranking_history.v1',
      product_run_id: 'run alpha',
      viewer_branch_id: 'branch-viewer',
      public_head_ordinal: 1713,
      publication_count: 1,
      publications: [{
        season_index: 28,
        week: 6,
        week_ordinal: 1713,
        snapshot_fingerprint: 'c'.repeat(64),
        policy_id: 'official-weekly',
        best_n: 12,
        row_count: 64
      }]
    })
    api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'legacy-run-alpha', snapshots: [] })

    renderWeek()

    expect(
      await screen.findByText(
        'No canonical ranking or source-matched Race publication is available for this week.'
      )
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ranking publication #1713' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps Race publication visible when canonical Ranking history fails', async () => {
    api.listViewerOfficialRankingHistory.mockRejectedValueOnce(new Error('canonical ranking outage'))

    renderWeek()

    expect(
      await screen.findByText(
        'Failed to load canonical ranking publications: canonical ranking outage'
      )
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Race publication #9' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/race/9'
    )
    expectNoForbiddenViewerActions()
  })

  it('keeps canonical Ranking publication visible when legacy Race history fails', async () => {
    api.listRaceSnapshots.mockRejectedValueOnce(new Error('race outage'))

    renderWeek()

    expect(await screen.findByText('Failed to load race publications: race outage')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ranking publication #1712' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%20alpha/rankings/1712'
    )
    expectNoForbiddenViewerActions()
  })

  it('keeps invalid week params local without calling publication APIs', async () => {
    renderWeek('/viewer/runs/run%20alpha/week-missing')

    expect(
      await screen.findByText(
        'Week must be a positive whole number in the URL (for example /weeks/12).'
      )
    ).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerCompletedTournaments).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})

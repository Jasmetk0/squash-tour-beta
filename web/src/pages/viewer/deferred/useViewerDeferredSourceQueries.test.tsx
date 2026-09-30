import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
}))

vi.mock('../../../api/client', () => api)

type HookProps = Parameters<typeof useViewerDeferredSourceQueries>[0]

function setupApiMocks(): void {
  api.getViewerRunCalendar.mockResolvedValue({
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    season_count: 1,
    event_count: 2,
    seasons: [
      {
        season: '2030/2031',
        event_count: 2,
        events: [
          {
            event_id: 'EVENT-1',
            season: '2030/2031',
            season_week: 1,
            calendar_year: 2030,
            year_week: 40,
            template_id: 'WT-GOLD',
            event_name: 'Completed Open',
            category: 'GOLD',
            tour_level: 'WORLD_TOUR',
            host_country: 'CZE',
            host_city: 'Brno',
            region: 'EUROPE',
            duration_in_season_weeks: 1,
            start_season_week: 1,
            end_season_week: 1,
            status: 'completed',
            main_draw_size: 32,
            qualification_draw_size: 16,
            seeds_count: 8,
            qualifier_spots: 4,
            wild_cards: 2,
            byes: 0,
            prestige: 8,
          },
          {
            event_id: 'EVENT-2',
            season: '2030/2031',
            season_week: 2,
            calendar_year: 2030,
            year_week: 41,
            template_id: 'WT-PLAT',
            event_name: 'Next Open',
            category: 'PLATINUM',
            tour_level: 'WORLD_TOUR',
            host_country: 'EGY',
            host_city: 'Cairo',
            region: 'AFRICA',
            duration_in_season_weeks: 1,
            start_season_week: 2,
            end_season_week: 2,
            status: 'planned',
            main_draw_size: 32,
            qualification_draw_size: 16,
            seeds_count: 8,
            qualifier_spots: 4,
            wild_cards: 2,
            byes: 0,
            prestige: 9,
          },
        ],
      },
    ],
  })
  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    tournament_count: 2,
    published_result_count: 1,
    tournaments: [
      {
        event_id: 'EVENT-1',
        season: '2030/2031',
        season_week: 1,
        event_name: 'Completed Open',
        template_id: 'WT-GOLD',
        category: 'GOLD',
        tour_level: 'WORLD_TOUR',
        host_country: 'CZE',
        host_city: 'Brno',
        region: 'EUROPE',
        main_draw_size: 32,
        qualification_draw_size: 16,
        seeds_count: 8,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: true,
        champion_player_id: 'P1',
        finalist_player_id: 'P2',
      },
    ],
  })
  api.listViewerOfficialRankingHistory.mockResolvedValue({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    public_head_ordinal: 100,
    publication_count: 1,
    publications: [
      {
        season_index: 30,
        week: 1,
        week_ordinal: 100,
        snapshot_fingerprint: 'a'.repeat(64),
        policy_id: 'best-15',
        best_n: 15,
        row_count: 64,
      },
    ],
  })
  api.getViewerFinalsRace.mockResolvedValue({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    latest_target_season_index: 30,
    publications: [
      {
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'run alpha',
        viewer_branch_id: 'branch-a',
        target_season_index: 30,
        cutoff_season_index: 30,
        cutoff_week: 1,
        best_n: 9,
        selection_published: false,
        finals_event_id: null,
        rows: [],
      },
    ],
  })
}

function renderHookProbe(props: HookProps): void {
  function Probe(): JSX.Element {
    const result = useViewerDeferredSourceQueries(props)
    return (
      <dl>
        <dt>loading</dt><dd>{String(result.isLoadingMetadata)}</dd>
        <dt>error</dt><dd>{String(result.hasMetadataError)}</dd>
        <dt>has metadata</dt><dd>{String(result.hasAnySourceMetadata)}</dd>
        <dt>calendar events</dt><dd>{String(result.metadata.calendarEventCount)}</dd>
        <dt>completed tournaments</dt><dd>{String(result.metadata.completedTournamentCount)}</dd>
        <dt>ranking publications</dt><dd>{String(result.metadata.rankingPublicationCount)}</dd>
        <dt>race publications</dt><dd>{String(result.metadata.finalsRacePublicationCount)}</dd>
        <dt>next event</dt><dd>{result.metadata.nextCalendarEvent?.event_id ?? 'none'}</dd>
      </dl>
    )
  }

  renderWithViewerProviders(<Probe />, { includeViewerContext: false })
}

describe('useViewerDeferredSourceQueries canonical sources', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupApiMocks()
  })

  it('disables all canonical calls when no Product Run is selected', () => {
    renderHookProbe({
      productRunId: null,
      kind: 'match-odds',
      scope: 'prediction',
    })

    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
    expect(screen.getByText('loading').nextSibling).toHaveTextContent('false')
    expect(screen.getByText('has metadata').nextSibling).toHaveTextContent('false')
  })

  it('loads only canonical Saved-Revision/publication sources for the Product Run', async () => {
    renderHookProbe({
      productRunId: 'run alpha',
      kind: 'match-odds',
      scope: 'prediction',
    })

    await waitFor(() => expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run alpha'))
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('run alpha')
    expect(api.listViewerOfficialRankingHistory).toHaveBeenCalledWith('run alpha')
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run alpha')

    await waitFor(() => {
      expect(screen.getByText('calendar events').nextSibling).toHaveTextContent('2')
      expect(screen.getByText('completed tournaments').nextSibling).toHaveTextContent('1')
      expect(screen.getByText('ranking publications').nextSibling).toHaveTextContent('1')
      expect(screen.getByText('race publications').nextSibling).toHaveTextContent('1')
      expect(screen.getByText('next event').nextSibling).toHaveTextContent('EVENT-2')
    })
  })

  it('fails closed when one canonical source is unavailable', async () => {
    api.getViewerTournamentHistory.mockRejectedValueOnce(new Error('history unavailable'))

    renderHookProbe({
      productRunId: 'run alpha',
      kind: 'title-leaders',
      scope: 'stats',
    })

    await waitFor(() => expect(screen.getByText('error').nextSibling).toHaveTextContent('true'))
  })
})

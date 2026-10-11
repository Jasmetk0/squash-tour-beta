import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { ViewerDeferredCanonicalMetadata } from './useViewerDeferredSourceQueries'
import {
  commonDeferredSourceMetadataItems,
  renderDeferredSourceLinks,
  renderLoadingValue,
  renderSourceMetadataList
} from './ViewerDeferredSourceMetadataRender'

const metadata: ViewerDeferredCanonicalMetadata = {
  viewerBranchId: 'branch-a',
  seasonCount: 2,
  calendarEventCount: 12,
  completedTournamentCount: 5,
  rankingPublicationCount: 4,
  finalsRacePublicationCount: 3,
  latestCompletedTournament: {
    event_id: 'British Open 2034',
    season: '2034/2035',
    season_week: 20,
    event_name: 'British Open 2034',
    template_id: 'BO',
    category: 'PLATINUM',
    tour_level: 'WORLD_TOUR',
    host_country: 'GBR',
    host_city: 'London',
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
    finalist_player_id: 'P2'
  },
  latestRankingPublication: {
    season_index: 34,
    week: 20,
    week_ordinal: 22,
    snapshot_fingerprint: 'a'.repeat(64),
    policy_id: 'best-15',
    best_n: 15,
    row_count: 64
  },
  latestFinalsRacePublication: {
    schema_version: 'viewer_finals_race_publication.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: 'branch-a',
    target_season_index: 34,
    cutoff_season_index: 34,
    cutoff_week: 20,
    best_n: 9,
    selection_published: true,
    finals_event_id: 'FINALS-34',
    rows: []
  },
  nextCalendarEvent: null
}

describe('ViewerDeferredSourceMetadata rendering helpers', () => {
  it('renders canonical Product Run metadata and source links', () => {
    render(
      <MemoryRouter>
        {renderSourceMetadataList(commonDeferredSourceMetadataItems({
          productRunId: 'run alpha',
          metadata,
          isLoading: false
        }))}
      </MemoryRouter>
    )

    const terms = screen.getAllByRole('term').map((term) => term.textContent)
    expect(terms).toEqual([
      'Product Run',
      'Viewer Branch',
      'Saved seasons',
      'Saved Calendar events',
      'Completed tournaments',
      'Official Ranking publications',
      'Finals Race publications',
      'Finals availability',
      'Latest completed tournament',
      'Latest Official Ranking',
      'Latest Finals Race'
    ])
    expect(screen.getByRole('link', { name: 'Finals selection published' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/finals')
    expect(screen.getByRole('link', { name: 'British Open 2034' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments/British%20Open%202034')
    expect(screen.getByRole('link', { name: /Season 34 W20 · #22/i })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/22')
    expect(screen.getByRole('link', { name: /Target season 34 · W20/i })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
  })

  it('preserves loading and fallback values', () => {
    render(
      <MemoryRouter>
        {renderSourceMetadataList([
          { label: 'Loading item', value: renderLoadingValue(true, null) },
          { label: 'Fallback item', value: renderLoadingValue(false, null) }
        ])}
      </MemoryRouter>
    )

    expect(within(screen.getByText('Loading item').closest('div') as HTMLElement).getByText('Loading…')).toBeInTheDocument()
    expect(within(screen.getByText('Fallback item').closest('div') as HTMLElement).getByText('—')).toBeInTheDocument()
  })

  it('renders deferred source links through the shared Viewer list component', () => {
    render(
      <MemoryRouter>
        {renderDeferredSourceLinks([
          { label: 'Open source A', to: '/viewer/runs/run%20alpha/source-a' },
          { label: 'Open source B', to: '/viewer/runs/run%20alpha/source-b' }
        ])}
      </MemoryRouter>
    )

    expect(screen.getByRole('link', { name: 'Open source A' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/source-a')
    expect(screen.getByRole('link', { name: 'Open source B' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/source-b')
  })
})

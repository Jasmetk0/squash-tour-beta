import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { DeferredSourceMetadata } from './viewerDeferredSourceMetadata'
import {
  commonDeferredSourceMetadataItems,
  renderDeferredSourceLinks,
  renderLoadingValue,
  renderSourceMetadataList
} from './ViewerDeferredSourceMetadata'

const metadata: DeferredSourceMetadata = {
  eventCount: 12,
  rankingSnapshotCount: 4,
  raceSnapshotCount: 3,
  latestPersistedEvent: { event_id: 'British Open 2034', event_sequence: 12, season: 2034, week: 20, template_id: 'BO', tournament_result: {} },
  latestRankingSnapshot: { snapshot_sequence: 22, snapshot_kind: 'ranking', source_event_id: 'British Open 2034', payload: {} },
  latestRaceSnapshot: { snapshot_sequence: 7, snapshot_kind: 'race', source_event_id: 'British Open 2034', payload: {} },
  finalsAvailability: 'Finals qualification available',
  hasFinalsAvailability: true
}

describe('ViewerDeferredSourceMetadata rendering helpers', () => {
  it('preserves common metadata label order and source link hrefs', () => {
    render(
      <MemoryRouter>
        {renderSourceMetadataList(commonDeferredSourceMetadataItems({
          activeRunId: 'run alpha',
          metadata,
          eventsLoading: false,
          rankingSnapshotsLoading: false,
          raceSnapshotsLoading: false,
          finalsLoading: false
        }))}
      </MemoryRouter>
    )

    const terms = screen.getAllByRole('term').map((term) => term.textContent)
    expect(terms).toEqual([
      'Active run ID',
      'Completed/persisted event count',
      'Ranking snapshot count',
      'Race snapshot count',
      'Finals availability',
      'Latest persisted event',
      'Latest ranking snapshot',
      'Latest race snapshot'
    ])
    expect(screen.getByRole('link', { name: 'Finals qualification available' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/finals')
    expect(screen.getByRole('link', { name: 'British Open 2034' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments/British%20Open%202034')
    expect(screen.getByRole('link', { name: '#22' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/22')
    expect(screen.getByRole('link', { name: '#7' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race/7')
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

  it('renders deferred source links through the shared Viewer active-run list component', () => {
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

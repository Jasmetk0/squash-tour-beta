import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { ViewerDeferredSourceCard } from './ViewerDeferredSourceCard'

const forbiddenViewerActionLabels = [
  'Simulate',
  'Generate',
  'Persist',
  'Apply',
  'Execute',
  'Delete',
  'Edit',
  'Import',
  'Rollover',
  'Rebuild',
  'Override',
  'Save changes',
  'Commit',
  'Regenerate',
  'Repair',
  'Merge',
  'Overwrite',
]

describe('ViewerDeferredSourceCard', () => {
  it('renders the shared deferred source shell without forbidden Viewer actions', () => {
    render(
      <MemoryRouter>
        <ViewerDeferredSourceCard
          title="Match Odds"
          subtitle="Outputs remain deferred."
          isLoadingMetadata={true}
          hasMetadataError={false}
          hasAnySourceMetadata={true}
          metadataItems={[
            { label: 'Active run ID', value: 'run alpha' },
            { label: 'Completed/persisted event count', value: 4 },
          ]}
          deferredCopy="No match odds are shown yet."
          sourceLinks={[{ label: 'Open run browser', to: '/viewer/runs' }]}
          sourceLinksAriaLabel="Match Odds links"
        />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('article', {
        name: 'Match Odds active run metadata summary',
      }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Match Odds sources' })).toBeInTheDocument()
    expect(screen.getByText('Loading active run metadata…')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Available source metadata' })).toBeInTheDocument()
    expect(screen.getByText('Completed/persisted event count')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Deferred output' })).toBeInTheDocument()
    expect(screen.getByText('No match odds are shown yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open run browser' })).toHaveAttribute('href', '/viewer/runs')

    for (const label of forbiddenViewerActionLabels) {
      expect(screen.queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })

  it('renders the preserved no-data empty state', () => {
    render(
      <MemoryRouter>
        <ViewerDeferredSourceCard
          title="Match Odds"
          subtitle="Outputs remain deferred."
          isLoadingMetadata={false}
          hasMetadataError={false}
          hasAnySourceMetadata={false}
          metadataItems={[{ label: 'Active run ID', value: 'run alpha' }]}
          deferredCopy="No match odds are shown yet."
          sourceLinks={[]}
          sourceLinksAriaLabel="Match Odds links"
        />
      </MemoryRouter>,
    )

    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
  })

  it('renders the preserved metadata error state', () => {
    render(
      <MemoryRouter>
        <ViewerDeferredSourceCard
          title="Match Odds"
          subtitle="Outputs remain deferred."
          isLoadingMetadata={false}
          hasMetadataError={true}
          hasAnySourceMetadata={false}
          metadataItems={[{ label: 'Active run ID', value: 'run alpha' }]}
          deferredCopy="No match odds are shown yet."
          sourceLinks={[]}
          sourceLinksAriaLabel="Match Odds links"
        />
      </MemoryRouter>,
    )

    expect(
      screen.getByText('Some active run metadata is temporarily unavailable.'),
    ).toBeInTheDocument()
  })

  it('does not render the no-data state while metadata is loading', () => {
    render(
      <MemoryRouter>
        <ViewerDeferredSourceCard
          title="Match Odds"
          subtitle="Outputs remain deferred."
          isLoadingMetadata={true}
          hasMetadataError={false}
          hasAnySourceMetadata={false}
          metadataItems={[{ label: 'Active run ID', value: 'run alpha' }]}
          deferredCopy="No match odds are shown yet."
          sourceLinks={[]}
          sourceLinksAriaLabel="Match Odds links"
        />
      </MemoryRouter>,
    )

    expect(screen.getByText('Loading active run metadata…')).toBeInTheDocument()
    expect(
      screen.queryByText('No data is available for this run yet.'),
    ).not.toBeInTheDocument()
  })

  it('does not render the no-data state when metadata has an error', () => {
    render(
      <MemoryRouter>
        <ViewerDeferredSourceCard
          title="Match Odds"
          subtitle="Outputs remain deferred."
          isLoadingMetadata={false}
          hasMetadataError={true}
          hasAnySourceMetadata={false}
          metadataItems={[{ label: 'Active run ID', value: 'run alpha' }]}
          deferredCopy="No match odds are shown yet."
          sourceLinks={[]}
          sourceLinksAriaLabel="Match Odds links"
        />
      </MemoryRouter>,
    )

    expect(
      screen.getByText('Some active run metadata is temporarily unavailable.'),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('No data is available for this run yet.'),
    ).not.toBeInTheDocument()
  })
})

import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
} from '../../../test/viewerTestUtils'
import { ViewerDeferredSourceCard } from './ViewerDeferredSourceCard'

describe('ViewerDeferredSourceCard', () => {
  it('renders the shared deferred source shell without forbidden Viewer actions', () => {
    renderWithViewerProviders(
      <ViewerDeferredSourceCard
        title="Match Odds"
        subtitle="Outputs remain deferred."
        isLoadingMetadata={true}
        hasMetadataError={false}
        hasAnySourceMetadata={true}
        metadataItems={[
          { label: 'Product Run', value: 'run alpha' },
          { label: 'Saved Calendar events', value: 4 },
        ]}
        deferredCopy="No match odds are shown yet."
        sourceLinks={[{ label: 'Open run browser', to: '/viewer/runs' }]}
        sourceLinksAriaLabel="Match Odds links"
      />,
      { includeViewerContext: false },
    )

    const card = screen.getByRole('article', {
      name: 'Match Odds canonical Product Run metadata summary',
    })
    expect(card).toBeInTheDocument()
    expect(card).toHaveClass('viewer-active-run-card')
    expect(card).toHaveClass('viewer-deferred-source-card')
    expect(
      screen.getByRole('heading', { name: 'Match Odds sources' }),
    ).toBeInTheDocument()
    const loadingMessage = screen.getByText('Loading canonical Saved-Revision metadata…')
    expect(loadingMessage).toBeInTheDocument()
    expect(loadingMessage).toHaveClass('status')
    expect(loadingMessage).toHaveClass('viewer-status-message')
    expect(loadingMessage).toHaveClass('viewer-status-message--loading')
    expect(
      screen.getByRole('heading', { name: 'Available source metadata' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Saved Calendar events'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Deferred output' }),
    ).toBeInTheDocument()
    const deferredOutput = screen.getByText('No match odds are shown yet.')
    expect(deferredOutput).toBeInTheDocument()
    expect(deferredOutput).toHaveClass('status')
    expect(deferredOutput).toHaveClass('viewer-status-message')
    expect(
      screen.getByRole('heading', { name: 'Source links' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'Open run browser' }),
    ).toHaveAttribute('href', '/viewer/runs')

    expectNoForbiddenViewerActions()
  })

  it('renders the preserved no-data empty state', () => {
    renderWithViewerProviders(
      <ViewerDeferredSourceCard
        title="Match Odds"
        subtitle="Outputs remain deferred."
        isLoadingMetadata={false}
        hasMetadataError={false}
        hasAnySourceMetadata={false}
        metadataItems={[{ label: 'Product Run', value: 'run alpha' }]}
        deferredCopy="No match odds are shown yet."
        sourceLinks={[]}
        sourceLinksAriaLabel="Match Odds links"
      />,
      { includeViewerContext: false },
    )

    expect(
      screen.getByText('No canonical source data is available for this Product Run yet.'),
    ).toBeInTheDocument()
  })

  it('renders the preserved metadata error state', () => {
    renderWithViewerProviders(
      <ViewerDeferredSourceCard
        title="Match Odds"
        subtitle="Outputs remain deferred."
        isLoadingMetadata={false}
        hasMetadataError={true}
        hasAnySourceMetadata={false}
        metadataItems={[{ label: 'Product Run', value: 'run alpha' }]}
        deferredCopy="No match odds are shown yet."
        sourceLinks={[]}
        sourceLinksAriaLabel="Match Odds links"
      />,
      { includeViewerContext: false },
    )

    expect(
      screen.getByText('Some canonical Saved-Revision metadata is temporarily unavailable.'),
    ).toBeInTheDocument()
  })

  it('does not render the no-data state while metadata is loading', () => {
    renderWithViewerProviders(
      <ViewerDeferredSourceCard
        title="Match Odds"
        subtitle="Outputs remain deferred."
        isLoadingMetadata={true}
        hasMetadataError={false}
        hasAnySourceMetadata={false}
        metadataItems={[{ label: 'Product Run', value: 'run alpha' }]}
        deferredCopy="No match odds are shown yet."
        sourceLinks={[]}
        sourceLinksAriaLabel="Match Odds links"
      />,
      { includeViewerContext: false },
    )

    expect(screen.getByText('Loading canonical Saved-Revision metadata…')).toBeInTheDocument()
    expect(
      screen.queryByText('No canonical source data is available for this Product Run yet.'),
    ).not.toBeInTheDocument()
  })

  it('does not render the no-data state when metadata has an error', () => {
    renderWithViewerProviders(
      <ViewerDeferredSourceCard
        title="Match Odds"
        subtitle="Outputs remain deferred."
        isLoadingMetadata={false}
        hasMetadataError={true}
        hasAnySourceMetadata={false}
        metadataItems={[{ label: 'Product Run', value: 'run alpha' }]}
        deferredCopy="No match odds are shown yet."
        sourceLinks={[]}
        sourceLinksAriaLabel="Match Odds links"
      />,
      { includeViewerContext: false },
    )

    expect(
      screen.getByText('Some canonical Saved-Revision metadata is temporarily unavailable.'),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('No canonical source data is available for this Product Run yet.'),
    ).not.toBeInTheDocument()
  })
})

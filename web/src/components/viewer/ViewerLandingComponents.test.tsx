import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  ViewerActiveRunCard,
  ViewerMetadataList,
  ViewerSectionCard,
  ViewerStatusMessage,
} from './ViewerLandingComponents'

describe('ViewerLandingComponents class contracts', () => {
  it('renders the ViewerActiveRunCard shared active-run shell', () => {
    render(
      <ViewerActiveRunCard ariaLabel="Current Viewer run" title="Run summary">
        <p>Run details.</p>
      </ViewerActiveRunCard>,
    )

    const card = screen.getByRole('article', { name: 'Current Viewer run' })
    expect(card).toHaveClass('viewer-active-run-card')
    expect(card).toHaveClass('viewer-active-run-card--summary')
    expect(card).toHaveAttribute('aria-label', 'Current Viewer run')
    expect(within(card).getByText('Active Viewer run')).toBeInTheDocument()
    expect(within(card).getByRole('heading', { name: 'Run summary' })).toBeInTheDocument()
    expect(within(card).getByText('Run details.')).toBeInTheDocument()
  })

  it('renders ViewerSectionCard standard and hero class hooks with content', () => {
    const { rerender } = render(
      <ViewerSectionCard kicker="Viewer section" title="Standard card">
        <p>Standard body.</p>
      </ViewerSectionCard>,
    )

    const standardCard = screen.getByRole('article')
    expect(standardCard).toHaveClass('viewer-home-card')
    expect(standardCard).toHaveClass('viewer-home-card--standard')
    expect(standardCard).toHaveClass('viewer-section-card')
    expect(within(standardCard).getByText('Viewer section')).toBeInTheDocument()
    expect(within(standardCard).getByRole('heading', { name: 'Standard card' })).toBeInTheDocument()
    expect(within(standardCard).getByText('Standard body.')).toBeInTheDocument()

    rerender(
      <ViewerSectionCard variant="hero" title="Hero card">
        <p>Hero body.</p>
      </ViewerSectionCard>,
    )

    const heroCard = screen.getByRole('article')
    expect(heroCard).toHaveClass('viewer-home-card')
    expect(heroCard).toHaveClass('viewer-home-card--hero')
    expect(heroCard).toHaveClass('viewer-section-card')
    expect(within(heroCard).getByRole('heading', { name: 'Hero card' })).toBeInTheDocument()
    expect(within(heroCard).getByText('Hero body.')).toBeInTheDocument()
  })

  it('renders ViewerMetadataList hooks and label/value pairs in order', () => {
    render(
      <ViewerMetadataList
        ariaLabel="Run metadata"
        className="custom-metadata-list"
        items={[
          { label: 'Active run ID', value: 'run alpha' },
          { label: 'Completed/persisted event count', value: 4 },
        ]}
      />,
    )

    const list = screen.getByLabelText('Run metadata')
    expect(list.tagName).toBe('DL')
    expect(list).toHaveClass('custom-metadata-list')
    expect(list).toHaveClass('viewer-metadata-list')

    const terms = within(list).getAllByRole('term')
    const definitions = within(list).getAllByRole('definition')
    expect(terms.map((term) => term.textContent)).toEqual([
      'Active run ID',
      'Completed/persisted event count',
    ])
    expect(definitions.map((definition) => definition.textContent)).toEqual(['run alpha', '4'])
  })

  it('keeps the default metadata-list class while adding viewer-metadata-list', () => {
    render(<ViewerMetadataList ariaLabel="Default metadata" items={[{ label: 'Season', value: '2004/05' }]} />)

    const list = screen.getByLabelText('Default metadata')
    expect(list).toHaveClass('metadata-list')
    expect(list).toHaveClass('viewer-metadata-list')
  })

  it('renders ViewerStatusMessage tone class hooks without changing visible text', () => {
    const { rerender } = render(<ViewerStatusMessage>Loading Viewer data.</ViewerStatusMessage>)

    const status = screen.getByText('Loading Viewer data.')
    expect(status).toHaveClass('status')
    expect(status).toHaveClass('viewer-status-message')
    expect(status).not.toHaveClass('viewer-status-message--empty')

    rerender(<ViewerStatusMessage tone="empty">No Viewer data.</ViewerStatusMessage>)

    const empty = screen.getByText('No Viewer data.')
    expect(empty).toHaveClass('empty-state')
    expect(empty).toHaveClass('viewer-status-message')
    expect(empty).toHaveClass('viewer-status-message--empty')
  })
})

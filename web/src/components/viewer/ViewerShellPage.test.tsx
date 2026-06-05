import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../test/viewerTestUtils'
import { ViewerShellPage } from './ViewerShellPage'


function renderShell(component: JSX.Element): void {
  renderWithViewerProviders(component)
}

describe('ViewerShellPage', () => {
  it('renders explicit title, kicker, description, and children', () => {
    renderShell(
      <ViewerShellPage title="Custom Viewer Page" kicker="Custom kicker" description="Custom description.">
        <p>Custom child content.</p>
      </ViewerShellPage>
    )

    expect(screen.getByText('Custom kicker')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Custom Viewer Page' })).toBeInTheDocument()
    expect(screen.getByText('Custom description.')).toBeInTheDocument()
    expect(screen.getByText('Custom child content.')).toBeInTheDocument()
  })

  it('renders default kicker and default description when omitted', () => {
    renderShell(<ViewerShellPage title="Defaulted Viewer Page" />)

    expect(screen.getByText('Read-only Viewer section')).toBeInTheDocument()
    expect(screen.getByText('This Viewer section is ready for read-only data. Future tour information will appear here once the read model is connected.')).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
  })

  it('shows the default Viewer context line', () => {
    renderShell(<ViewerShellPage title="Context Page" />)

    expect(screen.getByText('Viewer context: Season 2004/05 · W10. This section is ready for read-only tour data once the Viewer read model is connected.')).toBeInTheDocument()
  })

  it('does not expose forbidden Viewer action labels', () => {
    renderShell(<ViewerShellPage title="Safe Viewer Page" />)

    const shell = screen.getByRole('heading', { level: 2, name: 'Safe Viewer Page' }).closest('section')
    expect(shell).not.toBeNull()
    expectNoForbiddenViewerActions(within(shell as HTMLElement))
  })
})

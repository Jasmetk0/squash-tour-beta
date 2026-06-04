import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ViewerContextProvider } from '../../viewer/ViewerContext'
import { ViewerShellPage } from './ViewerShellPage'

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
  'Overwrite'
]

function renderShell(component: JSX.Element): void {
  render(<ViewerContextProvider>{component}</ViewerContextProvider>)
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
    for (const label of forbiddenViewerActionLabels) {
      expect(within(shell as HTMLElement).queryByText(label, { exact: true })).not.toBeInTheDocument()
    }
  })
})

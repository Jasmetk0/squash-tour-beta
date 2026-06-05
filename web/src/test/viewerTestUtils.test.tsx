import { screen } from '@testing-library/react'
import { Link, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../viewer/activeRun'
import { useViewerContext } from '../viewer/ViewerContext'
import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders } from './viewerTestUtils'

function LocationProbe(): JSX.Element {
  const location = useLocation()
  return <output aria-label="Current route">{location.pathname}</output>
}

function ViewerContextProbe(): JSX.Element {
  const context = useViewerContext()
  return <output aria-label="Viewer season">{context.selectedSeason}</output>
}

describe('viewerTestUtils', () => {
  beforeEach(() => {
    clearViewerStorage()
  })

  it('renderWithViewerProviders renders UI with router support', () => {
    renderWithViewerProviders(
      <>
        <Link to="/viewer/runs/run-a">Open run</Link>
        <LocationProbe />
      </>,
      { route: '/viewer' },
    )

    expect(screen.getByRole('link', { name: 'Open run' })).toHaveAttribute('href', '/viewer/runs/run-a')
    expect(screen.getByLabelText('Current route')).toHaveTextContent('/viewer')
  })

  it('activeRunId option writes Viewer active-run storage', () => {
    renderWithViewerProviders(<p>Active run fixture</p>, { activeRunId: 'run utility' })

    expect(screen.getByText('Active run fixture')).toBeInTheDocument()
    expect(localStorage.getItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)).toBe('run utility')
  })

  it('includeViewerContext false renders without ViewerContextProvider', () => {
    renderWithViewerProviders(<p>No Viewer context required</p>, { includeViewerContext: false })

    expect(screen.getByText('No Viewer context required')).toBeInTheDocument()
  })

  it('provides ViewerContextProvider by default', () => {
    renderWithViewerProviders(<ViewerContextProbe />)

    expect(screen.getByLabelText('Viewer season')).toHaveTextContent('2004/05')
  })

  it('expectNoForbiddenViewerActions passes when forbidden labels are absent', () => {
    renderWithViewerProviders(<p>Read-only viewer content</p>)

    expectNoForbiddenViewerActions()
  })
})

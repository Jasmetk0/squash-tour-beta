import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearViewerStorage,
  expectNoForbiddenViewerActions,
  renderWithViewerProviders,
  setViewerActiveProductRunId
} from '../../../test/viewerTestUtils'
import { ViewerTourCalendarPage } from './ViewerTourCalendarPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn()
}))

vi.mock('../../../api/client', () => api)

describe('ViewerTourCalendarPage canonical Saved Calendar landing', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    api.getViewerRunCalendar.mockResolvedValue({
      schema_version: 'viewer_run_calendar.v1',
      product_run_id: 'tour run',
      viewer_branch_id: 'branch-tour',
      season_count: 2,
      event_count: 17,
      seasons: []
    })
  })

  it('shows a Product Run empty state when nothing is selected', () => {
    renderWithViewerProviders(<ViewerTourCalendarPage />)

    expect(screen.getByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders canonical Saved Calendar metadata and run-scoped schedule link', async () => {
    setViewerActiveProductRunId('tour run')
    renderWithViewerProviders(<ViewerTourCalendarPage />)

    expect(await screen.findByRole('article', { name: 'Saved Calendar summary' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('tour run')
    expect(await screen.findByText('branch-tour')).toBeInTheDocument()
    expect(screen.getByText('Saved seasons')).toBeInTheDocument()
    expect(screen.getByText('Saved events')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run schedule' })).toHaveAttribute(
      'href',
      '/viewer/runs/tour%20run/calendar'
    )
    expectNoForbiddenViewerActions()
  })

  it('fails closed when Saved Calendar metadata cannot be loaded', async () => {
    setViewerActiveProductRunId('tour run')
    api.getViewerRunCalendar.mockRejectedValueOnce(new Error('calendar unavailable'))

    renderWithViewerProviders(<ViewerTourCalendarPage />)

    expect(await screen.findByText('Saved Calendar metadata is temporarily unavailable.')).toBeInTheDocument()
    expect(screen.queryByText(/calendar unavailable/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

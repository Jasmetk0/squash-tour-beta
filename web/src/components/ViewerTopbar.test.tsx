import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'

import { ViewerTopbar, isExactViewerActivePath } from './ViewerTopbar'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../test/viewerTestUtils'
import { ViewerContextProvider } from '../viewer/ViewerContext'
import { viewerDropdowns } from '../viewer/viewerNavigation'

const api = vi.hoisted(() => ({
  listRuns: vi.fn()
}))

vi.mock('../api/client', () => api)

const dropdownExpectations: Record<string, string[]> = {
  Rankings: ['MSA Rankings', 'Race to Finals', 'Next Gen Race', 'Elo Ranking', 'Power Rating', 'Form Ranking', 'No.1 History'],
  Tour: ['Season Hub', 'Season Calendar', 'Current Week', 'All Tournaments', 'Match Center', 'Tournament Categories', 'Past Champions'],
  Players: ['Players Hub', 'All Players', 'Active Players', 'Prospects / Next Gen', 'Retired Players', 'Compare Players'],
  Countries: ['Countries Hub', 'Country Ranking', 'All Countries', 'Hosting Nations', 'Talent Pipeline', 'Country Records'],
  H2H: ['H2H Explorer', 'Rivalry Rankings', 'Most Played Matchups', 'Finals Rivalries', 'Player Comparison', 'Predict Matchup'],
  Stats: ['Stats Hub', 'Records', 'Title Leaders', 'Weeks at No.1', 'Streaks', 'Biggest Upsets', 'Best Seasons', 'Player Stats', 'Tournament Stats', 'Country Stats', 'Awards', 'Hall of Fame', 'Era Rankings'],
  Predictions: ['Match Predictor', 'Match Odds', 'Tournament Odds', 'Finals Qualification', 'Season-End No.1', 'Upset Watch', 'Futures Markets']
}


function LocationProbe(): JSX.Element {
  const location = useLocation()
  return <output aria-label="Current location">{`${location.pathname}${location.search}`}</output>
}

function renderViewerTopbarAt(route: string): void {
  const client = createTestQueryClient()

  render(
    <QueryClientProvider client={client}>
      <ViewerContextProvider>
        <MemoryRouter initialEntries={[route]}>
          <ViewerTopbar />
          <Routes>
            <Route path="*" element={<LocationProbe />} />
          </Routes>
        </MemoryRouter>
      </ViewerContextProvider>
    </QueryClientProvider>
  )
}

describe('ViewerTopbar', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run-a',
          season: 2030,
          seed: 9,
          progress: { next_event_index: 0, total_events: 4, completed_event_count: 0 },
          source_type: 'fresh_seed',
          parent_run_id: null,
          child_run_count: 0
        },
        {
          run_id: 'run-b',
          season: 2031,
          seed: 11,
          progress: { next_event_index: 1, total_events: 5, completed_event_count: 1 },
          source_type: 'fresh_seed',
          parent_run_id: null,
          child_run_count: 0
        }
      ]
    })
  })

  it('shows exact Viewer topbar categories and dropdown menu items without forbidden Viewer actions', async () => {
    renderViewerTopbarAt('/viewer')

    const nav = await screen.findByTestId('viewer-primary-nav')
    expect(within(nav).getByRole('link', { name: 'MSA' })).toHaveAttribute('href', '/viewer')
    expect(within(nav).getByRole('search', { name: 'Viewer search' })).toBeInTheDocument()
    expect(within(nav).getByRole('textbox', { name: 'Search players, countries, tournaments' })).toHaveAttribute('placeholder', 'Search players, countries, tournaments…')

    for (const dropdown of viewerDropdowns) {
      expect(within(nav).getByRole('link', { name: dropdown.label })).toHaveAttribute('href', dropdown.to)
      expect(within(nav).queryByRole('button', { name: `${dropdown.label} submenu` })).not.toBeInTheDocument()
      expect(dropdown.items.map((item) => item.label)).toEqual(dropdownExpectations[dropdown.label])
      for (const item of dropdown.items) {
        expect(within(nav).getAllByRole('link', { name: item.label }).some((link) => link.getAttribute('href') === item.to)).toBe(true)
      }
    }

    expectNoForbiddenViewerActions(within(nav))
  })

  it('navigates Viewer search submissions to the canonical search route with encoded query text', async () => {
    const user = userEvent.setup()
    renderViewerTopbarAt('/viewer')

    const nav = await screen.findByTestId('viewer-primary-nav')
    await user.type(within(nav).getByRole('textbox', { name: 'Search players, countries, tournaments' }), 'Ali Farag')
    await user.click(within(nav).getByRole('button', { name: 'Open Viewer search' }))

    expect(screen.getByLabelText('Current location')).toHaveTextContent('/viewer/search?q=Ali%20Farag')
  })

  it('marks only the exact dropdown route active while keeping active state structural and neutral-style compatible', async () => {
    renderViewerTopbarAt('/viewer/tour/current-week')

    const nav = await screen.findByTestId('viewer-primary-nav')
    const tourParent = within(nav).getByRole('link', { name: 'Tour' })
    const seasonHub = within(nav).getByRole('link', { name: 'Season Hub' })
    const currentWeek = within(nav).getByRole('link', { name: 'Current Week' })

    expect(tourParent).toHaveClass('active')
    expect(currentWeek).toHaveClass('active')
    expect(seasonHub).not.toHaveClass('active')
    expect(isExactViewerActivePath('/viewer/tour/current-week', '/viewer/tour')).toBe(false)
    expect(isExactViewerActivePath('/viewer/tour/current-week', '/viewer/tour/current-week')).toBe(true)
  })

  it('keeps Country Ranking active under Countries instead of Rankings', async () => {
    renderViewerTopbarAt('/viewer/countries/ranking')

    const nav = await screen.findByTestId('viewer-primary-nav')

    expect(within(nav).getByRole('link', { name: 'Countries' })).toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'Rankings' })).not.toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'Country Ranking' })).toHaveClass('active')
  })

  it('keeps Records active under Stats without marking Stats Hub active', async () => {
    renderViewerTopbarAt('/viewer/records')

    const nav = await screen.findByTestId('viewer-primary-nav')

    expect(within(nav).getByRole('link', { name: 'Stats' })).toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'Records' })).toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'Stats Hub' })).not.toHaveClass('active')
  })

  it('keeps Stats Hub active under Stats without marking Records active', async () => {
    renderViewerTopbarAt('/viewer/stats')

    const nav = await screen.findByTestId('viewer-primary-nav')

    expect(within(nav).getByRole('link', { name: 'Stats' })).toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'Stats Hub' })).toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'Records' })).not.toHaveClass('active')
  })

  it('keeps canonical Tour tournaments active under Tour and All Tournaments', async () => {
    renderViewerTopbarAt('/viewer/tour/tournaments')

    const nav = await screen.findByTestId('viewer-primary-nav')

    expect(within(nav).getByRole('link', { name: 'Tour' })).toHaveClass('active')
    expect(within(nav).getByRole('link', { name: 'All Tournaments' })).toHaveClass('active')
  })

  it('keeps the public tournaments alias accepted under Tour topbar ownership', async () => {
    renderViewerTopbarAt('/viewer/tournaments')

    const nav = await screen.findByTestId('viewer-primary-nav')

    expect(within(nav).getByRole('link', { name: 'Tour' })).toHaveClass('active')
  })

  it('shows no duplicate Viewer run navigation row in Viewer topbar rendering', async () => {
    renderViewerTopbarAt('/viewer/runs/run-a/rankings')

    expect(await screen.findByTestId('viewer-primary-nav')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Run navigation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Viewer active run quick links' })).not.toBeInTheDocument()
  })

  it('shows and updates the compact Viewer active run control in the topbar', async () => {
    const user = userEvent.setup()
    renderViewerTopbarAt('/viewer')

    const nav = await screen.findByTestId('viewer-primary-nav')
    const control = within(nav).getByRole('form', { name: 'Viewer topbar active run' })
    expect(control).toHaveTextContent('Active run: None')
    expect(within(control).getByLabelText('Viewer active run')).toBeInTheDocument()
    expect(within(control).queryByRole('button', { name: 'Set run' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Viewer active run quick links' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Admin / Engine' })).not.toBeInTheDocument()

    await within(control).findByRole('option', { name: /run-b · S2031 · seed 11/ })
    await user.selectOptions(within(control).getByLabelText('Viewer active run'), 'run-b')

    expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBe('run-b')
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-b')
    expect(control).toHaveTextContent('Active run: run-b')
  })

  it('shows and expands the Season/Week selector on click', async () => {
    const user = userEvent.setup()
    renderViewerTopbarAt('/viewer')

    const selector = await screen.findByRole('button', { name: 'Season 2004/05 · W10' })
    expect(selector).toHaveAttribute('aria-expanded', 'false')

    await user.click(selector)

    expect(selector).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByLabelText('Selected season')).toHaveValue('2004/05')
    expect(screen.getByLabelText('Selected week')).toHaveValue(10)
    expect(screen.getByRole('button', { name: 'Set Viewer Week' })).toBeInTheDocument()
    expect(screen.getByText('Season Week: 10 / 61')).toBeInTheDocument()
    expect(screen.getByText('Calendar Year: 2004')).toBeInTheDocument()
    expect(screen.getByText('Year Week: 46')).toBeInTheDocument()
    expect(screen.getByText(/Status: selected viewer context/)).toBeInTheDocument()
  })
})

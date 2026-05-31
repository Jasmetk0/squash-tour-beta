import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { getModeSwitcherTarget, isExactViewerActivePath, Layout, viewerDropdowns } from './Layout'
import { renderWithRoute } from '../test/testUtils'

const dropdownExpectations: Record<string, string[]> = {
  Rankings: ['MSA Rankings', 'Race to Finals', 'Next Gen Race', 'Elo Ranking', 'Power Rating', 'Form Ranking', 'Country Ranking', 'No.1 History'],
  Tour: ['Season Hub', 'Season Calendar', 'Current Week', 'All Tournaments', 'Match Center', 'Tournament Categories', 'Past Champions'],
  Players: ['Players Hub', 'All Players', 'Active Players', 'Prospects / Next Gen', 'Retired Players', 'Compare Players'],
  Countries: ['Countries Hub', 'Country Ranking', 'All Countries', 'Hosting Nations', 'Talent Pipeline', 'Country Records'],
  H2H: ['H2H Explorer', 'Rivalry Rankings', 'Most Played Matchups', 'Finals Rivalries', 'Player Comparison', 'Predict Matchup'],
  Stats: ['Records', 'Title Leaders', 'Weeks at No.1', 'Streaks', 'Biggest Upsets', 'Best Seasons', 'Player Stats', 'Tournament Stats', 'Country Stats', 'Awards', 'Hall of Fame', 'Era Rankings'],
  Predictions: ['Match Predictor', 'Match Odds', 'Tournament Odds', 'Finals Qualification', 'Season-End No.1', 'Upset Watch', 'Futures Markets']
}

describe('Layout mode navigation', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('keeps Admin / Engine mode navigation and run-scoped admin links stable', async () => {
    renderWithRoute(<Layout />, '/admin/runs/run-a/finals')

    expect(await screen.findByText('Admin / Engine Mode')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Viewer / MSA' })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin/runs/run-a/finals')
    expect(screen.getByRole('link', { name: 'World' })).toHaveAttribute('href', '/admin/world')
    expect(screen.getByRole('link', { name: 'Tour & Seasons' })).toHaveAttribute('href', '/admin/tour-seasons')
    expect(screen.getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
    expect(screen.getByRole('link', { name: 'Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.getByRole('link', { name: 'Run Detail' })).toHaveAttribute('href', '/admin/runs/run-a')
    expect(screen.getByRole('link', { name: 'Events' })).toHaveAttribute('href', '/admin/runs/run-a/events')
    expect(screen.getByRole('link', { name: 'Season Calendar' })).toHaveAttribute('href', '/admin/runs/run-a/calendar')
    expect(screen.getAllByRole('link', { name: 'Diagnostics' })[1]).toHaveAttribute('href', '/admin/runs/run-a/diagnostics')
    expect(screen.getByRole('link', { name: 'World Generation' })).toHaveAttribute('href', '/admin/runs/run-a/world-generation')
    expect(screen.getByRole('link', { name: 'Ranking Snapshots' })).toHaveAttribute('href', '/admin/runs/run-a/snapshots/ranking')
    expect(screen.getByRole('link', { name: 'Race Snapshots' })).toHaveAttribute('href', '/admin/runs/run-a/snapshots/race')
    expect(screen.getByText('Current run context: run-a')).toBeInTheDocument()
  })

  it('shows one Viewer primary nav and no duplicate Viewer run nav', async () => {
    renderWithRoute(<Layout />, '/viewer/runs/run-a/rankings')

    expect(await screen.findByText('Viewer / MSA Website Mode')).toBeInTheDocument()
    expect(screen.getAllByTestId('viewer-primary-nav')).toHaveLength(1)
    expect(screen.queryByRole('navigation', { name: 'Run navigation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Viewer active run quick links' })).not.toBeInTheDocument()
  })

  it('shows exact Viewer topbar categories and dropdown menu items', async () => {
    renderWithRoute(<Layout />, '/viewer')

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
  })


  it('marks only the exact dropdown route active while keeping active state structural and neutral-style compatible', async () => {
    renderWithRoute(<Layout />, '/viewer/tour/current-week')

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


  it('keeps shared Viewer shortcut dropdown entries pointed at the same canonical routes', async () => {
    renderWithRoute(<Layout />, '/viewer')

    const nav = await screen.findByTestId('viewer-primary-nav')
    expect(within(nav).getAllByRole('link', { name: 'Country Ranking' }).map((link) => link.getAttribute('href'))).toEqual([
      '/viewer/countries/ranking',
      '/viewer/countries/ranking'
    ])
    expect(within(nav).getByRole('link', { name: 'Compare Players' })).toHaveAttribute('href', '/viewer/players/compare')
    expect(within(nav).getByRole('link', { name: 'Player Comparison' })).toHaveAttribute('href', '/viewer/players/compare')
    expect(within(nav).getByRole('link', { name: 'Predict Matchup' })).toHaveAttribute('href', '/viewer/predictions/match-predictor')
    expect(within(nav).getByRole('link', { name: 'Match Predictor' })).toHaveAttribute('href', '/viewer/predictions/match-predictor')
  })

  it('shows and expands the Season/Week selector on click', async () => {
    const user = userEvent.setup()
    renderWithRoute(<Layout />, '/viewer')

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

  it('maps context-aware Admin/Viewer switcher routes', () => {
    expect(getModeSwitcherTarget('/viewer')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin' })
    expect(getModeSwitcherTarget('/admin')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin' })
    expect(getModeSwitcherTarget('/viewer/players')).toEqual({ viewerTarget: '/viewer/players', adminTarget: '/admin/players' })
    expect(getModeSwitcherTarget('/admin/players')).toEqual({ viewerTarget: '/viewer/players', adminTarget: '/admin/players' })
    expect(getModeSwitcherTarget('/viewer/countries')).toEqual({ viewerTarget: '/viewer/countries', adminTarget: '/admin/world/countries' })
    expect(getModeSwitcherTarget('/admin/world/countries')).toEqual({ viewerTarget: '/viewer/countries', adminTarget: '/admin/world/countries' })
    expect(getModeSwitcherTarget('/viewer/tour')).toEqual({ viewerTarget: '/viewer/tour', adminTarget: '/admin/tour-seasons' })
    expect(getModeSwitcherTarget('/admin/tour-seasons')).toEqual({ viewerTarget: '/viewer/tour', adminTarget: '/admin/tour-seasons' })
    expect(getModeSwitcherTarget('/viewer/runs/abc/calendar')).toEqual({ viewerTarget: '/viewer/runs/abc/calendar', adminTarget: '/admin/runs/abc/calendar' })
    expect(getModeSwitcherTarget('/admin/runs/abc/calendar')).toEqual({ viewerTarget: '/viewer/runs/abc/calendar', adminTarget: '/admin/runs/abc/calendar' })
    expect(getModeSwitcherTarget('/viewer/runs/abc/players')).toEqual({ viewerTarget: '/viewer/runs/abc/players', adminTarget: '/admin/runs/abc/players' })
    expect(getModeSwitcherTarget('/admin/runs/abc/players')).toEqual({ viewerTarget: '/viewer/runs/abc/players', adminTarget: '/admin/runs/abc/players' })
    expect(getModeSwitcherTarget('/viewer/unknown')).toEqual({ viewerTarget: '/viewer/unknown', adminTarget: '/admin' })
    expect(getModeSwitcherTarget('/admin/unknown')).toEqual({ viewerTarget: '/viewer', adminTarget: '/admin/unknown' })
  })
})

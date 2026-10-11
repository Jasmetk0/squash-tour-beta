import appSource from '../App.tsx?raw'

import { describe, expect, it } from 'vitest'

import { viewerDropdowns } from './viewerNavigation'

const dropdownExpectations: Record<string, Array<{ label: string; to: string }>> = {
  Rankings: [
    { label: 'MSA Rankings', to: '/viewer/rankings' },
    { label: 'Race to Finals', to: '/viewer/rankings/race' },
    { label: 'Next Gen Race', to: '/viewer/rankings/next-gen' },
    { label: 'Elo Ranking', to: '/viewer/rankings/elo' },
    { label: 'Power Rating', to: '/viewer/rankings/power' },
    { label: 'Form Ranking', to: '/viewer/rankings/form' },
    { label: 'No.1 History', to: '/viewer/rankings/no1-history' }
  ],
  Tour: [
    { label: 'Season Hub', to: '/viewer/tour' },
    { label: 'Season Calendar', to: '/viewer/tour/calendar' },
    { label: 'Current Week', to: '/viewer/tour/current-week' },
    { label: 'All Tournaments', to: '/viewer/tour/tournaments' },
    { label: 'Match Center', to: '/viewer/tour/matches' },
    { label: 'Tournament Categories', to: '/viewer/tour/categories' },
    { label: 'Past Champions', to: '/viewer/tour/champions' }
  ],
  Players: [
    { label: 'Players Hub', to: '/viewer/players' },
    { label: 'All Players', to: '/viewer/players/all' },
    { label: 'Active Players', to: '/viewer/players/active' },
    { label: 'Prospects / Next Gen', to: '/viewer/players/next-gen' },
    { label: 'Retired Players', to: '/viewer/players/retired' },
    { label: 'Compare Players', to: '/viewer/players/compare' }
  ],
  Countries: [
    { label: 'Countries Hub', to: '/viewer/countries' },
    { label: 'Country Ranking', to: '/viewer/countries/ranking' },
    { label: 'All Countries', to: '/viewer/countries/all' },
    { label: 'Hosting Nations', to: '/viewer/countries/hosting' },
    { label: 'Talent Pipeline', to: '/viewer/countries/talent-pipeline' },
    { label: 'Country Records', to: '/viewer/countries/records' }
  ],
  H2H: [
    { label: 'H2H Explorer', to: '/viewer/h2h' },
    { label: 'Rivalry Rankings', to: '/viewer/h2h/rivalries' },
    { label: 'Most Played Matchups', to: '/viewer/h2h/most-played' },
    { label: 'Finals Rivalries', to: '/viewer/h2h/finals-rivalries' },
    { label: 'Player Comparison', to: '/viewer/players/compare' },
    { label: 'Predict Matchup', to: '/viewer/predictions/match-predictor' }
  ],
  Stats: [
    { label: 'Stats Hub', to: '/viewer/stats' },
    { label: 'Records', to: '/viewer/records' },
    { label: 'Title Leaders', to: '/viewer/stats/title-leaders' },
    { label: 'Weeks at No.1', to: '/viewer/stats/no1-weeks' },
    { label: 'Streaks', to: '/viewer/stats/streaks' },
    { label: 'Biggest Upsets', to: '/viewer/stats/upsets' },
    { label: 'Best Seasons', to: '/viewer/stats/best-seasons' },
    { label: 'Player Stats', to: '/viewer/stats/player-stats' },
    { label: 'Tournament Stats', to: '/viewer/stats/tournament-stats' },
    { label: 'Country Stats', to: '/viewer/stats/country-stats' },
    { label: 'Awards', to: '/viewer/stats/awards' },
    { label: 'Hall of Fame', to: '/viewer/stats/hall-of-fame' },
    { label: 'Era Rankings', to: '/viewer/stats/era-rankings' }
  ],
  Predictions: [
    { label: 'Match Predictor', to: '/viewer/predictions/match-predictor' },
    { label: 'Match Odds', to: '/viewer/predictions/match-odds' },
    { label: 'Tournament Odds', to: '/viewer/predictions/tournament-odds' },
    { label: 'Finals Qualification', to: '/viewer/predictions/finals-qualification' },
    { label: 'Season-End No.1', to: '/viewer/predictions/season-end-no1' },
    { label: 'Upset Watch', to: '/viewer/predictions/upset-watch' },
    { label: 'Futures Markets', to: '/viewer/predictions/futures' }
  ]
}

function appViewerTopLevelRoutes(): Set<string> {
  return new Set(
    [...appSource.matchAll(/<Route\s+path="(viewer(?:\/[^:"]*)?)"/g)].map((match) => `/${match[1]}`)
  )
}

describe('viewerNavigation', () => {
  it('keeps Viewer dropdown labels, order, and hrefs stable', () => {
    expect(viewerDropdowns.map((dropdown) => dropdown.label)).toEqual(Object.keys(dropdownExpectations))

    for (const dropdown of viewerDropdowns) {
      expect(dropdown.items).toEqual(dropdownExpectations[dropdown.label])
    }
  })

  it('keeps Country Ranking owned by Countries only', () => {
    const owners = viewerDropdowns.filter((dropdown) => dropdown.items.some((item) => item.label === 'Country Ranking'))

    expect(owners.map((dropdown) => dropdown.label)).toEqual(['Countries'])
    expect(owners[0].items.find((item) => item.label === 'Country Ranking')?.to).toBe('/viewer/countries/ranking')
  })

  it('keeps Records and Stats Hub on their canonical destinations', () => {
    const statsItems = viewerDropdowns.find((dropdown) => dropdown.label === 'Stats')?.items ?? []

    expect(statsItems.find((item) => item.label === 'Records')?.to).toBe('/viewer/records')
    expect(statsItems.find((item) => item.label === 'Stats Hub')?.to).toBe('/viewer/stats')
  })

  it('keeps every Viewer dropdown destination backed by an App Viewer route', () => {
    const appRoutes = appViewerTopLevelRoutes()
    const dropdownDestinations = viewerDropdowns.flatMap((dropdown) => [
      { label: dropdown.label, to: dropdown.to },
      ...dropdown.items.map((item) => ({ label: `${dropdown.label} > ${item.label}`, to: item.to }))
    ])

    expect(dropdownDestinations.filter((destination) => !appRoutes.has(destination.to))).toEqual([])
    expect([...appRoutes]).toEqual(expect.arrayContaining(['/viewer/tour/tournaments', '/viewer/tournaments']))
  })

  it('keeps shared Viewer shortcut dropdown entries pointed at the same canonical routes', () => {
    const allItems = viewerDropdowns.flatMap((dropdown) => dropdown.items)

    expect(allItems.filter((item) => item.label === 'Country Ranking').map((item) => item.to)).toEqual(['/viewer/countries/ranking'])
    expect(allItems.find((item) => item.label === 'Compare Players')?.to).toBe('/viewer/players/compare')
    expect(allItems.find((item) => item.label === 'Player Comparison')?.to).toBe('/viewer/players/compare')
    expect(allItems.find((item) => item.label === 'Predict Matchup')?.to).toBe('/viewer/predictions/match-predictor')
    expect(allItems.find((item) => item.label === 'Match Predictor')?.to).toBe('/viewer/predictions/match-predictor')
  })
})

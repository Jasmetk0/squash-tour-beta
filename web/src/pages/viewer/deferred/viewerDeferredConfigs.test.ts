import { describe, expect, it } from 'vitest'

import {
  viewerCountriesDeferredConfigs,
  viewerH2HSubrouteContent,
  viewerPlayersDeferredConfigs,
  viewerPredictionDeferredConfigs,
  viewerRankingDeferredConfigs,
  viewerStatsDeferredConfigs,
  viewerTourDeferredConfigs,
} from './viewerDeferredConfigs'

describe('viewerDeferredConfigs', () => {
  it('preserves ranking deferred config titles and copy by route kind', () => {
    expect(Object.keys(viewerRankingDeferredConfigs)).toEqual([
      'next-gen',
      'elo',
      'power',
      'form',
      'no1-history',
    ])
    expect(viewerRankingDeferredConfigs).toMatchObject({
      'next-gen': {
        title: 'Next Gen Race',
        deferredCopy:
          'No Next Gen ranking table is shown until a real Next Gen ranking read model exists.',
      },
      elo: {
        title: 'Elo Ranking',
        deferredCopy:
          'No Elo ranking table is shown until a real Elo ranking read model exists.',
      },
      power: {
        title: 'Power Rating',
        deferredCopy:
          'No Power Rating table is shown until a real Power Rating read model exists.',
      },
      form: {
        title: 'Form Ranking',
        deferredCopy:
          'No form ranking table is shown until a real form ranking read model exists.',
      },
      'no1-history': {
        title: 'No.1 History',
        deferredCopy:
          'No No.1 history table is shown until a real ranking history read model exists.',
      },
    })
  })

  it('preserves people and countries deferred config order', () => {
    expect(Object.entries(viewerPlayersDeferredConfigs)).toEqual([
      [
        'all',
        {
          title: 'All Players',
          deferredCopy:
            'No full player directory is shown until a real player directory read model exists.',
        },
      ],
      [
        'active',
        {
          title: 'Active Players',
          deferredCopy:
            'No active-player list is shown until a real player status read model exists.',
        },
      ],
      [
        'next-gen',
        {
          title: 'Prospects / Next Gen',
          deferredCopy:
            'No prospects list is shown until a real Next Gen player read model exists.',
        },
      ],
      [
        'retired',
        {
          title: 'Retired Players',
          deferredCopy:
            'No retired-player list is shown until a real player career-status read model exists.',
        },
      ],
    ])
    expect(Object.keys(viewerCountriesDeferredConfigs)).toEqual([
      'ranking',
      'all',
      'hosting',
      'talent-pipeline',
      'records',
    ])
    expect(viewerCountriesDeferredConfigs.ranking.title).toBe('Country Ranking')
    expect(viewerCountriesDeferredConfigs.records.deferredCopy).toBe(
      'No country records table is shown until a real country records read model exists.',
    )
  })

  it('preserves tour, prediction, stats, and h2h deferred route families', () => {
    expect(Object.entries(viewerTourDeferredConfigs)).toEqual([
      [
        'matches',
        {
          title: 'Match Center',
          deferredCopy:
            'No match list is shown until a real match read model exists.',
        },
      ],
      [
        'categories',
        {
          title: 'Tournament Categories',
          deferredCopy:
            'No connected category breakdown is shown until a real category read model exists.',
        },
      ],
      [
        'champions',
        {
          title: 'Past Champions',
          deferredCopy:
            'No champions index is shown until a real champions read model exists.',
        },
      ],
    ])
    expect(Object.keys(viewerPredictionDeferredConfigs)).toEqual([
      'match-odds',
      'tournament-odds',
      'finals-qualification',
      'season-end-no1',
      'upset-watch',
      'futures',
    ])
    expect(viewerPredictionDeferredConfigs['match-odds'].title).toBe(
      'Match Odds',
    )
    expect(Object.keys(viewerStatsDeferredConfigs)).toEqual([
      'title-leaders',
      'no1-weeks',
      'streaks',
      'upsets',
      'best-seasons',
      'player-stats',
      'tournament-stats',
      'country-stats',
      'awards',
      'hall-of-fame',
      'era-rankings',
    ])
    expect(viewerH2HSubrouteContent).toEqual({
      rivalries: {
        title: 'Rivalries',
        note: 'No rivalry list is shown until direct match records are available.',
      },
      'most-played': {
        title: 'Most Played Matchups',
        note: 'No matchup list is shown until completed match counts are available.',
      },
      'finals-rivalries': {
        title: 'Finals Rivalries',
        note: 'No finals rivalry list is shown until final-round match records are available.',
      },
    })
  })
})

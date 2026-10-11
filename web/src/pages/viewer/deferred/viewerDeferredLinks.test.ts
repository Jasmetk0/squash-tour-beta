import { describe, expect, it } from 'vitest'

import {
  buildCountriesDeferredSourceLinks,
  buildPlayersDeferredSourceLinks,
  buildPredictionDeferredSourceLinks,
  buildRankingDeferredSourceLinks,
  buildStatsDeferredSourceLinks,
  buildTourDeferredSourceLinks,
} from './viewerDeferredLinks'

describe('viewerDeferredLinks', () => {
  it('preserves ranking deferred source link label order and hrefs', () => {
    expect(buildRankingDeferredSourceLinks('run alpha')).toEqual([
      { label: 'Open active run rankings', to: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Open active run race', to: '/viewer/runs/run%20alpha/race' },
      {
        label: 'Open active run tournaments',
        to: '/viewer/runs/run%20alpha/tournaments',
      },
      {
        label: 'Open active run calendar',
        to: '/viewer/runs/run%20alpha/calendar',
      },
      { label: 'Open run browser', to: '/viewer/runs' },
    ])
  })

  it('preserves tour deferred source link label order and hrefs', () => {
    expect(buildTourDeferredSourceLinks('run alpha')).toEqual([
      {
        label: 'Open active run calendar',
        to: '/viewer/runs/run%20alpha/calendar',
      },
      {
        label: 'Open active run tournaments',
        to: '/viewer/runs/run%20alpha/tournaments',
      },
      { label: 'Open active run rankings', to: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Open active run race', to: '/viewer/runs/run%20alpha/race' },
      { label: 'Open run browser', to: '/viewer/runs' },
    ])
  })

  it('preserves prediction deferred source link label order and hrefs', () => {
    expect(buildPredictionDeferredSourceLinks('run alpha')).toEqual([
      { label: 'Open match predictor', to: '/viewer/predictions/match-predictor' },
      {
        label: 'Open active run tournaments',
        to: '/viewer/runs/run%20alpha/tournaments',
      },
      { label: 'Open active run rankings', to: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Open active run race', to: '/viewer/runs/run%20alpha/race' },
      { label: 'Open run browser', to: '/viewer/runs' },
    ])
  })

  it('preserves stats deferred source link label order and hrefs', () => {
    expect(buildStatsDeferredSourceLinks('run alpha')).toEqual([
      { label: 'Open records', to: '/viewer/records' },
      { label: 'Open stats', to: '/viewer/stats' },
      {
        label: 'Open active run tournaments',
        to: '/viewer/runs/run%20alpha/tournaments',
      },
      { label: 'Open active run rankings', to: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Open active run race', to: '/viewer/runs/run%20alpha/race' },
      { label: 'Open run browser', to: '/viewer/runs' },
    ])
  })

  it('preserves players deferred source link label order and hrefs', () => {
    expect(buildPlayersDeferredSourceLinks('run alpha')).toEqual([
      { label: 'Open active run players', to: '/viewer/runs/run%20alpha/players' },
      { label: 'Open active run countries', to: '/viewer/runs/run%20alpha/countries' },
      { label: 'Open active run rankings', to: '/viewer/runs/run%20alpha/rankings' },
      {
        label: 'Open active run tournaments',
        to: '/viewer/runs/run%20alpha/tournaments',
      },
      { label: 'Open Viewer search', to: '/viewer/search' },
      { label: 'Open run browser', to: '/viewer/runs' },
    ])
  })

  it('preserves countries deferred source link label order and hrefs', () => {
    expect(buildCountriesDeferredSourceLinks('run alpha')).toEqual([
      { label: 'Open active run countries', to: '/viewer/runs/run%20alpha/countries' },
      { label: 'Open active run players', to: '/viewer/runs/run%20alpha/players' },
      { label: 'Open active run rankings', to: '/viewer/runs/run%20alpha/rankings' },
      {
        label: 'Open active run tournaments',
        to: '/viewer/runs/run%20alpha/tournaments',
      },
      { label: 'Open Viewer search', to: '/viewer/search' },
      { label: 'Open run browser', to: '/viewer/runs' },
    ])
  })
})

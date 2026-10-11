import { describe, expect, it } from 'vitest'

import {
  buildStatsRecordsSourceLinks,
  deferredRecordGroups,
  deferredStatsGroups,
  getStatsRecordsDeferredGroups,
  getStatsRecordsLandingConfig
} from './viewerStatsRecordsDisplay'

describe('viewerStatsRecordsDisplay', () => {
  it('preserves deferred record group labels and descriptions in order', () => {
    expect(deferredRecordGroups).toEqual([
      { title: 'Title Leaders', description: 'needs dedicated records read model.' },
      { title: 'Weeks at No.1', description: 'needs dedicated records read model.' },
      { title: 'Streaks', description: 'needs dedicated records read model.' },
      { title: 'Biggest Upsets', description: 'needs match/prediction read model.' },
      { title: 'Best Seasons', description: 'needs historical stats read model.' }
    ])
    expect(getStatsRecordsDeferredGroups('records')).toBe(deferredRecordGroups)
  })

  it('preserves deferred stats group labels and descriptions in order', () => {
    expect(deferredStatsGroups).toEqual([
      { title: 'Player Stats', description: 'needs dedicated player statistics read model.' },
      { title: 'Tournament Stats', description: 'needs dedicated tournament statistics read model.' },
      { title: 'Country Stats', description: 'needs dedicated country statistics read model.' },
      { title: 'Awards', description: 'needs dedicated awards read model.' },
      { title: 'Hall of Fame', description: 'needs dedicated Hall of Fame read model.' },
      { title: 'Era Rankings', description: 'needs dedicated era comparison read model.' }
    ])
    expect(getStatsRecordsDeferredGroups('stats')).toBe(deferredStatsGroups)
  })

  it('preserves landing copy and source link order', () => {
    expect(getStatsRecordsLandingConfig('records')).toMatchObject({
      title: 'Records',
      shellDescription: 'Record book destination prepared for statistics, milestones, and historical achievements.',
      activeShellDescription: 'Conservative Records landing using existing active-run metadata only.',
      overviewTitle: 'Records Overview',
      deferredGroupsTitle: 'Deferred record groups'
    })
    expect(getStatsRecordsLandingConfig('stats')).toMatchObject({
      title: 'Stats',
      shellDescription: 'Stats library destination prepared for connected run-scoped statistical read models.',
      activeShellDescription: 'Conservative Stats landing using existing active-run metadata only.',
      overviewTitle: 'Stats Overview',
      deferredGroupsTitle: 'Deferred stat groups'
    })
    expect(buildStatsRecordsSourceLinks({
      activeRunId: 'run alpha',
      viewerRunsPath: () => '/viewer/runs',
      viewerTournamentsPath: (runId) => `/viewer/runs/${encodeURIComponent(runId)}/tournaments`,
      viewerRankingsPath: (runId) => `/viewer/runs/${encodeURIComponent(runId)}/rankings`,
      viewerRacePath: (runId) => `/viewer/runs/${encodeURIComponent(runId)}/race`,
      viewerFinalsPath: (runId) => `/viewer/runs/${encodeURIComponent(runId)}/finals`
    })).toEqual([
      { label: 'Open run browser', to: '/viewer/runs' },
      { label: 'Open active run tournaments', to: '/viewer/runs/run%20alpha/tournaments' },
      { label: 'Open active run rankings', to: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Open active run race', to: '/viewer/runs/run%20alpha/race' },
      { label: 'Open active run finals', to: '/viewer/runs/run%20alpha/finals' }
    ])
  })
})

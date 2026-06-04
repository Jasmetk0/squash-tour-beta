import { describe, expect, it } from 'vitest'

import {
  buildViewerActiveRunQuickLinks,
  formatViewerActiveRunLabel,
  formatViewerCompactRunOptionLabel,
  formatViewerRunOptionLabel
} from './activeRunDisplay'

describe('Viewer active run display helpers', () => {
  const run = {
    run_id: 'run-a',
    season: 2030,
    seed: 9,
    config_version: null,
    config_fingerprint: null,
    next_event_index: 0,
    total_events: 4,
    completed_event_ids: []
  }

  it('formats selector labels without changing existing text', () => {
    expect(formatViewerRunOptionLabel(run)).toBe('run-a — season 2030, seed 9')
    expect(formatViewerCompactRunOptionLabel(run)).toBe('run-a · S2030 · seed 9')
    expect(formatViewerActiveRunLabel(null)).toBe('None')
    expect(formatViewerActiveRunLabel('run-a')).toBe('run-a')
  })

  it('builds the active run quick links in the existing label and href order', () => {
    expect(buildViewerActiveRunQuickLinks('run alpha')).toEqual([
      { label: 'Open calendar', to: '/viewer/runs/run%20alpha/calendar' },
      { label: 'Open rankings', to: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Open race', to: '/viewer/runs/run%20alpha/race' },
      { label: 'Open tournaments', to: '/viewer/runs/run%20alpha/tournaments' },
      { label: 'Open players', to: '/viewer/runs/run%20alpha/players' },
      { label: 'Open countries', to: '/viewer/runs/run%20alpha/countries' },
      { label: 'Open history', to: '/viewer/runs/run%20alpha/history' },
      { label: 'Open finals', to: '/viewer/runs/run%20alpha/finals' }
    ])
  })
})

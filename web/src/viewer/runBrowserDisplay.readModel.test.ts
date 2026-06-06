import { describe, expect, it } from 'vitest'

import { buildRunBrowserContextLinks, buildRunBrowserMetadataItems, buildRunBrowserPrimaryLinks, type ViewerRunBrowserListItem } from './runBrowserDisplay'

function run(overrides: Record<string, unknown> = {}): ViewerRunBrowserListItem {
  return {
    run_id: 'read model/run #1',
    season: 2035,
    seed: 99,
    progress: { next_event_index: 8, total_events: 20, completed_event_count: 7 },
    source_type: 'rollover_bootstrap',
    parent_run_id: 'parent run',
    child_run_count: 2,
    ...overrides
  } as ViewerRunBrowserListItem
}

describe('run browser read-model display helpers', () => {
  it('builds metadata from only run-list fields with stable fallbacks', () => {
    expect(buildRunBrowserMetadataItems(run({ source_type: undefined, parent_run_id: undefined }))).toEqual([
      { label: 'Run id', value: 'read model/run #1' },
      { label: 'Season', value: 2035 },
      { label: 'Seed', value: 99 },
      { label: 'Source', value: '—' },
      { label: 'Parent run', value: '—' },
      { label: 'Child runs', value: 2 },
      { label: 'Next event index', value: 8 },
      { label: 'Total events', value: 20 },
      { label: 'Completed event count', value: 7 }
    ])
  })

  it('builds encoded primary and context route-helper links in read-only order', () => {
    expect([...buildRunBrowserPrimaryLinks('read model/run #1'), ...buildRunBrowserContextLinks('read model/run #1')]).toEqual([
      { label: 'Season calendar', to: '/viewer/runs/read%20model%2Frun%20%231/calendar' },
      { label: 'Tournaments', to: '/viewer/runs/read%20model%2Frun%20%231/tournaments' },
      { label: 'Rankings', to: '/viewer/runs/read%20model%2Frun%20%231/rankings' },
      { label: 'Race', to: '/viewer/runs/read%20model%2Frun%20%231/race' },
      { label: 'Players', to: '/viewer/runs/read%20model%2Frun%20%231/players' },
      { label: 'Countries', to: '/viewer/runs/read%20model%2Frun%20%231/countries' },
      { label: 'History', to: '/viewer/runs/read%20model%2Frun%20%231/history' },
      { label: 'Finals', to: '/viewer/runs/read%20model%2Frun%20%231/finals' }
    ])
  })
})

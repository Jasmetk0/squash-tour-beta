import { describe, expect, it } from 'vitest'

import {
  buildRunBrowserContextLinks,
  buildRunBrowserMetadataItems,
  buildRunBrowserPrimaryLinks,
  buildViewerRunBrowserLinks,
  formatRunSourceLabel,
  hasSafeRunMetadataValue,
  optionalRunField,
  type ViewerRunBrowserListItem
} from './runBrowserDisplay'

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

  it('returns em dash progress values when progress is missing', () => {
    expect(buildRunBrowserMetadataItems(run({ progress: undefined })).slice(-3)).toEqual([
      { label: 'Next event index', value: '—' },
      { label: 'Total events', value: '—' },
      { label: 'Completed event count', value: '—' }
    ])
  })

  it('does not stringify array or object metadata values from the run-list shape', () => {
    const fields = buildRunBrowserMetadataItems(
      run({
        source_type: ['unsafe-source'],
        parent_run_id: { id: 'parent run' },
        child_run_count: [2],
        progress: { next_event_index: { index: 8 }, total_events: ['20'], completed_event_count: { count: 7 } }
      })
    )

    expect(fields.filter((field) => field.value === '—').map((field) => field.label)).toEqual([
      'Source',
      'Parent run',
      'Child runs',
      'Next event index',
      'Total events',
      'Completed event count'
    ])
    expect(fields.map((field) => String(field.value))).not.toContain('[object Object]')
  })

  it('formats source labels according to the current primitive helper contract', () => {
    expect(formatRunSourceLabel(run({ source_type: true }))).toBe('true')
    expect(formatRunSourceLabel(run({ source_type: 12 }))).toBe('12')
    expect(formatRunSourceLabel(run({ source_type: null }))).toBe('—')
  })

  it('keeps primary and context link helpers stable and combines them without mutation', () => {
    const runId = 'read model/run #1'
    const primary = buildRunBrowserPrimaryLinks(runId)
    const context = buildRunBrowserContextLinks(runId)

    expect(primary).toEqual([
      { label: 'Season calendar', to: '/viewer/runs/read%20model%2Frun%20%231/calendar' },
      { label: 'Tournaments', to: '/viewer/runs/read%20model%2Frun%20%231/tournaments' },
      { label: 'Rankings', to: '/viewer/runs/read%20model%2Frun%20%231/rankings' },
      { label: 'Race', to: '/viewer/runs/read%20model%2Frun%20%231/race' }
    ])
    expect(context).toEqual([
      { label: 'Players', to: '/viewer/runs/read%20model%2Frun%20%231/players' },
      { label: 'Countries', to: '/viewer/runs/read%20model%2Frun%20%231/countries' },
      { label: 'History', to: '/viewer/runs/read%20model%2Frun%20%231/history' },
      { label: 'Finals', to: '/viewer/runs/read%20model%2Frun%20%231/finals' }
    ])
    expect(buildViewerRunBrowserLinks(runId)).toEqual([...primary, ...context])
  })

  it('keeps optional field and safe metadata predicates consistent', () => {
    const sample = run({ source_type: false, custom: 0 })

    expect(optionalRunField(sample, 'source_type')).toBe(false)
    expect(optionalRunField(sample, 'custom')).toBe(0)
    expect(hasSafeRunMetadataValue(false)).toBe(true)
    expect(hasSafeRunMetadataValue(0)).toBe(true)
    expect(hasSafeRunMetadataValue('')).toBe(false)
    expect(hasSafeRunMetadataValue(null)).toBe(false)
    expect(hasSafeRunMetadataValue(['unsafe'])).toBe(false)
    expect(hasSafeRunMetadataValue({ unsafe: true })).toBe(false)
  })

})

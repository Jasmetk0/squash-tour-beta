import { describe, expect, it } from 'vitest'

import {
  buildRunBrowserContextLinks,
  buildRunBrowserMetadataItems,
  buildRunBrowserPrimaryLinks,
  buildViewerRunBrowserLinks,
  formatRunSourceLabel,
  hasSafeRunMetadataValue,
  optionalRunField,
  viewerRunMetadataFields,
  type ViewerRunBrowserListItem
} from './runBrowserDisplay'

function sampleRun(overrides: Record<string, unknown> = {}): ViewerRunBrowserListItem {
  return {
    run_id: 'run alpha',
    season: 2031,
    seed: 42,
    progress: {
      next_event_index: 3,
      total_events: 11,
      completed_event_count: 2
    },
    source_type: 'fresh_seed',
    parent_run_id: 'parent-run',
    child_run_count: 0,
    ...overrides
  } as ViewerRunBrowserListItem
}

describe('Viewer Run Browser display helpers', () => {
  it('preserves conservative Run Browser metadata labels and order for a sample run', () => {
    expect(buildRunBrowserMetadataItems(sampleRun())).toEqual([
      { label: 'Run id', value: 'run alpha' },
      { label: 'Season', value: 2031 },
      { label: 'Seed', value: 42 },
      { label: 'Source', value: 'fresh_seed' },
      { label: 'Parent run', value: 'parent-run' },
      { label: 'Child runs', value: 0 },
      { label: 'Next event index', value: 3 },
      { label: 'Total events', value: 11 },
      { label: 'Completed event count', value: 2 }
    ])
  })

  it('keeps the previous viewerRunMetadataFields export as the metadata helper alias', () => {
    expect(viewerRunMetadataFields(sampleRun())).toEqual(buildRunBrowserMetadataItems(sampleRun()))
  })

  it('uses em dash fallback for missing optional metadata while preserving safe zero values', () => {
    expect(
      buildRunBrowserMetadataItems(
        sampleRun({
          progress: { next_event_index: 0, total_events: 0, completed_event_count: 0 },
          source_type: '',
          parent_run_id: null,
          child_run_count: 0
        })
      )
    ).toEqual([
      { label: 'Run id', value: 'run alpha' },
      { label: 'Season', value: 2031 },
      { label: 'Seed', value: 42 },
      { label: 'Source', value: '—' },
      { label: 'Parent run', value: '—' },
      { label: 'Child runs', value: 0 },
      { label: 'Next event index', value: 0 },
      { label: 'Total events', value: 0 },
      { label: 'Completed event count', value: 0 }
    ])
  })

  it('does not stringify unsafe object metadata values', () => {
    const fields = buildRunBrowserMetadataItems(
      sampleRun({
        source_type: { raw: 'source' },
        parent_run_id: ['parent'],
        child_run_count: { count: 1 },
        progress: { next_event_index: { raw: 1 }, total_events: ['x'], completed_event_count: null }
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
    expect(fields.some((field) => String(field.value) === '[object Object]')).toBe(false)
  })

  it('formats source labels with the same fallback used by the metadata list', () => {
    expect(formatRunSourceLabel(sampleRun())).toBe('fresh_seed')
    expect(formatRunSourceLabel(sampleRun({ source_type: null }))).toBe('—')
  })

  it('preserves primary run browser link labels, hrefs, and order', () => {
    expect(buildRunBrowserPrimaryLinks('run alpha/with #hash')).toEqual([
      { label: 'Season calendar', to: '/viewer/runs/run%20alpha%2Fwith%20%23hash/calendar' },
      { label: 'Tournaments', to: '/viewer/runs/run%20alpha%2Fwith%20%23hash/tournaments' },
      { label: 'Rankings', to: '/viewer/runs/run%20alpha%2Fwith%20%23hash/rankings' },
      { label: 'Race', to: '/viewer/runs/run%20alpha%2Fwith%20%23hash/race' }
    ])
  })

  it('preserves context run browser link labels, hrefs, and order', () => {
    expect(buildRunBrowserContextLinks('run alpha')).toEqual([
      { label: 'Players', to: '/viewer/runs/run%20alpha/players' },
      { label: 'Countries', to: '/viewer/runs/run%20alpha/countries' },
      { label: 'History', to: '/viewer/runs/run%20alpha/history' },
      { label: 'Finals', to: '/viewer/runs/run%20alpha/finals' }
    ])
  })

  it('combines primary and context links for the legacy run browser link helper', () => {
    expect(buildViewerRunBrowserLinks('run alpha')).toEqual([
      ...buildRunBrowserPrimaryLinks('run alpha'),
      ...buildRunBrowserContextLinks('run alpha')
    ])
  })

  it('exposes the same optional field and safe value helpers used by the browser metadata formatter', () => {
    const run = sampleRun({ custom: 'custom-value' })

    expect(optionalRunField(run, 'custom')).toBe('custom-value')
    expect(hasSafeRunMetadataValue('custom-value')).toBe(true)
    expect(hasSafeRunMetadataValue(0)).toBe(true)
    expect(hasSafeRunMetadataValue('')).toBe(false)
    expect(hasSafeRunMetadataValue({ raw: 'unsafe' })).toBe(false)
  })
})

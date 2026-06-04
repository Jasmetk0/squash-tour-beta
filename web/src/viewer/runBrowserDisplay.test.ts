import { describe, expect, it } from 'vitest'

import {
  buildViewerRunBrowserLinks,
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
    created_at: '2031-09-01T00:00:00Z',
    updated_at: '2031-09-02T00:00:00Z',
    ...overrides
  } as ViewerRunBrowserListItem
}

describe('Viewer Run Browser display helpers', () => {
  it('preserves Run Browser metadata labels and order for a sample run', () => {
    expect(viewerRunMetadataFields(sampleRun())).toEqual([
      { label: 'Run id', value: 'run alpha' },
      { label: 'Season', value: 2031 },
      { label: 'Seed', value: 42 },
      { label: 'Next event index', value: 3 },
      { label: 'Total events', value: 11 },
      { label: 'Completed event count', value: 2 },
      { label: 'Source', value: 'fresh_seed' },
      { label: 'Parent run', value: 'parent-run' },
      { label: 'Created', value: '2031-09-01T00:00:00Z' },
      { label: 'Updated', value: '2031-09-02T00:00:00Z' }
    ])
  })

  it('omits missing metadata values while preserving safe zero values', () => {
    expect(
      viewerRunMetadataFields(
        sampleRun({
          progress: { next_event_index: 0, total_events: 0, completed_event_count: 0 },
          source_type: '',
          parent_run_id: null,
          created_at: undefined,
          updated_at: undefined
        })
      )
    ).toEqual([
      { label: 'Run id', value: 'run alpha' },
      { label: 'Season', value: 2031 },
      { label: 'Seed', value: 42 },
      { label: 'Next event index', value: 0 },
      { label: 'Total events', value: 0 },
      { label: 'Completed event count', value: 0 }
    ])
  })

  it('preserves created_at/created and updated_at/updated fallback behavior', () => {
    expect(
      viewerRunMetadataFields(
        sampleRun({
          created_at: undefined,
          created: 'created fallback',
          updated_at: undefined,
          updated: 'updated fallback'
        })
      ).slice(-2)
    ).toEqual([
      { label: 'Created', value: 'created fallback' },
      { label: 'Updated', value: 'updated fallback' }
    ])
  })

  it('does not return unsafe object metadata values', () => {
    const fields = viewerRunMetadataFields(
      sampleRun({
        source_type: { raw: 'source' },
        parent_run_id: ['parent'],
        created_at: { raw: 'created' },
        updated_at: { raw: 'updated' }
      })
    )

    expect(fields.map((field) => field.label)).not.toContain('Source')
    expect(fields.map((field) => field.label)).not.toContain('Parent run')
    expect(fields.map((field) => field.label)).not.toContain('Created')
    expect(fields.map((field) => field.label)).not.toContain('Updated')
    expect(fields.some((field) => String(field.value) === '[object Object]')).toBe(false)
  })

  it('preserves Run Browser quick link labels, hrefs, and order', () => {
    expect(buildViewerRunBrowserLinks('run alpha')).toEqual([
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

  it('exposes the same optional field and safe value helpers used by the browser metadata formatter', () => {
    const run = sampleRun({ custom: 'custom-value' })

    expect(optionalRunField(run, 'custom')).toBe('custom-value')
    expect(hasSafeRunMetadataValue('custom-value')).toBe(true)
    expect(hasSafeRunMetadataValue(0)).toBe(true)
    expect(hasSafeRunMetadataValue('')).toBe(false)
    expect(hasSafeRunMetadataValue({ raw: 'unsafe' })).toBe(false)
  })
})

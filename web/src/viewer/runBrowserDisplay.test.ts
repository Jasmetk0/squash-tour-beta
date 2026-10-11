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
    display_name: 'Run Alpha',
    storage_kind: 'custom_local',
    read_only: false,
    world_id: 'official_fax_world',
    world_package_fingerprint: 'world-fp',
    config_version: 'v1',
    config_fingerprint: 'config-fp',
    global_seed: 42,
    timeline_start_season: 2000,
    timeline_end_season: 2049,
    viewer_branch_id: 'viewer',
    official_branch_id: 'main',
    status: 'ready',
    metadata_json: {},
    mapped_simulation_run_count: 1,
    ...overrides
  } as ViewerRunBrowserListItem
}

describe('Viewer Run Browser display helpers', () => {
  it('renders the Product Run metadata contract in stable order', () => {
    expect(buildRunBrowserMetadataItems(sampleRun())).toEqual([
      { label: 'Product Run ID', value: 'run alpha' },
      { label: 'Status', value: 'ready' },
      { label: 'Storage kind', value: 'custom_local' },
      { label: 'Read-only', value: 'false' },
      { label: 'World ID', value: 'official_fax_world' },
      { label: 'Timeline', value: '2000–2049' },
      { label: 'Official Branch ID', value: 'main' },
      { label: 'Mapped SimulationRuns', value: 1 }
    ])
  })

  it('keeps viewerRunMetadataFields as the metadata helper alias', () => {
    expect(viewerRunMetadataFields(sampleRun())).toEqual(buildRunBrowserMetadataItems(sampleRun()))
  })

  it('uses em dash fallbacks instead of unsafe or missing Product Run values', () => {
    const fields = buildRunBrowserMetadataItems(sampleRun({
      status: '',
      storage_kind: { bad: true },
      world_id: null,
      timeline_start_season: undefined,
      timeline_end_season: undefined,
      official_branch_id: null,
      mapped_simulation_run_count: { bad: true }
    }))
    expect(fields.filter((field) => field.value === '—').map((field) => field.label)).toEqual([
      'Status',
      'Storage kind',
      'World ID',
      'Timeline',
      'Official Branch ID',
      'Mapped SimulationRuns'
    ])
    expect(fields.some((field) => String(field.value) === '[object Object]')).toBe(false)
  })

  it('retains conservative compatibility helpers for legacy optional source fields', () => {
    expect(formatRunSourceLabel(sampleRun({ source_type: 'fresh_seed' }))).toBe('fresh_seed')
    expect(formatRunSourceLabel(sampleRun({ source_type: null }))).toBe('—')
    expect(optionalRunField(sampleRun({ custom: 'custom-value' }), 'custom')).toBe('custom-value')
    expect(hasSafeRunMetadataValue('custom-value')).toBe(true)
    expect(hasSafeRunMetadataValue(0)).toBe(true)
    expect(hasSafeRunMetadataValue(false)).toBe(true)
    expect(hasSafeRunMetadataValue('')).toBe(false)
    expect(hasSafeRunMetadataValue({ raw: 'unsafe' })).toBe(false)
  })

  it('preserves Product Run browser link labels, hrefs, and order', () => {
    expect(buildRunBrowserPrimaryLinks('run alpha/with #hash')).toEqual([
      { label: 'Season calendar', to: '/viewer/runs/run%20alpha%2Fwith%20%23hash/calendar' },
      { label: 'Tournaments', to: '/viewer/runs/run%20alpha%2Fwith%20%23hash/tournaments' },
      { label: 'Rankings', to: '/viewer/runs/run%20alpha%2Fwith%20%23hash/rankings' },
      { label: 'Race', to: '/viewer/runs/run%20alpha%2Fwith%20%23hash/race' }
    ])
    expect(buildRunBrowserContextLinks('run alpha')).toEqual([
      { label: 'Players', to: '/viewer/runs/run%20alpha/players' },
      { label: 'Countries', to: '/viewer/runs/run%20alpha/countries' },
      { label: 'History', to: '/viewer/runs/run%20alpha/history' },
      { label: 'Finals', to: '/viewer/runs/run%20alpha/finals' }
    ])
    expect(buildViewerRunBrowserLinks('run alpha')).toEqual([
      ...buildRunBrowserPrimaryLinks('run alpha'),
      ...buildRunBrowserContextLinks('run alpha')
    ])
  })
})

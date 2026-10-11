import { describe, expect, it } from 'vitest'

import {
  buildRunBrowserContextLinks,
  buildRunBrowserMetadataItems,
  buildRunBrowserPrimaryLinks,
  buildViewerRunBrowserLinks,
  hasSafeRunMetadataValue,
  optionalRunField,
  type ViewerRunBrowserListItem
} from './runBrowserDisplay'

function run(overrides: Record<string, unknown> = {}): ViewerRunBrowserListItem {
  return {
    run_id: 'read model/run #1',
    display_name: 'Read Model',
    storage_kind: 'built_in',
    read_only: true,
    world_id: 'fax-world',
    world_package_fingerprint: 'world-fp',
    config_version: null,
    config_fingerprint: null,
    global_seed: 99,
    timeline_start_season: 2000,
    timeline_end_season: 2049,
    official_branch_id: 'official',
    status: 'ready',
    metadata_json: {},
    mapped_simulation_run_count: 2,
    ...overrides
  } as ViewerRunBrowserListItem
}

describe('run browser read-model display helpers', () => {
  it('builds only safe Product Run metadata with stable fallbacks', () => {
    expect(buildRunBrowserMetadataItems(run({ world_id: null, official_branch_id: null }))).toEqual([
      { label: 'Product Run ID', value: 'read model/run #1' },
      { label: 'Status', value: 'ready' },
      { label: 'Storage kind', value: 'built_in' },
      { label: 'Read-only', value: 'true' },
      { label: 'World ID', value: '—' },
      { label: 'Timeline', value: '2000–2049' },
      { label: 'Official Branch ID', value: '—' },
      { label: 'Mapped SimulationRuns', value: 2 }
    ])
  })

  it('does not stringify object metadata or incomplete timelines', () => {
    const fields = buildRunBrowserMetadataItems(run({
      status: ['unsafe'],
      storage_kind: { unsafe: true },
      world_id: { id: 'world' },
      timeline_start_season: { value: 2000 },
      timeline_end_season: null,
      official_branch_id: ['branch'],
      mapped_simulation_run_count: { count: 2 }
    }))
    expect(fields.filter((field) => field.value === '—').map((field) => field.label)).toEqual([
      'Status',
      'Storage kind',
      'World ID',
      'Timeline',
      'Official Branch ID',
      'Mapped SimulationRuns'
    ])
    expect(fields.map((field) => String(field.value))).not.toContain('[object Object]')
  })

  it('keeps encoded Product Run route helpers stable', () => {
    const id = 'read model/run #1'
    expect([...buildRunBrowserPrimaryLinks(id), ...buildRunBrowserContextLinks(id)]).toEqual([
      { label: 'Season calendar', to: '/viewer/runs/read%20model%2Frun%20%231/calendar' },
      { label: 'Tournaments', to: '/viewer/runs/read%20model%2Frun%20%231/tournaments' },
      { label: 'Rankings', to: '/viewer/runs/read%20model%2Frun%20%231/rankings' },
      { label: 'Race', to: '/viewer/runs/read%20model%2Frun%20%231/race' },
      { label: 'Players', to: '/viewer/runs/read%20model%2Frun%20%231/players' },
      { label: 'Countries', to: '/viewer/runs/read%20model%2Frun%20%231/countries' },
      { label: 'History', to: '/viewer/runs/read%20model%2Frun%20%231/history' },
      { label: 'Finals', to: '/viewer/runs/read%20model%2Frun%20%231/finals' }
    ])
    expect(buildViewerRunBrowserLinks(id)).toEqual([
      ...buildRunBrowserPrimaryLinks(id),
      ...buildRunBrowserContextLinks(id)
    ])
  })

  it('keeps optional-field and safe-value predicates conservative', () => {
    const sample = run({ custom: 0 })
    expect(optionalRunField(sample, 'custom')).toBe(0)
    expect(hasSafeRunMetadataValue(false)).toBe(true)
    expect(hasSafeRunMetadataValue(0)).toBe(true)
    expect(hasSafeRunMetadataValue('')).toBe(false)
    expect(hasSafeRunMetadataValue(null)).toBe(false)
    expect(hasSafeRunMetadataValue(['unsafe'])).toBe(false)
    expect(hasSafeRunMetadataValue({ unsafe: true })).toBe(false)
  })
})

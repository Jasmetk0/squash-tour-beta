import { afterEach, describe, expect, it, vi } from 'vitest'
import { getGlobalFullSimulationOperations } from './client'

function example() {
  return {
    schema_version: 'global_full_simulation_operations.v1',
    visibility: 'durable_receipts_only',
    pending_count: 1,
    legacy_pending_count: 0,
    operations: [{
      run_id: 'run', run_name: 'Run', run_status: 'working', run_read_only: false,
      branch_id: 'branch', branch_name: 'Timeline 1', branch_status: 'active',
      branch_read_only: false, command_id: 'parent', control_state: 'paused',
      start_week: {season_index: 3, week: 10}, final_week: {season_index: 49, week: 61},
      completed_season_count: 4, final_completed_week_count: 0,
      review_fingerprint: 'a'.repeat(64), worker_activity: 'unknown',
      lease_state: 'matching_expired', lease_expires_at_unix: 1_800_000_000
    }]
  }
}

async function read(payload: unknown) {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(payload), {
      status: 200, headers: {'Content-Type': 'application/json'}
    })
  )
  const result = getGlobalFullSimulationOperations()
  await expect(result).resolves.toBeDefined()
  expect(fetchMock).toHaveBeenCalledTimes(1)
}

describe('global Full Simulation client boundary', () => {
  afterEach(() => vi.restoreAllMocks())

  it('allows a bounded pending parent with an expired lease without claiming worker health', async () => {
    await read(example())
  })

  it.each([
    ['season outside the Run', (value: ReturnType<typeof example>) => { value.operations[0].final_week.season_index = 99 }],
    ['week outside the Run', (value: ReturnType<typeof example>) => { value.operations[0].final_week.week = 999 }],
    ['incorrect original target', (value: ReturnType<typeof example>) => { value.operations[0].final_week.week = 60 }],
    ['invalid start', (value: ReturnType<typeof example>) => { value.operations[0].start_week.week = 0 }],
    ['impossible season progress', (value: ReturnType<typeof example>) => { value.operations[0].completed_season_count = 999 }],
    ['impossible final progress', (value: ReturnType<typeof example>) => { value.operations[0].final_completed_week_count = 999 }],
    ['bad scope', (value: ReturnType<typeof example>) => { value.operations[0].branch_id = '' }],
    ['false worker health', (value: ReturnType<typeof example>) => { value.operations[0].worker_activity = 'running' }],
    ['unrecognized lease', (value: ReturnType<typeof example>) => { value.operations[0].lease_state = 'healthy_worker' }],
    ['invalid lease expiry', (value: ReturnType<typeof example>) => { value.operations[0].lease_expires_at_unix = -1 }],
  ])('rejects %s rather than rendering corrupt evidence', async (_, mutate) => {
    const payload = example()
    mutate(payload)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(payload), {
      status: 200, headers: {'Content-Type': 'application/json'}
    }))
    await expect(getGlobalFullSimulationOperations()).rejects.toThrow(
      'Global Full Simulation parent evidence is invalid.'
    )
  })

  it('rejects duplicate parents and distinct commands in the same pending Run/Branch', async () => {
    for (const duplicateCommandId of ['parent', 'second']) {
      const payload = example()
      payload.operations.push({...payload.operations[0], command_id: duplicateCommandId})
      payload.pending_count = 2
      vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(payload), {
        status: 200, headers: {'Content-Type': 'application/json'}
      }))
      await expect(getGlobalFullSimulationOperations()).rejects.toThrow(
        'Global Full Simulation parent evidence is invalid.'
      )
      vi.restoreAllMocks()
    }
  })
})

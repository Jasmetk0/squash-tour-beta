import { afterEach, describe, expect, it, vi } from 'vitest'
import { retargetAuthoritativeFullSimulation } from './client'

const payload = {
  control_command_id: 'target-3', target_command_id: 'original-command',
  target_week: { season_index: 4, week: 20 },
  operator_label: 'Operator', audit_reason: 'Shorten to a known safe week'
}

function response() {
  return {
    schema_version: 'authoritative_full_simulation_target_result.v1',
    run_id: 'run/one', branch_id: 'branch two',
    control_command_id: 'target-3', target_command_id: 'original-command',
    requested_target_week: { season_index: 4, week: 20 },
    effective_target_week: { season_index: 4, week: 20 },
    original_final_week: { season_index: 49, week: 61 },
    applied_revision: 2, target_revision: 2, replayed: false,
    committed_child_work_persists: true
  }
}

describe('Full Simulation target command transport and validation', () => {
  afterEach(() => vi.restoreAllMocks())

  it('uses the exact Run/Branch scope and preserves the audited command identity', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(response()), {
      status: 200, headers: {'Content-Type': 'application/json'}
    }))
    await expect(retargetAuthoritativeFullSimulation('run/one', 'branch two', payload))
      .resolves.toMatchObject({target_revision: 2, replayed: false})
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/runs/run%2Fone/branches/branch%20two/authoritative-simulation/full-simulation/target',
      expect.objectContaining({method: 'POST', body: JSON.stringify(payload)})
    )
  })

  it.each([
    ['wrong Run scope', (data: ReturnType<typeof response>) => {data.run_id = 'another-run'}],
    ['wrong target parent', (data: ReturnType<typeof response>) => {data.target_command_id = 'another-command'}],
    ['wrong command ID', (data: ReturnType<typeof response>) => {data.control_command_id = 'changed'}],
    ['invalid original final', (data: ReturnType<typeof response>) => {data.original_final_week.week = 60}],
    ['wrong requested target', (data: ReturnType<typeof response>) => {data.requested_target_week.week = 19}],
    ['unbounded effective target', (data: ReturnType<typeof response>) => {data.effective_target_week.season_index = 99}],
    ['inconsistent version', (data: ReturnType<typeof response>) => {data.applied_revision = 3}],
    ['false persistence', (data: ReturnType<typeof response>) => {data.committed_child_work_persists = false}],
  ])('rejects %s', async (_why, mutate) => {
    const data = response()
    mutate(data)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(data), {
      status: 200, headers: {'Content-Type': 'application/json'}
    }))
    await expect(retargetAuthoritativeFullSimulation('run/one', 'branch two', payload))
      .rejects.toThrow()
  })
})

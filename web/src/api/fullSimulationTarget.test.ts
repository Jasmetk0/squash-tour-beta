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


describe('relative week and season target response provenance', () => {
  afterEach(() => vi.restoreAllMocks())

  it.each([
    ['weeks', 3, {season_index: 3, week: 2}],
    ['seasons', 1, {season_index: 3, week: 60}],
  ] as const)('resolves %s and preserves immutable control identity', async (unit, count, resolved) => {
    const requestPayload = {
      control_command_id: 'relative-target',
      target_command_id: 'original-command',
      relative_target: {unit, count},
      operator_label: 'Operator',
      audit_reason: 'Resolve on the server'
    }
    const output = {...response(),
      control_command_id: 'relative-target',
      requested_target_week: resolved,
      requested_relative_target: {unit, count},
      resolved_from_week: {season_index: 2, week: 60},
      effective_target_week: resolved,
    }
    const mock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(output), {
      status: 200, headers: {'Content-Type': 'application/json'}
    }))
    await expect(retargetAuthoritativeFullSimulation('run/one', 'branch two', requestPayload))
      .resolves.toMatchObject({requested_target_week: resolved, requested_relative_target: {unit, count}})
    expect(mock).toHaveBeenCalledWith(expect.stringContaining('/full-simulation/target'),
      expect.objectContaining({method: 'POST', body: JSON.stringify(requestPayload)}))
  })

  it.each([
    ['incorrect source week', (v: any) => {v.resolved_from_week.week = 59}],
    ['incorrect relative unit', (v: any) => {v.requested_relative_target.unit = 'seasons'}],
    ['incorrect relative count', (v: any) => {v.requested_relative_target.count = 2}],
    ['fabricated endpoint', (v: any) => {v.requested_target_week.week = 3}],
    ['missing anchor', (v: any) => {delete v.resolved_from_week}],
  ])('rejects %s', async (_label, corrupt) => {
    const requestPayload = {
      control_command_id: 'relative-target', target_command_id: 'original-command',
      relative_target: {unit: 'weeks' as const, count: 3},
      operator_label: 'Operator', audit_reason: 'Resolve on the server'
    }
    const output: any = {...response(),
      control_command_id: 'relative-target',
      requested_target_week: {season_index: 3, week: 2},
      requested_relative_target: {unit: 'weeks', count: 3},
      resolved_from_week: {season_index: 2, week: 60},
    }
    corrupt(output)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(output), {
      status: 200, headers: {'Content-Type': 'application/json'}
    }))
    await expect(retargetAuthoritativeFullSimulation('run/one', 'branch two', requestPayload))
      .rejects.toThrow('Full Simulation target revision response is invalid.')
  })
})

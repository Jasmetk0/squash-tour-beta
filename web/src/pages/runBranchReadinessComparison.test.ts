import { describe, expect, it, vi } from 'vitest'
import type { RunBranch } from '../api/types'
import type { RunHomeReadiness } from '../api/runHomeReadiness'
import { runHomeReadinessFixture } from '../test/runHomeReadinessFixture'
import {
  inspectBranchReadinessComparison, serializeBranchReadinessComparison
} from './runBranchReadinessComparison'

const RUN = 'same-run'
const LEFT = 'branch-A'
const RIGHT = 'branch-B'
const HEAD_A = 'head-A'
const HEAD_B = 'head-B'

function branch(id: string, head: string, run = RUN): RunBranch {
  return {
    run_id: run, branch_id: id, display_name: id, status: 'active',
    read_only: false, branch_seed: null, forked_from_branch_id: null,
    forked_from_checkpoint_id: null, saved_head_revision_id: head,
    head_checkpoint_id: null, legacy_simulation_run_id: null, metadata_json: {},
    is_official: false
  }
}
function left(overrides: Partial<RunHomeReadiness> = {}): RunHomeReadiness {
  return runHomeReadinessFixture(RUN, LEFT, {
    saved_revision_id: HEAD_A, ...overrides
  })
}
function right(overrides: Partial<RunHomeReadiness> = {}): RunHomeReadiness {
  return runHomeReadinessFixture(RUN, RIGHT, {
    saved_revision_id: HEAD_B, ...overrides
  })
}
function setup(a: unknown = left(), b: unknown = right()) {
  const rows = [branch(LEFT, HEAD_A), branch(RIGHT, HEAD_B)]
  const reader = {
    branches: vi.fn(async () => ({ run_branches: rows })),
    readiness: vi.fn(async (_run: string, id: string) => id === LEFT ? a : b)
  }
  return reader
}

describe('independent Saved Branch readiness comparison', () => {
  it('reads both HEADs, verifies the second branch list and provides a truthful scoped comparison', async () => {
    const reader = setup()
    const report = await inspectBranchReadinessComparison(reader, RUN, LEFT, RIGHT, HEAD_A)
    expect(reader.branches).toHaveBeenCalledTimes(2)
    expect(reader.readiness).toHaveBeenCalledTimes(2)
    expect(reader.readiness).toHaveBeenCalledWith(RUN, LEFT)
    expect(reader.readiness).toHaveBeenCalledWith(RUN, RIGHT)
    expect(report.left.saved_head_revision_id).toBe(HEAD_A)
    expect(report.right.saved_head_revision_id).toBe(HEAD_B)
    expect(report.comparisons.map(r => r.code)).toEqual([
      'world', 'calendar_package', 'population', 'health', 'official_ranking', 'working_draft'
    ])
    expect(report.same_calendar).toBe(true)
    expect(report.cross_branch_atomic_snapshot).toBe(false)
    expect(report.operation_preflight_required).toBe(true)
    const json = JSON.parse(serializeBranchReadinessComparison(report))
    expect(json.evidence_kind).toBe('independent_read_only_saved_inspections')
    expect(json.left.saved_content_hash).toBe('a'.repeat(64))
    expect(json.differences).toHaveLength(6)
    expect(json.left).not.toHaveProperty('player_list')
    expect(json.right).not.toHaveProperty('raw_payload')
  })

  it('computes differences without mistaking missing ranking candidates for publications', async () => {
    const b = right({
      items: [
        { code: 'world', status: 'saved', evidence_count: 240 },
        { code: 'calendar_package', status: 'saved', evidence_count: 22 },
        { code: 'population', status: 'saved', evidence_count: 700 },
        { code: 'health', status: 'optional', evidence_count: 0 },
        { code: 'official_ranking', status: 'saved', evidence_count: 2 },
        { code: 'working_draft', status: 'saved', evidence_count: 0 }
      ],
      saved_published_ranking_count: 2,
      current_calendar: {
        schema_version: 'run_calendar.v1', weeks_per_year: 61,
        season_start_year_week: 37, start_year: 2000, season_count: 50
      },
      saved_transition_count: 5,
      active_full_simulation_task_count: 1,
      historical_full_simulation_task_count: 1,
      phase: 'sporting_history'
    })
    const report = await inspectBranchReadinessComparison(setup(left(), b), RUN, LEFT, RIGHT, HEAD_A)
    expect(report.same_calendar).toBe(false)
    expect(report.same_phase).toBe(false)
    expect(report.saved_transitions_delta).toBe(5)
    expect(report.published_rankings_delta).toBe(2)
    expect(report.active_tasks_delta).toBe(1)
    expect(report.comparisons[0].count_delta).toBe(-10)
    expect(report.comparisons[1].status_changed).toBe(true)
    expect(report.comparisons[4].left.status).toBe('candidate_only')
    expect(report.comparisons[4].right.status).toBe('saved')
  })

  it('refuses a comparison with the same Branch, no Run or unpinned selected HEAD', async () => {
    const reader = setup()
    for (const args of [
      [RUN, LEFT, LEFT, HEAD_A],
      ['', LEFT, RIGHT, HEAD_A],
      [RUN, LEFT, RIGHT, '']
    ]) {
      await expect(inspectBranchReadinessComparison(reader, ...args as [string,string,string,string]))
        .rejects.toThrow('Select two different Branches')
    }
    expect(reader.branches).not.toHaveBeenCalled()
    expect(reader.readiness).not.toHaveBeenCalled()
  })

  it('rejects foreign and duplicated Branch-list entries before reading content', async () => {
    for (const rows of [
      [branch(LEFT, HEAD_A), branch(RIGHT, HEAD_B, 'foreign-run')],
      [branch(LEFT, HEAD_A), branch(RIGHT, HEAD_B), branch(LEFT, HEAD_A)],
      [branch(LEFT, HEAD_A)]
    ]) {
      const reader = setup()
      reader.branches.mockResolvedValue({ run_branches: rows })
      await expect(inspectBranchReadinessComparison(reader, RUN, LEFT, RIGHT, HEAD_A)).rejects.toThrow()
      expect(reader.readiness).not.toHaveBeenCalled()
    }
  })

  it('fails closed when either HEAD changes after first lookup', async () => {
    const reader = setup()
    reader.branches.mockResolvedValueOnce({run_branches:[branch(LEFT,HEAD_A),branch(RIGHT,HEAD_B)]})
      .mockResolvedValueOnce({run_branches:[branch(LEFT,HEAD_A),branch(RIGHT,'new-head')]})
    await expect(inspectBranchReadinessComparison(reader, RUN, LEFT, RIGHT, HEAD_A))
      .rejects.toThrow('Saved HEAD changed')
    expect(reader.readiness).toHaveBeenCalledTimes(2)
  })

  it('rejects stale selected HEAD before making the two expensive reads', async () => {
    const reader = setup()
    await expect(inspectBranchReadinessComparison(reader, RUN, LEFT, RIGHT, 'another-head'))
      .rejects.toThrow('Saved HEAD changed before')
    expect(reader.readiness).not.toHaveBeenCalled()
  })

  it('does not mix foreign, mismatched or forged Saved responses', async () => {
    for (const foreign of [
      right({ saved_revision_id: 'stale-head' }),
      right({ run_id: 'foreign-run' }),
      right({ branch_id: 'other-branch' }),
      right({ saved_revision_content_hash: 'unverified-hash' }),
      right({ items: right().items.slice(1) }),
      { ...right(), source: 'cached_unverified_draft' }
    ]) {
      const reader = setup(left(), foreign)
      await expect(inspectBranchReadinessComparison(reader, RUN, LEFT, RIGHT, HEAD_A))
        .rejects.toThrow()
    }
  })

  it('permits identical inherited HEAD identities without pretending the branches are one owner', async () => {
    const reader = setup(left(), right({ saved_revision_id: HEAD_A }))
    reader.branches.mockResolvedValue({run_branches:[branch(LEFT,HEAD_A),branch(RIGHT,HEAD_A)]})
    const report = await inspectBranchReadinessComparison(reader, RUN, LEFT, RIGHT, HEAD_A)
    expect(report.same_saved_head).toBe(true)
    expect(report.left.branch_id).not.toBe(report.right.branch_id)
    expect(report.cross_branch_atomic_snapshot).toBe(false)
  })
})

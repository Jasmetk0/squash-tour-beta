import { describe, expect, it } from 'vitest'
import { verifiedVisibleProspects } from './viewerVisibleProspects'

const runId = 'product run'
const branchId = 'viewer-branch'
const visibleWeek = { season_index: 4, week: 10 }

function good() {
  return {
    schema_version: 'visible_pre_tour_prospects.v1',
    run_id: runId, branch_id: branchId,
    week: visibleWeek, lifecycle_fingerprint: 'a'.repeat(64),
    total: 1, limit: 50, offset: 0,
    prospects: [{
      player_id: 'p1', display_name: 'Jan Novak', short_name: null,
      country_code: 'CZE', country_name: 'Czechia', age: 15,
      birth_year: 1989, birth_year_week: 46,
      lifecycle_status: 'active', tour_status: 'pre_tour',
      visible_since_week: visibleWeek,
    }],
  }
}

describe('verified public Next Gen projection', () => {
  it('accepts only exact source-bound valid public rows', () => {
    const item = good()
    expect(verifiedVisibleProspects(item, runId, branchId, 50, 0))
      .toEqual(item)
    expect(verifiedVisibleProspects(item, 'wrong-run', branchId, 50, 0)).toBeNull()
    expect(verifiedVisibleProspects(item, runId, 'other-branch', 50, 0)).toBeNull()
    expect(verifiedVisibleProspects(item, runId, branchId, 50, 50)).toBeNull()
  })

  it('rejects private fields, wrong schema and an invalid lifecycle fingerprint', () => {
    expect(verifiedVisibleProspects({ ...good(), private_seed: 'secret' }, runId, branchId, 50, 0)).toBeNull()
    expect(verifiedVisibleProspects({ ...good(), schema_version: 'unknown' }, runId, branchId, 50, 0)).toBeNull()
    expect(verifiedVisibleProspects({ ...good(), lifecycle_fingerprint: 'tampered' }, runId, branchId, 50, 0)).toBeNull()
    const item = good()
    item.prospects[0] = { ...item.prospects[0], profile_json: 'SECRET' } as typeof item.prospects[0]
    expect(verifiedVisibleProspects(item, runId, branchId, 50, 0)).toBeNull()
  })

  it('rejects future cohorts, duplicates, malformed ages and invalid week clocks', () => {
    const future = good()
    future.prospects[0].visible_since_week = { season_index: 4, week: 11 }
    expect(verifiedVisibleProspects(future, runId, branchId, 50, 0)).toBeNull()
    const duplicate = good()
    duplicate.total = 2
    duplicate.prospects.push({ ...duplicate.prospects[0] })
    expect(verifiedVisibleProspects(duplicate, runId, branchId, 50, 0)).toBeNull()
    const age = good()
    age.prospects[0].age = -1
    expect(verifiedVisibleProspects(age, runId, branchId, 50, 0)).toBeNull()
    expect(verifiedVisibleProspects({ ...good(), week: { season_index: 4, week: 62 } }, runId, branchId, 50, 0)).toBeNull()
  })

  it('bounds both current and visibility clocks to the canonical legacy 50-season model', () => {
    const valid = good()
    valid.week = { season_index: 49, week: 61 }
    valid.prospects[0].visible_since_week = { season_index: 49, week: 61 }
    expect(verifiedVisibleProspects(valid, runId, branchId, 50, 0)).toEqual(valid)
    const invalidClock = { ...valid, week: { season_index: 50, week: 1 } }
    expect(verifiedVisibleProspects(invalidClock, runId, branchId, 50, 0)).toBeNull()
    const invalidVisibility = { ...invalidClock, prospects: [{
      ...valid.prospects[0], visible_since_week: { season_index: 50, week: 1 },
    }] }
    expect(verifiedVisibleProspects(invalidVisibility, runId, branchId, 50, 0)).toBeNull()
    expect(verifiedVisibleProspects({ ...valid, week: { season_index: 49, week: 62 } }, runId, branchId, 50, 0)).toBeNull()
  })

  it('rejects incorrect counts and truncated pages while accepting exact empty last page', () => {
    expect(verifiedVisibleProspects({ ...good(), total: 2 }, runId, branchId, 50, 0)).toBeNull()
    expect(verifiedVisibleProspects({ ...good(), limit: 100 }, runId, branchId, 50, 0)).toBeNull()
    const empty = { ...good(), prospects: [], total: 0 }
    expect(verifiedVisibleProspects(empty, runId, branchId, 50, 0)).toEqual(empty)
    const beyond = { ...good(), prospects: [], total: 1, offset: 50 }
    expect(verifiedVisibleProspects(beyond, runId, branchId, 50, 50)).toEqual(beyond)
  })
})

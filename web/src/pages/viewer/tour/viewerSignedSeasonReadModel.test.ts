import { describe, expect, it } from 'vitest'

import { verifiedSignedSeasonBranch, verifiedSignedSeasonComparison, verifiedSignedSeasonList } from './viewerSignedSeasonReadModel'
import { signedSeasonListFixture, signedSeasonComparisonFixture } from './viewerSignedSeasonFixture'

const list = (data: unknown) => verifiedSignedSeasonList(data, 'run alpha', 'branch-tour')
const compare = (data: unknown, against: number | null = null) =>
  verifiedSignedSeasonComparison(data, 'run alpha', 'branch-tour', 'rev-20', 1, against, [0, 1])

describe('public Viewer signed season source guards', () => {
  it('requires current Product Run and its actual Viewer Branch', () => {
    expect(verifiedSignedSeasonBranch({
      product_run_id: 'run alpha', official_branch_id: 'branch-tour'
    }, 'run alpha')).toBe('branch-tour')
    expect(verifiedSignedSeasonBranch({
      product_run_id: 'other', official_branch_id: 'branch-tour'
    }, 'run alpha')).toBeNull()
    expect(verifiedSignedSeasonBranch({
      product_run_id: 'run alpha', official_branch_id: ' '
    }, 'run alpha')).toBeNull()
  })

  it('accepts only sorted signed completed seasons from the exact Saved source', () => {
    expect(list(signedSeasonListFixture())).toEqual({
      savedHead: 'rev-20',
      seasons: [{ index: 0, label: '2000/01' }, { index: 1, label: '2001/02' }]
    })
    const fixture = signedSeasonListFixture()
    for (const patch of [
      { run_id: 'other' }, { branch_id: 'wrong' }, { saved_head_revision_id: '' },
      { from_season_index: 1 }, { country_code: 'CZE' }, { leaderboard_limit: 100 },
      { completed_seasons: [1, 0] }, { completed_seasons: [0, 2] },
      { as_of_season_index: 0 }, { source_seasons: fixture.source_seasons.slice(1) }
    ]) expect(list({ ...fixture, ...patch })).toBeNull()
  })

  it('checks exact selected and compared seasons and unchanged Saved HEAD', () => {
    expect(compare(signedSeasonComparisonFixture())).not.toBeNull()
    expect(compare(signedSeasonComparisonFixture(true), 0)).not.toBeNull()
    expect(compare(signedSeasonComparisonFixture(true))).toBeNull()
    expect(compare(signedSeasonComparisonFixture(), 0)).toBeNull()
    expect(verifiedSignedSeasonComparison(signedSeasonComparisonFixture(), 'run alpha',
      'branch-tour', 'another-revision', 1, null, [0, 1])).toBeNull()
    expect(compare(signedSeasonComparisonFixture(), 9)).toBeNull()
  })

  it('blocks forged national comparison arithmetic, duplicate countries and fake editions', () => {
    const base = signedSeasonComparisonFixture(true)
    const wrongDelta = structuredClone(base)
    wrongDelta.country_deltas[0].awarded_points_delta = 10
    expect(compare(wrongDelta, 0)).toBeNull()

    const wrongCountry = structuredClone(base)
    wrongCountry.country_deltas[0].country_code = 'USA'
    expect(compare(wrongCountry, 0)).toBeNull()

    const duplicates = structuredClone(base)
    duplicates.selected.countries.push(duplicates.selected.countries[0])
    expect(compare(duplicates, 0)).toBeNull()

    const fakeEdition = structuredClone(base)
    fakeEdition.selected.completed_edition_count = 40
    expect(compare(fakeEdition, 0)).toBeNull()

    const futureWeek = structuredClone(base)
    futureWeek.selected.editions[0].week = 70
    expect(compare(futureWeek, 0)).toBeNull()
  })

  it('rejects invalid final-week ranking and cross-Run source drift', () => {
    const fake = structuredClone(signedSeasonComparisonFixture(true))
    fake.selected.last_week_published_ranking.week = 51
    expect(compare(fake, 0)).toBeNull()
    fake.selected.last_week_published_ranking.week = 52
    fake.comparison!.source_tour_fingerprint = 'b'.repeat(64)
    expect(compare(fake, 0)).toBeNull()
    fake.comparison!.source_tour_fingerprint = 'a'.repeat(64)
    fake.selected.run_id = 'foreign'
    expect(compare(fake, 0)).toBeNull()
  })
})

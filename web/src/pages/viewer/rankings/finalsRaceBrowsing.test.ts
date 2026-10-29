import { describe, expect, it } from 'vitest'
import {
  filterRacePlayerRows, parseRacePage, raceSeasonLabel, raceSeasonsNewestFirst,
  validViewerRaceHistory, viewerRaceBranch
} from './finalsRaceBrowsing'

function row(rank = 1, id = 'player-a', points = 20) {
  return {
    rank, player_id: id, race_points: points,
    tournaments_counted: 1, finals_selected: null, finals_seed: null, qualification_source: null,
    counted_results: [{ event_id: 'event-' + id, completed_season_index: 4, completed_week: 10, race_points: points }]
  }
}
function publication(season = 4, rows = [row()]) {
  return {
    schema_version: 'viewer_finals_race_publication.v1',
    product_run_id: 'run-a', viewer_branch_id: 'branch-a',
    target_season_index: season, cutoff_season_index: season, cutoff_week: 55,
    best_n: 2, selection_published: false, finals_event_id: null,
    rows: rows.map(x => ({
      ...x, counted_results: x.counted_results.map(r => ({ ...r, completed_season_index: season }))
    }))
  }
}
function history(publications = [publication()]) {
  return {
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'run-a', viewer_branch_id: 'branch-a',
    latest_target_season_index: publications.length ? Math.max(...publications.map(x => x.target_season_index)) : null,
    publications
  }
}
describe('saved Finals Race history source/legacy V1 guards', () => {
  it('checks the exact current Viewer Branch and legitimate empty history/rows', () => {
    expect(viewerRaceBranch({ product_run_id: 'run-a', official_branch_id: 'branch-a' }, 'run-a')).toBe('branch-a')
    expect(viewerRaceBranch({ product_run_id: 'wrong', official_branch_id: 'branch-a' }, 'run-a')).toBeNull()
    expect(viewerRaceBranch({ product_run_id: 'run-a', official_branch_id: '  ' }, 'run-a')).toBeNull()
    expect(validViewerRaceHistory(history([]), 'run-a', 'branch-a')).toBe(true)
    expect(validViewerRaceHistory(history([publication(4, [])]), 'run-a', 'branch-a')).toBe(true)
    expect(raceSeasonLabel(4)).toBe('2004/05')
  })
  it('selects latest by saved target season, not server array order', () => {
    const value = history([publication(9), publication(3), publication(5)])
    expect(validViewerRaceHistory(value, 'run-a', 'branch-a')).toBe(true)
    expect(raceSeasonsNewestFirst(value).map(x => x.target_season_index)).toEqual([9, 5, 3])
    expect(value.publications.map(x => x.target_season_index)).toEqual([9, 3, 5])
  })
  it('fails closed on foreign, duplicate and incoherent publications and counted results', () => {
    const good = history([publication(4)])
    const one = good.publications[0]
    expect(validViewerRaceHistory(good, 'run-a', 'branch-a')).toBe(true)
    const invalid: unknown[] = [
      { ...good, schema_version: 'other' },
      { ...good, product_run_id: 'foreign' },
      { ...good, viewer_branch_id: 'foreign' },
      { ...good, latest_target_season_index: 3 },
      { ...good, publications: [one, one] },
      { ...good, publications: [{ ...one, viewer_branch_id: 'foreign' }] },
      { ...good, publications: [{ ...one, cutoff_season_index: 3 }] },
      { ...good, publications: [{ ...one, cutoff_week: 62 }] },
      { ...good, publications: [{ ...one, best_n: 0 }] },
      { ...good, publications: [{ ...one, rows: [row(1, 'a', 20), row(1, 'b', 10)] }] },
      { ...good, publications: [{ ...one, rows: [row(1, 'a', 20), row(2, 'a', 10)] }] },
      { ...good, publications: [{ ...one, rows: [row(1, 'a', 10), row(2, 'b', 20)] }] },
      { ...good, publications: [{ ...one, rows: [{ ...row(), tournaments_counted: 2 }] }] },
      { ...good, publications: [{ ...one, rows: [{ ...row(), race_points: 2 }] }] },
      { ...good, publications: [{ ...one, rows: [{ ...row(), counted_results: [{ ...row().counted_results[0], completed_week: 56 }] }] }] },
      { ...good, publications: [{ ...one, rows: [{ ...row(), finals_selected: true, finals_seed: 1, qualification_source: 'race' }] }] },
      { ...good, publications: [{ ...one, selection_published: true, finals_event_id: null }] }
    ]
    for (const bad of invalid) expect(validViewerRaceHistory(bad, 'run-a', 'branch-a')).toBe(false)
    expect(validViewerRaceHistory(good, 'wrong-run', 'branch-a')).toBe(false)
    expect(validViewerRaceHistory(good, 'run-a', 'other-branch')).toBe(false)
  })
  it('preserves selection pending vs excluded and validates distinct selected seeds', () => {
    const p = publication(4, [row(1, 'p1', 30), row(2, 'p2', 20)])
    p.selection_published = true
    p.finals_event_id = 'FINALS'
    p.rows[0].finals_selected = true
    p.rows[0].finals_seed = 1
    p.rows[0].qualification_source = 'race'
    p.rows[1].finals_selected = true
    p.rows[1].finals_seed = 2
    p.rows[1].qualification_source = 'direct_entry'
    expect(validViewerRaceHistory(history([p]), 'run-a', 'branch-a')).toBe(true)
    p.rows[1].finals_seed = 1
    expect(validViewerRaceHistory(history([p]), 'run-a', 'branch-a')).toBe(false)
  })
  it('searches across full saved standings and accepts only bounded page jumps', () => {
    const rows = [row(1, 'Alice', 40), row(2, 'bob', 25), row(3, 'ALICE-2', 10)]
    expect(filterRacePlayerRows(rows, ' alice ')).toEqual([rows[0], rows[2]])
    expect(filterRacePlayerRows(rows, '')).toEqual(rows)
    expect(filterRacePlayerRows(rows, 'none')).toEqual([])
    expect(parseRacePage(' 2 ', 3)).toBe(2)
    for (const bad of ['', '0', '-1', '03', '3e1', '4', '2.0', '999999999999999999999']) {
      expect(parseRacePage(bad, 3)).toBeNull()
    }
  })
})

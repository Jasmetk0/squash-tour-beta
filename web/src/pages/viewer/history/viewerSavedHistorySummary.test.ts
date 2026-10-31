import { describe, expect, it } from 'vitest'
import type {
  ViewerTournamentHistory, ViewerOfficialRankingHistory, ViewerFinalsRaceHistory
} from '../../../api/types'
import { rankingSeasonLabel, verifiedSavedHistory } from './viewerSavedHistorySummary'

function tournaments(): ViewerTournamentHistory {
  return {
    schema_version: 'viewer_tournament_history.v1', product_run_id: 'run a', viewer_branch_id: 'branch a',
    tournament_count: 2, published_result_count: 1,
    tournaments: [
      {
        event_id: 'later', season: '2003/04', season_week: 20, event_name: 'Later',
        template_id: 'template', category: 'GOLD', tour_level: 'WORLD_TOUR',
        host_country: 'CZE', host_city: 'Brno', region: 'Europe', main_draw_size: 32,
        qualification_draw_size: 16, seeds_count: 8, qualifier_spots: 4, wild_cards: 2,
        byes: 0, ranking_status: 'planned', result_published: false,
        champion_player_id: null, finalist_player_id: null
      },
      {
        event_id: 'winner', season: '2002/03', season_week: 10, event_name: 'Winner',
        template_id: 'template', category: 'GOLD', tour_level: 'WORLD_TOUR',
        host_country: 'CZE', host_city: 'Brno', region: 'Europe', main_draw_size: 32,
        qualification_draw_size: 16, seeds_count: 8, qualifier_spots: 4, wild_cards: 2,
        byes: 0, ranking_status: 'completed', result_published: true,
        champion_player_id: 'player-1', finalist_player_id: 'player-2'
      }
    ]
  }
}
function rankings(): ViewerOfficialRankingHistory {
  return {
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'run a', viewer_branch_id: 'branch a',
    public_head_ordinal: 123, publication_count: 2,
    publications: [
      { season_index: 2, week: 2, week_ordinal: 123, snapshot_fingerprint: 'a'.repeat(64), policy_id: 'policy2', best_n: 15, row_count: 0 },
      { season_index: 2, week: 1, week_ordinal: 122, snapshot_fingerprint: 'b'.repeat(64), policy_id: 'policy1', best_n: 15, row_count: 10 }
    ]
  }
}
function race(): ViewerFinalsRaceHistory {
  return {
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: 'run a', viewer_branch_id: 'branch a',
    latest_target_season_index: 3,
    publications: [
      { schema_version: 'viewer_finals_race_publication.v1', product_run_id: 'run a',
        viewer_branch_id: 'branch a', target_season_index: 3, cutoff_season_index: 3,
        cutoff_week: 56, best_n: 15, selection_published: false,
        finals_event_id: null, rows: [] }
    ]
  }
}
const check = (t: unknown, r: unknown, f: unknown) => verifiedSavedHistory(t, r, f, 'run a', 'branch a')

describe('canonical saved Viewer history hub validation', () => {
  it('accepts complete same-Branch publications and finds latest actual events', () => {
    expect(check(tournaments(), rankings(), race())).toMatchObject({
      tournamentCount: 2, publishedTournamentCount: 1, rankingCount: 2, raceCount: 1,
      lastTournament: { event_id: 'winner' }, lastRanking: { week_ordinal: 123 }, latestRaceSeason: 3
    })
    expect(rankingSeasonLabel(2)).toBe('2002/03')
  })

  it('accepts genuine empty histories but not missing or inconsistent evidence', () => {
    const t = { ...tournaments(), tournament_count: 0, published_result_count: 0, tournaments: [] }
    const r = { ...rankings(), public_head_ordinal: 0, publication_count: 0, publications: [] }
    const f = { ...race(), latest_target_season_index: null, publications: [] }
    expect(check(t, r, f)).toEqual({
      tournamentCount: 0, publishedTournamentCount: 0, rankingCount: 0, raceCount: 0,
      lastTournament: null, lastRanking: null, latestRaceSeason: null
    })
    expect(check(t, null, f)).toBeNull()
    expect(check(t, { ...r, publication_count: 2 }, f)).toBeNull()
  })

  it('rejects foreign Run/Viewer Branch independently in each authority', () => {
    const t = tournaments(), r = rankings(), f = race()
    expect(check({ ...t, viewer_branch_id: 'branch b' }, r, f)).toBeNull()
    expect(check(t, { ...r, viewer_branch_id: 'branch b' }, f)).toBeNull()
    expect(check(t, r, { ...f, viewer_branch_id: 'branch b' })).toBeNull()
    expect(check(t, r, { ...f, publications: [{ ...f.publications[0], viewer_branch_id: 'branch b' }] })).toBeNull()
    expect(verifiedSavedHistory(t, r, f, 'other run', 'branch a')).toBeNull()
  })

  it('rejects invalid or duplicated tournament and ranking publication evidence', () => {
    const t = tournaments(), r = rankings(), f = race()
    expect(check({ ...t, tournament_count: 3 }, r, f)).toBeNull()
    expect(check({ ...t, published_result_count: 2 }, r, f)).toBeNull()
    expect(check({ ...t, tournaments: [t.tournaments[0], { ...t.tournaments[1], event_id: 'later' }] }, r, f)).toBeNull()
    expect(check({ ...t, tournaments: [{ ...t.tournaments[0], result_published: false, champion_player_id: 'future' }, t.tournaments[1]] }, r, f)).toBeNull()
    expect(check(t, { ...r, public_head_ordinal: 124 }, f)).toBeNull()
    expect(check(t, { ...r, publications: [r.publications[0], r.publications[0]] }, f)).toBeNull()
    expect(check(t, { ...r, publications: [{ ...r.publications[0], week_ordinal: 122 }, r.publications[1]] }, f)).toBeNull()
    expect(check(t, { ...r, publications: [{ ...r.publications[0], snapshot_fingerprint: 'corrupt' }, r.publications[1]] }, f)).toBeNull()
  })

  it('requires distinct actual published finalists before selecting latest Tournament history', () => {
    const t = tournaments(), r = rankings(), f = race()
    const valid = (fields: Partial<ViewerTournamentHistory['tournaments'][number]>) =>
      check({...t, tournaments:[
        t.tournaments[0], {...t.tournaments[1], ...fields}
      ]}, r, f)
    expect(check(t, r, f)?.lastTournament?.event_id).toBe('winner')
    expect(valid({champion_player_id:null})).toBeNull()
    expect(valid({finalist_player_id:null})).toBeNull()
    expect(valid({champion_player_id:null,finalist_player_id:null})).toBeNull()
    expect(valid({champion_player_id:' '})).toBeNull()
    expect(valid({finalist_player_id:' '})).toBeNull()
    expect(valid({champion_player_id:'same',finalist_player_id:'same'})).toBeNull()
    expect(valid({result_published:false,champion_player_id:null,
      finalist_player_id:null})).toBeNull() // Published count must still reconcile.
  })

  it('rejects duplicate Finals Race seasons and stale latest publication', () => {
    const t = tournaments(), r = rankings(), f = race()
    expect(check(t, r, { ...f, latest_target_season_index: 2 })).toBeNull()
    expect(check(t, r, { ...f, publications: [f.publications[0], f.publications[0]] })).toBeNull()
    expect(check(t, r, { ...f, publications: [{ ...f.publications[0], cutoff_season_index: 2 }] })).toBeNull()
    expect(check(t, r, { ...f, publications: [{ ...f.publications[0], schema_version: 'broken' }] })).toBeNull()
  })
})

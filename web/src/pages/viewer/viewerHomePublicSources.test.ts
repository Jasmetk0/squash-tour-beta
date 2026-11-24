import { describe, expect, it } from 'vitest'
import { verifiedHomeSources, verifiedHomeTournamentHistory } from './viewerHomePublicSources'

const run = 'run alpha'
const branch = 'viewer-a'
function tournament(eventId: string, week: number, published = true) {
  return {
    event_id: eventId, season: '2031/32', season_week: week,
    event_name: eventId, template_id: 'gold', category: 'GOLD',
    tour_level: 'WORLD_TOUR', host_country: 'CZE',
    host_city: 'Brno', region: 'Europe',
    main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8,
    qualifier_spots: 4, wild_cards: 2, byes: 0,
    ranking_status: published ? 'ranked' : 'planned',
    result_published: published,
    champion_player_id: published ? 'winner-' + eventId : null,
    finalist_player_id: published ? 'finalist-' + eventId : null,
  }
}
function sources() {
  return {
    tournaments: {
      schema_version: 'viewer_tournament_history.v1', product_run_id: run,
      viewer_branch_id: branch, tournament_count: 3, published_result_count: 2,
      tournaments: [tournament('newer', 10), tournament('unpublished', 20, false), tournament('older', 2)],
    },
    ranking: {
      schema_version: 'viewer_official_ranking_history.v1', product_run_id: run,
      viewer_branch_id: branch, public_head_ordinal: 1930, publication_count: 2,
      publications: [
        { season_index: 30, week: 1, week_ordinal: 1830, snapshot_fingerprint: 'a'.repeat(64), policy_id: 'A', best_n: 12, row_count: 1 },
        { season_index: 31, week: 40, week_ordinal: 1930, snapshot_fingerprint: 'b'.repeat(64), policy_id: 'B', best_n: 12, row_count: 1 },
      ],
    },
    race: {
      schema_version: 'viewer_finals_race_history.v1', product_run_id: run,
      viewer_branch_id: branch, latest_target_season_index: null,
      publications: [],
    },
  }
}
describe('Viewer Home exact public Run/Branch sources', () => {
  it('selects the true latest published result and ranking by historical time, not array order', () => {
    const s = sources()
    const v = verifiedHomeSources(s.tournaments, s.ranking, s.race, run, branch)
    expect(v?.latestPublishedTournament?.event_id).toBe('newer')
    expect(v?.latestRankingPublication?.week_ordinal).toBe(1930)
    expect(v?.publishedTournaments).toHaveLength(2)
    expect(v?.racePublicationCount).toBe(0)
  })

  it('rejects foreign Run/Branch in each independent reader', () => {
    const s = sources()
    expect(verifiedHomeSources(s.tournaments, s.ranking, s.race, 'another', branch)).toBeNull()
    expect(verifiedHomeSources({ ...s.tournaments, viewer_branch_id: 'foreign' }, s.ranking, s.race, run, branch)).toBeNull()
    expect(verifiedHomeSources(s.tournaments, { ...s.ranking, viewer_branch_id: 'foreign' }, s.race, run, branch)).toBeNull()
    expect(verifiedHomeSources(s.tournaments, s.ranking, { ...s.race, viewer_branch_id: 'foreign' }, run, branch)).toBeNull()
  })

  it('rejects false result totals, duplicates and incomplete winners', () => {
    const s = sources()
    expect(verifiedHomeTournamentHistory({ ...s.tournaments, published_result_count: 3 }, run, branch)).toBeNull()
    expect(verifiedHomeTournamentHistory({ ...s.tournaments, tournaments: [
      tournament('same', 2), tournament('same', 4), tournament('third', 8, false),
    ] }, run, branch)).toBeNull()
    expect(verifiedHomeTournamentHistory({ ...s.tournaments, tournaments: [
      tournament('a', 2), { ...tournament('b', 5), champion_player_id: null }, tournament('c', 8, false),
    ] }, run, branch)).toBeNull()
  })

  it('rejects invalid country codes and blank regions in public tournament rows', () => {
    const s = sources()
    for (const patch of [{ host_country: 'CZ' }, { host_country: 'CZECH' },
      { host_country: '   ' }, { region: '' }, { region: '  ' }]) {
      expect(verifiedHomeTournamentHistory({
        ...s.tournaments,
        tournaments: [{ ...s.tournaments.tournaments[0], ...patch }, ...s.tournaments.tournaments.slice(1)],
      }, run, branch)).toBeNull()
    }
    expect(verifiedHomeTournamentHistory(s.tournaments, run, branch)).not.toBeNull()
  })

  it('rejects inconsistent ranking head and malformed Finals evidence', () => {
    const s = sources()
    expect(verifiedHomeSources(s.tournaments, { ...s.ranking, public_head_ordinal: 1931 }, s.race, run, branch)).toBeNull()
    expect(verifiedHomeSources(s.tournaments, { ...s.ranking, publications: [
      { ...s.ranking.publications[0], week_ordinal: 4000 }, s.ranking.publications[1],
    ] }, s.race, run, branch)).toBeNull()
    expect(verifiedHomeSources(s.tournaments, s.ranking, { ...s.race, latest_target_season_index: 31 }, run, branch)).toBeNull()
  })

  it('accepts real zero publications but never treats absent sources as an empty history', () => {
    const s = sources()
    const zero = { ...s.tournaments, tournament_count: 0, published_result_count: 0, tournaments: [] }
    expect(verifiedHomeSources(zero, s.ranking, s.race, run, branch)?.publishedTournaments).toHaveLength(0)
    expect(verifiedHomeSources(undefined, s.ranking, s.race, run, branch)).toBeNull()
    expect(verifiedHomeSources(s.tournaments, null, s.race, run, branch)).toBeNull()
  })
})

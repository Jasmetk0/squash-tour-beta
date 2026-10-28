import { describe, expect, it } from 'vitest'
import {
  matchLoadedCareer, parseCareerCompletion, parseCareerOutcome, parseCareerPage,
  parseCareerSeason, parsePageInput, parsePlayerRally, totalCareerPages,
  validPlayerReplayPagePair,
} from './savedPlayerCareerNavigation'
import type { SavedPlayerMatch, SavedPlayerMatchDetail } from '../api/types'

const match: SavedPlayerMatch = {
  event_id: 'EV1', event_name: 'Brno Cup', match_id: 'M12', season_index: 2,
  season: '2002/03', week: 17, draw_type: 'main', round_number: 2,
  opponent_player_id: 'B', outcome: 'win', completion: 'played', scoreline: '3-2',
}
const detail = (offset: number, total = 30): SavedPlayerMatchDetail => ({
  schema_version: 'saved_player_match_detail.v1', source: 'selected_branch_saved_revision',
  run_id: 'R', branch_id: 'B', saved_revision_id: 'HEAD', player_id: 'A',
  match, winner_player_id: 'A', loser_player_id: 'B',
  player_a_id: 'A', player_b_id: 'B', replay_status: 'available',
  offset, limit: 25, total_rallies: total, has_more: offset + 25 < total,
  rallies: Array.from({ length: Math.max(0, Math.min(25, total - offset)) }, (_, i) => ({
    rally_index: offset + i + 1, set_number: 1, server_player_id: 'A',
    winner_player_id: 'A', score_a_before: offset + i, score_b_before: 0,
    score_a_after: offset + i + 1, score_b_after: 0, sets_a_after: 0,
    sets_b_after: 0, set_complete: false, match_complete: false,
  })),
})

describe('current-HEAD player career URL contracts', () => {
  it('accepts only supported zero-based season and page links', () => {
    expect(parseCareerSeason(null)).toBe('all')
    expect(parseCareerSeason('49')).toBe('49')
    for (const raw of ['-1', '50', '01', '1.5', 'Infinity', '']) expect(parseCareerSeason(raw)).toBeNull()
    expect(parseCareerPage('0')).toBe(0)
    expect(parseCareerPage('10000')).toBe(10000)
    for (const raw of ['-1','10001','NaN','01','2.2','']) expect(parseCareerPage(raw)).toBeNull()
    expect(totalCareerPages(0)).toBe(0)
    expect(totalCareerPages(21)).toBe(2)
    expect(parsePageInput('2', 2)).toBe(1)
    for (const raw of ['0','3','-1','01','1.1','']) expect(parsePageInput(raw, 2)).toBeNull()
  })
  it('validates local filter URLs and matches only verified loaded fields', () => {
    expect(parseCareerOutcome('win')).toBe('win')
    expect(parseCareerOutcome('WIN')).toBeNull()
    expect(parseCareerCompletion('walkover')).toBe('walkover')
    expect(parseCareerCompletion('forfeit')).toBeNull()
    for (const q of ['brno','ev1','m12','b','Bravo','3-2'])
      expect(matchLoadedCareer(match, { B:'Bravo' }, q, 'win', 'played')).toBe(true)
    expect(matchLoadedCareer(match, { B:'Bravo' }, 'Wrong name', 'all', 'all')).toBe(false)
    expect(matchLoadedCareer(match, {}, 'Bravo', 'all', 'all')).toBe(false)
    expect(matchLoadedCareer(match, {}, '', 'loss', 'all')).toBe(false)
    expect(matchLoadedCareer(match, {}, '', 'all', 'walkover')).toBe(false)
  })
  it('rejects invalid rally positions and mixed archive boundaries', () => {
    expect(parsePlayerRally(null)).toBe(1)
    expect(parsePlayerRally('100000')).toBe(100000)
    for (const raw of ['0', '01', '100001', '-1', '2.5', '1e3', '']) expect(parsePlayerRally(raw)).toBeNull()
    const first = detail(0), second = detail(25)
    expect(validPlayerReplayPagePair(first, second)).toBe(true)
    expect(validPlayerReplayPagePair(first, {...second, saved_revision_id:'NEW'})).toBe(false)
    expect(validPlayerReplayPagePair(first, {...second, player_id:'C'})).toBe(false)
    expect(validPlayerReplayPagePair(first, {...second, total_rallies:31})).toBe(false)
    expect(validPlayerReplayPagePair(first, {...second, rallies:second.rallies.map((x,i)=>
      i===0 ? {...x,score_a_before:99}:x)})).toBe(false)
    // An empty out-of-range page is not a neighbor and cannot poison the last page.
    expect(validPlayerReplayPagePair(first, detail(50))).toBe(false)
    const boundary = detail(0)
    boundary.rallies[24] = {...boundary.rallies[24], set_complete:true}
    const next = detail(25)
    next.rallies[0] = {...next.rallies[0], set_number:2, score_a_before:0, score_b_before:0}
    expect(validPlayerReplayPagePair(boundary,next)).toBe(true)
  })
})

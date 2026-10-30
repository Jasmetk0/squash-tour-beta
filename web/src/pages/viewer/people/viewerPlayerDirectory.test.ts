import { describe, expect, it } from 'vitest'
import type { ViewerPlayer, ViewerPlayers } from '../../../api/types'
import {
  filteredPlayerDirectory, parsePlayerDirectoryPage, playerDirectoryCountries,
  playerViewerBranch, verifiedViewerPlayers
} from './viewerPlayerDirectory'

function player(id: string, status: 'active' | 'retired' = 'active',
  ovr: number | null = 120, country = 'CZE'): ViewerPlayer {
  return {
    player_id: id, name: id, country_code: country, age: 22,
    status, identity_source: 'initial_world', tour_entry_season_index: null,
    tour_entry_week: null, current_ovr: ovr, potential_ovr: null,
    current_form: null, match_sharpness: null, long_term_fatigue: null
  }
}
function players(items: ViewerPlayer[] = [player('p1')], run = 'run-1', branch = 'branch-1'): ViewerPlayers {
  return {
    schema_version: 'viewer_players.v1', product_run_id: run, viewer_branch_id: branch,
    season_index: 5, week: 12, player_count: items.length,
    active_player_count: items.filter(x => x.status === 'active').length,
    retired_player_count: items.filter(x => x.status === 'retired').length,
    players: items
  }
}
const check = (value: unknown) => verifiedViewerPlayers(value, 'run-1', 'branch-1')
const filters = { search: '', status: 'all' as const, origin: 'all' as const,
  country: 'all', sort: 'name' as const }

describe('verified Viewer saved player population', () => {
  it('rejects context from another Product Run and preserves legitimate empty population', () => {
    expect(playerViewerBranch({ product_run_id: 'run-1', official_branch_id: 'branch-1' }, 'run-1')).toBe('branch-1')
    expect(playerViewerBranch({ product_run_id: 'other', official_branch_id: 'branch-1' }, 'run-1')).toBeNull()
    expect(playerViewerBranch({ product_run_id: 'run-1', official_branch_id: ' ' }, 'run-1')).toBeNull()
    expect(check(players([]))).toMatchObject({ player_count: 0, players: [] })
  })

  it('validates both source identities, exact totals and unique player IDs', () => {
    const good = players([player('A'), player('B', 'retired')])
    expect(check(good)).toBe(good)
    for (const invalid of [
      { ...good, schema_version: 'viewer_players.v2' },
      { ...good, product_run_id: 'other' },
      { ...good, viewer_branch_id: 'other' },
      { ...good, player_count: 3 },
      { ...good, active_player_count: 2 },
      { ...good, retired_player_count: 2 },
      { ...good, week: 62 },
      { ...good, season_index: -1 },
      { ...good, players: [good.players[0], good.players[0]] },
      { ...good, players: [good.players[0]] },
      null
    ]) expect(check(invalid)).toBeNull()
  })

  it('rejects malformed public fields and unsupported statuses without guessing defaults', () => {
    const base = players()
    const one = base.players[0]
    for (const modified of [
      { ...one, player_id: '' },
      { ...one, name: '  ' },
      { ...one, country_code: 'CZ' },
      { ...one, country_code: 'czE' },
      { ...one, age: 121 },
      { ...one, current_ovr: 201 },
      { ...one, identity_source: 'private' },
      { ...one, status: 'unknown' },
      { ...one, match_sharpness: 101 },
      { ...one, tour_entry_week: 62 },
      { ...one, current_form: 'hidden' }
    ]) expect(check({ ...base, players: [modified] })).toBeNull()
  })

  it('supports null public power without showing hidden future attributes', () => {
    const data = players([player('A', 'retired', null)])
    expect(check(data)).toBe(data)
    expect(data.players[0].current_ovr).toBeNull()
  })

  it('filters entire saved roster by player ID/name, status, country, origin and public power', () => {
    const a = { ...player('p-3', 'active', 100, 'CZE'), name: 'Adam' }
    const b = { ...player('p-2', 'retired', null, 'NZL'), name: 'Zdenek' }
    const c = { ...player('p-1', 'active', 190, 'NZL'), name: 'Bob', identity_source: 'run_prospect' as const }
    const d = { ...player('p-4', 'active', 190, 'NZL'), name: 'Alena' }
    const source = players([b, a, c, d])
    expect(playerDirectoryCountries(source)).toEqual(['CZE', 'NZL'])
    expect(filteredPlayerDirectory(source, filters).map(x => x.player_id)).toEqual(['p-3', 'p-4', 'p-1', 'p-2'])
    expect(filteredPlayerDirectory(source, { ...filters, sort: 'public_ovr' }).map(x => x.player_id))
      .toEqual(['p-1', 'p-4', 'p-3', 'p-2'])
    expect(filteredPlayerDirectory(source, { ...filters, status: 'retired' }).map(x => x.player_id)).toEqual(['p-2'])
    expect(filteredPlayerDirectory(source, { ...filters, origin: 'run_prospect' }).map(x => x.player_id)).toEqual(['p-1'])
    expect(filteredPlayerDirectory(source, { ...filters, country: 'CZE' }).map(x => x.player_id)).toEqual(['p-3'])
    expect(filteredPlayerDirectory(source, { ...filters, search: ' BOB ' }).map(x => x.player_id)).toEqual(['p-1'])
    expect(filteredPlayerDirectory(source, { ...filters, search: 'p-4' }).map(x => x.player_id)).toEqual(['p-4'])
    expect(source.players[0].player_id).toBe('p-2')
  })

  it('never accepts out-of-range, fractional or exponential pagination', () => {
    expect(parsePlayerDirectoryPage(' 2 ', 3)).toBe(2)
    for (const bad of ['', '0', '-1', '02', '4', '1.1', '1e1', '999999999999999999999']) {
      expect(parsePlayerDirectoryPage(bad, 3)).toBeNull()
    }
  })
})

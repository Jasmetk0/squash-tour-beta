import { describe, expect, it } from 'vitest'

import type { EventRecord, RunPlayerListItem, SeasonStateResponse } from '../../../api/types'
import { buildSearchTournamentResults, comparablePlayerIds, comparisonStatFields, formatComparisonDifference, normalizeViewerSearchQuery, playerNumericField, searchTextMatches, verifiedComparisonPlayerDetail } from './viewerComparisonDisplay'

function makePlayer(overrides: Partial<RunPlayerListItem> = {}): RunPlayerListItem {
  return {
    player_id: 'player-a',
    name: 'Player A',
    country_code: 'EGY',
    age: 25,
    source_type: 'planner_generated',
    override_id: null,
    quality_band: 'elite',
    is_top_band: true,
    origin_source_type: 'planner_generated',
    origin_quality_band: 'elite',
    origin_override_id: null,
    origin_season: 2024,
    technique: 80,
    movement: 81,
    physical: 82,
    mental: 83,
    overall: 84,
    ...overrides
  }
}

describe('viewer comparison display helpers', () => {
  it('preserves comparison stat labels and order', () => {
    expect(comparisonStatFields.map((field) => field.label)).toEqual([
      'Power Rating difference',
      'Technique difference',
      'Movement difference',
      'Physical difference',
      'Mental difference',
      'Age difference'
    ])
  })

  it('preserves numeric field and difference formatting behavior', () => {
    const playerA = makePlayer({ overall: 90, technique: 80, movement: 70 })
    const playerB = makePlayer({ player_id: 'player-b', overall: 86, technique: 80, movement: 72 })

    expect(playerNumericField(playerA, 'overall')).toBe(90)
    expect(formatComparisonDifference(playerA, playerB, 'overall')).toBe('+4')
    expect(formatComparisonDifference(playerA, playerB, 'technique')).toBe('0')
    expect(formatComparisonDifference(playerA, playerB, 'movement')).toBe('-2')
  })

  it('preserves missing and non-finite numeric fallbacks', () => {
    const playerA = makePlayer({ overall: Number.NaN })
    const playerB = makePlayer({ overall: 86 })

    expect(playerNumericField(playerA, 'overall')).toBeNull()
    expect(formatComparisonDifference(playerA, playerB, 'overall')).toBe('—')
  })

  it('normalizes supported search query param aliases', () => {
    expect(normalizeViewerSearchQuery(new URLSearchParams('q=%20Ali%20'))).toBe('Ali')
    expect(normalizeViewerSearchQuery(new URLSearchParams('query=Egypt'))).toBe('Egypt')
    expect(normalizeViewerSearchQuery(new URLSearchParams('search=Gold'))).toBe('Gold')
  })

  it('preserves case-insensitive search matching', () => {
    expect(searchTextMatches('egy', ['EGY', null])).toBe(true)
    expect(searchTextMatches('gold', ['Silver', 42])).toBe(false)
  })

  it('accepts a verified exact detail even when its ID is beyond the old 50-player sample', () => {
    const player = makePlayer({player_id:'player-900',name:'Ninth hundredth player'})
    expect(verifiedComparisonPlayerDetail(player, 'player-900')).toBe(player)
    expect(verifiedComparisonPlayerDetail(player, 'player-1')).toBeNull()
  })

  it('rejects forged identity, invalid attributes, and malformed player details', () => {
    const player = makePlayer()
    for (const invalid of [
      null, [], 3, {...player,player_id:'foreign'},
      {...player,name:' '}, {...player,country_code:''},
      {...player,overall:Number.NaN}, {...player,technique:Number.POSITIVE_INFINITY},
      {...player,movement:undefined}, {...player,age:23.5},
      {...player,source_type:'unknown'}, {...player,is_top_band:'yes'},
      {...player,quality_band:{}}
    ]) {
      expect(verifiedComparisonPlayerDetail(invalid, 'player-a')).toBeNull()
    }
    expect(verifiedComparisonPlayerDetail(player, '')).toBeNull()
  })

  it('requires two different exact nonblank IDs before starting detail requests', () => {
    expect(comparablePlayerIds('player-1', 'player-900')).toBe(true)
    for (const pair of [['a','a'],['','b'],[' ','b'],['a',''],['a ','b'],
      ['a',' b'],['a'.repeat(257),'b']]) {
      expect(comparablePlayerIds(pair[0], pair[1])).toBe(false)
    }
  })

  it('combines planned and persisted tournaments without changing result shape', () => {
    const planned = [
      { event_id: 'evt-1', season: 2024, week: 7, category: 'Gold', tour: 'World Tour', template_id: 'tmpl-1' }
    ] as SeasonStateResponse['season_state']['ordered_events']
    const persisted = [
      { event_id: 'evt-1', event_sequence: 1, season: 2024, week: 7, template_id: 'tmpl-1', tournament_result: null },
      { event_id: 'evt-2', event_sequence: 2, season: 2024, week: 8, template_id: 'tmpl-2', tournament_result: null }
    ] as EventRecord[]

    expect(buildSearchTournamentResults(planned, persisted, 'evt')).toEqual([
      {
        eventId: 'evt-1',
        season: 2024,
        week: 7,
        tour: 'World Tour',
        category: 'Gold',
        templateId: 'tmpl-1',
        hasPlannedEvent: true,
        hasPersistedEvent: true
      },
      {
        eventId: 'evt-2',
        season: 2024,
        week: 8,
        tour: null,
        category: null,
        templateId: 'tmpl-2',
        hasPlannedEvent: false,
        hasPersistedEvent: true
      }
    ])
  })
})

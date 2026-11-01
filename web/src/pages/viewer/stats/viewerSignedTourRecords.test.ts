import { describe, expect, it } from 'vitest'

import { signedRecordFixture } from './viewerSignedTourRecordsFixture'
import { verifiedViewerSignedTourRecords, viewerRecordsBranch } from './viewerSignedTourRecords'


function valid(data: unknown): boolean {
  return verifiedViewerSignedTourRecords(data, 'record run', 'viewer-a',
    { asOfSeason: null, fromSeason: 0, countryCode: null }) !== null
}

describe('Saved Viewer native Tour records source contracts', () => {
  it('requires exact Viewer context, rejects unrelated Runs and missing Viewer Branch', () => {
    expect(viewerRecordsBranch({ product_run_id: 'record run', official_branch_id: 'viewer-a' }, 'record run')).toBe('viewer-a')
    expect(viewerRecordsBranch({ product_run_id: 'other', official_branch_id: 'viewer-a' }, 'record run')).toBeNull()
    expect(viewerRecordsBranch({ product_run_id: 'record run', official_branch_id: '' }, 'record run')).toBeNull()
    expect(viewerRecordsBranch({}, 'record run')).toBeNull()
  })

  it('accepts six bounded actual signed records, co-holder history and completed-season provenance', () => {
    expect(valid(signedRecordFixture())).toBe(true)
    const data = signedRecordFixture()
    expect(verifiedViewerSignedTourRecords(data, 'record run', 'viewer-a',
      { asOfSeason: 1, fromSeason: 0, countryCode: null })).not.toBeNull()
    expect(verifiedViewerSignedTourRecords(data, 'record run', 'viewer-a',
      { asOfSeason: 0, fromSeason: 0, countryCode: null })).toBeNull()
  })

  it('fails closed for foreign, stale and malformed source identity', () => {
    for (const patch of [
      { run_id: 'elsewhere' }, { branch_id: 'wrong' }, { saved_head_revision_id: '' },
      { source_tour_fingerprint: 'untrusted' }, { schema_version: 'draft' },
      { leaderboard_limit: 100 }, { country_code: 'USA' }, { from_season_index: 1 }
    ]) {
      expect(valid({ ...signedRecordFixture(), ...patch })).toBe(false)
    }
  })

  it('rejects missing or duplicated metrics, unsigned chronology and invented edition totals', () => {
    const data = signedRecordFixture()
    expect(valid({ ...data, records: data.records.slice(0, 5) })).toBe(false)
    expect(valid({ ...data, records: [...data.records.slice(0, 5), data.records[0]] })).toBe(false)
    expect(valid({ ...data, completed_seasons: [1, 0] })).toBe(false)
    expect(valid({ ...data, source_seasons: data.source_seasons.slice(1) })).toBe(false)
    expect(valid({ ...data, completed_edition_count: 90 })).toBe(false)
    expect(valid({ ...data, as_of_season_index: 2 })).toBe(false)
  })

  it('rejects falsified leaderboard ordering, negative values, duplicate identities and holder claims', () => {
    const make = () => structuredClone(signedRecordFixture())
    const wrongRank = make()
    wrongRank.records[0].leaderboard[0].rank = 2
    expect(valid(wrongRank)).toBe(false)
    const wrongValue = make()
    wrongValue.records[0].holders[0].titles = 100
    expect(valid(wrongValue)).toBe(false)
    const wrongTotal = make()
    wrongTotal.records[0].leaderboard_total = 0
    expect(valid(wrongTotal)).toBe(false)
    const duplicate = make()
    duplicate.records[0].holders.push(duplicate.records[0].holders[0])
    expect(valid(duplicate)).toBe(false)
    const negative = make()
    negative.records[0].value = -1
    expect(valid(negative)).toBe(false)
  })

  it('rejects invented future history, unsorted histories and invalid transition classification', () => {
    const make = () => structuredClone(signedRecordFixture())
    const future = make()
    future.records[0].holder_history[0].season_index = 3
    expect(valid(future)).toBe(false)
    const falseChange = make()
    falseChange.records[0].holder_history[0].change = 'improved'
    expect(valid(falseChange)).toBe(false)
    const duplicated = make()
    duplicated.records[0].holder_history.push(duplicated.records[0].holder_history[0])
    expect(valid(duplicated)).toBe(false)
  })

  it('enforces selected period and exact ISO country scope', () => {
    const d = signedRecordFixture()
    const country = { ...d, country_code: 'CZE' }
    expect(verifiedViewerSignedTourRecords(country, 'record run', 'viewer-a',
      { asOfSeason: 1, fromSeason: 0, countryCode: 'CZE' })).not.toBeNull()
    expect(verifiedViewerSignedTourRecords(country, 'record run', 'viewer-a',
      { asOfSeason: 1, fromSeason: 0, countryCode: 'USA' })).toBeNull()
    const foreign = structuredClone(country)
    foreign.records[0].holders[0].country_code = 'USA'
    expect(verifiedViewerSignedTourRecords(foreign, 'record run', 'viewer-a',
      { asOfSeason: 1, fromSeason: 0, countryCode: 'CZE' })).toBeNull()
  })
})

import { describe, expect, it } from 'vitest'

import { signedRecordFixture } from './viewerSignedTourRecordsFixture'
import { verifiedViewerSignedTourRecords, viewerRecordsBranch } from './viewerSignedTourRecordsModel'


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

  it('rejects contradictory holder identity, labels and top-ranked rows', () => {
    const make = () => structuredClone(signedRecordFixture())
    const wrongHolder = make()
    wrongHolder.records[0].holder_history[0].holder_ids = ['other-player']
    expect(valid(wrongHolder)).toBe(false)
    const wrongLabel = make()
    wrongLabel.records[0].holder_history[0].holder_labels = ['Other name']
    expect(valid(wrongLabel)).toBe(false)
    const wrongLeader = make()
    wrongLeader.records[0].leaderboard[0].entity_id = 'other-player'
    expect(valid(wrongLeader)).toBe(false)
    const wrongMetrics = make()
    wrongMetrics.records[0].leaderboard[0].finals = 99
    expect(valid(wrongMetrics)).toBe(false)
    const missingLeader = make()
    missingLeader.records[0].leaderboard = []
    expect(valid(missingLeader)).toBe(false)
  })

  it('retains all 21 legitimate tied holders with only 20 visible leaderboard rows', () => {
    const data = signedRecordFixture()
    const r = data.records[0]
    const holders = Array.from({ length: 21 }, (_, i) => ({
      ...r.holders[0], entity_id: 'p-' + String(i).padStart(2, '0'), label: 'Player ' + i,
    }))
    r.holders = holders
    r.leaderboard = holders.slice(0, 20).map(holder => ({ ...holder, rank: 1 }))
    r.leaderboard_total = holders.length
    r.holder_history[0].holder_ids = holders.map(holder => holder.entity_id)
    r.holder_history[0].holder_labels = holders.map(holder => holder.label)
    expect(valid(data)).toBe(true)
    r.holder_history[0].holder_ids.pop()
    r.holder_history[0].holder_labels.pop()
    expect(valid(data)).toBe(false)
  })

  it('requires exact season closure identity and properly formed fingerprints', () => {
    const wrongLabel = signedRecordFixture()
    wrongLabel.records[0].holder_history[0].season_label = 'different season'
    expect(valid(wrongLabel)).toBe(false)
    const wrongClosure = signedRecordFixture()
    wrongClosure.records[0].holder_history[0].boundary_command_id = 'different closure'
    expect(valid(wrongClosure)).toBe(false)
    const wrongFingerprint = signedRecordFixture()
    wrongFingerprint.source_seasons[0].published_ranking_fingerprint = 'not-a-fingerprint'
    expect(valid(wrongFingerprint)).toBe(false)
    const missingStart = signedRecordFixture()
    missingStart.source_seasons.shift()
    missingStart.completed_seasons.shift()
    expect(valid(missingStart)).toBe(false)
  })

  it('returns invalid rather than crashing when a holder history entry is null', () => {
    const data = signedRecordFixture()
    const record = { ...data.records[0], holder_history: [null] }
    expect(valid({ ...data, records: [record, ...data.records.slice(1)] })).toBe(false)
  })

})

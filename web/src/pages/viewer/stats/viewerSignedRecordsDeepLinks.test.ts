import { describe, expect, it } from 'vitest'
import { clearSignedRecordsDeepLink, readSignedRecordsDeepLink, writeSignedRecordsDeepLink } from './viewerSignedRecordsDeepLinks'

const run = 'record run/#', branch = 'viewer-a', head = 'revision-7', fingerprint = 'a'.repeat(64)
const filters = { asOfSeason: 1, fromSeason: 0, countryCode: 'CZE' }

describe('native Signed Tour Records URL ownership and Saved evidence', () => {
  it('does not automatically select an initial report without query params', () => {
    expect(readSignedRecordsDeepLink(new URLSearchParams('keep=x'), run, branch, head, fingerprint))
      .toEqual({ kind: 'none' })
  })
  it('round-trips canonical country and season filters with immutable scope', () => {
    const url = writeSignedRecordsDeepLink(new URLSearchParams('keep=one&keep=two'), run, branch, head, fingerprint, filters)
    expect(readSignedRecordsDeepLink(url, run, branch, head, fingerprint))
      .toEqual({ kind: 'selection', filters })
    expect(url.get('recordsRun')).toBe(run)
    expect(url.get('recordsHead')).toBe(head)
    expect(url.get('recordsFingerprint')).toBe(fingerprint)
    expect(url.getAll('keep')).toEqual(['one', 'two'])
    const withoutCountry = writeSignedRecordsDeepLink(url, run, branch, head, fingerprint,
      { ...filters, countryCode: null })
    expect(withoutCountry.has('recordsCountry')).toBe(false)
    expect(readSignedRecordsDeepLink(withoutCountry, run, branch, head, fingerprint))
      .toEqual({ kind: 'selection', filters: { ...filters, countryCode: null } })
  })
  it('refuses partial, duplicated, foreign or stale Saved scope', () => {
    const good = writeSignedRecordsDeepLink(new URLSearchParams(), run, branch, head, fingerprint, filters)
    expect(readSignedRecordsDeepLink(good, 'wrong', branch, head, fingerprint)).toEqual({ kind: 'invalid' })
    expect(readSignedRecordsDeepLink(good, run, 'wrong', head, fingerprint)).toEqual({ kind: 'invalid' })
    expect(readSignedRecordsDeepLink(good, run, branch, 'new-head', fingerprint)).toEqual({ kind: 'invalid' })
    expect(readSignedRecordsDeepLink(good, run, branch, head, 'b'.repeat(64))).toEqual({ kind: 'invalid' })
    expect(readSignedRecordsDeepLink(good, run, branch, null, fingerprint)).toEqual({ kind: 'invalid' })
    for (const key of ['recordsRun','recordsBranch','recordsHead','recordsFingerprint','recordsAsOf','recordsFrom']) {
      const missing = new URLSearchParams(good); missing.delete(key)
      expect(readSignedRecordsDeepLink(missing, run, branch, head, fingerprint)).toEqual({ kind: 'invalid' })
    }
    for (const key of ['recordsRun','recordsBranch','recordsHead','recordsFingerprint','recordsAsOf','recordsFrom','recordsCountry']) {
      const duplicate = new URLSearchParams(good); duplicate.append(key, good.get(key)!)
      expect(readSignedRecordsDeepLink(duplicate, run, branch, head, fingerprint)).toEqual({ kind: 'invalid' })
    }
  })
  it('rejects noncanonical indexes, reversed periods and bad country codes', () => {
    const good = writeSignedRecordsDeepLink(new URLSearchParams(), run, branch, head, fingerprint, filters)
    for (const key of ['recordsAsOf','recordsFrom']) {
      for (const raw of ['', '01', '-1','+1','1e0','1.0','NaN','9007199254740993']) {
        const invalid = new URLSearchParams(good); invalid.set(key, raw)
        expect(readSignedRecordsDeepLink(invalid, run, branch, head, fingerprint)).toEqual({ kind: 'invalid' })
      }
    }
    for (const badCountry of ['', 'cz', 'czE','CZ', 'CZEE','1CZ']) {
      const invalid = new URLSearchParams(good); invalid.set('recordsCountry', badCountry)
      expect(readSignedRecordsDeepLink(invalid, run, branch, head, fingerprint)).toEqual({ kind: 'invalid' })
    }
    const reversed = new URLSearchParams(good); reversed.set('recordsFrom','2')
    expect(readSignedRecordsDeepLink(reversed, run, branch, head, fingerprint)).toEqual({ kind: 'invalid' })
  })
  it('preserves unrelated duplicated keys when clearing a historical records filter', () => {
    const original = new URLSearchParams('keep=one&keep=two&unrelated=hello')
    const link = writeSignedRecordsDeepLink(original, run, branch, head, fingerprint, filters)
    const cleared = clearSignedRecordsDeepLink(link)
    expect(cleared.toString()).toBe(original.toString())
    expect(readSignedRecordsDeepLink(cleared, run, branch, head, fingerprint)).toEqual({ kind: 'none' })
  })
})

import { describe, expect, it } from 'vitest'
import { clearRankingDetailDeepLink, readRankingDetailDeepLink, writeRankingDetailDeepLink } from './rankingDetailDeepLinks'

const scope = ['run alpha/#', 'branch/one', 61, 'b'.repeat(64)] as const

describe('source-locked Official Ranking detail links', () => {
  it('shows the unfiltered first page by default and round-trips exact scope', () => {
    expect(readRankingDetailDeepLink(new URLSearchParams(), ...scope))
      .toEqual({ kind: 'valid', player: '', page: 1 })
    const written = writeRankingDetailDeepLink(new URLSearchParams('keep=x'), ...scope, 'Alice /#', 2)
    expect(readRankingDetailDeepLink(written, ...scope))
      .toEqual({ kind: 'valid', player: 'Alice /#', page: 2 })
    expect(written.get('keep')).toBe('x')
    expect(written.get('rankDetailRun')).toBe(scope[0])
    expect(written.get('rankDetailBranch')).toBe(scope[1])
    expect(written.get('rankDetailOrdinal')).toBe('61')
    expect(written.get('rankDetailFingerprint')).toBe(scope[3])
  })

  it('rejects wrong run, branch, ordinal, fingerprint and partial scopes', () => {
    const link = writeRankingDetailDeepLink(new URLSearchParams(), ...scope, '', 1)
    expect(readRankingDetailDeepLink(link, 'other', scope[1], scope[2], scope[3])).toEqual({ kind: 'invalid' })
    expect(readRankingDetailDeepLink(link, scope[0], 'other', scope[2], scope[3])).toEqual({ kind: 'invalid' })
    expect(readRankingDetailDeepLink(link, scope[0], scope[1], 62, scope[3])).toEqual({ kind: 'invalid' })
    expect(readRankingDetailDeepLink(link, scope[0], scope[1], scope[2], 'c'.repeat(64))).toEqual({ kind: 'invalid' })
    expect(readRankingDetailDeepLink(link, scope[0], scope[1], scope[2], null)).toEqual({ kind: 'invalid' })
    for (const key of ['rankDetailRun', 'rankDetailBranch', 'rankDetailOrdinal', 'rankDetailFingerprint']) {
      const missing = new URLSearchParams(link)
      missing.delete(key)
      expect(readRankingDetailDeepLink(missing, ...scope)).toEqual({ kind: 'invalid' })
    }
  })

  it('rejects duplicate keys, noncanonical/out-of-range pages, and oversized player queries', () => {
    const base = writeRankingDetailDeepLink(new URLSearchParams(), ...scope, 'Alice', 1)
    for (const extra of [
      ['rankDetailRun', scope[0]],
      ['rankDetailBranch', scope[1]],
      ['rankDetailOrdinal', String(scope[2])],
      ['rankDetailFingerprint', scope[3]],
      ['rankDetailPlayer', 'Bob'],
      ['rankDetailPage', '2'],
    ]) {
      const copied = new URLSearchParams(base)
      copied.append(extra[0], extra[1])
      expect(readRankingDetailDeepLink(copied, ...scope)).toEqual({ kind: 'invalid' })
    }
    for (const raw of ['', '0', '-1', '+1', '01', '1.5', '1e2', 'NaN', '9007199254740993']) {
      const copied = new URLSearchParams(base)
      copied.set('rankDetailPage', raw)
      expect(readRankingDetailDeepLink(copied, ...scope)).toEqual({ kind: 'invalid' })
    }
    const large = new URLSearchParams(base)
    large.set('rankDetailPlayer', 'x'.repeat(257))
    expect(readRankingDetailDeepLink(large, ...scope)).toEqual({ kind: 'invalid' })
  })

  it('clears only owned parameters, including duplicates, preserving unrelated query entries', () => {
    const original = new URLSearchParams('keep=one&keep=two&flag=three')
    const active = writeRankingDetailDeepLink(original, ...scope, 'SUE', 3)
    expect(active.getAll('keep')).toEqual(['one', 'two'])
    expect(readRankingDetailDeepLink(active, ...scope)).toEqual({ kind: 'valid', player: 'SUE', page: 3 })
    const clear = clearRankingDetailDeepLink(active)
    expect(clear.toString()).toBe(original.toString())
    expect(readRankingDetailDeepLink(clear, ...scope)).toEqual({ kind: 'valid', player: '', page: 1 })
  })
})

import { describe, expect, it } from 'vitest'
import { readSignedSeasonDeepLink, writeSignedSeasonDeepLink } from './viewerSignedSeasonDeepLinks'

const run = 'run alpha/#'
const branch = 'saved/branch one'

describe('Signed season source-authenticated deep links', () => {
  it('requires a complete exact Run and Viewer Branch identity', () => {
    expect(readSignedSeasonDeepLink(new URLSearchParams(), run, branch)).toEqual({ kind: 'none' })
    const good = new URLSearchParams({ signedRun: run, signedBranch: branch, signedHead: 'rev-20', signedSeason: '125' })
    expect(readSignedSeasonDeepLink(good, run, branch))
      .toEqual({ kind: 'selection', savedHead: 'rev-20', selected: 125, comparison: null })
    expect(readSignedSeasonDeepLink(good, 'other-run', branch)).toEqual({ kind: 'invalid' })
    expect(readSignedSeasonDeepLink(good, run, 'other-branch')).toEqual({ kind: 'invalid' })
  })

  it('rejects malformed, partial, noncanonical, duplicated, same-season or unsafe IDs', () => {
    const pairs = [
      'signedSeason=1',
      'signedRun=run+alpha%2F%23&signedSeason=1',
      'signedRun=run+alpha%2F%23&signedBranch=saved%2Fbranch+one',
      'signedSeason=01',
      'signedSeason=-1',
      'signedSeason=1.1',
      'signedSeason=1e2',
      'signedSeason=NaN',
      'signedSeason=9007199254740993',
      'signedSeason=1&signedSeason=2',
      'signedSeason=1&compareSeason=1',
      'signedSeason=1&compareSeason=01',
      'signedSeason=1&compareSeason=-1',
      'signedSeason=1&compareSeason=0&compareSeason=1',
      'signedSeason=1&signedRun=another',
      'signedSeason=1&signedHead=other',
    ]
    for (const fragment of pairs) {
      const params = new URLSearchParams('signedRun=' + encodeURIComponent(run) +
        '&signedBranch=' + encodeURIComponent(branch) + '&signedHead=rev-20&' + fragment)
      expect(readSignedSeasonDeepLink(params, run, branch)).toEqual({ kind: 'invalid' })
    }
  })

  it('writes only owned params and preserves duplicated unrelated query params', () => {
    const start = new URLSearchParams('keep=one&keep=two&signedSeason=99&compareSeason=98&signedHead=old')
    const url = writeSignedSeasonDeepLink(start, run, branch, 'rev-20', 1, 0)
    expect(url.getAll('keep')).toEqual(['one', 'two'])
    expect(url.get('signedRun')).toBe(run)
    expect(url.get('signedBranch')).toBe(branch)
    expect(url.get('signedHead')).toBe('rev-20')
    expect(url.get('signedSeason')).toBe('1')
    expect(url.get('compareSeason')).toBe('0')
    expect(readSignedSeasonDeepLink(url, run, branch))
      .toEqual({ kind: 'selection', savedHead: 'rev-20', selected: 1, comparison: 0 })
    const reset = writeSignedSeasonDeepLink(url, run, branch, 'rev-20', 0, null)
    expect(reset.has('compareSeason')).toBe(false)
    expect(reset.getAll('keep')).toEqual(['one', 'two'])
    expect(readSignedSeasonDeepLink(reset, run, branch))
      .toEqual({ kind: 'selection', savedHead: 'rev-20', selected: 0, comparison: null })
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { readRecentProductRuns, rememberProductRun } from './recentProductRuns'

const KEY = 'squash-engine-recent-product-runs-v1'

describe('recentProductRuns', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('returns empty history for missing, invalid, and non-array storage', () => {
    expect(readRecentProductRuns()).toEqual([])
    localStorage.setItem(KEY, '{broken')
    expect(readRecentProductRuns()).toEqual([])
    localStorage.setItem(KEY, JSON.stringify({ run: 'run-1' }))
    expect(readRecentProductRuns()).toEqual([])
  })

  it('skips malformed entries and duplicates before applying the eight-Run limit', () => {
    localStorage.setItem(KEY, JSON.stringify([
      '', null, 'run-1', 'run-1', 99, ' ', 'run-2', 'run-3',
      'run-4', 'run-5', 'run-6', 'run-7', 'run-8', 'run-9',
    ]))
    expect(readRecentProductRuns()).toEqual([
      'run-1', 'run-2', 'run-3', 'run-4',
      'run-5', 'run-6', 'run-7', 'run-8',
    ])
  })

  it('moves an opened Run to the front without duplicates and bounds history', () => {
    for (let n = 1; n <= 10; n++) rememberProductRun(`run-${n}`)
    expect(readRecentProductRuns()).toEqual([
      'run-10', 'run-9', 'run-8', 'run-7',
      'run-6', 'run-5', 'run-4', 'run-3',
    ])
    rememberProductRun('run-7')
    expect(readRecentProductRuns()).toEqual([
      'run-7', 'run-10', 'run-9', 'run-8',
      'run-6', 'run-5', 'run-4', 'run-3',
    ])
    rememberProductRun(' ')
    expect(readRecentProductRuns()[0]).toBe('run-7')
  })

  it('fails closed when localStorage is unavailable', () => {
    const getItem = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('Storage unavailable')
    })
    expect(readRecentProductRuns()).toEqual([])
    getItem.mockRestore()

    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage unavailable')
    })
    expect(() => rememberProductRun('run-1')).not.toThrow()
    setItem.mockRestore()
  })
})

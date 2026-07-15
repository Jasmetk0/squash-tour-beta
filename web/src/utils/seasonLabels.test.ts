import { describe, expect, it } from 'vitest'

import { isValidSeasonLabel, safeToCompactSeasonLabel, safeToLongSeasonLabel, seasonLabelFromStartYear, toCompactSeasonLabel, toLongSeasonLabel } from './seasonLabels'

describe('seasonLabels', () => {
  it('normalizes compact and long labels to compact', () => {
    expect(toCompactSeasonLabel('2000/01')).toBe('2000/01')
    expect(toCompactSeasonLabel('2000/2001')).toBe('2000/01')
  })

  it('converts to long labels', () => {
    expect(toLongSeasonLabel('2000/01')).toBe('2000/2001')
    expect(toLongSeasonLabel('2000/2001')).toBe('2000/2001')
  })

  it('builds compact label from start year', () => {
    expect(seasonLabelFromStartYear(2049)).toBe('2049/50')
  })

  it('rejects malformed labels', () => {
    expect(() => toCompactSeasonLabel('2000/03')).toThrow()
    expect(() => toCompactSeasonLabel('2000/2003')).toThrow()
    expect(() => toCompactSeasonLabel('2000')).toThrow()
  })

  it('exposes safe helpers for invalid input handling', () => {
    expect(safeToCompactSeasonLabel('2000/01')).toBe('2000/01')
    expect(safeToCompactSeasonLabel('2000/2001')).toBe('2000/01')
    expect(safeToLongSeasonLabel('2000/01')).toBe('2000/2001')
    expect(safeToCompactSeasonLabel('invalid')).toBeNull()
    expect(safeToLongSeasonLabel('invalid')).toBeNull()
    expect(isValidSeasonLabel('2000/01')).toBe(true)
    expect(isValidSeasonLabel('invalid')).toBe(false)
  })
})

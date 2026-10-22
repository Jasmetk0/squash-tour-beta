import { describe, expect, it } from 'vitest'
import { prettyLabJson } from './LabJson'

describe('Lab JSON editor utilities', () => {
  it('formats a JSON object without changing its values', () => {
    const initial = '{"schema_version":"scenario.v1","seed":42,"variants":[{"id":"a"}]}'
    expect(JSON.parse(prettyLabJson(initial))).toEqual(JSON.parse(initial))
    expect(prettyLabJson(initial)).toContain('\n  "seed": 42,')
  })

  it('rejects JSON primitives, arrays, null and invalid syntax without inventing a scenario', () => {
    for (const value of ['null', '[]', '42', '"example"', 'true']) {
      expect(() => prettyLabJson(value)).toThrow('A Lab scenario must be a JSON object.')
    }
    expect(() => prettyLabJson('{broken')).toThrow('Invalid JSON syntax.')
  })
})

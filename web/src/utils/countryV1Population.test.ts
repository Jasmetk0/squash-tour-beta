import { describe, expect, it } from 'vitest'

import { countryV1PopulationPayloadFromRows } from './countryV1Population'

describe('countryV1PopulationPayloadFromRows', () => {
  it('builds a sorted canonical payload and preserves the package fingerprint', () => {
    expect(countryV1PopulationPayloadFromRows([
      { year: '2020', population: '1000000' },
      { year: '2000', population: '900000' },
    ], 'fp-1')).toEqual({
      values_by_year: {
        '2000': 900000,
        '2020': 1000000,
      },
      expected_package_fingerprint: 'fp-1',
    })
  })

  it('requires authored population year 2020', () => {
    expect(() => countryV1PopulationPayloadFromRows([
      { year: '2000', population: '900000' },
    ])).toThrow('Population year 2020 is required')
  })

  it('rejects duplicate authored years', () => {
    expect(() => countryV1PopulationPayloadFromRows([
      { year: '2020', population: '1000000' },
      { year: '2020', population: '1100000' },
    ])).toThrow('Population year 2020 is already authored')
  })

  it('rejects years outside the supported 1955–2050 range', () => {
    expect(() => countryV1PopulationPayloadFromRows([
      { year: '1954', population: '1000000' },
      { year: '2020', population: '1000000' },
    ])).toThrow('Population year must be between 1955 and 2050')

    expect(() => countryV1PopulationPayloadFromRows([
      { year: '2020', population: '1000000' },
      { year: '2051', population: '1000000' },
    ])).toThrow('Population year must be between 1955 and 2050')
  })

  it('rejects zero, negative, and fractional population values', () => {
    expect(() => countryV1PopulationPayloadFromRows([
      { year: '2020', population: '0' },
    ])).toThrow('Population must be a positive integer')

    expect(() => countryV1PopulationPayloadFromRows([
      { year: '2020', population: '-1' },
    ])).toThrow('Population must be a positive integer')

    expect(() => countryV1PopulationPayloadFromRows([
      { year: '2020', population: '1000.5' },
    ])).toThrow('Population must be a positive integer')
  })
})

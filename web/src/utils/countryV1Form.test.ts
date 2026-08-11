import { describe, expect, it } from 'vitest'

import type { CountryV1Record } from '../api/countryV1'
import {
  COUNTRY_V1_RATING_FIELDS,
  countryV1CreatePayloadFromDraft,
  countryV1FormDraftFromRecord,
  countryV1UpdatePayloadFromDraft,
  type CountryV1FormDraft,
} from './countryV1Form'

const draft: CountryV1FormDraft = {
  name: 'Exampleland',
  notes: 'Country V1 fixture',
  area_km2: '12345',
  region: 'EUR',
  travel_region: 'EUROPE_CENTRAL',
  court_count: '42',
  squash_popularity: '4',
  squash_access: '3',
  development_quality: '5',
  competition_quality: '4',
  elite_support: '2',
  squash_tradition: '3',
}

describe('countryV1Form', () => {
  it('defines exactly the six canonical authored Country V1 ratings', () => {
    expect(COUNTRY_V1_RATING_FIELDS.map((field) => field.key)).toEqual([
      'squash_popularity',
      'squash_access',
      'development_quality',
      'competition_quality',
      'elite_support',
      'squash_tradition',
    ])
  })

  it('builds the canonical update payload without legacy country attributes', () => {
    expect(countryV1UpdatePayloadFromDraft(draft, 'fingerprint-1')).toEqual({
      name: 'Exampleland',
      notes: 'Country V1 fixture',
      area_km2: 12345,
      region: 'EUR',
      travel_region: 'EUROPE_CENTRAL',
      court_count: 42,
      squash_popularity: 4,
      squash_access: 3,
      development_quality: 5,
      competition_quality: 4,
      elite_support: 2,
      squash_tradition: 3,
      expected_package_fingerprint: 'fingerprint-1',
    })
  })

  it('builds the canonical create payload with population timeline and fingerprint', () => {
    expect(countryV1CreatePayloadFromDraft(draft, 'EXP', { '2020': 1_000_000 }, 'fingerprint-2')).toEqual({
      name: 'Exampleland',
      notes: 'Country V1 fixture',
      area_km2: 12345,
      region: 'EUR',
      travel_region: 'EUROPE_CENTRAL',
      court_count: 42,
      squash_popularity: 4,
      squash_access: 3,
      development_quality: 5,
      competition_quality: 4,
      elite_support: 2,
      squash_tradition: 3,
      code: 'EXP',
      population_by_year: { '2020': 1_000_000 },
      expected_package_fingerprint: 'fingerprint-2',
    })
  })

  it('maps nullable factual values to blank form fields', () => {
    const country: CountryV1Record = {
      code: 'EXP',
      name: 'Exampleland',
      flag_asset: null,
      region: 'EUR',
      population: 1_000_000,
      area_km2: null,
      default_population_year: 2020,
      default_population: 1_000_000,
      population_by_year: { '2020': 1_000_000 },
      court_count: null,
      travel_region: null,
      notes: null,
      squash_popularity: 4,
      squash_access: 3,
      development_quality: 5,
      competition_quality: 4.5,
      elite_support: 2,
      squash_tradition: 3,
    }

    expect(countryV1FormDraftFromRecord(country)).toEqual({
      name: 'Exampleland',
      notes: '',
      area_km2: '',
      region: 'EUR',
      travel_region: '',
      court_count: '',
      squash_popularity: '4',
      squash_access: '3',
      development_quality: '5',
      competition_quality: '4.5',
      elite_support: '2',
      squash_tradition: '3',
    })
  })

  it('accepts fractional authored ratings and rejects values outside 1 to 5', () => {
    expect(countryV1UpdatePayloadFromDraft({
      ...draft,
      squash_access: '2.25',
      competition_quality: '4.5',
    })).toMatchObject({
      squash_access: 2.25,
      competition_quality: 4.5,
    })

    expect(() => countryV1UpdatePayloadFromDraft({ ...draft, elite_support: '5.01' })).toThrow(
      'elite_support must be a number from 1 to 5',
    )
    expect(() => countryV1UpdatePayloadFromDraft({ ...draft, elite_support: '0.99' })).toThrow(
      'elite_support must be a number from 1 to 5',
    )
  })

  it('keeps optional factual values nullable and rejects invalid integer input', () => {
    const payload = countryV1UpdatePayloadFromDraft({
      ...draft,
      notes: '',
      area_km2: '',
      travel_region: '',
      court_count: '',
    })
    expect(payload.notes).toBeNull()
    expect(payload.area_km2).toBeNull()
    expect(payload.travel_region).toBeNull()
    expect(payload.court_count).toBeNull()
    expect(payload).not.toHaveProperty('expected_package_fingerprint')

    expect(() => countryV1UpdatePayloadFromDraft({ ...draft, court_count: '12.5' })).toThrow(
      'court_count must be an integer',
    )
    expect(() => countryV1UpdatePayloadFromDraft({ ...draft, area_km2: '0' })).toThrow(
      'area_km2 must be greater than 0',
    )
  })
})

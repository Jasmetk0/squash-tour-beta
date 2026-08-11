import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { WorldPackageCountryV1CreatePayload } from './countryV1'
import {
  createWorldPackageCountryV1,
  deleteWorldPackageCountryV1,
  getWorldPackageCountriesV1,
  getWorldPackageCountryV1,
  updateWorldPackageCountryPopulationV1,
  updateWorldPackageCountryV1,
} from './countryV1Client'

const client = vi.hoisted(() => ({
  getWorldPackageCountries: vi.fn(),
  getWorldPackageCountry: vi.fn(),
  createWorldPackageCountry: vi.fn(),
  updateWorldPackageCountry: vi.fn(),
  updateWorldPackageCountryPopulation: vi.fn(),
  deleteWorldPackageCountry: vi.fn(),
}))

vi.mock('./client', () => client)

beforeEach(() => {
  vi.clearAllMocks()
  for (const mock of Object.values(client)) mock.mockResolvedValue({})
})

describe('countryV1Client', () => {
  it('delegates list and detail reads to the established World Package client', async () => {
    await getWorldPackageCountriesV1('my world')
    await getWorldPackageCountryV1('my world', 'A B')

    expect(client.getWorldPackageCountries).toHaveBeenCalledWith('my world')
    expect(client.getWorldPackageCountry).toHaveBeenCalledWith('my world', 'A B')
  })

  it('passes only the canonical Country V1 create payload to the shared client', async () => {
    const payload: WorldPackageCountryV1CreatePayload = {
      code: 'EXP',
      name: 'Exampleland',
      notes: null,
      area_km2: 100,
      region: 'EUR',
      travel_region: null,
      court_count: 10,
      squash_popularity: 4,
      squash_access: 3,
      development_quality: 5,
      competition_quality: 4,
      elite_support: 2,
      squash_tradition: 3,
      population_by_year: { '2020': 1_000_000 },
      expected_package_fingerprint: 'fp-1',
    }

    await createWorldPackageCountryV1('custom_world', payload)

    expect(client.createWorldPackageCountry).toHaveBeenCalledWith('custom_world', payload)
    const serialized = JSON.stringify(client.createWorldPackageCountry.mock.calls[0]?.[1])
    expect(serialized).not.toContain('wealth_support')
    expect(serialized).not.toContain('system_quality')
    expect(serialized).not.toContain('competition_density')
    expect(serialized).not.toContain('federation_quality')
    expect(serialized).not.toContain('style_dna')
  })

  it('delegates canonical update and population payloads unchanged', async () => {
    const updatePayload = {
      name: 'Exampleland',
      notes: null,
      area_km2: null,
      region: 'EUR',
      travel_region: null,
      court_count: null,
      squash_popularity: 3 as const,
      squash_access: 3 as const,
      development_quality: 3 as const,
      competition_quality: 3 as const,
      elite_support: 3 as const,
      squash_tradition: 3 as const,
    }
    const populationPayload = {
      values_by_year: { '2020': 1_000_000 },
      expected_package_fingerprint: 'fp-2',
    }

    await updateWorldPackageCountryV1('custom_world', 'EXP', updatePayload)
    await updateWorldPackageCountryPopulationV1('custom_world', 'EXP', populationPayload)

    expect(client.updateWorldPackageCountry).toHaveBeenCalledWith('custom_world', 'EXP', updatePayload)
    expect(client.updateWorldPackageCountryPopulation).toHaveBeenCalledWith(
      'custom_world',
      'EXP',
      populationPayload,
    )
  })

  it('passes optimistic-concurrency fingerprint to shared delete transport', async () => {
    await deleteWorldPackageCountryV1('custom_world', 'EXP', 'fp with space')

    expect(client.deleteWorldPackageCountry).toHaveBeenCalledWith(
      'custom_world',
      'EXP',
      'fp with space',
    )
  })

  it('preserves shared client errors without wrapping them', async () => {
    const error = new Error('bad country')
    client.getWorldPackageCountries.mockRejectedValueOnce(error)

    await expect(getWorldPackageCountriesV1('custom_world')).rejects.toBe(error)
  })
})

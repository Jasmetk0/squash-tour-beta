import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from './client'
import type { WorldPackageCountryV1CreatePayload } from './countryV1'
import {
  createWorldPackageCountryV1,
  deleteWorldPackageCountryV1,
  getWorldPackageCountriesV1,
  updateWorldPackageCountryV1,
} from './countryV1Client'

function response(body: string, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body,
  } as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('countryV1Client', () => {
  it('uses the canonical world-package countries endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response('{"countries":[]}'))
    vi.stubGlobal('fetch', fetchMock)

    await getWorldPackageCountriesV1('my world')

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0]?.[0]).toEqual(expect.stringContaining('/world/packages/my%20world/countries'))
    expect(fetchMock.mock.calls[0]?.[1]).toEqual(expect.objectContaining({
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
    }))
  })

  it('posts only the canonical Country V1 create payload supplied by the form adapter', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response('{}', 201))
    vi.stubGlobal('fetch', fetchMock)
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

    const [, init] = fetchMock.mock.calls[0] ?? []
    expect(init).toEqual(expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) }))
    expect(String((init as RequestInit).body)).not.toContain('wealth_support')
    expect(String((init as RequestInit).body)).not.toContain('system_quality')
    expect(String((init as RequestInit).body)).not.toContain('competition_density')
    expect(String((init as RequestInit).body)).not.toContain('federation_quality')
    expect(String((init as RequestInit).body)).not.toContain('style_dna')
  })

  it('uses the V1 update endpoint and preserves the supplied country code safely', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response('{}'))
    vi.stubGlobal('fetch', fetchMock)

    await updateWorldPackageCountryV1('custom_world', 'A B', {
      name: 'Exampleland',
      notes: null,
      area_km2: null,
      region: 'EUR',
      travel_region: null,
      court_count: null,
      squash_popularity: 3,
      squash_access: 3,
      development_quality: 3,
      competition_quality: 3,
      elite_support: 3,
      squash_tradition: 3,
    })

    expect(fetchMock.mock.calls[0]?.[0]).toEqual(
      expect.stringContaining('/world/packages/custom_world/countries/A%20B'),
    )
    expect(fetchMock.mock.calls[0]?.[1]).toEqual(expect.objectContaining({ method: 'PUT' }))
  })

  it('sends optimistic-concurrency fingerprint when deleting', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response('{}'))
    vi.stubGlobal('fetch', fetchMock)

    await deleteWorldPackageCountryV1('custom_world', 'EXP', 'fp with space')

    expect(fetchMock.mock.calls[0]?.[0]).toEqual(
      expect.stringContaining('/world/packages/custom_world/countries/EXP?expected_package_fingerprint=fp+with+space'),
    )
    expect(fetchMock.mock.calls[0]?.[1]).toEqual(expect.objectContaining({ method: 'DELETE' }))
  })

  it('keeps the existing ApiError behavior for non-success responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response('{"detail":"bad country"}', 422)))

    const error = await getWorldPackageCountriesV1('custom_world').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(422)
    expect((error as ApiError).message).toContain('bad country')
  })
})

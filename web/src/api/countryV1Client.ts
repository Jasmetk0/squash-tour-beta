import {
  createWorldPackageCountry,
  deleteWorldPackageCountry,
  getWorldPackageCountries,
  getWorldPackageCountry,
  updateWorldPackageCountry,
  updateWorldPackageCountryPopulation,
} from './client'
import type {
  CountryV1Rating,
  CountryV1Record,
  WorldPackageCountriesV1Response,
  WorldPackageCountryV1CreatePayload,
  WorldPackageCountryV1DeleteResponse,
  WorldPackageCountryV1Detail,
  WorldPackageCountryV1PopulationUpdatePayload,
  WorldPackageCountryV1UpdatePayload,
  WorldPackageCountryV1UpdateResponse,
} from './countryV1'

type LegacyCountryReadShape = Partial<CountryV1Record> & {
  wealth_support?: unknown
  system_quality?: unknown
  competition_density?: unknown
  federation_quality?: unknown
  style_dna?: unknown
}

function readRating(value: unknown, field: string): CountryV1Rating {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 1 || value > 5) {
    throw new Error(`${field} must be a number from 1 to 5`)
  }
  return value
}

/**
 * Read-only compatibility boundary for responses produced by a pre-V1 server or
 * stale integration fixture. It mirrors the backend legacy load bridge, then
 * immediately exposes only canonical V1 fields to the active frontend.
 *
 * No legacy field is preserved on the returned record or written back.
 */
export function normalizeCountryV1Read(country: LegacyCountryReadShape): CountryV1Record {
  return {
    code: country.code as string,
    name: country.name as string,
    flag_asset: country.flag_asset ?? null,
    region: country.region as string,
    population: country.population as number,
    area_km2: country.area_km2 ?? null,
    default_population_year: country.default_population_year ?? null,
    default_population: country.default_population ?? null,
    population_by_year: country.population_by_year ?? null,
    court_count: country.court_count ?? null,
    travel_region: country.travel_region ?? null,
    notes: country.notes ?? null,
    squash_popularity: readRating(country.squash_popularity, 'squash_popularity'),
    squash_access: readRating(country.squash_access ?? country.wealth_support, 'squash_access'),
    development_quality: readRating(
      country.development_quality ?? country.system_quality,
      'development_quality',
    ),
    competition_quality: readRating(
      country.competition_quality ?? country.competition_density ?? country.system_quality,
      'competition_quality',
    ),
    elite_support: readRating(
      country.elite_support ?? country.federation_quality ?? country.wealth_support,
      'elite_support',
    ),
    squash_tradition: readRating(country.squash_tradition, 'squash_tradition'),
  }
}

/**
 * Country V1 keeps canonical frontend contracts while reusing the repository's
 * established World Package transport functions. The backend endpoints are the
 * same; only the frontend type surface is being migrated in this PR.
 */
export async function getWorldPackageCountriesV1(worldId: string): Promise<WorldPackageCountriesV1Response> {
  const response = await getWorldPackageCountries(worldId) as unknown as WorldPackageCountriesV1Response
  return {
    ...response,
    countries: response.countries.map((country) => normalizeCountryV1Read(country as LegacyCountryReadShape)),
  }
}

export async function getWorldPackageCountryV1(
  worldId: string,
  countryCode: string,
): Promise<WorldPackageCountryV1Detail> {
  const detail = await getWorldPackageCountry(worldId, countryCode) as unknown as WorldPackageCountryV1Detail
  return {
    ...detail,
    country: normalizeCountryV1Read(detail.country as LegacyCountryReadShape),
  }
}

export function createWorldPackageCountryV1(
  worldId: string,
  payload: WorldPackageCountryV1CreatePayload,
): Promise<WorldPackageCountryV1UpdateResponse> {
  return createWorldPackageCountry(
    worldId,
    payload as unknown as Parameters<typeof createWorldPackageCountry>[1],
  ) as unknown as Promise<WorldPackageCountryV1UpdateResponse>
}

export function updateWorldPackageCountryV1(
  worldId: string,
  countryCode: string,
  payload: WorldPackageCountryV1UpdatePayload,
): Promise<WorldPackageCountryV1UpdateResponse> {
  return updateWorldPackageCountry(
    worldId,
    countryCode,
    payload as unknown as Parameters<typeof updateWorldPackageCountry>[2],
  ) as unknown as Promise<WorldPackageCountryV1UpdateResponse>
}

export function updateWorldPackageCountryPopulationV1(
  worldId: string,
  countryCode: string,
  payload: WorldPackageCountryV1PopulationUpdatePayload,
): Promise<WorldPackageCountryV1UpdateResponse> {
  return updateWorldPackageCountryPopulation(
    worldId,
    countryCode,
    payload as unknown as Parameters<typeof updateWorldPackageCountryPopulation>[2],
  ) as unknown as Promise<WorldPackageCountryV1UpdateResponse>
}

export function deleteWorldPackageCountryV1(
  worldId: string,
  countryCode: string,
  expectedPackageFingerprint: string,
): Promise<WorldPackageCountryV1DeleteResponse> {
  return deleteWorldPackageCountry(
    worldId,
    countryCode,
    expectedPackageFingerprint,
  ) as unknown as Promise<WorldPackageCountryV1DeleteResponse>
}

import {
  createWorldPackageCountry,
  deleteWorldPackageCountry,
  getWorldPackageCountries,
  getWorldPackageCountry,
  updateWorldPackageCountry,
  updateWorldPackageCountryPopulation,
} from './client'
import type {
  WorldPackageCountriesV1Response,
  WorldPackageCountryV1CreatePayload,
  WorldPackageCountryV1DeleteResponse,
  WorldPackageCountryV1Detail,
  WorldPackageCountryV1PopulationUpdatePayload,
  WorldPackageCountryV1UpdatePayload,
  WorldPackageCountryV1UpdateResponse,
} from './countryV1'

/**
 * Country V1 keeps canonical frontend contracts while reusing the repository's
 * established World Package transport functions. The backend endpoints are the
 * same; only the frontend type surface is being migrated in this PR.
 */
export function getWorldPackageCountriesV1(worldId: string): Promise<WorldPackageCountriesV1Response> {
  return getWorldPackageCountries(worldId) as unknown as Promise<WorldPackageCountriesV1Response>
}

export function getWorldPackageCountryV1(
  worldId: string,
  countryCode: string,
): Promise<WorldPackageCountryV1Detail> {
  return getWorldPackageCountry(worldId, countryCode) as unknown as Promise<WorldPackageCountryV1Detail>
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

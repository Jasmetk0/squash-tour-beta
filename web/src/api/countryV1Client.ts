import { ApiError } from './client'
import type {
  WorldPackageCountriesV1Response,
  WorldPackageCountryV1CreatePayload,
  WorldPackageCountryV1DeleteResponse,
  WorldPackageCountryV1Detail,
  WorldPackageCountryV1PopulationUpdatePayload,
  WorldPackageCountryV1UpdatePayload,
  WorldPackageCountryV1UpdateResponse,
} from './countryV1'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function requestCountryV1<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })

  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(body || 'Request failed', response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  if (!text) {
    return undefined as T
  }
  return JSON.parse(text) as T
}

export function getWorldPackageCountriesV1(worldId: string): Promise<WorldPackageCountriesV1Response> {
  return requestCountryV1(`/world/packages/${encodeURIComponent(worldId)}/countries`)
}

export function getWorldPackageCountryV1(
  worldId: string,
  countryCode: string,
): Promise<WorldPackageCountryV1Detail> {
  return requestCountryV1(
    `/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}`,
  )
}

export function createWorldPackageCountryV1(
  worldId: string,
  payload: WorldPackageCountryV1CreatePayload,
): Promise<WorldPackageCountryV1UpdateResponse> {
  return requestCountryV1(`/world/packages/${encodeURIComponent(worldId)}/countries`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateWorldPackageCountryV1(
  worldId: string,
  countryCode: string,
  payload: WorldPackageCountryV1UpdatePayload,
): Promise<WorldPackageCountryV1UpdateResponse> {
  return requestCountryV1(
    `/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}`,
    { method: 'PUT', body: JSON.stringify(payload) },
  )
}

export function updateWorldPackageCountryPopulationV1(
  worldId: string,
  countryCode: string,
  payload: WorldPackageCountryV1PopulationUpdatePayload,
): Promise<WorldPackageCountryV1UpdateResponse> {
  return requestCountryV1(
    `/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}/population`,
    { method: 'PUT', body: JSON.stringify(payload) },
  )
}

export function deleteWorldPackageCountryV1(
  worldId: string,
  countryCode: string,
  expectedPackageFingerprint: string,
): Promise<WorldPackageCountryV1DeleteResponse> {
  const query = new URLSearchParams({ expected_package_fingerprint: expectedPackageFingerprint })
  return requestCountryV1(
    `/world/packages/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(countryCode)}?${query.toString()}`,
    { method: 'DELETE' },
  )
}

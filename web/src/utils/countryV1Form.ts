import type {
  CountryV1Rating,
  CountryV1Record,
  WorldPackageCountryV1CreatePayload,
  WorldPackageCountryV1UpdatePayload,
} from '../api/countryV1'

export const COUNTRY_V1_RATING_FIELDS = [
  { key: 'squash_popularity', label: 'Squash Popularity' },
  { key: 'squash_access', label: 'Squash Access' },
  { key: 'development_quality', label: 'Development Quality' },
  { key: 'competition_quality', label: 'Competition Quality' },
  { key: 'elite_support', label: 'Elite Support' },
  { key: 'squash_tradition', label: 'Squash Tradition' },
] as const

export type CountryV1RatingField = (typeof COUNTRY_V1_RATING_FIELDS)[number]['key']

export type CountryV1FormDraft = {
  name: string
  notes: string
  area_km2: string
  region: string
  travel_region: string
  court_count: string
  squash_popularity: string
  squash_access: string
  development_quality: string
  competition_quality: string
  elite_support: string
  squash_tradition: string
}

export function countryV1FormDraftFromRecord(country: CountryV1Record): CountryV1FormDraft {
  return {
    name: country.name,
    notes: country.notes ?? '',
    area_km2: country.area_km2 == null ? '' : String(country.area_km2),
    region: country.region,
    travel_region: country.travel_region ?? '',
    court_count: country.court_count == null ? '' : String(country.court_count),
    squash_popularity: String(country.squash_popularity),
    squash_access: String(country.squash_access),
    development_quality: String(country.development_quality),
    competition_quality: String(country.competition_quality),
    elite_support: String(country.elite_support),
    squash_tradition: String(country.squash_tradition),
  }
}

function parseRating(value: string, field: CountryV1RatingField): CountryV1Rating {
  if (!/^[1-5]$/.test(value.trim())) {
    throw new Error(`${field} must be an integer from 1 to 5`)
  }
  return Number(value) as CountryV1Rating
}

function parseOptionalInteger(value: string, field: 'area_km2' | 'court_count'): number | null {
  const normalized = value.trim()
  if (normalized === '') return null
  if (!/^\d+$/.test(normalized)) {
    throw new Error(`${field} must be an integer`)
  }
  const parsed = Number(normalized)
  if (field === 'area_km2' && parsed <= 0) {
    throw new Error('area_km2 must be greater than 0')
  }
  return parsed
}

export function countryV1UpdatePayloadFromDraft(
  draft: CountryV1FormDraft,
  expectedPackageFingerprint?: string,
): WorldPackageCountryV1UpdatePayload {
  return {
    name: draft.name,
    notes: draft.notes === '' ? null : draft.notes,
    area_km2: parseOptionalInteger(draft.area_km2, 'area_km2'),
    region: draft.region,
    travel_region: draft.travel_region === '' ? null : draft.travel_region,
    court_count: parseOptionalInteger(draft.court_count, 'court_count'),
    squash_popularity: parseRating(draft.squash_popularity, 'squash_popularity'),
    squash_access: parseRating(draft.squash_access, 'squash_access'),
    development_quality: parseRating(draft.development_quality, 'development_quality'),
    competition_quality: parseRating(draft.competition_quality, 'competition_quality'),
    elite_support: parseRating(draft.elite_support, 'elite_support'),
    squash_tradition: parseRating(draft.squash_tradition, 'squash_tradition'),
    ...(expectedPackageFingerprint === undefined
      ? {}
      : { expected_package_fingerprint: expectedPackageFingerprint }),
  }
}

export function countryV1CreatePayloadFromDraft(
  draft: CountryV1FormDraft,
  code: string,
  populationByYear: Record<string, number>,
  expectedPackageFingerprint: string,
): WorldPackageCountryV1CreatePayload {
  const updatePayload = countryV1UpdatePayloadFromDraft(draft)
  return {
    ...updatePayload,
    code,
    population_by_year: populationByYear,
    expected_package_fingerprint: expectedPackageFingerprint,
  }
}

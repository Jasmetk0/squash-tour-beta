import type {
  WorldPackage,
  WorldPackageContinent,
  WorldPackageRegion,
  WorldPackageTravelRegion,
  WorldPackageValidation,
} from './types'

/** Canonical authored Country V1 rating accepted by the backend. */
export type CountryV1Rating = 1 | 2 | 3 | 4 | 5

/**
 * Frontend representation of the canonical Country V1 API response.
 *
 * Keep this contract aligned with src/beta_engine/api/country_v1_schemas.py.
 * Legacy country attributes intentionally do not belong here.
 */
export type CountryV1Record = {
  code: string
  name: string
  flag_asset: string | null
  region: string
  population: number
  area_km2: number | null
  default_population_year: number | null
  default_population: number | null
  population_by_year: Record<string, number | null> | null
  court_count: number | null
  travel_region: string | null
  notes: string | null

  squash_popularity: CountryV1Rating
  squash_access: CountryV1Rating
  development_quality: CountryV1Rating
  competition_quality: CountryV1Rating
  elite_support: CountryV1Rating
  squash_tradition: CountryV1Rating
}

export type CountriesV1ListResponse = {
  countries: CountryV1Record[]
}

export type CountriesV1DatasetResponse = {
  dataset_status: string | null
  countries: CountryV1Record[]
}

export type WorldPackageCountriesV1Response = {
  world_id: string
  world_name: string
  type: string
  source: string
  read_only: boolean
  country_count: number
  source_path: string
  countries: CountryV1Record[]
}

export type WorldPackageCountryV1Detail = {
  package: WorldPackage
  country: CountryV1Record
  region: WorldPackageRegion | null
  continent: WorldPackageContinent | null
  travel_region: WorldPackageTravelRegion | null
  source_path: string
}

export type WorldPackageCountryV1UpdatePayload = {
  name: string
  notes: string | null
  area_km2: number | null
  region: string
  travel_region: string | null
  court_count: number | null

  squash_popularity: CountryV1Rating
  squash_access: CountryV1Rating
  development_quality: CountryV1Rating
  competition_quality: CountryV1Rating
  elite_support: CountryV1Rating
  squash_tradition: CountryV1Rating

  expected_package_fingerprint?: string
}

export type WorldPackageCountryV1CreatePayload = Omit<
  WorldPackageCountryV1UpdatePayload,
  'expected_package_fingerprint'
> & {
  code: string
  population_by_year: Record<string, number>
  expected_package_fingerprint: string
}

export type WorldPackageCountryV1UpdateResponse = {
  country_detail: WorldPackageCountryV1Detail
  package: WorldPackage
  validation: WorldPackageValidation
}

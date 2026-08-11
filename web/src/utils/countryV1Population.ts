import type { WorldPackageCountryV1PopulationUpdatePayload } from '../api/countryV1'

export type CountryV1PopulationDraftRow = {
  year: string
  population: string
}

function parseYear(value: string): number {
  const normalized = value.trim()
  if (!/^\d{4}$/.test(normalized)) {
    throw new Error('Population year must be a four-digit integer')
  }
  const year = Number(normalized)
  if (year < 1955 || year > 2050) {
    throw new Error('Population year must be between 1955 and 2050')
  }
  return year
}

function parsePopulation(value: string): number {
  const normalized = value.trim()
  if (!/^\d+$/.test(normalized)) {
    throw new Error('Population must be a positive integer')
  }
  const population = Number(normalized)
  if (population <= 0) {
    throw new Error('Population must be a positive integer')
  }
  return population
}

export function countryV1PopulationPayloadFromRows(
  rows: CountryV1PopulationDraftRow[],
  expectedPackageFingerprint?: string,
): WorldPackageCountryV1PopulationUpdatePayload {
  if (rows.length === 0) {
    throw new Error('At least population year 2020 is required')
  }

  const valuesByYear: Record<string, number> = {}
  for (const row of rows) {
    const year = parseYear(row.year)
    const yearKey = String(year)
    if (Object.prototype.hasOwnProperty.call(valuesByYear, yearKey)) {
      throw new Error(`Population year ${yearKey} is already authored`)
    }
    valuesByYear[yearKey] = parsePopulation(row.population)
  }

  if (!Object.prototype.hasOwnProperty.call(valuesByYear, '2020')) {
    throw new Error('Population year 2020 is required')
  }

  return {
    values_by_year: Object.fromEntries(
      Object.entries(valuesByYear).sort(([left], [right]) => Number(left) - Number(right)),
    ),
    ...(expectedPackageFingerprint === undefined
      ? {}
      : { expected_package_fingerprint: expectedPackageFingerprint }),
  }
}

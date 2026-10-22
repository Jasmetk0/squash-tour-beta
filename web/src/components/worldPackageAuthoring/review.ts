/** Local checks mirror WorldPackageCountryV1 API and service contracts.
 * The backend still validates and owns every write and the semantic fingerprint.
 * Never derive an effective/interpolated population here. */
export type PopulationInput = { year: string; population: string }
export type ReviewChange = { field: string; before: string; after: string }

function required(raw: string, label: string, cs: boolean): string {
  if (!raw.trim()) throw new Error(cs ? `${label}: povinný údaj nesmí být prázdný.` : `${label}: this field is required.`)
  return raw.trim()
}

export function requiredName(raw: string, label: string, cs: boolean): string {
  return required(raw, label, cs)
}

export function parseInteger(raw: string, label: string, cs: boolean, min: number, max?: number, optional = false): number | null {
  if (!raw.trim() && optional) return null
  const value = required(raw, label, cs)
  if (!/^[+-]?\d+$/.test(value) || !Number.isSafeInteger(Number(value))) {
    throw new Error(cs ? `${label}: zadejte celé číslo.` : `${label}: enter a whole number.`)
  }
  const number = Number(value)
  if (number < min || (max !== undefined && number > max)) {
    const range = max === undefined ? `${min} nebo více` : `${min}–${max}`
    const enRange = max === undefined ? `at least ${min}` : `${min}–${max}`
    throw new Error(cs ? `${label}: povolený rozsah je ${range}.` : `${label}: allowed range is ${enRange}.`)
  }
  return number
}

export function parseRating(raw: string, label: string, cs: boolean, scale: 'country_ratings_1_5.v1' | 'country_ratings_1_10.v2'): number {
  const value = required(raw, label, cs)
  const number = Number(value)
  const maximum = scale === 'country_ratings_1_10.v2' ? 10 : 5
  if (!Number.isFinite(number) || number < 1 || number > maximum) {
    throw new Error(cs ? `${label}: zadejte číslo od 1 do ${maximum}.` : `${label}: enter a number from 1 to ${maximum}.`)
  }
  // The authored v2 API accepts at most one decimal. Legacy v1 intentionally does not impose this.
  if (maximum === 10 && !/^[+]?(?:\d+)(?:\.\d)?$/.test(value)) {
    throw new Error(cs ? `${label}: nejvýše jedno desetinné místo (tečka).` : `${label}: at most one decimal place (dot).`)
  }
  return number
}

export function parsePopulations(rows: PopulationInput[], cs: boolean): Record<string, number> {
  const result: Record<string, number> = {}
  for (const row of rows) {
    const year = parseInteger(row.year, cs ? 'Rok' : 'Year', cs, 1955, 2050)
    const population = parseInteger(row.population, cs ? 'Populace' : 'Population', cs, 1)
    if (year === null || population === null) throw new Error('Unreachable required population')
    if (Object.prototype.hasOwnProperty.call(result, year)) {
      throw new Error(cs ? `Rok ${year} je zadán vícekrát.` : `Year ${year} is entered more than once.`)
    }
    result[String(year)] = population
  }
  if (!Object.prototype.hasOwnProperty.call(result, '2020')) {
    throw new Error(cs ? 'Výchozí populační rok 2020 je povinný.' : 'Default population year 2020 is required.')
  }
  return result
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

export function fieldChanges(original: object, updated: object, fields: readonly string[]): ReviewChange[] {
  const old = original as Record<string, unknown>
  const next = updated as Record<string, unknown>
  return fields.filter(field => (old[field] ?? null) !== (next[field] ?? null))
    .map(field => ({ field: field.replace(/_/g, ' '), before: display(old[field]), after: display(next[field]) }))
}

export function populationChanges(original: Record<string, number | null> | null | undefined, next: Record<string, number>): ReviewChange[] {
  return [...new Set([...Object.keys(original ?? {}), ...Object.keys(next)])]
    .sort((a, b) => Number(a) - Number(b))
    .filter(year => ((original ?? {})[year] ?? null) !== (next[year] ?? null))
    .map(year => ({ field: year, before: display(original?.[year]), after: display(next[year]) }))
}

export function isFingerprintConflict(error: unknown): boolean {
  return typeof error === 'object' && error !== null &&
    'status' in error && (error as { status?: unknown }).status === 409
}

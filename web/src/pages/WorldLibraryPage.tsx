import type { FormEvent } from 'react'
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  cloneOfficialWorldPackage,
  createWorldPackageCountry,
  deleteWorldPackageCountry,
  getWorldPackage,
  getWorldPackageCountries,
  getWorldPackageCountry,
  getWorldPackageGeography,
  getWorldPackageValidation,
  listWorldPackages,
  updateWorldPackageCountry,
  updateWorldPackageCountryPopulation
} from '../api/client'
import { formatApiError } from '../utils/apiErrors'

type CountryV1 = {
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
  squash_popularity: number
  squash_access: number
  development_quality: number
  competition_quality: number
  elite_support: number
  squash_tradition: number
}

type PackageLike = {
  world_id: string
  name: string
  description: string
  type: 'official' | 'custom'
  source: string
  editable: boolean
  version: string
  fingerprint: string
  country_count: number
  validation_status: string
}

type GeographyLike = {
  regions: Array<{ code: string; name: string }>
  travel_regions: Array<{ code: string; name: string }>
}

const RATING_FIELDS = [
  ['squash_popularity', 'Squash Popularity'],
  ['squash_access', 'Squash Access'],
  ['development_quality', 'Development Quality'],
  ['competition_quality', 'Competition Quality'],
  ['elite_support', 'Elite Support'],
  ['squash_tradition', 'Squash Tradition']
] as const

type RatingField = (typeof RATING_FIELDS)[number][0]

type CountryFormState = {
  name: string
  notes: string
  area_km2: string
  region: string
  travel_region: string
  court_count: string
} & Record<RatingField, number>

function toForm(country: CountryV1): CountryFormState {
  return {
    name: country.name,
    notes: country.notes ?? '',
    area_km2: country.area_km2 == null ? '' : String(country.area_km2),
    region: country.region,
    travel_region: country.travel_region ?? '',
    court_count: country.court_count == null ? '' : String(country.court_count),
    squash_popularity: country.squash_popularity,
    squash_access: country.squash_access,
    development_quality: country.development_quality,
    competition_quality: country.competition_quality,
    elite_support: country.elite_support,
    squash_tradition: country.squash_tradition
  }
}

function emptyForm(): CountryFormState {
  return {
    name: '',
    notes: '',
    area_km2: '',
    region: '',
    travel_region: '',
    court_count: '',
    squash_popularity: 3,
    squash_access: 3,
    development_quality: 3,
    competition_quality: 3,
    elite_support: 3,
    squash_tradition: 3
  }
}

function toPayload(form: CountryFormState, fingerprint?: string) {
  return {
    name: form.name.trim(),
    notes: form.notes.trim() || null,
    area_km2: form.area_km2.trim() ? Number(form.area_km2) : null,
    region: form.region,
    travel_region: form.travel_region || null,
    court_count: form.court_count.trim() ? Number(form.court_count) : null,
    squash_popularity: form.squash_popularity,
    squash_access: form.squash_access,
    development_quality: form.development_quality,
    competition_quality: form.competition_quality,
    elite_support: form.elite_support,
    squash_tradition: form.squash_tradition,
    ...(fingerprint ? { expected_package_fingerprint: fingerprint } : {})
  }
}

function parsePopulationTimeline(text: string): Record<string, number> {
  const result: Record<string, number> = {}
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line) continue
    const [rawYear, rawValue] = line.split(/[=,:;\s]+/, 2)
    const year = Number(rawYear)
    const value = Number(rawValue)
    if (!Number.isInteger(year) || year < 1955 || year > 2050) throw new Error(`Invalid population year: ${rawYear}`)
    if (!Number.isInteger(value) || value <= 0) throw new Error(`Invalid population for ${year}`)
    result[String(year)] = value
  }
  if (!result['2020']) throw new Error('Population timeline must contain year 2020.')
  return result
}

function timelineText(country: CountryV1): string {
  const timeline = country.population_by_year ?? { 2020: country.population }
  return Object.entries(timeline)
    .filter((entry): entry is [string, number] => typeof entry[1] === 'number')
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([year, value]) => `${year}=${value}`)
    .join('\n')
}

function RatingInputs({ form, onChange, disabled = false }: { form: CountryFormState; onChange: (field: RatingField, value: number) => void; disabled?: boolean }) {
  return (
    <div className="form-grid">
      {RATING_FIELDS.map(([field, label]) => (
        <label key={field}>
          <span>{label} (1–5)</span>
          <input
            type="number"
            min={1}
            max={5}
            step={1}
            value={form[field]}
            disabled={disabled}
            onChange={(event) => onChange(field, Math.max(1, Math.min(5, Number(event.target.value))))}
          />
        </label>
      ))}
    </div>
  )
}

function CountryForm({ form, geography, setForm, disabled = false }: { form: CountryFormState; geography?: GeographyLike; setForm: (next: CountryFormState) => void; disabled?: boolean }) {
  const update = <K extends keyof CountryFormState>(key: K, value: CountryFormState[K]) => setForm({ ...form, [key]: value })
  return (
    <>
      <div className="form-grid">
        <label><span>Name</span><input value={form.name} disabled={disabled} onChange={(e) => update('name', e.target.value)} /></label>
        <label><span>Region</span>
          <select value={form.region} disabled={disabled} onChange={(e) => update('region', e.target.value)}>
            <option value="">Select region</option>
            {(geography?.regions ?? []).map((region) => <option key={region.code} value={region.code}>{region.name} ({region.code})</option>)}
          </select>
        </label>
        <label><span>Travel Region</span>
          <select value={form.travel_region} disabled={disabled} onChange={(e) => update('travel_region', e.target.value)}>
            <option value="">Inherited / none</option>
            {(geography?.travel_regions ?? []).map((region) => <option key={region.code} value={region.code}>{region.name} ({region.code})</option>)}
          </select>
        </label>
        <label><span>Area km²</span><input type="number" min={1} value={form.area_km2} disabled={disabled} onChange={(e) => update('area_km2', e.target.value)} /></label>
        <label><span>Court Count (factual data)</span><input type="number" min={0} value={form.court_count} disabled={disabled} onChange={(e) => update('court_count', e.target.value)} /></label>
      </div>
      <h3>Country Game Attributes V1</h3>
      <p className="muted">Six authored ratings only. Population, area and court count are factual data; Competitive Depth and country strength are derived by the engine.</p>
      <RatingInputs form={form} disabled={disabled} onChange={(field, value) => update(field, value)} />
      <label><span>Notes</span><textarea rows={3} value={form.notes} disabled={disabled} onChange={(e) => update('notes', e.target.value)} /></label>
    </>
  )
}

export function WorldLibraryPage(): JSX.Element {
  const queryClient = useQueryClient()
  const packagesQuery = useQuery({ queryKey: ['world-packages'], queryFn: listWorldPackages })
  const [cloneId, setCloneId] = useState('')
  const [cloneName, setCloneName] = useState('')
  const cloneMutation = useMutation({
    mutationFn: () => cloneOfficialWorldPackage({ new_world_id: cloneId.trim(), name: cloneName.trim(), dry_run: false }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['world-packages'] })
  })
  const packages = ((packagesQuery.data as any)?.packages ?? []) as PackageLike[]

  return (
    <div className="page-stack">
      <header><p className="eyebrow">Global Admin · World</p><h1>World Packages</h1><p>Built-in packages are read-only sources. Custom packages are editable local worlds.</p></header>
      {packagesQuery.isError && <p className="error">{formatApiError(packagesQuery.error)}</p>}
      <section className="panel">
        <table>
          <thead><tr><th>Package</th><th>Type</th><th>Countries</th><th>Editable</th><th>Validation</th></tr></thead>
          <tbody>{packages.map((item) => (
            <tr key={item.world_id}>
              <td><Link to={`/admin/world/library/${item.world_id}`}>{item.name}</Link><div className="muted">{item.world_id}</div></td>
              <td>{item.type}</td><td>{item.country_count}</td><td>{item.editable ? 'Yes' : 'No'}</td><td>{item.validation_status}</td>
            </tr>
          ))}</tbody>
        </table>
      </section>
      <section className="panel">
        <h2>Clone Official FAX World</h2>
        <p className="muted">Creates an independent editable Custom World Package.</p>
        <div className="form-grid">
          <label><span>New world id</span><input value={cloneId} onChange={(e) => setCloneId(e.target.value)} placeholder="my_world" /></label>
          <label><span>Name</span><input value={cloneName} onChange={(e) => setCloneName(e.target.value)} placeholder="My World" /></label>
        </div>
        <button disabled={!cloneId.trim() || !cloneName.trim() || cloneMutation.isPending} onClick={() => cloneMutation.mutate()}>Create editable clone</button>
        {cloneMutation.isError && <p className="error">{formatApiError(cloneMutation.error)}</p>}
      </section>
    </div>
  )
}

export function WorldLibraryDetailPage(): JSX.Element {
  const { worldId = '' } = useParams()
  const packageQuery = useQuery({ queryKey: ['world-package', worldId], queryFn: () => getWorldPackage(worldId), enabled: Boolean(worldId) })
  const validationQuery = useQuery({ queryKey: ['world-package-validation', worldId], queryFn: () => getWorldPackageValidation(worldId), enabled: Boolean(worldId) })
  const item = packageQuery.data as unknown as PackageLike | undefined
  const validation = validationQuery.data as any
  if (packageQuery.isLoading) return <p>Loading World Package…</p>
  if (packageQuery.isError || !item) return <p className="error">{formatApiError(packageQuery.error)}</p>
  return (
    <div className="page-stack">
      <p><Link to="/admin/world/library">← World Packages</Link></p>
      <header><p className="eyebrow">{item.type} · {item.editable ? 'Editable' : 'Read-only'}</p><h1>{item.name}</h1><p>{item.description}</p></header>
      <section className="panel">
        <p><strong>ID:</strong> {item.world_id}</p><p><strong>Version:</strong> {item.version}</p><p><strong>Countries:</strong> {item.country_count}</p>
        <p><strong>Validation:</strong> {validation?.status ?? item.validation_status}</p>
        <Link to={`/admin/world/library/${item.world_id}/countries`}>Open countries →</Link>
      </section>
    </div>
  )
}

export function WorldPackageCountriesPage(): JSX.Element {
  const { worldId = '' } = useParams()
  const packageQuery = useQuery({ queryKey: ['world-package', worldId], queryFn: () => getWorldPackage(worldId), enabled: Boolean(worldId) })
  const countriesQuery = useQuery({ queryKey: ['world-package-countries', worldId], queryFn: () => getWorldPackageCountries(worldId), enabled: Boolean(worldId) })
  const item = packageQuery.data as unknown as PackageLike | undefined
  const countries = (((countriesQuery.data as any)?.countries ?? []) as CountryV1[])
  return (
    <div className="page-stack">
      <p><Link to={`/admin/world/library/${worldId}`}>← World Package</Link></p>
      <header><h1>{item?.name ?? worldId} · Countries</h1><p>Country Game Attributes V1 are six 1–5 ratings. Current depth/strength is derived, not authored.</p></header>
      {item?.editable && <p><Link to={`/admin/world/library/${worldId}/countries/new`}>+ Create country</Link></p>}
      {countriesQuery.isError && <p className="error">{formatApiError(countriesQuery.error)}</p>}
      <section className="panel" style={{ overflowX: 'auto' }}>
        <table>
          <thead><tr><th>Country</th><th>Population</th>{RATING_FIELDS.map(([, label]) => <th key={label}>{label}</th>)}</tr></thead>
          <tbody>{countries.map((country) => (
            <tr key={country.code}>
              <td><Link to={`/admin/world/library/${worldId}/countries/${country.code}`}>{country.name}</Link><div className="muted">{country.code}</div></td>
              <td>{country.population.toLocaleString()}</td>
              {RATING_FIELDS.map(([field]) => <td key={field}>{country[field]}</td>)}
            </tr>
          ))}</tbody>
        </table>
      </section>
    </div>
  )
}

export function WorldPackageCountryCreatePage(): JSX.Element {
  const { worldId = '' } = useParams()
  const navigate = useNavigate()
  const [code, setCode] = useState('')
  const [form, setForm] = useState<CountryFormState>(emptyForm())
  const [population, setPopulation] = useState('2020=1000000')
  const [localError, setLocalError] = useState('')
  const packageQuery = useQuery({ queryKey: ['world-package', worldId], queryFn: () => getWorldPackage(worldId), enabled: Boolean(worldId) })
  const geographyQuery = useQuery({ queryKey: ['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), enabled: Boolean(worldId) })
  const item = packageQuery.data as unknown as PackageLike | undefined
  const geography = geographyQuery.data as unknown as GeographyLike | undefined
  const mutation = useMutation({
    mutationFn: async () => {
      if (!item) throw new Error('World Package is not loaded.')
      const payload = { code: code.trim().toUpperCase(), ...toPayload(form), population_by_year: parsePopulationTimeline(population), expected_package_fingerprint: item.fingerprint }
      return createWorldPackageCountry(worldId, payload as any)
    },
    onSuccess: (result: any) => navigate(`/admin/world/library/${worldId}/countries/${result.country_detail.country.code}`)
  })
  const submit = (event: FormEvent) => {
    event.preventDefault(); setLocalError('')
    try { parsePopulationTimeline(population); mutation.mutate() } catch (error) { setLocalError(error instanceof Error ? error.message : String(error)) }
  }
  if (item && !item.editable) return <p className="error">This built-in World Package is read-only.</p>
  return (
    <form className="page-stack" onSubmit={submit}>
      <p><Link to={`/admin/world/library/${worldId}/countries`}>← Countries</Link></p>
      <header><h1>Create Country</h1></header>
      <section className="panel">
        <label><span>3-letter code</span><input value={code} maxLength={3} onChange={(e) => setCode(e.target.value.toUpperCase())} /></label>
        <CountryForm form={form} geography={geography} setForm={setForm} />
        <label><span>Population timeline (one `YEAR=VALUE` per line; 2020 required)</span><textarea rows={8} value={population} onChange={(e) => setPopulation(e.target.value)} /></label>
        {(localError || mutation.isError) && <p className="error">{localError || formatApiError(mutation.error)}</p>}
        <button type="submit" disabled={mutation.isPending || code.trim().length !== 3 || !form.name.trim() || !form.region}>Create country</button>
      </section>
    </form>
  )
}

export function WorldPackageCountryDetailPage(): JSX.Element {
  const { worldId = '', countryCode = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const detailQuery = useQuery({ queryKey: ['world-package-country', worldId, countryCode], queryFn: () => getWorldPackageCountry(worldId, countryCode), enabled: Boolean(worldId && countryCode) })
  const geographyQuery = useQuery({ queryKey: ['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), enabled: Boolean(worldId) })
  const detail = detailQuery.data as any
  const country = detail?.country as CountryV1 | undefined
  const item = detail?.package as PackageLike | undefined
  const geography = geographyQuery.data as unknown as GeographyLike | undefined
  const initialForm = useMemo(() => country ? toForm(country) : null, [country])
  const [draft, setDraft] = useState<CountryFormState | null>(null)
  const [populationDraft, setPopulationDraft] = useState<string | null>(null)
  const [localError, setLocalError] = useState('')
  const form = draft ?? initialForm
  const population = populationDraft ?? (country ? timelineText(country) : '')

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['world-package-country', worldId, countryCode] }),
      queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }),
      queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }),
      queryClient.invalidateQueries({ queryKey: ['world-packages'] })
    ])
  }
  const updateMutation = useMutation({
    mutationFn: () => updateWorldPackageCountry(worldId, countryCode, { ...toPayload(form!), expected_package_fingerprint: item!.fingerprint } as any),
    onSuccess: async () => { setDraft(null); await refresh() }
  })
  const populationMutation = useMutation({
    mutationFn: () => updateWorldPackageCountryPopulation(worldId, countryCode, { values_by_year: parsePopulationTimeline(population), expected_package_fingerprint: item!.fingerprint } as any),
    onSuccess: async () => { setPopulationDraft(null); await refresh() }
  })
  const deleteMutation = useMutation({
    mutationFn: () => deleteWorldPackageCountry(worldId, countryCode, item!.fingerprint),
    onSuccess: async () => { await refresh(); navigate(`/admin/world/library/${worldId}/countries`) }
  })

  if (detailQuery.isLoading) return <p>Loading country…</p>
  if (detailQuery.isError || !country || !item || !form) return <p className="error">{formatApiError(detailQuery.error)}</p>

  return (
    <div className="page-stack">
      <p><Link to={`/admin/world/library/${worldId}/countries`}>← Countries</Link></p>
      <header><p className="eyebrow">{country.code} · {item.editable ? 'Editable custom package' : 'Read-only built-in package'}</p><h1>{country.name}</h1></header>
      <section className="panel">
        <CountryForm form={form} geography={geography} setForm={setDraft} disabled={!item.editable} />
        {item.editable && <button disabled={updateMutation.isPending} onClick={() => updateMutation.mutate()}>Save country attributes</button>}
        {updateMutation.isError && <p className="error">{formatApiError(updateMutation.error)}</p>}
      </section>
      <section className="panel">
        <h2>Population Timeline</h2>
        <p className="muted">Factual data. One `YEAR=VALUE` per line; year 2020 is required by the current storage contract.</p>
        <textarea rows={10} value={population} disabled={!item.editable} onChange={(e) => setPopulationDraft(e.target.value)} />
        {item.editable && <button disabled={populationMutation.isPending} onClick={() => { setLocalError(''); try { parsePopulationTimeline(population); populationMutation.mutate() } catch (error) { setLocalError(error instanceof Error ? error.message : String(error)) } }}>Save population</button>}
        {(localError || populationMutation.isError) && <p className="error">{localError || formatApiError(populationMutation.error)}</p>}
      </section>
      <section className="panel">
        <h2>Derived concepts</h2>
        <p>Effective Squash Pool, Competitive Depth, Talent Discovery Rate, Professional Conversion Rate and Current Country Strength are engine-derived values — they are deliberately not editable country ratings.</p>
      </section>
      {item.editable && <section className="panel"><h2>Delete country</h2><p>This removes the country from this Custom World Package only.</p><button disabled={deleteMutation.isPending} onClick={() => { if (window.confirm(`Delete ${country.name} (${country.code}) from this package?`)) deleteMutation.mutate() }}>Delete country</button>{deleteMutation.isError && <p className="error">{formatApiError(deleteMutation.error)}</p>}</section>}
    </div>
  )
}

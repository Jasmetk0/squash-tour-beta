import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { getWorldPackage, getWorldPackageGeography } from '../api/client'
import { createWorldPackageCountryV1 } from '../api/countryV1Client'
import {
  COUNTRY_V1_RATING_FIELDS,
  countryV1CreatePayloadFromDraft,
  type CountryV1FormDraft,
  type CountryV1RatingField,
} from '../utils/countryV1Form'
import { formatApiError } from '../utils/apiErrors'

const DEFAULT_DRAFT: CountryV1FormDraft = {
  name: '',
  notes: '',
  area_km2: '',
  region: '',
  travel_region: '',
  court_count: '0',
  squash_popularity: '3',
  squash_access: '3',
  development_quality: '3',
  competition_quality: '3',
  elite_support: '3',
  squash_tradition: '3',
}

type PopulationRow = { id: number, year: string, population: string }

export function CountryV1RatingsFieldset({
  draft,
  onChange,
}: {
  draft: CountryV1FormDraft
  onChange: (key: CountryV1RatingField, value: string) => void
}): JSX.Element {
  return (
    <fieldset>
      <legend>Squash / Country strength</legend>
      {COUNTRY_V1_RATING_FIELDS.map(({ key, label }) => (
        <label key={key}>
          {label}
          <input
            type="number"
            required
            min="1"
            max="5"
            step="1"
            value={draft[key]}
            onChange={(event) => onChange(key, event.target.value)}
          />
        </label>
      ))}
      <label>
        Court Count
        <input
          type="number"
          min="0"
          step="1"
          value={draft.court_count}
          onChange={(event) => onChangeCourtCount(event.target.value)}
        />
      </label>
    </fieldset>
  )

  function onChangeCourtCount(value: string): void {
    // Keep the fieldset callback narrowly typed for authored ratings; court count
    // is factual data and is handled through the draft object by the caller.
    const ratingAwareCallback = onChange as unknown as (key: keyof CountryV1FormDraft, value: string) => void
    ratingAwareCallback('court_count', value)
  }
}

export function WorldPackageCountryCreateV1Page(): JSX.Element {
  const { worldId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [draft, setDraft] = useState<CountryV1FormDraft>(DEFAULT_DRAFT)
  const [populations, setPopulations] = useState<PopulationRow[]>([
    { id: 0, year: '2020', population: '' },
  ])
  const [validationError, setValidationError] = useState('')

  const packageQuery = useQuery({
    queryKey: ['world-package', worldId],
    queryFn: () => getWorldPackage(worldId),
    enabled: Boolean(worldId),
    retry: false,
  })
  const geographyQuery = useQuery({
    queryKey: ['world-package-geography', worldId],
    queryFn: () => getWorldPackageGeography(worldId),
    enabled: Boolean(worldId),
    retry: false,
  })

  const mutation = useMutation({
    mutationFn: (payload: Parameters<typeof createWorldPackageCountryV1>[1]) =>
      createWorldPackageCountryV1(worldId, payload),
    onSuccess: async (response) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-validation', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-packages'] }),
      ])
      navigate(
        `/admin/world/library/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(response.country_detail.country.code)}`,
      )
    },
  })

  const pkg = packageQuery.data
  const allowed = pkg?.type === 'custom' && pkg.source === 'custom_config' && pkg.editable
  const sortedPopulations = [...populations].sort((left, right) => Number(left.year) - Number(right.year))

  function setDraftValue(key: keyof CountryV1FormDraft, value: string): void {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (!pkg || !allowed) return

    const years = populations.map((row) => row.year)
    const duplicate = years.find((year, index) => year !== '' && years.indexOf(year) !== index)
    if (duplicate) {
      setValidationError(`Year ${duplicate} is already authored.`)
      return
    }
    if (!years.includes('2020')) {
      setValidationError('Population year 2020 is required.')
      return
    }

    try {
      const populationByYear = Object.fromEntries(
        sortedPopulations.map((row) => [row.year, Number(row.population)]),
      )
      const payload = countryV1CreatePayloadFromDraft(
        draft,
        code,
        populationByYear,
        pkg.fingerprint,
      )
      setValidationError('')
      mutation.mutate(payload)
    } catch (error) {
      setValidationError(error instanceof Error ? error.message : String(error))
    }
  }

  if (packageQuery.isLoading || geographyQuery.isLoading) {
    return <p className="status">Loading country form...</p>
  }

  if (packageQuery.error) {
    return <p className="error">Failed to load World Package: {formatApiError(packageQuery.error)}</p>
  }
  if (geographyQuery.error) {
    return <p className="error">Failed to load geography: {formatApiError(geographyQuery.error)}</p>
  }

  if (!allowed) {
    return (
      <section className="panel">
        <p className="error">Countries can only be created in an editable Custom World source.</p>
      </section>
    )
  }

  return (
    <section className="panel">
      <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries`}>Back to countries</Link></p>
      <h2>Add country</h2>
      <form onSubmit={submit}>
        {(validationError || mutation.error) && (
          <p className="error" role="alert">
            {validationError || formatApiError(mutation.error)}
          </p>
        )}

        <fieldset>
          <legend>Identity</legend>
          <label>
            Code
            <input
              required
              pattern="[A-Z]{3}"
              maxLength={3}
              value={code}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
            />
          </label>
          <label>
            Name
            <input required value={draft.name} onChange={(event) => setDraftValue('name', event.target.value)} />
          </label>
          <label>
            Notes
            <textarea value={draft.notes} onChange={(event) => setDraftValue('notes', event.target.value)} />
          </label>
          <label>
            Area km²
            <input
              type="number"
              min="1"
              step="1"
              value={draft.area_km2}
              onChange={(event) => setDraftValue('area_km2', event.target.value)}
            />
          </label>
        </fieldset>

        <fieldset>
          <legend>Geography</legend>
          <label>
            Region
            <select required value={draft.region} onChange={(event) => setDraftValue('region', event.target.value)}>
              <option value="">Select region</option>
              {geographyQuery.data?.regions.map((item) => (
                <option key={item.code} value={item.code}>{item.name} ({item.code})</option>
              ))}
            </select>
          </label>
          <label>
            Travel Region
            <select value={draft.travel_region} onChange={(event) => setDraftValue('travel_region', event.target.value)}>
              <option value="">None</option>
              {geographyQuery.data?.travel_regions.map((item) => (
                <option key={item.code} value={item.code}>{item.name} ({item.code})</option>
              ))}
            </select>
          </label>
        </fieldset>

        <fieldset>
          <legend>Population</legend>
          {sortedPopulations.map((row) => (
            <div key={row.id}>
              <input
                aria-label={`Population year ${row.id === 0 ? '2020' : row.id}`}
                type="number"
                min="1955"
                max="2050"
                required
                readOnly={row.year === '2020'}
                value={row.year}
                onChange={(event) => setPopulations((rows) => rows.map((item) =>
                  item.id === row.id ? { ...item, year: event.target.value } : item,
                ))}
              />
              <input
                aria-label={`Population value ${row.year || row.id}`}
                type="number"
                min="1"
                step="1"
                required
                value={row.population}
                onChange={(event) => setPopulations((rows) => rows.map((item) =>
                  item.id === row.id ? { ...item, population: event.target.value } : item,
                ))}
              />
              {row.year !== '2020' && (
                <button
                  type="button"
                  onClick={() => setPopulations((rows) => rows.filter((item) => item.id !== row.id))}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() => setPopulations((rows) => [
              ...rows,
              { id: Math.max(...rows.map((row) => row.id)) + 1, year: '', population: '' },
            ])}
          >
            + Add authored year
          </button>
        </fieldset>

        <CountryV1RatingsFieldset
          draft={draft}
          onChange={(key, value) => setDraftValue(key, value)}
        />

        <p>
          <button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? 'Saving…' : 'Save country'}
          </button>
        </p>
      </form>
    </section>
  )
}

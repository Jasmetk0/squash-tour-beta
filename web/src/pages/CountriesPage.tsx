import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useMemo, useState } from 'react'

import {
  ApiError,
  createCountry,
  deleteCountry,
  getCountriesMetadata,
  listCountries,
  updateCountry
} from '../api/client'
import type { CountryRecord, CountryUpsertPayload } from '../api/types'
import { EmptyState, PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'

type Mode = 'create' | 'edit'

type FormState = CountryUpsertPayload

const EMPTY_FORM: FormState = {
  code: '',
  name: '',
  flag_asset: '',
  region: '',
  population: 1,
  wealth_support: 3,
  squash_popularity: 3,
  squash_tradition: 3,
  system_quality: 3
}

function normalizeCode(value: string): string {
  return value.toUpperCase().slice(0, 3)
}

export function CountriesPage(): JSX.Element {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<Mode>('create')
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const countriesQuery = useQuery({ queryKey: ['countries-list'], queryFn: listCountries, retry: false })
  const metadataQuery = useQuery({ queryKey: ['countries-metadata'], queryFn: getCountriesMetadata, retry: false })

  const sortedCountries = useMemo(
    () => [...(countriesQuery.data?.countries ?? [])].sort((left, right) => left.code.localeCompare(right.code)),
    [countriesQuery.data?.countries]
  )

  const refetchAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['countries-list'] }),
      queryClient.invalidateQueries({ queryKey: ['countries-metadata'] })
    ])
  }

  const createMutation = useMutation({
    mutationFn: createCountry,
    onSuccess: async (created) => {
      setSubmitSuccess(`Country ${created.code} created.`)
      setSubmitError(null)
      setSelectedCode(created.code)
      setMode('edit')
      setForm({ ...created, flag_asset: created.flag_asset ?? '' })
      await refetchAll()
    },
    onError: (error) => {
      setSubmitSuccess(null)
      setSubmitError(`Create failed: ${formatApiError(error)}`)
    }
  })

  const updateMutation = useMutation({
    mutationFn: ({ code, payload }: { code: string; payload: CountryUpsertPayload }) => updateCountry(code, payload),
    onSuccess: async (updated) => {
      setSubmitSuccess(`Country ${updated.code} updated.`)
      setSubmitError(null)
      setSelectedCode(updated.code)
      setForm({ ...updated, flag_asset: updated.flag_asset ?? '' })
      await refetchAll()
    },
    onError: (error) => {
      setSubmitSuccess(null)
      setSubmitError(`Update failed: ${formatApiError(error)}`)
    }
  })

  const deleteMutation = useMutation({
    mutationFn: deleteCountry,
    onSuccess: async (_, code) => {
      setDeleteError(null)
      setSubmitSuccess(`Country ${code} deleted.`)
      setSubmitError(null)
      setSelectedCode(null)
      setMode('create')
      setForm(EMPTY_FORM)
      await refetchAll()
    },
    onError: (error) => {
      setSubmitSuccess(null)
      setDeleteError(`Delete failed: ${formatApiError(error)}`)
    }
  })

  const onSelect = (country: CountryRecord) => {
    setMode('edit')
    setSelectedCode(country.code)
    setForm({ ...country, flag_asset: country.flag_asset ?? '' })
    setSubmitError(null)
    setSubmitSuccess(null)
    setDeleteError(null)
  }

  const onDuplicate = (country: CountryRecord) => {
    setMode('create')
    setSelectedCode(null)
    setForm({
      ...country,
      code: '',
      name: `${country.name} Copy`,
      flag_asset: country.flag_asset ?? ''
    })
    setSubmitError(null)
    setSubmitSuccess('Country duplicated into create form. Set a unique 3-letter code before saving.')
  }

  const onResetCreate = () => {
    setMode('create')
    setSelectedCode(null)
    setForm(EMPTY_FORM)
    setSubmitError(null)
    setSubmitSuccess(null)
    setDeleteError(null)
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitError(null)
    setSubmitSuccess(null)
    const payload: CountryUpsertPayload = {
      ...form,
      code: normalizeCode(form.code),
      name: form.name.trim(),
      region: form.region.trim(),
      flag_asset: form.flag_asset?.trim() ? form.flag_asset.trim() : null
    }

    if (mode === 'create') {
      createMutation.mutate(payload)
      return
    }

    if (!selectedCode) {
      setSubmitError('Select a country before update.')
      return
    }
    updateMutation.mutate({ code: selectedCode, payload })
  }

  const onDelete = () => {
    if (!selectedCode) return
    if (!window.confirm(`Delete country ${selectedCode}?`)) return
    deleteMutation.mutate(selectedCode)
  }

  const busy = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending

  return (
    <section className="panel">
      <PageIntro
        title="Countries Editor"
        subtitle="Manage country data directly in-app; changes are written to canonical runtime countries JSON."
      />

      <SectionCard title="Dataset status">
        {metadataQuery.isLoading ? <p className="status">Loading dataset metadata…</p> : null}
        {metadataQuery.isError ? <p className="error">Metadata unavailable: {formatApiError(metadataQuery.error)}</p> : null}
        {metadataQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Dataset status', value: metadataQuery.data.dataset_status ?? 'unset' },
                { label: 'Country count', value: metadataQuery.data.country_count }
              ]}
            />
            <p className="status">Source path: {metadataQuery.data.source_path}</p>
            <p className="status">
              Current saves affect future generation workflows; existing historical runs are not auto-regenerated by this page.
            </p>
          </>
        ) : null}
      </SectionCard>

      <div className="grid">
        <SectionCard title="Countries list">
          {countriesQuery.isLoading ? <p className="status">Loading countries…</p> : null}
          {countriesQuery.isError ? <p className="error">Countries unavailable: {formatApiError(countriesQuery.error)}</p> : null}
          {!countriesQuery.isLoading && !countriesQuery.isError && sortedCountries.length === 0 ? (
            <EmptyState message="No countries configured. Use the form to create the first country." />
          ) : null}
          {!countriesQuery.isLoading && !countriesQuery.isError && sortedCountries.length > 0 ? (
            <table aria-label="Countries table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Region</th>
                  <th>Population</th>
                  <th>Wealth</th>
                  <th>Popularity</th>
                  <th>Tradition</th>
                  <th>System</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedCountries.map((country) => (
                  <tr key={country.code}>
                    <td>{country.code}</td>
                    <td>{country.name}</td>
                    <td>{country.region}</td>
                    <td>{country.population.toLocaleString()}</td>
                    <td>{country.wealth_support}</td>
                    <td>{country.squash_popularity}</td>
                    <td>{country.squash_tradition}</td>
                    <td>{country.system_quality}</td>
                    <td>
                      <button type="button" onClick={() => onSelect(country)} disabled={busy}>
                        Edit
                      </button>{' '}
                      <button type="button" onClick={() => onDuplicate(country)} disabled={busy}>
                        Duplicate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </SectionCard>

        <SectionCard title={mode === 'create' ? 'Create country' : `Edit country ${selectedCode ?? ''}`}>
          <form onSubmit={onSubmit}>
            <div className="grid">
              <label>
                Code (3 letters)
                <input
                  value={form.code}
                  onChange={(event) => setForm((current) => ({ ...current, code: normalizeCode(event.target.value) }))}
                  maxLength={3}
                  required
                />
              </label>
              <label>
                Name
                <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required />
              </label>
              <label>
                Flag asset (optional)
                <input
                  value={form.flag_asset ?? ''}
                  onChange={(event) => setForm((current) => ({ ...current, flag_asset: event.target.value }))}
                />
              </label>
              <label>
                Region
                <input
                  value={form.region}
                  onChange={(event) => setForm((current) => ({ ...current, region: event.target.value }))}
                  required
                />
              </label>
              <label>
                Population
                <input
                  type="number"
                  min={1}
                  value={form.population}
                  onChange={(event) => setForm((current) => ({ ...current, population: Number(event.target.value) }))}
                  required
                />
              </label>
              <label>
                Wealth support (1..5)
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={form.wealth_support}
                  onChange={(event) => setForm((current) => ({ ...current, wealth_support: Number(event.target.value) }))}
                  required
                />
              </label>
              <label>
                Squash popularity (1..5)
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={form.squash_popularity}
                  onChange={(event) => setForm((current) => ({ ...current, squash_popularity: Number(event.target.value) }))}
                  required
                />
              </label>
              <label>
                Squash tradition (1..5)
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={form.squash_tradition}
                  onChange={(event) => setForm((current) => ({ ...current, squash_tradition: Number(event.target.value) }))}
                  required
                />
              </label>
              <label>
                System quality (1..5)
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={form.system_quality}
                  onChange={(event) => setForm((current) => ({ ...current, system_quality: Number(event.target.value) }))}
                  required
                />
              </label>
            </div>

            <div className="dashboard-actions-row">
              <button type="submit" disabled={busy}>
                {mode === 'create'
                  ? createMutation.isPending
                    ? 'Creating…'
                    : 'Create country'
                  : updateMutation.isPending
                    ? 'Saving…'
                    : 'Save changes'}
              </button>
              <button type="button" onClick={onResetCreate} disabled={busy}>
                New country form
              </button>
              <button type="button" onClick={onDelete} disabled={busy || mode !== 'edit' || !selectedCode}>
                {deleteMutation.isPending ? 'Deleting…' : 'Delete country'}
              </button>
            </div>
          </form>

          {submitSuccess ? <p className="status">{submitSuccess}</p> : null}
          {submitError ? <p className="error">{submitError}</p> : null}
          {deleteError ? <p className="error">{deleteError}</p> : null}

          {submitError && submitError.includes('422') ? (
            <p className="error">Validation failed. Check required fields and 1..5 factor ranges.</p>
          ) : null}
          {submitError ? (
            <p className="status">
              {submitError.includes('already exists')
                ? 'Country code must be unique.'
                : submitError.includes('422')
                  ? 'Backend validation rejected the payload.'
                  : 'Request failed; inspect API response.'}
            </p>
          ) : null}
        </SectionCard>
      </div>
    </section>
  )
}

function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.status} ${error.message}`
  }
  return String(error)
}

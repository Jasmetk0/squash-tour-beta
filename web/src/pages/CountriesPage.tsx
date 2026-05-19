import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChangeEvent, FormEvent, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  ApiError,
  createCountry,
  deleteCountry,
  exportCountriesCsv,
  getCountriesMetadata,
  importCountries,
  listCountries,
  updateCountry
} from '../api/client'
import type { CountriesImportResponse, CountryRecord, CountryUpsertPayload } from '../api/types'
import { EmptyState, SummaryPills } from '../components/RunScopedUi'

type Mode = 'create' | 'edit'
type SortKey =
  | 'code'
  | 'name'
  | 'region'
  | 'population'
  | 'wealth_support'
  | 'squash_popularity'
  | 'squash_tradition'
  | 'system_quality'
  | 'competition_density'
  | 'federation_quality'
  | 'court_count'
  | 'travel_region'
type SortDirection = 'asc' | 'desc'
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
  system_quality: 3,
  competition_density: 3,
  federation_quality: 3,
  court_count: null,
  travel_region: '',
  notes: '',
  style_dna: {}
}

const COMPACT_NUMBER = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1
})

function normalizeCode(value: string): string {
  return value.toUpperCase().slice(0, 3)
}

function formatStyleDna(styleDna: Record<string, number>): string {
  return JSON.stringify(styleDna ?? {}, null, 2)
}

function formatPopulation(value: number): string {
  return COMPACT_NUMBER.format(value)
}

function countryToForm(country: CountryRecord): FormState {
  return {
    ...country,
    flag_asset: country.flag_asset ?? '',
    competition_density: country.competition_density ?? 3,
    federation_quality: country.federation_quality ?? country.system_quality,
    court_count: country.court_count ?? null,
    travel_region: country.travel_region ?? country.region,
    notes: country.notes ?? '',
    style_dna: country.style_dna ?? {}
  }
}

export function CountriesPage(): JSX.Element {
  const queryClient = useQueryClient()

  const [mode, setMode] = useState<Mode>('create')
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [showImportPanel, setShowImportPanel] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [regionFilter, setRegionFilter] = useState('all')
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [styleDnaText, setStyleDnaText] = useState('{}')
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const [importCsvText, setImportCsvText] = useState('')
  const [importResult, setImportResult] = useState<CountriesImportResponse | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const [importFileName, setImportFileName] = useState<string | null>(null)

  const countriesQuery = useQuery({ queryKey: ['countries-list'], queryFn: listCountries, retry: false })
  const metadataQuery = useQuery({ queryKey: ['countries-metadata'], queryFn: getCountriesMetadata, retry: false })

  const countries = countriesQuery.data?.countries ?? []

  const regionOptions = useMemo(
    () => ['all', ...new Set(countries.map((country) => country.region).filter(Boolean).sort((a, b) => a.localeCompare(b)))],
    [countries]
  )

  const filteredCountries = useMemo(() => {
    const text = searchText.trim().toLowerCase()

    return countries
      .filter((country) => {
        if (regionFilter !== 'all' && country.region !== regionFilter) {
          return false
        }

        if (!text) {
          return true
        }

        return (
          country.code.toLowerCase().includes(text) ||
          country.name.toLowerCase().includes(text) ||
          country.region.toLowerCase().includes(text)
        )
      })
      .sort((left, right) => {
        const compareText = (leftValue: string, rightValue: string) => leftValue.localeCompare(rightValue)
        const compareNumber = (leftValue: number, rightValue: number) => leftValue - rightValue

        let result = 0
        switch (sortKey) {
          case 'code':
            result = compareText(left.code, right.code)
            break
          case 'name':
            result = compareText(left.name, right.name)
            break
          case 'region':
            result = compareText(left.region, right.region) || compareText(left.name, right.name)
            break
          case 'population':
            result = compareNumber(left.population, right.population)
            break
          case 'wealth_support':
            result = compareNumber(left.wealth_support, right.wealth_support)
            break
          case 'squash_popularity':
            result = compareNumber(left.squash_popularity, right.squash_popularity)
            break
          case 'squash_tradition':
            result = compareNumber(left.squash_tradition, right.squash_tradition)
            break
          case 'system_quality':
            result = compareNumber(left.system_quality, right.system_quality)
            break
          case 'competition_density':
            result = compareNumber(left.competition_density ?? 0, right.competition_density ?? 0)
            break
          case 'federation_quality':
            result = compareNumber(left.federation_quality ?? left.system_quality, right.federation_quality ?? right.system_quality)
            break
          case 'court_count':
            if (left.court_count == null && right.court_count == null) {
              result = 0
            } else if (left.court_count == null) {
              result = 1
            } else if (right.court_count == null) {
              result = -1
            } else {
              result = compareNumber(left.court_count, right.court_count)
            }
            break
          case 'travel_region':
            result = compareText(left.travel_region ?? left.region, right.travel_region ?? right.region)
            break
        }

        if (result === 0) {
          result = compareText(left.name, right.name)
        }

        return sortDirection === 'asc' ? result : -result
      })
  }, [countries, regionFilter, searchText, sortDirection, sortKey])


  const onSortHeaderClick = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }

    setSortKey(key)
    setSortDirection(key === 'population' ? 'desc' : 'asc')
  }

  const getSortIndicator = (key: SortKey) => {
    if (sortKey !== key) return '↕'
    return sortDirection === 'asc' ? '↑' : '↓'
  }

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
      setForm(countryToForm(created))
      setStyleDnaText(formatStyleDna(created.style_dna ?? {}))
      setDrawerOpen(true)
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
      setForm(countryToForm(updated))
      setStyleDnaText(formatStyleDna(updated.style_dna ?? {}))
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
      setStyleDnaText('{}')
      setDrawerOpen(false)
      await refetchAll()
    },
    onError: (error) => {
      setSubmitSuccess(null)
      setDeleteError(`Delete failed: ${formatApiError(error)}`)
    }
  })

  const importMutation = useMutation({
    mutationFn: importCountries,
    onSuccess: async (result) => {
      setImportResult(result)
      setImportError(null)
      if (result.ok && !result.dry_run) {
        setSubmitSuccess(
          `Countries import complete. Imported ${result.summary.total_records} records (${result.summary.new_records} new, ${result.summary.updated_records} updated).`
        )
        await refetchAll()
      }
    },
    onError: (error) => {
      setImportResult(null)
      setImportError(`Import failed: ${formatApiError(error)}`)
    }
  })

  const exportMutation = useMutation({
    mutationFn: exportCountriesCsv,
    onSuccess: (csvText) => {
      const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8' })
      const href = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = href
      link.download = 'countries-export.csv'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(href)
      setImportError(null)
      setSubmitSuccess('Countries CSV export downloaded.')
    },
    onError: (error) => {
      setImportError(`Export failed: ${formatApiError(error)}`)
    }
  })

  const onSelect = (country: CountryRecord) => {
    setMode('edit')
    setSelectedCode(country.code)
    setForm(countryToForm(country))
    setStyleDnaText(formatStyleDna(country.style_dna ?? {}))
    setDrawerOpen(true)
    setSubmitError(null)
    setDeleteError(null)
  }

  const onDuplicate = (country: CountryRecord) => {
    setMode('create')
    setSelectedCode(null)
    setForm({ ...countryToForm(country), code: '', name: `${country.name} Copy` })
    setStyleDnaText(formatStyleDna(country.style_dna ?? {}))
    setDrawerOpen(true)
    setSubmitError(null)
    setSubmitSuccess('Country duplicated into create form. Set a unique 3-letter code before saving.')
  }

  const onOpenCreate = () => {
    setMode('create')
    setSelectedCode(null)
    setForm(EMPTY_FORM)
    setStyleDnaText('{}')
    setDrawerOpen(true)
    setSubmitError(null)
    setDeleteError(null)
  }

  const onCloseDrawer = () => {
    setDrawerOpen(false)
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitError(null)
    setSubmitSuccess(null)

    let parsedStyleDna: Record<string, number>
    try {
      const parsed = JSON.parse(styleDnaText || '{}') as unknown
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        throw new Error('Style DNA must be a JSON object.')
      }

      parsedStyleDna = Object.fromEntries(
        Object.entries(parsed as Record<string, unknown>).map(([key, value]) => {
          if (typeof value !== 'number' || Number.isNaN(value)) {
            throw new Error('Style DNA values must be numeric.')
          }
          return [key, value]
        })
      )
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Style DNA must be valid JSON.')
      return
    }

    const payload: CountryUpsertPayload = {
      ...form,
      code: normalizeCode(form.code),
      name: form.name.trim(),
      region: form.region.trim(),
      flag_asset: form.flag_asset?.trim() ? form.flag_asset.trim() : null,
      court_count: form.court_count === null ? null : Number(form.court_count),
      travel_region: form.travel_region?.trim() || form.region.trim(),
      notes: form.notes?.trim() || null,
      style_dna: parsedStyleDna
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

  const onImportFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const text = await file.text()
    setImportCsvText(text)
    setImportFileName(file.name)
    setImportResult(null)
    setImportError(null)
  }

  const onRunImportDryRun = () => {
    setImportResult(null)
    setImportError(null)
    importMutation.mutate({ csv_text: importCsvText, dry_run: true })
  }

  const onApplyImport = () => {
    setImportResult(null)
    setImportError(null)

    if (!window.confirm('Import replaces the full canonical countries dataset. Continue?')) {
      return
    }

    importMutation.mutate({ csv_text: importCsvText, dry_run: false })
  }

  const busy =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending ||
    importMutation.isPending ||
    exportMutation.isPending

  return (
    <section className="countries-editor-shell">
      <header className="countries-editor-header panel">
        <h2>Countries Editor</h2>
        <p className="subtitle">Author, validate, import, and tune the country database used by FAX talent generation.</p>
        <SummaryPills
          items={[
            { label: 'Dataset status', value: metadataQuery.data?.dataset_status ?? (metadataQuery.isLoading ? 'Loading…' : 'Ready') },
            { label: 'Country count', value: metadataQuery.data?.country_count ?? countries.length },
            { label: 'Source path', value: metadataQuery.data?.source_path ?? 'Not available' },
            { label: 'Validation state', value: importResult ? (importResult.ok ? 'Valid' : 'Needs review') : 'Not validated' }
          ]}
        />
        <p className="status">Current saves affect future generation workflows.</p>
        {metadataQuery.isError ? <p className="error">Metadata unavailable: {formatApiError(metadataQuery.error)}</p> : null}
      </header>

      <section className="countries-toolbar panel">
        <div className="countries-toolbar__left">
          <label>
            Search countries
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Search countries…"
            />
          </label>

          <label>
            Region
            <select value={regionFilter} onChange={(event) => setRegionFilter(event.target.value)}>
              <option value="all">All regions</option>
              {regionOptions
                .filter((item) => item !== 'all')
                .map((region) => (
                  <option key={region} value={region}>
                    {region}
                  </option>
                ))}
            </select>
          </label>

          <label>
            Sort
            <select
              value={`${sortKey}:${sortDirection}`}
              onChange={(event) => {
                const [nextKey, nextDirection] = event.target.value.split(':') as [SortKey, SortDirection]
                setSortKey(nextKey)
                setSortDirection(nextDirection)
              }}
            >
              <option value="name:asc">Name A-Z</option>
              <option value="name:desc">Name Z-A</option>
              <option value="population:desc">Population high-low</option>
              <option value="population:asc">Population low-high</option>
              <option value="region:asc">Region A-Z</option>
              <option value="code:asc">Code A-Z</option>
            </select>
          </label>
        </div>

        <div className="countries-toolbar__right">
          <button type="button" className="button-secondary" onClick={() => exportMutation.mutate()} disabled={busy}>
            {exportMutation.isPending ? 'Exporting…' : 'Export CSV'}
          </button>
          <button type="button" className="button-ghost" onClick={() => setShowImportPanel((current) => !current)}>
            {showImportPanel ? 'Hide Import / Export' : 'Import / Export'}
          </button>
          <button type="button" onClick={onOpenCreate} disabled={busy}>
            + Create Country
          </button>
        </div>
      </section>

      {showImportPanel ? (
        <section className="panel countries-import-panel">
          <h3>Import / Export</h3>

          <label>
            Import countries CSV
            <input type="file" accept=".csv,text/csv" onChange={onImportFileSelected} disabled={busy} />
          </label>

          <label>
            CSV payload
            <textarea
              rows={8}
              value={importCsvText}
              onChange={(event) => setImportCsvText(event.target.value)}
              placeholder="Paste countries CSV here"
            />
          </label>

          {importFileName ? <p className="status">Loaded file: {importFileName}</p> : null}
          <p className="error">Warning: import replaces the entire countries dataset after confirmation.</p>

          <div className="dashboard-actions-row">
            <button type="button" onClick={onRunImportDryRun} disabled={busy || !importCsvText.trim()}>
              {importMutation.isPending ? 'Validating…' : 'Validate import (dry run)'}
            </button>
            <button type="button" className="button-secondary" onClick={onApplyImport} disabled={busy || !importCsvText.trim()}>
              {importMutation.isPending ? 'Importing…' : 'Apply import'}
            </button>
          </div>

          {importError ? <p className="error">{importError}</p> : null}
          {importResult ? (
            <>
              <p className={importResult.ok ? 'status' : 'error'}>
                {importResult.ok
                  ? importResult.dry_run
                    ? 'Dry-run succeeded. You can now apply import.'
                    : 'Import applied to canonical countries dataset.'
                  : 'Import validation failed. No data was written.'}
              </p>

              {importResult.errors.length > 0 ? (
                <ul>
                  {importResult.errors.slice(0, 20).map((item, idx) => (
                    <li
                      key={`${item.row_number ?? 'dataset'}-${item.field ?? 'general'}-${idx}`}
                      className="error"
                    >
                      Row {item.row_number ?? '-'} {item.field ? `(${item.field})` : ''}: {item.message}
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : null}
        </section>
      ) : null}

      <section className="panel countries-table-card">
        <h3>Countries</h3>
        {!countriesQuery.isLoading && !countriesQuery.isError && filteredCountries.length === 0 ? (
          <EmptyState message="No countries match current filters." />
        ) : null}

        <div className="table-scroll">
          <table aria-label="Countries table">
            <thead>
              <tr>
                <th><button type="button" className={`sort-header-button ${sortKey === 'code' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('code')}>Code <span aria-hidden="true">{getSortIndicator('code')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'name' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('name')}>Name <span aria-hidden="true">{getSortIndicator('name')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'region' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('region')}>Region <span aria-hidden="true">{getSortIndicator('region')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'population' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('population')}>Population <span aria-hidden="true">{getSortIndicator('population')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'wealth_support' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('wealth_support')}>Wealth <span aria-hidden="true">{getSortIndicator('wealth_support')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'squash_popularity' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('squash_popularity')}>Popularity <span aria-hidden="true">{getSortIndicator('squash_popularity')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'squash_tradition' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('squash_tradition')}>Tradition <span aria-hidden="true">{getSortIndicator('squash_tradition')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'system_quality' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('system_quality')}>System <span aria-hidden="true">{getSortIndicator('system_quality')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'competition_density' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('competition_density')}>Competition <span aria-hidden="true">{getSortIndicator('competition_density')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'federation_quality' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('federation_quality')}>Federation <span aria-hidden="true">{getSortIndicator('federation_quality')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'court_count' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('court_count')}>Courts <span aria-hidden="true">{getSortIndicator('court_count')}</span></button></th>
                <th><button type="button" className={`sort-header-button ${sortKey === 'travel_region' ? 'sort-header-button-active' : ''}`} onClick={() => onSortHeaderClick('travel_region')}>Travel <span aria-hidden="true">{getSortIndicator('travel_region')}</span></button></th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCountries.map((country) => (
                <tr key={country.code} className={selectedCode === country.code ? 'country-row-selected' : ''}>
                  <td>
                    <span className="country-code-badge">{country.code}</span>
                  </td>
                  <td>{country.name}</td>
                  <td>
                    <span className="region-badge">{country.region}</span>
                  </td>
                  <td className="cell-number" title={country.population.toLocaleString()}>
                    {formatPopulation(country.population)}
                  </td>
                  <td className="cell-number">{country.wealth_support}</td>
                  <td className="cell-number">{country.squash_popularity}</td>
                  <td className="cell-number">{country.squash_tradition}</td>
                  <td className="cell-number">{country.system_quality}</td>
                  <td className="cell-number">{country.competition_density ?? 3}</td>
                  <td className="cell-number">{country.federation_quality ?? country.system_quality}</td>
                  <td className="cell-number">{country.court_count?.toLocaleString() ?? '—'}</td>
                  <td>{country.travel_region ?? country.region}</td>
                  <td>
                    <div className="actions-inline">
                      <Link className="button-link" to={`/admin/world/countries/${country.code}`}>
                        Open
                      </Link>
                      <button type="button" className="button-ghost" onClick={() => onSelect(country)} disabled={busy}>
                        Edit
                      </button>
                      <button type="button" className="button-ghost" onClick={() => onDuplicate(country)} disabled={busy}>
                        Copy
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {drawerOpen ? (
        <>
          <button type="button" className="country-drawer-backdrop" aria-label="Close editor" onClick={onCloseDrawer} />

          <aside className="country-drawer panel">
            <div className="country-drawer-header">
              <h3>{mode === 'create' ? 'Create Country' : `Edit Country: ${selectedCode ?? ''}`}</h3>
              <button type="button" className="button-ghost" onClick={onCloseDrawer} aria-label="Close drawer">
                Close ✕
              </button>
            </div>

            <form onSubmit={onSubmit}>
              <section className="country-drawer-section">
                <h4>Basic</h4>
                <div className="grid">
                  <label>
                    Code (3 letters)
                    <input
                      value={form.code}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, code: normalizeCode(event.target.value) }))
                      }
                      maxLength={3}
                      required
                    />
                  </label>

                  <label>
                    Name
                    <input
                      value={form.name}
                      onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                      required
                    />
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
                    Travel region
                    <input
                      value={form.travel_region ?? ''}
                      onChange={(event) => setForm((current) => ({ ...current, travel_region: event.target.value }))}
                      placeholder="Defaults to region"
                    />
                  </label>
                </div>
              </section>

              <section className="country-drawer-section">
                <h4>Scale</h4>
                <div className="grid">
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
                      onChange={(event) =>
                        setForm((current) => ({ ...current, wealth_support: Number(event.target.value) }))
                      }
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
                      onChange={(event) =>
                        setForm((current) => ({ ...current, squash_popularity: Number(event.target.value) }))
                      }
                      required
                    />
                  </label>
                </div>
              </section>

              <section className="country-drawer-section">
                <h4>Talent Model</h4>
                <div className="grid">
                  <label>
                    Squash tradition (1..5)
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={form.squash_tradition}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, squash_tradition: Number(event.target.value) }))
                      }
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
                      onChange={(event) =>
                        setForm((current) => ({ ...current, system_quality: Number(event.target.value) }))
                      }
                      required
                    />
                  </label>

                  <label>
                    Competition density (1..5)
                    <input
                      type="number"
                      min={1}
                      max={5}
                      step={0.1}
                      value={form.competition_density}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, competition_density: Number(event.target.value) }))
                      }
                      required
                    />
                  </label>

                  <label>
                    Federation quality (1..5)
                    <input
                      type="number"
                      min={1}
                      max={5}
                      step={0.1}
                      value={form.federation_quality}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, federation_quality: Number(event.target.value) }))
                      }
                      required
                    />
                  </label>
                </div>
              </section>

              <section className="country-drawer-section">
                <h4>Infrastructure</h4>
                <div className="grid">
                  <label>
                    Court count (optional)
                    <input
                      type="number"
                      min={0}
                      value={form.court_count ?? ''}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          court_count: event.target.value ? Number(event.target.value) : null
                        }))
                      }
                    />
                  </label>
                </div>
              </section>

              <section className="country-drawer-section">
                <h4>Notes / Style DNA</h4>
                <label>
                  Notes
                  <textarea
                    rows={3}
                    value={form.notes ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                  />
                </label>

                <label>
                  Style DNA (JSON numeric modifiers)
                  <textarea rows={4} value={styleDnaText} onChange={(event) => setStyleDnaText(event.target.value)} />
                </label>
              </section>

              <div className="country-drawer-footer">
                <button type="button" className="button-ghost" onClick={onCloseDrawer}>
                  Cancel
                </button>
                <button type="submit" disabled={busy}>
                  {mode === 'create' ? 'Create Country' : 'Save Country'}
                </button>
                <button
                  type="button"
                  className="button-danger"
                  onClick={onDelete}
                  disabled={busy || mode !== 'edit' || !selectedCode}
                >
                  {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
                </button>
              </div>
            </form>

            {submitSuccess ? <p className="status">{submitSuccess}</p> : null}
            {submitError ? <p className="error">{submitError}</p> : null}
            {deleteError ? <p className="error">{deleteError}</p> : null}
          </aside>
        </>
      ) : null}
    </section>
  )
}

function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.status} ${error.message}`
  }
  return String(error)
}

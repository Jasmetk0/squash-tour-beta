import { useState, type FormEvent } from 'react'

import type {
  WorldPackageCountryV1Detail,
  WorldPackageCountryV1PopulationUpdatePayload,
} from '../api/countryV1'
import {
  countryV1PopulationPayloadFromRows,
  type CountryV1PopulationDraftRow,
} from '../utils/countryV1Population'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

type PopulationFormRow = CountryV1PopulationDraftRow & { id: number }

function initialRows(detail: WorldPackageCountryV1Detail): PopulationFormRow[] {
  const rows = Object.entries(detail.country.population_by_year ?? {})
    .filter((entry): entry is [string, number] => entry[1] != null)
    .sort(([left], [right]) => Number(left) - Number(right))
    .map(([year, population], id) => ({ id, year, population: String(population) }))

  if (!rows.some((row) => row.year === '2020')) {
    rows.push({ id: rows.length, year: '2020', population: '' })
  }
  return rows.sort((left, right) => Number(left.year) - Number(right.year))
}

export function CountryV1PopulationRowsEditor({
  rows,
  onChange,
  onRemove,
  onAdd,
}: {
  rows: PopulationFormRow[]
  onChange: (id: number, key: 'year' | 'population', value: string) => void
  onRemove: (id: number) => void
  onAdd: () => void
}): JSX.Element {
  const sortedRows = [...rows].sort((left, right) => Number(left.year) - Number(right.year))

  return (
    <fieldset>
      <legend>Authored population timeline</legend>
      {sortedRows.map((row) => (
        <div key={row.id}>
          <input
            aria-label={`Population year ${row.id}`}
            type="number"
            min="1955"
            max="2050"
            step="1"
            required
            readOnly={row.year === '2020'}
            value={row.year}
            onChange={(event) => onChange(row.id, 'year', event.target.value)}
          />
          <input
            aria-label={`Population value ${row.year || row.id}`}
            type="number"
            min="1"
            step="1"
            required
            value={row.population}
            onChange={(event) => onChange(row.id, 'population', event.target.value)}
          />
          {row.year !== '2020' && (
            <button type="button" onClick={() => onRemove(row.id)}>Remove</button>
          )}
        </div>
      ))}
      <button type="button" onClick={onAdd}>+ Add authored year</button>
    </fieldset>
  )
}

export function CountryV1PopulationEditForm({
  detail,
  saving,
  error,
  onCancel,
  onSave,
}: {
  detail: WorldPackageCountryV1Detail
  saving: boolean
  error: unknown
  onCancel: () => void
  onSave: (payload: WorldPackageCountryV1PopulationUpdatePayload) => void
}): JSX.Element {
  const [rows, setRows] = useState<PopulationFormRow[]>(() => initialRows(detail))
  const [validationError, setValidationError] = useState('')

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    try {
      const payload = countryV1PopulationPayloadFromRows(rows, detail.package.fingerprint)
      setValidationError('')
      onSave(payload)
    } catch (submitError) {
      setValidationError(submitError instanceof Error ? submitError.message : String(submitError))
    }
  }

  return (
    <SectionCard title="Edit population timeline">
      <form onSubmit={submit}>
        {(validationError || error != null) && (
          <p className="error" role="alert">
            {validationError || formatApiError(error)}
          </p>
        )}
        <CountryV1PopulationRowsEditor
          rows={rows}
          onChange={(id, key, value) => setRows((current) => current.map((row) =>
            row.id === id ? { ...row, [key]: value } : row,
          ))}
          onRemove={(id) => setRows((current) => current.filter((row) => row.id !== id))}
          onAdd={() => setRows((current) => [
            ...current,
            { id: Math.max(-1, ...current.map((row) => row.id)) + 1, year: '', population: '' },
          ])}
        />
        <p>
          <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save population'}</button>{' '}
          <button type="button" disabled={saving} onClick={onCancel}>Cancel</button>
        </p>
      </form>
    </SectionCard>
  )
}

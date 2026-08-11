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
  onPopulationChange,
  onRemove,
}: {
  rows: PopulationFormRow[]
  onPopulationChange: (id: number, value: string) => void
  onRemove: (id: number) => void
}): JSX.Element {
  const sortedRows = [...rows].sort((left, right) => Number(left.year) - Number(right.year))

  return (
    <table aria-label="Edit authored population timeline">
      <thead>
        <tr><th>Year</th><th>Population</th><th>Action</th></tr>
      </thead>
      <tbody>
        {sortedRows.map((row) => (
          <tr key={row.id}>
            <td>{row.year}{row.year === '2020' ? ' · Default year' : ''}</td>
            <td>
              <input
                aria-label={`Population ${row.year}`}
                type="number"
                min="1"
                step="1"
                required
                value={row.population}
                onChange={(event) => onPopulationChange(row.id, event.target.value)}
              />
            </td>
            <td>
              {row.year !== '2020' && (
                <button type="button" onClick={() => onRemove(row.id)}>Remove {row.year}</button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
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
  const [newYear, setNewYear] = useState('')
  const [newPopulation, setNewPopulation] = useState('')
  const [validationError, setValidationError] = useState('')

  function addRow(): void {
    try {
      const candidate = { year: newYear, population: newPopulation }
      countryV1PopulationPayloadFromRows([...rows, candidate])
      setRows((current) => [
        ...current,
        {
          id: Math.max(-1, ...current.map((row) => row.id)) + 1,
          year: newYear.trim(),
          population: newPopulation.trim(),
        },
      ])
      setNewYear('')
      setNewPopulation('')
      setValidationError('')
    } catch (addError) {
      setValidationError(addError instanceof Error ? addError.message : String(addError))
    }
  }

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
          onPopulationChange={(id, value) => setRows((current) => current.map((row) =>
            row.id === id ? { ...row, population: value } : row,
          ))}
          onRemove={(id) => setRows((current) => current.filter((row) => row.id !== id))}
        />

        <fieldset>
          <legend>Add authored population year</legend>
          <label>
            New population year
            <input
              aria-label="New population year"
              type="number"
              min="1955"
              max="2050"
              step="1"
              value={newYear}
              onChange={(event) => setNewYear(event.target.value)}
            />
          </label>
          <label>
            New population value
            <input
              aria-label="New population value"
              type="number"
              min="1"
              step="1"
              value={newPopulation}
              onChange={(event) => setNewPopulation(event.target.value)}
            />
          </label>
          <button type="button" onClick={addRow}>+ Add authored year</button>
        </fieldset>

        <p>
          <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save population'}</button>{' '}
          <button type="button" disabled={saving} onClick={onCancel}>Cancel</button>
        </p>
      </form>
    </SectionCard>
  )
}
